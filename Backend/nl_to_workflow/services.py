"""
NL to Workflow service for generating workflows from natural language.
"""

import json
import re
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Generator, Tuple
from django.conf import settings

from gateway.providers.registry import get_registry, register_default_providers, ProviderRegistry
from .constants import (
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    FALLBACK_MODEL,
    ERROR_MESSAGES,
    VALIDATION_MESSAGES,
    MODIFICATION_KEYWORDS,
    SUGGESTION_EXTRACTION_PATTERNS,
    SUPPORTED_NODE_TYPES,
    SUGGESTION_TEMPLATES,
    MAX_SUGGESTIONS,
)
from .output_parser import WorkflowOutputParser
from .prompts import (
    WorkflowType,
    get_workflow_generation_prompt,
    format_workflow_prompt,
    get_modification_prompt,
)

logger = logging.getLogger(__name__)

# Module-level constant for the workflow generation prompt template
# Using string concatenation instead of .format() to avoid brace escaping issues
FALLBACK_WORKFLOW_TEMPLATE = """
## 工作流结构要求

### 必须包含的节点
1. **start**: 开始节点 - 每个工作流只能有一个开始节点（自动放置在流程起点）
2. **end**: 结束节点 - 标记工作流结束（可以有多个）

### 可选节点类型（根据需求选择）
{node_types}

### 节点配置说明
- **LLM节点**: 必须指定 model（如 llama3, gpt-4, claude-3）
- **条件节点**: 必须配置 conditions 数组，指定判断字段和分支
- **工具节点**: 必须指定 tool_name 和 parameters
- **代码节点**: 必须提供可执行的代码

### 输出格式（必须是有效JSON）
请严格按照以下JSON格式输出，不要包含任何其他内容：

{{
    "name": "工作流名称（简洁、有意义）",
    "description": "工作流功能描述（1-2句话）",
    "nodes": [
        {{
            "id": "唯一ID（如 node_1, node_2...）",
            "type": "节点类型（start/end/input/llm/condition/tool/code/output）",
            "name": "节点显示名称",
            "position": {{"x": 数字, "y": 数字}},
            "config": {{
                // 节点类型相关的配置
                // LLM节点: {{"model": "模型名", "prompt": "提示词", "temperature": 0.7}}
                // 条件节点: {{"conditions": [{{"field": "字段", "operator": "equals", "value": "值"}}]}}
                // 工具节点: {{"tool_name": "工具名", "parameters": {{}}}}
            }}
        }}
    ],
    "edges": [
        {{
            "id": "唯一ID（如 edge_1, edge_2...）",
            "source": "源节点ID",
            "target": "目标节点ID",
            "label": "连线标签（如条件分支名称，可为空字符串）"
        }}
    ]
}}

## 工作流示例

### 示例1：简单顺序工作流（问答机器人）
输入：帮我做一个问答机器人，用户问问题，AI自动回答

输出：
{{
    "name": "智能问答机器人",
    "description": "接收用户问题，AI自动生成回答并返回",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 100}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "接收问题", "position": {{"x": 280, "y": 100}}, "config": {{"input_name": "user_question", "input_type": "text"}}}},
        {{"id": "node_3", "type": "llm", "name": "AI回答", "position": {{"x": 460, "y": 100}}, "config": {{"model": "llama3", "prompt": "你是一个专业的AI助手，请简洁准确地回答用户的问题：{{{{input.user_question}}}}", "temperature": 0.7}}}},
        {{"id": "node_4", "type": "output", "name": "返回结果", "position": {{"x": 640, "y": 100}}, "config": {{"format": "text"}}}},
        {{"id": "node_5", "type": "end", "name": "结束", "position": {{"x": 820, "y": 100}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}}
    ]
}}

### 示例2：条件分支工作流（评论处理）
输入：分析用户评论，如果是投诉就转人工，如果是表扬就回复感谢

输出：
{{
    "name": "评论智能分类处理",
    "description": "分析评论情感，自动分流处理投诉和表扬",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 150}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "接收评论", "position": {{"x": 280, "y": 150}}, "config": {{"input_name": "comment", "input_type": "text"}}}},
        {{"id": "node_3", "type": "llm", "name": "情感分析", "position": {{"x": 460, "y": 150}}, "config": {{"model": "llama3", "prompt": "分析以下评论的情感倾向，返回 positive 或 negative：{{{{input.comment}}}}", "temperature": 0.3}}}},
        {{"id": "node_4", "type": "condition", "name": "判断情感", "position": {{"x": 640, "y": 150}}, "config": {{"conditions": [{{"field": "sentiment", "operator": "equals", "value": "positive"}}]}}}},
        {{"id": "node_5", "type": "tool", "name": "回复感谢", "position": {{"x": 820, "y": 80}}, "config": {{"tool_name": "send_email", "parameters": {{"template": "thanks"}}}}}},
        {{"id": "node_6", "type": "tool", "name": "转人工", "position": {{"x": 820, "y": 220}}, "config": {{"tool_name": "transfer_to_agent", "parameters": {{}}}}}},
        {{"id": "node_7", "type": "output", "name": "处理完成", "position": {{"x": 1000, "y": 150}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1180, "y": 150}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": "表扬"}},
        {{"id": "edge_5", "source": "node_4", "target": "node_6", "label": "投诉"}},
        {{"id": "edge_6", "source": "node_5", "target": "node_7", "label": ""}},
        {{"id": "edge_7", "source": "node_6", "target": "node_7", "label": ""}},
        {{"id": "edge_8", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

### 示例3：API调用工作流（数据获取）
输入：获取天气信息然后发送给用户

输出：
{{
    "name": "天气查询通知",
    "description": "查询指定城市的天气并发送给用户",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 150}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "输入城市", "position": {{"x": 280, "y": 150}}, "config": {{"input_name": "city", "input_type": "text", "placeholder": "请输入城市名称"}}}},
        {{"id": "node_3", "type": "tool", "name": "查询天气API", "position": {{"x": 460, "y": 150}}, "config": {{"tool_name": "http_request", "parameters": {{"url": "https://api.weather.com/v3/wx/conditions/current", "method": "GET", "headers": {{"Authorization": "Bearer xxx"}}}}}}}},
        {{"id": "node_4", "type": "code", "name": "格式化数据", "position": {{"x": 640, "y": 150}}, "config": {{"code": "def format_weather(data):\\n    return f'{{data.city}}今天气温{{data.temp}}度'"}}}}},
        {{"id": "node_5", "type": "output", "name": "发送结果", "position": {{"x": 820, "y": 150}}, "config": {{"format": "text"}}}},
        {{"id": "node_6", "type": "end", "name": "结束", "position": {{"x": 1000, "y": 150}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}},
        {{"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""}}
    ]
}}

### 示例4：并行分支工作流（多任务处理）
输入：同时查询多个数据源并汇总结果

输出：
{{
    "name": "多源数据汇总",
    "description": "并行查询多个数据源并汇总结果",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 200}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "查询参数", "position": {{"x": 280, "y": 200}}, "config": {{"input_name": "query", "input_type": "text"}}}},
        {{"id": "node_3", "type": "tool", "name": "查询数据库", "position": {{"x": 460, "y": 100}}, "config": {{"tool_name": "db_query", "parameters": {{"sql": "SELECT * FROM products"}}}}}},
        {{"id": "node_4", "type": "tool", "name": "查询API", "position": {{"x": 460, "y": 200}}, "config": {{"tool_name": "http_request", "parameters": {{"url": "https://api.example.com/search"}}}}}},
        {{"id": "node_5", "type": "tool", "name": "查询缓存", "position": {{"x": 460, "y": 300}}, "config": {{"tool_name": "redis_get", "parameters": {{"key": "cache_key"}}}}}},
        {{"id": "node_6", "type": "llm", "name": "汇总结果", "position": {{"x": 640, "y": 200}}, "config": {{"model": "llama3", "prompt": "请汇总以下多个来源的数据，提取关键信息：{{{{input.data}}}}", "temperature": 0.3}}}},
        {{"id": "node_7", "type": "output", "name": "输出结果", "position": {{"x": 820, "y": 200}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1000, "y": 200}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": "数据库"}},
        {{"id": "edge_3", "source": "node_2", "target": "node_4", "label": "API"}},
        {{"id": "edge_4", "source": "node_2", "target": "node_5", "label": "缓存"}},
        {{"id": "edge_5", "source": "node_3", "target": "node_6", "label": ""}},
        {{"id": "edge_6", "source": "node_4", "target": "node_6", "label": ""}},
        {{"id": "edge_7", "source": "node_5", "target": "node_6", "label": ""}},
        {{"id": "edge_8", "source": "node_6", "target": "node_7", "label": ""}},
        {{"id": "edge_9", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

### 示例5：循环处理工作流（批量处理）
输入：批量处理一批数据，对每条数据进行分析

输出：
{{
    "name": "批量数据处理",
    "description": "对批量数据进行逐条分析和统计",
    "nodes": [
        {{"id": "node_1", "type": "start", "name": "开始", "position": {{"x": 100, "y": 200}}, "config": {{}}}},
        {{"id": "node_2", "type": "input", "name": "输入数据", "position": {{"x": 280, "y": 200}}, "config": {{"input_name": "data_batch", "input_type": "array"}}}},
        {{"id": "node_3", "type": "code", "name": "初始化计数器", "position": {{"x": 460, "y": 200}}, "config": {{"code": "count = 0\\nresults = []"}}}}},
        {{"id": "node_4", "type": "llm", "name": "分析单条数据", "position": {{"x": 640, "y": 200}}, "config": {{"model": "llama3", "prompt": "分析以下数据并返回关键信息：{{{{current_item}}}}", "temperature": 0.3}}}},
        {{"id": "node_5", "type": "code", "name": "收集结果", "position": {{"x": 820, "y": 200}}, "config": {{"code": "results.append(result)\\ncount += 1"}}}}},
        {{"id": "node_6", "type": "condition", "name": "检查是否完成", "position": {{"x": 1000, "y": 200}}, "config": {{"conditions": [{{"field": "count", "operator": "less_than", "value": "{{{{total_count}}}}"}}]}}}},
        {{"id": "node_7", "type": "output", "name": "输出汇总", "position": {{"x": 1180, "y": 200}}, "config": {{"format": "json"}}}},
        {{"id": "node_8", "type": "end", "name": "结束", "position": {{"x": 1360, "y": 200}}, "config": {{}}}}
    ],
    "edges": [
        {{"id": "edge_1", "source": "node_1", "target": "node_2", "label": ""}},
        {{"id": "edge_2", "source": "node_2", "target": "node_3", "label": ""}},
        {{"id": "edge_3", "source": "node_3", "target": "node_4", "label": ""}},
        {{"id": "edge_4", "source": "node_4", "target": "node_5", "label": ""}},
        {{"id": "edge_5", "source": "node_5", "target": "node_6", "label": ""}},
        {{"id": "edge_6", "source": "node_6", "target": "node_4", "label": "继续"}},
        {{"id": "edge_7", "source": "node_6", "target": "node_7", "label": "完成"}},
        {{"id": "edge_8", "source": "node_7", "target": "node_8", "label": ""}}
    ]
}}

## 注意事项
1. 所有节点必须有唯一ID（建议使用 node_1, node_2, ...）
2. 所有连线必须有唯一ID（建议使用 edge_1, edge_2, ...）
3. 节点的 position 用于画布布局，x 表示水平位置，y 表示垂直位置
4. 使用 {{{{{variable}}}}} 语法引用变量
5. 只输出JSON，不要有其他内容
6. 避免创建循环依赖的工作流，否则会导致执行时无限循环

现在开始生成工作流（只输出JSON）："""


