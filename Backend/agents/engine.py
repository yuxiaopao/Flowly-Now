"""
Agent Engine for executing AI Agent tasks.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union

import httpx
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from django.conf import settings
from utils.helpers import safe_json_loads, safe_json_dumps, dict_get, format_datetime
from config.constants import (
    TOOL_TIMEOUT_DEFAULT, HTTP_TOOL_TIMEOUT, OLLAMA_CHAT_TIMEOUT,
    OPENWEATHER_API_URL, WTIRR_API_URL, OLLAMA_MODEL_PREFIXES,
    DEFAULT_OLLAMA_MODEL as DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_CONTEXT_WINDOW,
)

logger = logging.getLogger(__name__)

# Magic numbers as named constants
DEFAULT_NUM_RESULTS = 5
DEFAULT_MAX_LENGTH = 2000
MAX_TOOL_ITERATIONS = 5

DEFAULT_MAX_LENGTH = 2000
DEFAULT_NUM_RESULTS = 5
MAX_TOOL_ITERATIONS = 5


class AgentTool:
    """Base class for Agent tools."""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute the tool. Override in subclasses for custom behavior."""
        return {
            "success": False,
            "error": f"Tool '{self.name}' has no default implementation. Please configure this tool."
        }

    def get_schema(self) -> Dict[str, Any]:
        """Get the tool schema for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class CalculatorTool(AgentTool):
    """Calculator tool for mathematical operations."""

    name = "calculator"
    description = "执行数学计算。输入数学表达式，返回计算结果。"
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，例如: 2 + 2, sin(pi/2), sqrt(16)"
            }
        },
        "required": ["expression"]
    }

    # Allowed math functions for safe evaluation
    ALLOWED_FUNCTIONS = {
        'abs': abs,
        'round': round,
        'min': min,
        'max': max,
        'sum': sum,
        'pow': pow,
        'divmod': divmod,
    }

    # Allowed constants
    ALLOWED_CONSTANTS = {
        'pi': math.pi,
        'e': math.e,
        'tau': math.tau,
        'inf': math.inf,
    }

    def run(self, expression: str) -> Dict[str, Any]:
        """Execute calculation using safe AST-based evaluation."""
        try:
            # Parse the expression into an AST
            try:
                tree = ast.parse(expression, mode='eval')
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"表达式语法错误: {str(e)}",
                    "expression": expression
                }

            # Build the safe namespace with allowed functions and constants
            safe_namespace = {
                k: v for k, v in math.__dict__.items()
                if not k.startswith('_')
            }
            safe_namespace.update(self.ALLOWED_FUNCTIONS)
            safe_namespace.update(self.ALLOWED_CONSTANTS)

            # Compile and evaluate safely
            code = compile(tree, filename='<calc>', mode='eval')
            result = eval(code, {"__builtins__": {}}, safe_namespace)

            # Validate result type
            if not isinstance(result, (int, float, complex)):
                return {
                    "success": False,
                    "error": "表达式结果必须是数值类型",
                    "expression": expression
                }

            # Handle complex numbers by converting to string
            if isinstance(result, complex):
                result = f"{result.real}+{result.imag}j"

            return {
                "success": True,
                "result": result,
                "expression": expression
            }
        except ValueError as e:
            logger.warning(f"Calculator value error for expression '{expression}': {e}")
            return {
                "success": False,
                "error": f"计算错误: {str(e)}",
                "expression": expression
            }
        except Exception as e:
            logger.error(f"Calculator error for expression '{expression}': {e}")
            return {
                "success": False,
                "error": f"计算错误: 无效的表达式",
                "expression": expression
            }


class SearchTool(AgentTool):
    """Web search tool using DuckDuckGo."""

    name = "search"
    description = "搜索网络获取信息。输入搜索关键词，返回搜索结果。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词"
            },
            "num_results": {
                "type": "integer",
                "description": "返回结果数量",
                "default": 5
            }
        },
        "required": ["query"]
    }

    def run(self, query: str, num_results: int = DEFAULT_NUM_RESULTS) -> Dict[str, Any]:
        """Execute search."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", "")
                    })

            return {
                "success": True,
                "query": query,
                "results": results
            }
        except ImportError:
            logger.warning("Search tool: duckduckgo-search not installed")
            return {
                "success": False,
                "error": "搜索功能未安装，请安装 duckduckgo-search",
                "query": query
            }
        except Exception as e:
            logger.error(f"Search tool error for query '{query}': {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }


class WeatherTool(AgentTool):
    """Weather information tool using OpenWeatherMap API."""

    name = "weather"
    description = "获取指定城市的天气信息。使用此工具查询天气、温度、湿度等。"
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市名称（中文或英文），例如：北京、上海、Beijing"
            },
            "country": {
                "type": "string",
                "description": "国家代码（可选），例如：CN、US",
                "default": "CN"
            }
        },
        "required": ["city"]
    }

    def run(self, city: str, country: str = "CN") -> Dict[str, Any]:
        """Get weather for city using OpenWeatherMap API."""
        try:
            api_key = getattr(settings, 'OPENWEATHER_API_KEY', None) or \
                     getattr(settings, 'WEATHER_API_KEY', None)

            if not api_key:
                return self._get_weather_free(city)

            params = {
                "q": f"{city},{country}",
                "appid": api_key,
                "units": "metric",
                "lang": "zh_cn"
            }

            response = httpx.get(OPENWEATHER_API_URL, params=params, timeout=HTTP_TOOL_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                weather_data = data.get("weather", [{}])[0] if data.get("weather") else {}
                return {
                    "success": True,
                    "city": data.get("name", city),
                    "country": data.get("sys", {}).get("country", country),
                    "weather": weather_data.get("description", ""),
                    "temperature": f"{data.get('main', {}).get('temp', 0):.1f}°C",
                    "feels_like": f"{data.get('main', {}).get('feels_like', 0):.1f}°C",
                    "humidity": f"{data.get('main', {}).get('humidity', 0)}%",
                    "pressure": f"{data.get('main', {}).get('pressure', 0)} hPa",
                    "wind_speed": f"{data.get('wind', {}).get('speed', 0)} m/s",
                    "clouds": f"{data.get('clouds', {}).get('all', 0)}%",
                    "sunrise": data.get("sys", {}).get("sunrise", 0),
                    "sunset": data.get("sys", {}).get("sunset", 0)
                }
            elif response.status_code == 401:
                logger.warning(f"Weather API: invalid API key for city '{city}'")
                return {
                    "success": False,
                    "error": "Weather API key无效，请检查配置"
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": f"未找到城市：{city}"
                }
            else:
                logger.error(f"Weather API error: status={response.status_code}, city={city}")
                return {
                    "success": False,
                    "error": f"Weather API error: {response.status_code}"
                }

        except httpx.TimeoutException:
            logger.warning(f"Weather API timeout for city '{city}'")
            return {
                "success": False,
                "error": "Weather API request timeout"
            }
        except httpx.RequestError as e:
            logger.error(f"Weather API network error for city '{city}': {e}")
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Weather tool error for city '{city}': {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _get_weather_free(self, city: str) -> Dict[str, Any]:
        """Get weather using free API (wttr.in) - no API key required."""
        try:
            url = f"{WTIRR_API_URL}/{city}?format=j1"
            response = httpx.get(url, timeout=HTTP_TOOL_TIMEOUT)

            if response.status_code == 200:
                data = response.json()
                current = data.get("current_condition", [{}])[0]

                return {
                    "success": True,
                    "city": city,
                    "weather": current.get("weatherDesc", [{}])[0].get("value", ""),
                    "temperature": f"{current.get('temp_C', '0')}°C",
                    "feels_like": f"{current.get('FeelsLikeC', '0')}°C",
                    "humidity": f"{current.get('humidity', '0')}%",
                    "wind_speed": f"{current.get('windspeedKmph', '0')} km/h",
                    "precipitation": f"{current.get('precipMM', '0')} mm",
                    "visibility": f"{current.get('visibility', '0')} km",
                    "note": "使用免费 wttr.in API，数据可能有延迟"
                }

            logger.warning(f"Free weather API failed for city '{city}': status={response.status_code}")
            return {
                "success": False,
                "error": f"Failed to get weather for {city}"
            }
        except Exception as e:
            logger.error(f"Free weather lookup failed for city '{city}': {e}")
            return {
                "success": False,
                "error": f"Weather lookup failed: {str(e)}"
            }


class WebScraperTool(AgentTool):
    """Web page content scraper."""

    name = "web_scraper"
    description = "抓取网页内容。输入URL，返回页面主要内容。"
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "网页URL"
            },
            "max_length": {
                "type": "integer",
                "description": "最大抓取字符数",
                "default": 2000
            }
        },
        "required": ["url"]
    }

    def run(self, url: str, max_length: int = DEFAULT_MAX_LENGTH) -> Dict[str, Any]:
        """Scrape web page."""
        try:
            from bs4 import BeautifulSoup

            response = httpx.get(url, timeout=HTTP_TOOL_TIMEOUT)
            content = response.text
            soup = BeautifulSoup(content, 'html.parser')

            for tag in soup(["script", "style"]):
                tag.decompose()

            text = soup.get_text(separator=' ', strip=True)
            text = ' '.join(text.split())[:max_length]

            return {
                "success": True,
                "url": url,
                "content": text,
                "title": soup.title.string if soup.title else ""
            }
        except ImportError:
            logger.warning("Web scraper tool: missing dependencies (httpx or beautifulsoup4)")
            return {
                "success": False,
                "error": "网页抓取需要安装 httpx 和 beautifulsoup4",
                "url": url
            }
        except Exception as e:
            logger.error(f"Web scraper error for URL '{url}': {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }


class TextTemplateTool(AgentTool):
    """Text template processing tool."""

    name = "text_template"
    description = "使用模板和变量生成文本。"
    parameters = {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "description": "模板文本，使用 {variable} 占位"
            },
            "variables": {
                "type": "object",
                "description": "变量字典"
            }
        },
        "required": ["template"]
    }

    def run(self, template: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process template."""
        try:
            variables = variables or {}
            result = template.format_map({k: str(v) for k, v in variables.items()})
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class JsonParserTool(AgentTool):
    """JSON parsing and manipulation tool."""

    name = "json_parser"
    description = "解析和操作 JSON 数据。"
    parameters = {
        "type": "object",
        "properties": {
            "json_string": {
                "type": "string",
                "description": "JSON 字符串"
            },
            "operation": {
                "type": "string",
                "description": "操作类型: parse, stringify, get",
                "default": "parse"
            },
            "path": {
                "type": "string",
                "description": "JSONPath 路径 (用于 get 操作)"
            }
        },
        "required": ["json_string"]
    }

    def run(self, json_string: str, operation: str = "parse", path: Optional[str] = None) -> Dict[str, Any]:
        """Parse and manipulate JSON."""
        if operation == "parse":
            data = safe_json_loads(json_string)
            if data is None:
                return {"success": False, "error": "JSON 解析错误"}
            return {"success": True, "data": data}

        elif operation == "stringify":
            data = safe_json_loads(json_string)
            if data is None:
                return {"success": False, "error": "JSON 解析错误"}
            return {"success": True, "result": safe_json_dumps(data)}

        elif operation == "get":
            data = safe_json_loads(json_string)
            if data is None:
                return {"success": False, "error": "JSON 解析错误"}
            value = dict_get(data, path) if path else data
            return {"success": True, "data": value}

        return {"success": False, "error": f"未知操作: {operation}"}


class DateTimeTool(AgentTool):
    """Date and time utility tool."""

    name = "datetime"
    description = "获取当前日期时间或进行日期计算。"
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "操作: now, format, add_days",
                "default": "now"
            },
            "format": {
                "type": "string",
                "description": "日期格式"
            },
            "days": {
                "type": "integer",
                "description": "加减天数"
            }
        }
    }

    def run(self, operation: str = "now", fmt: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Get or manipulate datetime."""
        days = kwargs.get('days') or kwargs.get('input', {}).get('days')
        now = datetime.now()

        if operation == "now":
            return {"success": True, "result": format_datetime(now, fmt or "%Y-%m-%d %H:%M:%S"), "datetime": now.isoformat()}

        elif operation == "format":
            return {"success": True, "result": format_datetime(now, fmt or "%Y-%m-%d")}

        elif operation == "add_days" and days is not None:
            new_date = now + timedelta(days=int(days))
            return {"success": True, "result": format_datetime(new_date, fmt or "%Y-%m-%d"), "datetime": new_date.isoformat()}

        return {"success": False, "error": f"未知操作: {operation}"}


class AgentEngine:
    """Engine for running AI Agents with tools."""

    # Available tools registry
    TOOLS_REGISTRY = {
        "calculator": CalculatorTool,
        "search": SearchTool,
        "weather": WeatherTool,
        "web_scraper": WebScraperTool,
        "text_template": TextTemplateTool,
        "json_parser": JsonParserTool,
        "datetime": DateTimeTool,
    }

    def __init__(
        self,
        system_prompt: str = "",
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tools: Optional[List[str]] = None,
        memory_enabled: bool = True,
        context_window: int = DEFAULT_CONTEXT_WINDOW
    ):
        """Initialize the Agent Engine."""
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or getattr(settings, 'OPENAI_API_KEY', None)
        self.base_url = base_url or getattr(settings, 'OPENAI_BASE_URL', None)
        self.tools = tools or []
        self.memory_enabled = memory_enabled
        self.context_window = context_window

        self._llm = None
        self._tool_instances = {}
        self._history: List[Dict[str, str]] = []

        logger.debug(f"AgentEngine initialized with model={model}, tools={self.tools}")

    def _get_provider(self) -> str:
        """Determine provider from model name or base_url."""
        if self.base_url and "ollama" in self.base_url.lower():
            return "ollama"
        if self.base_url and "azure" in self.base_url.lower():
            return "azure"
        if any(x in self.model.lower() for x in ["gpt-", "chatgpt", "o1-", "o3-", "o4-"]):
            return "openai"
        if any(x in self.model.lower() for x in ["claude", "sonnet", "haiku", "opus"]):
            return "anthropic"
        if any(x in self.model.lower() for x in ["gemini", "gemma"]):
            return "google"
        return "ollama" if not self.api_key else "openai"

    @property
    def llm(self):
        """Lazy initialization of LLM."""
        if self._llm is None:
            provider = self._get_provider()

            if provider == "ollama":
                model_kwargs = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "timeout": OLLAMA_CHAT_TIMEOUT,
                }
                if self.base_url:
                    model_kwargs["base_url"] = self.base_url.rstrip("/")
                self._llm = ChatOllama(**model_kwargs)

            elif provider == "azure":
                model_kwargs = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "api_key": self.api_key,
                    "azure_endpoint": self.base_url,
                    "api_version": "2024-02-01",
                    "timeout": OLLAMA_CHAT_TIMEOUT,
                }
                self._llm = AzureChatOpenAI(**model_kwargs)

            else:
                model_kwargs = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                    "timeout": OLLAMA_CHAT_TIMEOUT,
                }
                if self.api_key:
                    model_kwargs["api_key"] = self.api_key
                if self.base_url and self.base_url != "https://api.openai.com/v1":
                    model_kwargs["base_url"] = self.base_url
                self._llm = ChatOpenAI(**model_kwargs)

        return self._llm

    def get_tool(self, tool_name: str) -> Optional[AgentTool]:
        """Get or create tool instance."""
        if tool_name not in self._tool_instances:
            tool_class = self.TOOLS_REGISTRY.get(tool_name)
            if tool_class:
                self._tool_instances[tool_name] = tool_class()
            else:
                return None
        return self._tool_instances[tool_name]

    def get_tools_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas for all enabled tools."""
        schemas = []
        for tool_name in self.tools:
            tool = self.get_tool(tool_name)
            if tool:
                schemas.append(tool.get_schema())
        return schemas

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given arguments."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            }

        try:
            result = tool.run(**arguments)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def build_messages(self, user_message: str, include_system: bool = True) -> List:
        """Build message list for LLM."""
        messages = []

        # Add system prompt
        if include_system and self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        # Add history context if enabled
        if self.memory_enabled:
            for entry in self._history[-self.context_window:]:
                messages.append(HumanMessage(content=entry.get("input", "")))
                if entry.get("output"):
                    messages.append(AIMessage(content=entry["output"]))

        # Add user message
        messages.append(HumanMessage(content=user_message))

        return messages

    def chat(
        self,
        message: str,
        stream: bool = False,
        callbacks: Optional[List[Callable]] = None
    ) -> Dict[str, Any]:
        """Chat with the agent."""
        callbacks = callbacks or []

        try:
            messages = self.build_messages(message)

            if stream:
                response = self.llm.stream(messages)
                full_response_parts = []
                for chunk in response:
                    content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    full_response_parts.append(content)
                    for callback in callbacks:
                        callback(content)
                response_content = "".join(full_response_parts)
            else:
                response = self.llm.invoke(messages)
                response_content = response.content if isinstance(response.content, str) else str(response.content)

            if self.memory_enabled:
                self._history.append({
                    "input": message,
                    "output": response_content
                })

            return {
                "success": True,
                "response": response_content,
                "tool_calls": None
            }

        except Exception as e:
            logger.error(f"AgentEngine.chat() error: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": None,
                "tool_calls": None
            }

    def stream_chat(self, message: str):
        """Stream chat response as a generator."""
        try:
            messages = self.build_messages(message)
            response = self.llm.stream(messages)

            for chunk in response:
                content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                yield {
                    "type": "content",
                    "content": content
                }

            yield {
                "type": "done",
                "content": ""
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }

    def reset_memory(self):
        """Clear conversation memory."""
        self._history = []


# Factory function to create agent engine from database model
def create_agent_engine(agent_model) -> AgentEngine:
    """Create AgentEngine from Agent model instance."""
    from django.conf import settings as django_settings

    api_key = None
    if agent_model.owner:
        api_key = getattr(agent_model.owner, 'openai_api_key', None)
    if not api_key:
        model_settings = agent_model.settings
        if isinstance(model_settings, dict):
            api_key = model_settings.get('api_key')
    base_url = (agent_model.settings.get('base_url')
                if isinstance(agent_model.settings, dict) else None)

    # Auto-detect Ollama: local models like qwen, llama, smollm, etc.
    model_lower = agent_model.model.lower()
    is_ollama_model = any(x in model_lower for x in OLLAMA_MODEL_PREFIXES)
    if is_ollama_model and not base_url:
        base_url = getattr(django_settings, 'OLLAMA_BASE_URL', None)

    return AgentEngine(
        system_prompt=agent_model.system_prompt,
        model=agent_model.model,
        temperature=agent_model.temperature,
        max_tokens=agent_model.max_tokens,
        api_key=api_key,
        base_url=base_url,
        tools=agent_model.tools or [],
        memory_enabled=agent_model.memory_enabled,
        context_window=agent_model.context_window
    )
