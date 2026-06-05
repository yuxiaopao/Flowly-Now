"""
Tool executor service for running workflow tools.
Provides enhanced tool execution with retry, caching, and monitoring.
"""

import json
import time
import logging
import hashlib
from typing import Any, Dict, Optional
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executor for workflow tools.
    
    Supports built-in tools, API tools, and script tools with:
    - Retry with exponential backoff
    - Result caching
    - Usage statistics tracking
    - Custom handlers
    """

    def __init__(self, tool):
        """
        Initialize tool executor.
        
        Args:
            tool: Tool model instance
        """
        self.tool = tool
        self._cache_enabled = getattr(tool, 'cache_enabled', False)
        self._cache_ttl = getattr(tool, 'cache_ttl_seconds', 300)

    def execute(self, input_data: Dict[str, Any], use_cache: bool = True) -> Dict[str, Any]:
        """
        Execute the tool with given input.
        
        Args:
            input_data: Input data for the tool
            use_cache: Whether to use cached results
            
        Returns:
            Tool execution result
        """
        start_time = time.time()
        
        cache_key = None
        if use_cache and self._cache_enabled:
            cache_key = self._generate_cache_key(input_data)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                execution_time = int((time.time() - start_time) * 1000)
                self._update_stats(success=True, execution_time=execution_time, cache_hit=True)
                return {
                    'success': True,
                    'result': cached_result,
                    'execution_time_ms': execution_time,
                    'cache_hit': True
                }

        retry_count = 0
        max_retries = self.tool.retry_policy.get('max_retries', 0) if hasattr(self.tool, 'retry_policy') else 0
        
        last_error = None
        while retry_count <= max_retries:
            try:
                if self.tool.tool_type == 'builtin':
                    result = self._execute_builtin(input_data)
                elif self.tool.tool_type == 'api':
                    result = self._execute_api(input_data)
                elif self.tool.tool_type == 'script':
                    result = self._execute_script(input_data)
                else:
                    result = self._execute_custom(input_data)
                
                execution_time = int((time.time() - start_time) * 1000)
                
                self._update_stats(success=True, execution_time=execution_time)
                
                if cache_key:
                    self._cache_result(cache_key, result)
                
                return {
                    'success': True,
                    'result': result,
                    'execution_time_ms': execution_time,
                    'retry_count': retry_count
                }
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count <= max_retries:
                    delay = self._calculate_retry_delay(retry_count)
                    logger.info(f"Retrying tool {self.tool.name} after {delay}s (attempt {retry_count}/{max_retries})")
                    time.sleep(delay)
                else:
                    execution_time = int((time.time() - start_time) * 1000)
                    self._update_stats(success=False, execution_time=execution_time)
                    
                    return {
                        'success': False,
                        'error': str(last_error),
                        'execution_time_ms': execution_time,
                        'retry_count': retry_count - 1
                    }

    def _generate_cache_key(self, input_data: Dict) -> str:
        """Generate cache key from input data."""
        data_str = json.dumps(input_data, sort_keys=True, default=str)
        hash_obj = hashlib.sha256(f"{self.tool.name}:{data_str}".encode())
        return f"tool:{self.tool.name}:{hash_obj.hexdigest()[:16]}"

    def _get_cached_result(self, cache_key: str) -> Optional[Dict]:
        """Get cached result if available."""
        try:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for tool {self.tool.name}")
                return cached
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None

    def _cache_result(self, cache_key: str, result: Dict) -> None:
        """Cache tool result."""
        try:
            cache.set(cache_key, result, self._cache_ttl)
            logger.debug(f"Cached result for tool {self.tool.name}")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")

    def _calculate_retry_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay."""
        base_delay = 1.0
        multiplier = 2
        max_delay = 30.0
        
        delay = min(base_delay * (multiplier ** (retry_count - 1)), max_delay)
        
        if hasattr(self.tool, 'retry_policy'):
            policy = self.tool.retry_policy
            if 'base_delay' in policy:
                delay = min(policy['base_delay'] * (policy.get('multiplier', 2) ** (retry_count - 1)), max_delay)
        
        return delay

    def _execute_builtin(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute built-in tool."""
        definition = self.tool.definition or {}
        tool_name = definition.get('name', self.tool.name)
        
        builtins = {
            'calculator': self._builtin_calculator,
            'date_time': self._builtin_datetime,
            'json_parser': self._builtin_json_parser,
            'string_ops': self._builtin_string_ops,
            'http_request': self._builtin_http_request,
            'regex': self._builtin_regex,
            'uuid_generator': self._builtin_uuid,
            'hash_generator': self._builtin_hash,
            'base64_tool': self._builtin_base64,
        }
        
        if tool_name in builtins:
            return builtins[tool_name](input_data)
        
        raise ValueError(f"Unknown built-in tool: {tool_name}")

    def _builtin_calculator(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in calculator tool."""
        expression = input_data.get('expression', '0')
        precision = input_data.get('precision', 10)
        
        import math
        safe_ns = {
            'math': math,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
            'abs': abs,
            'pow': pow,
            'round': round,
        }
        
        try:
            result = eval(expression, {"__builtins__": {}}, safe_ns)
            if isinstance(result, float):
                result = round(result, precision)
            return {'result': result, 'expression': expression}
        except Exception as e:
            raise ValueError(f"Calculator error: {e}")

    def _builtin_datetime(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in datetime tool."""
        from datetime import datetime
        import pytz
        
        now = timezone.now()
        
        result = {
            'now': now.isoformat(),
            'timestamp': now.timestamp(),
            'formatted': now.strftime('%Y-%m-%d %H:%M:%S'),
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'weekday': now.strftime('%A'),
            'year': now.year,
            'month': now.month,
            'day': now.day,
            'hour': now.hour,
            'minute': now.minute,
            'second': now.second,
        }
        
        action = input_data.get('action')
        if action == 'add':
            delta_type = input_data.get('delta_type', 'days')
            delta_value = input_data.get('delta_value', 0)
            
            delta_map = {
                'days': {'days': delta_value},
                'hours': {'hours': delta_value},
                'minutes': {'minutes': delta_value},
                'seconds': {'seconds': delta_value},
            }
            
            from datetime import timedelta
            delta = timedelta(**delta_map.get(delta_type, {'days': delta_value}))
            new_time = now + delta
            
            result['new_time'] = new_time.isoformat()
            result['delta'] = str(delta)
        
        return result

    def _builtin_json_parser(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in JSON parser tool."""
        json_string = input_data.get('json_string', input_data.get('json', '{}'))
        action = input_data.get('action', 'parse')
        
        if action == 'parse':
            try:
                parsed = json.loads(json_string)
                return {'result': parsed, 'type': type(parsed).__name__}
            except json.JSONDecodeError as e:
                raise ValueError(f"JSON parse error: {e}")
        
        elif action == 'stringify':
            indent = input_data.get('indent', None)
            return {'result': json.dumps(input_data.get('data', {}), indent=indent)}
        
        elif action == 'validate':
            try:
                json.loads(json_string)
                return {'valid': True, 'message': 'Valid JSON'}
            except json.JSONDecodeError as e:
                return {'valid': False, 'message': str(e)}
        
        raise ValueError(f"Unknown JSON action: {action}")

    def _builtin_string_ops(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in string operations tool."""
        text = input_data.get('text', '')
        operation = input_data.get('operation', 'upper')
        
        operations = {
            'upper': str.upper,
            'lower': str.lower,
            'strip': str.strip,
            'title': str.title,
            'capitalize': str.capitalize,
            'swapcase': str.swapcase,
            'reverse': lambda s: s[::-1],
            'length': len,
            'word_count': lambda s: len(s.split()),
            'char_count': len,
        }
        
        if operation in operations:
            if operation in ('length', 'word_count', 'char_count'):
                return {'result': operations[operation](text), 'operation': operation}
            return {'result': operations[operation](text), 'operation': operation}
        
        raise ValueError(f"Unknown string operation: {operation}")

    def _builtin_http_request(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in HTTP request tool."""
        import httpx
        
        url = input_data.get('url')
        method = input_data.get('method', 'GET').upper()
        headers = input_data.get('headers', {})
        body = input_data.get('body')
        timeout = getattr(self.tool, 'timeout_seconds', 30)
        
        if not url:
            raise ValueError("URL is required")
        
        try:
            with httpx.Client(timeout=timeout) as client:
                if method == 'GET':
                    response = client.get(url, headers=headers, params=input_data.get('params'))
                elif method == 'POST':
                    response = client.post(url, headers=headers, json=body)
                elif method == 'PUT':
                    response = client.put(url, headers=headers, json=body)
                elif method == 'DELETE':
                    response = client.delete(url, headers=headers)
                elif method == 'PATCH':
                    response = client.patch(url, headers=headers, json=body)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                content_type = response.headers.get('content-type', '')
                
                return {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'body': response.json() if 'application/json' in content_type else response.text,
                    'elapsed_ms': response.elapsed.total_seconds() * 1000
                }
        except httpx.TimeoutException:
            raise ValueError("Request timeout")
        except httpx.HTTPError as e:
            raise ValueError(f"HTTP error: {e}")

    def _builtin_regex(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in regex tool."""
        import re
        
        text = input_data.get('text', '')
        pattern = input_data.get('pattern', '')
        action = input_data.get('action', 'match')
        
        try:
            regex = re.compile(pattern)
            
            if action == 'match':
                match = regex.match(text)
                if match:
                    return {
                        'matched': True,
                        'group': match.group(),
                        'groups': match.groups(),
                        'span': match.span()
                    }
                return {'matched': False}
            
            elif action == 'search':
                match = regex.search(text)
                if match:
                    return {
                        'found': True,
                        'group': match.group(),
                        'groups': match.groups(),
                        'span': match.span()
                    }
                return {'found': False}
            
            elif action == 'findall':
                matches = regex.findall(text)
                return {'matches': matches, 'count': len(matches)}
            
            elif action == 'sub':
                replacement = input_data.get('replacement', '')
                result = regex.sub(replacement, text)
                return {'result': result, 'count': len(regex.findall(text))}
            
            raise ValueError(f"Unknown regex action: {action}")
            
        except re.error as e:
            raise ValueError(f"Regex error: {e}")

    def _builtin_uuid(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in UUID generator tool."""
        import uuid
        
        count = input_data.get('count', 1)
        version = input_data.get('version', 4)
        
        uuids = []
        for _ in range(min(count, 100)):
            if version == 1:
                uuids.append(str(uuid.uuid1()))
            elif version == 4:
                uuids.append(str(uuid.uuid4()))
            else:
                uuids.append(str(uuid.uuid4()))
        
        return {'uuid': uuids[0] if count == 1 else uuids, 'count': len(uuids)}

    def _builtin_hash(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in hash generator tool."""
        import hashlib
        
        text = input_data.get('text', '')
        algorithm = input_data.get('algorithm', 'sha256').lower()
        
        encodings = ['utf-8', 'latin-1', 'ascii']
        text_bytes = None
        for enc in encodings:
            try:
                text_bytes = text.encode(enc)
                break
            except:
                continue
        
        if text_bytes is None:
            text_bytes = text.encode('utf-8', errors='ignore')
        
        algorithms = {
            'md5': hashlib.md5,
            'sha1': hashlib.sha1,
            'sha256': hashlib.sha256,
            'sha512': hashlib.sha512,
        }
        
        if algorithm in algorithms:
            return {algorithm: algorithms[algorithm](text_bytes).hexdigest()}
        
        raise ValueError(f"Unknown hash algorithm: {algorithm}")

    def _builtin_base64(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Built-in base64 tool."""
        import base64
        
        text = input_data.get('text', '')
        action = input_data.get('action', 'encode')
        
        if action == 'encode':
            encoded = base64.b64encode(text.encode('utf-8')).decode('utf-8')
            return {'original': text, 'encoded': encoded}
        
        elif action == 'decode':
            try:
                decoded = base64.b64decode(text.encode('utf-8')).decode('utf-8')
                return {'encoded': text, 'decoded': decoded}
            except Exception as e:
                raise ValueError(f"Base64 decode error: {e}")
        
        raise ValueError(f"Unknown base64 action: {action}")

    def _execute_api(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API tool."""
        import httpx
        
        definition = self.tool.definition or {}
        endpoint = definition.get('endpoint')
        method = definition.get('method', 'GET').upper()
        
        if not endpoint:
            raise ValueError("API endpoint is required")
        
        headers = {}
        if self.tool.credential:
            cred = self.tool.credential
            if cred.auth_type == 'api_key':
                header_name = cred.service_config.get('header_name', 'X-API-Key')
                headers[header_name] = cred.credential_data
            elif cred.auth_type == 'bearer':
                headers['Authorization'] = f"Bearer {cred.credential_data}"
        
        timeout = getattr(self.tool, 'timeout_seconds', 30)
        
        try:
            with httpx.Client(timeout=timeout) as client:
                if method == 'GET':
                    response = client.get(endpoint, headers=headers, params=input_data)
                else:
                    response = client.request(
                        method=method,
                        url=endpoint,
                        headers=headers,
                        json=input_data
                    )
                
                content_type = response.headers.get('content-type', '')
                
                return {
                    'status_code': response.status_code,
                    'body': response.json() if 'application/json' in content_type else response.text,
                    'headers': dict(response.headers)
                }
        except httpx.TimeoutException:
            raise ValueError("API request timeout")
        except Exception as e:
            raise ValueError(f"API execution error: {e}")

    def _execute_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute script tool."""
        definition = self.tool.definition or {}
        script = definition.get('script', '')
        
        if not script:
            raise ValueError("Script is required")
        
        safe_globals = {
            '__builtins__': {
                'True': True, 'False': False, 'None': None,
                'abs': abs, 'all': all, 'any': any, 'bool': bool,
                'dict': dict, 'enumerate': enumerate, 'filter': filter,
                'float': float, 'int': int, 'isinstance': isinstance,
                'len': len, 'list': list, 'map': map, 'max': max,
                'min': min, 'range': range, 'round': round,
                'set': set, 'sorted': sorted, 'str': str, 'sum': sum,
                'tuple': tuple, 'zip': zip,
                'json': json, 'math': __import__('math'),
            }
        }
        safe_locals = {'input': input_data, 'output': {}}
        
        exec(script, safe_globals, safe_locals)
        
        return safe_locals.get('output', {})

    def _execute_custom(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute custom tool using handler."""
        definition = self.tool.definition or {}
        handler = definition.get('handler')
        
        if not handler:
            raise ValueError("Custom tool handler is required")
        
        try:
            module_path, func_name = handler.rsplit('.', 1)
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            return func(input_data, self.tool)
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Custom tool handler error: {e}")

    def _update_stats(self, success: bool, execution_time: int, cache_hit: bool = False):
        """Update tool usage statistics."""
        self.tool.usage_count += 1
        
        if self.tool.avg_execution_time_ms:
            self.tool.avg_execution_time_ms = (
                (self.tool.avg_execution_time_ms * (self.tool.usage_count - 1) + execution_time)
                / self.tool.usage_count
            )
        else:
            self.tool.avg_execution_time_ms = execution_time
        
        if success:
            if self.tool.success_rate:
                self.tool.success_rate = (
                    (self.tool.success_rate * (self.tool.usage_count - 1) + 100)
                    / self.tool.usage_count
                )
            else:
                self.tool.success_rate = 100
        else:
            if self.tool.success_rate:
                self.tool.success_rate = (
                    self.tool.success_rate * (self.tool.usage_count - 1)
                ) / self.tool.usage_count
            else:
                self.tool.success_rate = 0
        
        try:
            self.tool.save(update_fields=['usage_count', 'avg_execution_time_ms', 'success_rate'])
        except Exception as e:
            logger.warning(f"Failed to update tool stats: {e}")