# ---------------------------------------------------------------------------
# Intent Analysis Keywords
# ---------------------------------------------------------------------------

INTENT_KEYWORDS = {
    'create': ['创建', '生成', '做一个', '帮我', '设计', 'build', 'create', 'generate', 'make'],
    'modify': ['修改', '改一下', '把', '改成', '添加', '加上', '再加', '调整', '更新', 'edit', 'modify', 'change', 'update', 'add'],
    'delete': ['删除', '移除', '不要', '去掉', 'delete', 'remove', 'drop'],
}

# Workflow subtype detection keywords
WORKFLOW_SUBTYPE_KEYWORDS = {
    'qa_bot': ['问答', '问答机器人', '客服', 'faq', 'q&a', 'question', 'answer', '问题', '回答', '机器人', 'qa bot'],
    'data_processing': ['数据', 'csv', 'excel', '处理', '清洗', '转换', 'etl', 'data', 'process', '文件处理'],
    'translation': ['翻译', 'translation', '多语言', 'language', '语言转换'],
    'moderation': ['审核', 'moderation', '过滤', 'content', '内容', '敏感', '检查', '合规'],
    'article_generation': ['文章', 'article', '生成文章', '写作', '写文章', '内容生成', '创作'],
    'customer_service': ['客服', 'customer service', 'support', '售后', '服务', '客户'],
    'generic': [],
}

# Retry/regenerate keywords
RETRY_KEYWORDS = ['重试', 'retry', '重新', 'regenerate', '再试', '再来', '重新生成', '再生成', 'try again']


def detect_workflow_subtype(message: str) -> str:
    """
    Detect workflow subtype from message.
    
    Args:
        message: User's message text
        
    Returns:
        Subtype: 'qa_bot', 'data_processing', 'translation', 'moderation', 
                 'article_generation', 'customer_service', or 'generic'
    """
    message_lower = message.lower()
    
    for subtype, keywords in WORKFLOW_SUBTYPE_KEYWORDS.items():
        if subtype == 'generic':
            continue
        for keyword in keywords:
            if keyword in message_lower:
                return subtype
    
    return 'generic'


def is_retry_intent(message: str) -> bool:
    """
    Detect if user wants to retry/regenerate.
    
    Args:
        message: User's message text
        
    Returns:
        True if retry intent detected
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in RETRY_KEYWORDS)


def analyze_intent(message: str) -> Dict[str, Any]:
    """
    Analyze user intent from message with enhanced subtype detection.
    
    Args:
        message: User's message text
        
    Returns:
        Dict with intent type, subtype, and retry flag
    """
    message_lower = message.lower()
    
    # Check for retry intent first
    is_retry = is_retry_intent(message_lower)
    
    # Check for delete intent first (most specific)
    for keyword in INTENT_KEYWORDS['delete']:
        if keyword in message_lower:
            return {
                'intent': 'delete',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    # Check for modify intent
    for keyword in INTENT_KEYWORDS['modify']:
        if keyword in message_lower:
            return {
                'intent': 'modify',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    # Check for create intent
    for keyword in INTENT_KEYWORDS['create']:
        if keyword in message_lower:
            return {
                'intent': 'create',
                'subtype': detect_workflow_subtype(message_lower),
                'is_retry': is_retry
            }
    
    return {
        'intent': 'chat',
        'subtype': detect_workflow_subtype(message_lower),
        'is_retry': is_retry
    }


# ---------------------------------------------------------------------------
# Node Position Calculator
# ---------------------------------------------------------------------------

def calculate_node_positions(node_count: int, start_x: int = 100, start_y: int = 150, 
                             spacing_x: int = 180, spacing_y: int = 120) -> List[Dict[str, int]]:
    """
    Calculate positions for nodes in a grid layout.
    
    Args:
        node_count: Number of nodes to position
        start_x: Starting X position
        start_y: Starting Y position
        spacing_x: Horizontal spacing between nodes
        spacing_y: Vertical spacing between nodes
        
    Returns:
        List of {x, y} position dicts
    """
    positions = []
    for i in range(node_count):
        row = i % 4
        col = i // 4
        positions.append({
            'x': start_x + row * spacing_x,
            'y': start_y + col * spacing_y
        })
    return positions


class NLToWorkflowService:
    """
    Service for converting natural language to workflow.

    Uses the provider registry to dynamically select an LLM provider
    based on the configured model. Supports Ollama (local), OpenAI,
    Anthropic, and any other registered provider.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        user=None,
    ):
        """
        Initialize NL to workflow service.

        Args:
            model: Model to use. If not provided, uses default from registry or settings.
            temperature: Sampling temperature for generation.
            max_tokens: Maximum tokens to generate.
            user: Django user for API key lookups.
        """
        self.model = model or getattr(settings, 'NL_WORKFLOW_MODEL', None)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user = user
        self._registry: Optional[ProviderRegistry] = None
        self._llm = None

    def __repr__(self):
        model = self._resolve_model()
        return f"<NLToWorkflowService model={model} temp={self.temperature}>"

    @property
    def registry(self) -> ProviderRegistry:
        """Lazy-initialized provider registry."""
        if self._registry is None:
            self._registry = get_registry()
            if not self._registry.get_all():
                register_default_providers()
        return self._registry

    def _get_provider_for_model(self, model: str):
        """Find the appropriate provider for a given model."""
        for name in self.registry.get_all():
            provider = self.registry.get(name)
            if provider and provider.supports_model(model):
                return provider
        return None

    def _resolve_model(self) -> Optional[str]:
        """
        Resolve which model to use.
        Priority: instance model > settings default > registry default.
        """
        if self.model:
            return self.model

        default_model = getattr(settings, 'NL_WORKFLOW_MODEL', None)
        if default_model:
            return default_model

        available = self.registry.list_models()
        if available:
            return available[0].model_id

        return None

    @property
    def llm(self):
        """Get the provider for the configured model."""
        if self._llm is not None:
            return self._llm

        model = self._resolve_model()
        if not model:
            logger.warning("No LLM model available for NL-to-workflow generation")
            return None

        provider = self._get_provider_for_model(model)
        if provider:
            self._llm = provider
            return provider

        provider_name = self.registry.find_provider_for_model(model)
        if provider_name:
            provider = self.registry.get(provider_name)
            self._llm = provider
            return provider

        return None

    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Call the LLM through the provider registry.
        Falls back to mock response in DEBUG mode when no provider is available.

        Returns a dict with 'content' (response text) or 'error'.
        """
        provider = self.llm
        model = self._resolve_model()

        if not provider:
            # Check if we're in debug mode and should use mock responses
            debug_mode = getattr(settings, 'DEBUG', False)
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = debug_mode or nl_debug_mode

            if use_mock:
                # Extract user description from messages
                user_description = ''
                for msg in messages:
                    if msg.get('role') == 'user':
                        user_description = msg.get('content', '')
                        break

                from .constants import get_mock_workflow
                mock_workflow = get_mock_workflow(user_description)
                return {'content': json.dumps(mock_workflow)}

            return {
                'error': ERROR_MESSAGES['no_provider']
            }

        try:
            response = provider.chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            if response.error:
                return {'error': f"Provider error: {response.error}"}
            return {'content': response.content}
        except Exception as e:
            logger.exception(f"LLM call failed: {e}")
            return {'error': ERROR_MESSAGES['llm_call_failed'].format(error=str(e))}

    def _stream_llm(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """Stream LLM response through the provider registry."""
        provider = self.llm
        model = self._resolve_model()

        if not provider:
            debug_mode = getattr(settings, 'DEBUG', False)
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = debug_mode or nl_debug_mode

            if use_mock:
                from .constants import get_mock_workflow
                user_description = ''
                for msg in messages:
                    if msg.get('role') == 'user':
                        user_description = msg.get('content', '')
                        break
                mock_workflow = get_mock_workflow(user_description)
                yield json.dumps({'type': 'content', 'content': json.dumps(mock_workflow)})
                return

            yield json.dumps({'error': ERROR_MESSAGES['no_provider']})
            return

        try:
            for chunk in provider.stream_chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                yield json.dumps(chunk)
        except Exception as e:
            logger.exception(f"LLM stream failed: {e}")
            yield json.dumps({'error': str(e)})

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all models available for NL-to-workflow generation."""
        models = []
        for m in self.registry.list_models():
            if m.model_type == 'chat':
                models.append({
                    'model_id': m.model_id,
                    'name': m.name,
                    'provider': m.provider,
                    'max_tokens': m.max_tokens,
                    'supports_streaming': m.supports_streaming,
                    'context_window': m.context_window,
                })
        return models

    def generate_workflow(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None,
        include_validation: bool = True
    ) -> Dict[str, Any]:
        """
        Generate workflow from natural language description.

        Args:
            description: User's natural language description
            context: Additional context for generation
            include_validation: Whether to validate the generated workflow

        Returns:
            Dict containing workflow structure
        """
        result = self._call_llm(
            [{"role": "user", "content": self._create_workflow_generation_prompt(description, context)}]
        )

        if 'error' in result:
            return {
                'error': result['error'],
                'name': 'Generated Workflow',
                'description': description,
                'nodes': [],
                'edges': []
            }

        # Use structured output parser for type-safe parsing
        workflow_data = WorkflowOutputParser.parse_workflow(result['content'])

        if 'error' not in workflow_data and include_validation:
            workflow_data = WorkflowOutputParser.validate_workflow(workflow_data)

        return workflow_data

    def generate_workflow_streaming(
        self,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        Generate workflow with streaming output and progress updates.
        
        Yields JSON-serialized progress messages and final workflow.
        
        Args:
            description: User's natural language description
            context: Additional context for generation
            
        Yields:
            JSON-serialized dicts with progress updates and final workflow
        """
        # Initial progress
        yield json.dumps({
            'type': 'progress',
            'stage': 'starting',
            'message': '正在理解您的需求...',
            'progress': 10
        })
        
        messages = [
            {"role": "user", "content": self._create_workflow_generation_prompt(description, context)}
        ]
        
        # Yield parsing progress
        yield json.dumps({
            'type': 'progress',
            'stage': 'generating',
            'message': '正在生成工作流结构...',
            'progress': 30
        })
        
        provider = self.llm
        model = self._resolve_model()
        
        if not provider:
            # Use mock mode
            debug_mode = getattr(settings, 'DEBUG', False)
            nl_debug_mode = getattr(settings, 'NL_WORKFLOW_USE_MOCK', False)
            use_mock = debug_mode or nl_debug_mode
            
            if use_mock:
                from .constants import get_mock_workflow
                mock_workflow = get_mock_workflow(description)
                mock_workflow = self._normalize_workflow(mock_workflow)
                mock_workflow = self._validate_workflow(mock_workflow)
                
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'validating',
                    'message': '正在验证工作流结构...',
                    'progress': 70
                })
                
                yield json.dumps({
                    'type': 'progress',
                    'stage': 'complete',
                    'message': '工作流生成完成',
                    'progress': 100
                })
                
                yield json.dumps({
                    'type': 'workflow',
                    'workflow': mock_workflow
                })
                return
            
            yield json.dumps({
                'type': 'error',
                'error': ERROR_MESSAGES['no_provider']
            })
            return
        
        try:
            full_content = ""
            
            yield json.dumps({
                'type': 'progress',
                'stage': 'generating',
                'message': '正在生成节点和连线...',
                'progress': 40
            })
            
            for chunk in provider.stream_chat(
                messages=messages,
                model=model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            ):
                chunk_data = chunk if isinstance(chunk, dict) else json.loads(chunk) if isinstance(chunk, str) else {}
                
                if chunk_data.get('type') == 'error':
                    yield json.dumps(chunk_data)
                    return
                
                content = chunk_data.get('content', '')
                if content:
                    full_content += content
                    yield json.dumps({
                        'type': 'token',
                        'content': content,
                        'progress': 50
                    })
                
                if chunk_data.get('type') == 'done':
                    yield json.dumps({
                        'type': 'progress',
                        'stage': 'parsing',
                        'message': '正在解析工作流...',
                        'progress': 60
                    })
            
            # Parse and validate using structured output parser
            workflow_data = WorkflowOutputParser.parse_workflow(full_content)
            
            if 'error' in workflow_data:
                yield json.dumps({
                    'type': 'error',
                    'error': workflow_data['error']
                })
                return
            
            yield json.dumps({
                'type': 'progress',
                'stage': 'validating',
                'message': '正在验证工作流...',
                'progress': 80
            })
            
            workflow_data = WorkflowOutputParser.validate_workflow(workflow_data)
            
            yield json.dumps({
                'type': 'progress',
                'stage': 'complete',
                'message': '工作流生成完成',
                'progress': 100
            })
            
            yield json.dumps({
                'type': 'workflow',
                'workflow': workflow_data
            })
            
        except Exception as e:
            logger.exception(f"Streaming workflow generation failed: {e}")
            yield json.dumps({
                'type': 'error',
                'error': str(e)
            })

    def continue_conversation(
        self,
        session_messages: List[Dict],
        user_message: str,
        current_workflow: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Continue a conversation to refine or modify the workflow.
        
        Analyzes user intent and handles:
        - modify: Updates existing workflow based on feedback
        - delete: Removes nodes/edges from workflow
        - add: Adds new nodes/edges to workflow
        - chat: General conversation response
        
        Args:
            session_messages: Previous conversation messages
            user_message: Current user message
            current_workflow: Current workflow dict if available
            
        Returns:
            Dict with message, suggestions, workflow updates, and changes
        """
        intent_info = analyze_intent(user_message)
        intent = intent_info.get('intent', 'chat')
        
        logger.info(f"Continue conversation - intent: {intent}, details: {intent_info}")
        
        if intent == 'modify' and current_workflow:
            # Handle workflow modification
            modification_prompt = self._create_modification_prompt(current_workflow, user_message)
            result = self._call_llm([{"role": "user", "content": modification_prompt}])

            if 'error' in result:
                return {
                    "message": f"修改失败: {result['error']}",
                    "suggestions": [],
                    "workflow": current_workflow,
                    "intent": intent
                }

            # Use structured output parser for modification
            updated_workflow = WorkflowOutputParser.parse_modification(
                result['content'],
                current_workflow
            )

            if 'error' in updated_workflow:
                return {
                    "message": f"解析修改结果失败: {updated_workflow['error']}",
                    "suggestions": [],
                    "workflow": current_workflow,
                    "intent": intent
                }
            
            updated_workflow = self._validate_workflow(updated_workflow)
            
            return {
                "message": "已根据您的要求修改工作流",
                "suggestions": self._generate_suggestions(updated_workflow),
                "workflow": updated_workflow,
                "changes": self._describe_changes(current_workflow, updated_workflow),
                "intent": intent
            }
        
        elif intent == 'delete' and current_workflow:
            # Handle node/edge deletion
            return self._handle_delete_intent(user_message, current_workflow)
        
        elif intent == 'create':
            # Handle new workflow creation request
            # Extract description from message
            description = self._extract_workflow_description(user_message)
            if description:
                return self._handle_create_intent(description)
            else:
                return {
                    "message": "请提供您想要创建的工作流描述",
                    "suggestions": ["描述您想要的工作流功能"],
                    "workflow": current_workflow,
                    "intent": intent
                }
        
        else:
            # General conversation (chat)
            messages = session_messages + [{"role": "user", "content": user_message}]
            result = self._call_llm(messages)

            if 'error' in result:
                return {
                    "message": f"处理失败: {result['error']}",
                    "suggestions": [],
                    "intent": 'error'
                }

            return {
                "message": result['content'],
                "suggestions": self._extract_suggestions(result['content']),
                "workflow": current_workflow,
                "intent": intent
            }

    def _extract_workflow_description(self, message: str) -> str:
        """
        Extract workflow description from creation message.
        
        Attempts to find the actual workflow description in a creation request.
        """
        # Remove common prefixes
        prefixes_to_remove = [
            '创建一个工作流：', '创建一个：', '做一个工作流：',
            '生成一个工作流：', '帮我做一个：', '帮我创建一个：',
            'create a workflow:', '生成一个：', '做一个：'
        ]
        
        description = message
        for prefix in prefixes_to_remove:
            if prefix in description.lower():
                idx = description.lower().find(prefix)
                description = description[idx + len(prefix):].strip()
                break
        
        # If description is too short, return empty
        if len(description) < 5:
            return ""
        
        return description

    def _handle_delete_intent(self, user_message: str, current_workflow: Dict) -> Dict[str, Any]:
        """
        Handle delete intent - remove nodes or edges from workflow.
        
        Args:
            user_message: User's delete request
            current_workflow: Current workflow dict
            
        Returns:
            Dict with updated workflow and changes
        """
        message_lower = user_message.lower()
        
        # Try to identify what to delete
        nodes = current_workflow.get('nodes', [])
        edges = current_workflow.get('edges', [])
        
        # Look for node type mentions
        node_to_delete = None
        for node in nodes:
            if node.get('type', '').lower() in message_lower:
                node_to_delete = node.get('id')
                break
            if node.get('name', '').lower() in message_lower:
                node_to_delete = node.get('id')
                break
        
        if node_to_delete:
            # Remove node and its connected edges
            new_nodes = [n for n in nodes if n.get('id') != node_to_delete]
            new_edges = [
                e for e in edges 
                if e.get('source') != node_to_delete and e.get('target') != node_to_delete
            ]
            
            updated_workflow = {
                **current_workflow,
                'nodes': new_nodes,
                'edges': new_edges
            }
            
            return {
                "message": f"已删除节点",
                "suggestions": self._generate_suggestions(updated_workflow),
                "workflow": updated_workflow,
                "changes": [f"删除了节点 {node_to_delete}"],
                "intent": "delete"
            }
        
        # No specific node found to delete
        return {
            "message": "没有找到要删除的节点。请具体说明要删除哪个节点。",
            "suggestions": ["删除某个特定类型的节点", "删除整个工作流重新开始"],
            "workflow": current_workflow,
            "intent": "delete"
        }

    def _handle_create_intent(self, description: str) -> Dict[str, Any]:
        """
        Handle new workflow creation intent.
        
        Args:
            description: Workflow description
            
        Returns:
            Dict with new workflow
        """
        try:
            workflow_data = self.generate_workflow(description)
            
            if 'error' in workflow_data:
                return {
                    "message": f"创建工作流失败: {workflow_data['error']}",
                    "suggestions": [],
                    "workflow": None,
                    "intent": "create"
                }
            
            return {
                "message": f"已创建新的工作流: {workflow_data.get('name', '未命名')}",
                "suggestions": self._generate_suggestions(workflow_data),
                "workflow": workflow_data,
                "changes": ["创建了新的工作流"],
                "intent": "create"
            }
        except Exception as e:
            logger.exception(f"Create intent failed: {e}")
            return {
                "message": f"创建工作流时出错: {str(e)}",
                "suggestions": [],
                "workflow": None,
                "intent": "create"
            }

    def _create_workflow_generation_prompt(self, description: str, context: Optional[Dict] = None) -> str:
        """Create comprehensive prompt for workflow generation with diverse few-shot examples."""
        # Use the new prompts module for structured prompt generation
        intent_info = analyze_intent(description)
        workflow_type = WorkflowType(intent_info.get('subtype', 'generic'))

        prompt_data = format_workflow_prompt(
            description=description,
            workflow_type=workflow_type,
            context=context
        )

        # Combine system and user messages
        return f"{prompt_data['system']}\n\n{prompt_data['user']}"

    def _create_modification_prompt(self, current_workflow: Dict, user_feedback: str) -> str:
        """Create prompt for modifying existing workflow."""
        # Use the new prompts module
        intent_info = analyze_intent(user_feedback)
        if intent_info.get('intent') == 'delete':
            prompt_data = get_modification_prompt(
                current_workflow,
                user_feedback,
                modification_type='delete'
            )
        else:
            prompt_data = get_modification_prompt(
                current_workflow,
                user_feedback,
                modification_type='modify'
            )

        return f"{prompt_data['system']}\n\n{prompt_data['user']}"

    def _analyze_intent(self, user_message: str) -> str:
        """Analyze user intent from message using constants."""
        return analyze_intent(user_message)

    def _get_intent_details(self, user_message: str) -> Dict[str, Any]:
        """
        Get detailed intent analysis including modification targets.
        
        Returns:
            Dict with intent type and extracted targets
        """
        message_lower = user_message.lower()
        intent = analyze_intent(user_message)
        
        result = {
            'intent': intent,
            'message': user_message,
            'targets': []
        }
        
        if intent == 'modify':
            # Extract modification targets (node names, etc.)
            # Look for quoted text or specific patterns
            patterns = [
                r'把(.+?)改成',
                r'把(.+?)改为',
                r'把(.+?)改成',
                r'添加(.+?)节点',
                r'添加(.+?)连接',
                r'删除(.+?)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                result['targets'].extend(matches)
        
        elif intent == 'delete':
            # Extract things to delete
            patterns = [
                r'删除(.+?)节点',
                r'删除(.+?)连接',
                r'删除(.+?)',
                r'移除(.+?)',
                r'不要(.+?)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, message_lower)
                result['targets'].extend(matches)
        
        return result

    def _parse_workflow_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to workflow structure."""
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                workflow_data = json.loads(json_match.group())
                return self._normalize_workflow(workflow_data)
            except json.JSONDecodeError:
                pass

        code_block_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', response)
        if code_block_match:
            try:
                workflow_data = json.loads(code_block_match.group(1))
                return self._normalize_workflow(workflow_data)
            except json.JSONDecodeError:
                pass

        return {
            "error": "无法解析工作流描述",
            "raw_response": response[:500] if len(response) > 500 else response
        }

    def _normalize_workflow(self, workflow: Dict) -> Dict[str, Any]:
        """Normalize workflow structure with required fields."""
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])

        node_id_map = {}
        for i, node in enumerate(nodes):
            if 'id' not in node:
                node['id'] = f'node_{i + 1}'
            node_id_map[node['id']] = node['id']

        normalized_edges = []
        for i, edge in enumerate(edges):
            normalized_edge = {
                'id': edge.get('id', f'edge_{i + 1}'),
                'source': node_id_map.get(edge.get('source'), edge.get('source')),
                'target': node_id_map.get(edge.get('target'), edge.get('target')),
                'label': edge.get('label', '')
            }
            normalized_edges.append(normalized_edge)

        return {
            'name': workflow.get('name', 'Generated Workflow'),
            'description': workflow.get('description', ''),
            'nodes': [
                {
                    'id': node.get('id'),
                    'type': node.get('type', 'llm'),
                    'name': node.get('name', 'Node'),
                    'position': node.get('position', {'x': 0, 'y': 0}),
                    'config': node.get('config', {})
                }
                for node in nodes
            ],
            'edges': normalized_edges
        }

    def _has_cycle_detection(self, workflow: Dict) -> Tuple[bool, List[str]]:
        """
        Detect cycles in workflow graph using DFS algorithm.
        
        Args:
            workflow: Workflow dict with nodes and edges
            
        Returns:
            Tuple of (has_cycle: bool, cycle_path: list of node IDs)
        """
        nodes = workflow.get('nodes', [])
        edges = workflow.get('edges', [])
        
        # Build adjacency list
        graph = {}
        for node in nodes:
            graph[node.get('id')] = []
        
        for edge in edges:
            source = edge.get('source')
            target = edge.get('target')
            if source and target and source in graph and target in graph:
                graph[source].append(target)
        
        # DFS-based cycle detection
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> List[str]:
            """DFS traversal that returns cycle path if found."""
            if node_id not in graph:
                return []
            
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle - extract the cycle path
                    cycle_start_idx = path.index(neighbor)
                    return path[cycle_start_idx:] + [neighbor]
            
            path.pop()
            rec_stack.remove(node_id)
            return []
        
        # Check all nodes (in case graph is disconnected)
        for node in nodes:
            node_id = node.get('id')
            if node_id and node_id not in visited:
                cycle = dfs(node_id)
                if cycle:
                    return True, cycle
        
        return False, []
    
    def _estimate_workflow_cost(self, workflow: Dict) -> float:
        """
        Estimate workflow execution cost based on node types and count.
        
        Cost factors (in arbitrary units):
        - LLM nodes: high cost (depends on model)
        - HTTP/tool nodes: medium cost
        - Code nodes: medium cost
        - Other nodes: low cost
        
        Args:
            workflow: Workflow dict with nodes
            
        Returns:
            Estimated cost (float)
        """
        nodes = workflow.get('nodes', [])
        
        # Cost weights per node type
        COST_WEIGHTS = {
            'llm': 10.0,        # LLM calls are expensive
            'prompt': 5.0,       # Prompt processing
            'http': 3.0,         # HTTP requests
            'tool': 3.0,         # External tool calls
            'code': 2.0,         # Code execution
            'email': 2.0,       # Email sending
            'webhook': 2.0,     # Webhook calls
            'condition': 0.5,   # Simple condition check
            'input': 0.5,       # Input processing
            'output': 0.5,      # Output processing
            'start': 0.1,       # Minimal cost
            'end': 0.1,          # Minimal cost
        }
        
        total_cost = 0.0
        node_type_counts = {}
        
        for node in nodes:
            node_type = node.get('type', 'unknown')
            cost = COST_WEIGHTS.get(node_type, 1.0)
            
            # Adjust cost based on configuration
            config = node.get('config', {})
            
            # LLM nodes with larger context window cost more
            if node_type == 'llm':
                model = config.get('model', '')
                if 'gpt-4' in model.lower() or 'claude' in model.lower():
                    cost *= 2.0  # Premium models cost more
                elif 'gpt-3.5' in model.lower():
                    cost *= 0.5  # Cheaper models
                    
            # HTTP nodes with more parameters might be more expensive
            if node_type in ('http', 'tool'):
                params = config.get('parameters', {})
                cost += len(params) * 0.1
            
            total_cost += cost
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        
        # Add edge cost (communication overhead)
        edges = workflow.get('edges', [])
        total_cost += len(edges) * 0.1
        
        # Complexity multiplier based on node count
        node_count = len(nodes)
        if node_count > 20:
            total_cost *= 1.5  # Complex workflows have overhead
        elif node_count > 10:
            total_cost *= 1.2
        
        return round(total_cost, 2)
    
    def _generate_workflow_name(self, description: str) -> str:
        """
        Auto-generate workflow name from description.
        
        Args:
            description: User's workflow description
            
        Returns:
            Generated workflow name
        """
        # Common prefixes
        prefixes = ['自动化', '智能', '高效', '快捷', 'AI', '智能']
        
        # Extract key action and subject from description
        desc_lower = description.lower()
        
        # Action verbs mapping
        action_map = {
            '翻译': '翻译',
            '处理': '处理',
            '审核': '审核',
            '生成': '生成',
            '分析': '分析',
            '转换': '转换',
            '提取': '提取',
            '分类': '分类',
            '通知': '通知',
            '发送': '发送',
            '收集': '收集',
        }
        
        # Subject words mapping
        subject_map = {
            '数据': '数据',
            '文本': '文本',
            '文章': '文章',
            '图片': '图片',
            '邮件': '邮件',
            '文件': '文件',
            '评论': '评论',
            '内容': '内容',
            '用户': '用户',
            '订单': '订单',
        }
        
        # Find action and subject
        action = '工作流'
        subject = ''
        
        for keyword, label in action_map.items():
            if keyword in desc_lower:
                action = label
                break
        
        for keyword, label in subject_map.items():
            if keyword in desc_lower:
                subject = label
                break
        
        # If no subject found, try to extract from description
        if not subject:
            words = description.replace('，', ' ').replace(',', ' ').split()
            for word in words:
                if len(word) >= 2 and len(word) <= 4:
                    subject = word
                    break
        
        # Combine into name
        import random
        prefix = random.choice(prefixes)
        
        if subject:
            return f"{prefix}{action}{subject}"
        else:
            return f"{prefix}{action}"
    
    def _validate_workflow(self, workflow: Dict) -> Dict[str, Any]:
        """Validate workflow structure with enhanced checks including cycle detection."""
        errors = []
        warnings = []

        if not workflow.get('name'):
            # Auto-generate name if missing
            description = workflow.get('description', '')
            if description:
                workflow['name'] = self._generate_workflow_name(description)
            else:
                errors.append(VALIDATION_MESSAGES['missing_name'])

        if not workflow.get('nodes'):
            errors.append(VALIDATION_MESSAGES['missing_nodes'])

        node_types = [n.get('type') for n in workflow.get('nodes', [])]

        if 'start' not in node_types:
            warnings.append(VALIDATION_MESSAGES['missing_start'])

        if 'end' not in node_types:
            warnings.append(VALIDATION_MESSAGES['missing_end'])

        start_count = node_types.count('start')
        if start_count > 1:
            errors.append(VALIDATION_MESSAGES['multiple_starts'].format(count=start_count))

        connected_nodes = set()
        for edge in workflow.get('edges', []):
            if edge.get('source'):
                connected_nodes.add(edge.get('source'))
            if edge.get('target'):
                connected_nodes.add(edge.get('target'))

        node_ids = set(n.get('id') for n in workflow.get('nodes', []))
        disconnected = node_ids - connected_nodes - {'start'}

        if disconnected:
            warnings.append(VALIDATION_MESSAGES['disconnected_nodes'].format(
                nodes=', '.join(list(disconnected)[:3])
            ))
        
        # DAG Cycle Detection
        has_cycle, cycle_path = self._has_cycle_detection(workflow)
        if has_cycle:
            cycle_str = ' -> '.join(cycle_path[:6])  # Show first 6 nodes in cycle
            if len(cycle_path) > 6:
                cycle_str += ' -> ...'
            errors.append(f"工作流存在循环依赖: {cycle_str}。这会导致执行时无限循环，请修改工作流结构。")

        # Estimate workflow cost
        estimated_cost = self._estimate_workflow_cost(workflow)

        # Auto-calculate node positions if not provided
        nodes = workflow.get('nodes', [])
        needs_position_calc = any(
            n.get('position') is None or 
            n.get('position', {}).get('x') is None or
            n.get('position', {}).get('y') is None
            for n in nodes
        )
        
        if needs_position_calc:
            positions = calculate_node_positions(len(nodes))
            for i, node in enumerate(nodes):
                if node.get('position') is None:
                    node['position'] = positions[i]
                elif node['position'].get('x') is None or node['position'].get('y') is None:
                    node['position'] = positions[i]

        return {
            **workflow,
            'estimated_cost': estimated_cost,
            'validation': {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
        }

    def _describe_changes(self, old_workflow: Dict, new_workflow: Dict) -> List[str]:
        """Describe what changed between workflows."""
        changes = []

        if old_workflow.get('name') != new_workflow.get('name'):
            changes.append(f"名称: {old_workflow.get('name')} -> {new_workflow.get('name')}")

        old_node_ids = set(n.get('id') for n in old_workflow.get('nodes', []))
        new_node_ids = set(n.get('id') for n in new_workflow.get('nodes', []))

        added = new_node_ids - old_node_ids
        removed = old_node_ids - new_node_ids

        if added:
            changes.append(f"添加了 {len(added)} 个节点")
        if removed:
            changes.append(f"删除了 {len(removed)} 个节点")

        return changes

    def _generate_suggestions(self, workflow: Dict) -> List[str]:
        """Generate follow-up suggestions based on workflow using constants."""
        node_types = [n.get('type') for n in workflow.get('nodes', [])]

        suggestions = []
        if 'llm' not in node_types:
            suggestions.append('添加 AI 处理节点')
        if 'condition' not in node_types:
            suggestions.append('添加条件分支')
        if 'tool' not in node_types:
            suggestions.append('添加外部工具调用')

        suggestions.extend(SUGGESTION_TEMPLATES['general'])
        return suggestions[:MAX_SUGGESTIONS]

    def _generate_suggestions_from_description(self, description: str) -> List[str]:
        """Generate initial suggestions from description using constants."""
        suggestions = list(SUGGESTION_TEMPLATES['initial'])

        desc_lower = description.lower()

        if any(k in desc_lower for k in ['ai', 'llm', 'gpt', 'chat', '模型']):
            suggestions.insert(0, '使用 AI 模型处理')
        if any(k in desc_lower for k in ['判断', '条件', 'if', 'branch', '分流']):
            suggestions.insert(0, '添加条件分支')
        if any(k in desc_lower for k in ['api', 'http', '请求', '调用']):
            suggestions.insert(0, '添加外部 API 调用')
        if any(k in desc_lower for k in ['输入', 'form', '表单', '用户']):
            suggestions.insert(0, '添加用户输入节点')

        return suggestions[:MAX_SUGGESTIONS]

    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract follow-up suggestions from response using constants."""
        suggestions = []

        for pattern in SUGGESTION_EXTRACTION_PATTERNS:
            matches = re.findall(pattern, text)
            suggestions.extend(matches[:2])

        return suggestions[:MAX_SUGGESTIONS]


def get_nl_service(model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 4096, user=None) -> NLToWorkflowService:
    """Factory function to create an NL service with specific configuration."""
    return NLToWorkflowService(model=model, temperature=temperature, max_tokens=max_tokens, user=user)


def generate_suggestions(description: str) -> List[str]:
    """
    Standalone function to generate workflow suggestions from description.
    Used by Celery tasks and external callers.
    """
    service = NLToWorkflowService()
    return service._generate_suggestions_from_description(description)


nl_to_workflow_service = NLToWorkflowService()
