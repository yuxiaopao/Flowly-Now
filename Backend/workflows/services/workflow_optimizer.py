"""
Rule-based workflow optimizer for the editor assistant.

Analyzes nodes/edges from the frontend canvas and returns structured suggestions
without requiring an LLM call.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set


DEFAULT_DIMENSIONS = [
    'performance',
    'error_handling',
    'maintainability',
    'cost',
    'security',
]

LLM_NODE_TYPES = {'llm', 'model', 'chat', 'openai', 'agent'}
HTTP_NODE_TYPES = {'http', 'http_request', 'api', 'webhook'}
SENSITIVE_KEY_PATTERN = ('api_key', 'apikey', 'secret', 'password', 'token', 'credential')


def _node_id(node: Dict[str, Any]) -> str:
    return str(node.get('id') or '')


def _node_type(node: Dict[str, Any]) -> str:
    data = node.get('data') or {}
    return str(node.get('type') or data.get('type') or data.get('nodeType') or '').lower()


def _node_label(node: Dict[str, Any]) -> str:
    data = node.get('data') or {}
    return str(
        node.get('label')
        or data.get('label')
        or data.get('name')
        or _node_id(node)
        or '未命名节点'
    )


def _node_config(node: Dict[str, Any]) -> Dict[str, Any]:
    data = node.get('data') or {}
    config = (
        node.get('config')
        or data.get('config')
        or data.get('parameters')
        or data.get('params')
        or {}
    )
    return config if isinstance(config, dict) else {}


def _build_adjacency(edges: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    graph: Dict[str, List[str]] = {}
    for edge in edges:
        source = str(edge.get('source') or edge.get('sourceNode') or '')
        target = str(edge.get('target') or edge.get('targetNode') or '')
        if source and target:
            graph.setdefault(source, []).append(target)
    return graph


def _find_unreachable_nodes(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    if not nodes:
        return []

    node_ids = {_node_id(n) for n in nodes if _node_id(n)}
    if not node_ids:
        return []

    incoming: Dict[str, int] = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        target = str(edge.get('target') or edge.get('targetNode') or '')
        if target in incoming:
            incoming[target] += 1

    starts = [
        _node_id(n) for n in nodes
        if _node_type(n) in {'input', 'start', 'trigger', 'webhook_trigger'} or incoming.get(_node_id(n), 0) == 0
    ]
    if not starts:
        starts = [next(iter(node_ids))]

    graph = _build_adjacency(edges)
    visited: Set[str] = set()
    stack = list(starts)
    while stack:
        current = stack.pop()
        if current in visited or current not in node_ids:
            continue
        visited.add(current)
        stack.extend(graph.get(current, []))

    return sorted(node_ids - visited)


def _config_has_sensitive_values(config: Dict[str, Any]) -> bool:
    def walk(value: Any, key_path: str = '') -> bool:
        if isinstance(value, dict):
            return any(walk(v, f'{key_path}.{k}' if key_path else k) for k, v in value.items())
        if isinstance(value, list):
            return any(walk(item, key_path) for item in value)
        if not isinstance(value, str):
            return False
        lowered_key = key_path.lower()
        if any(token in lowered_key for token in SENSITIVE_KEY_PATTERN):
            return bool(value.strip()) and not value.strip().startswith('{{')
        return False

    return walk(config)


def analyze_workflow(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
    dimensions: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return optimization suggestions for a workflow graph."""
    active_dimensions = set(dimensions or DEFAULT_DIMENSIONS)
    suggestions: List[Dict[str, Any]] = []

    if not nodes:
        suggestions.append({
            'type': 'maintainability',
            'severity': 'warning',
            'title': '工作流为空',
            'description': '当前工作流没有任何节点，请添加输入、处理与输出节点后再执行。',
            'affectedNodes': [],
            'expectedBenefit': '确保工作流可执行',
            'autoApplicable': False,
        })
        return suggestions

    node_map = {_node_id(n): n for n in nodes if _node_id(n)}

    if 'performance' in active_dimensions:
        for node in nodes:
            node_type = _node_type(node)
            if node_type not in LLM_NODE_TYPES:
                continue
            config = _node_config(node)
            timeout = config.get('timeout') or config.get('timeoutMs') or config.get('timeout_ms')
            if timeout in (None, '', 0):
                label = _node_label(node)
                suggestions.append({
                    'type': 'performance',
                    'severity': 'warning',
                    'title': f'LLM 节点「{label}」未设置超时',
                    'description': '未配置超时可能导致工作流长时间阻塞，建议设置合理的超时与重试策略。',
                    'affectedNodes': [_node_id(node)],
                    'expectedBenefit': '减少异常等待时间',
                    'autoApplicable': True,
                    'fix': '{"timeout": 60, "retryPolicy": {"maxRetries": 2, "retryDelay": 1000}}',
                })

    if 'error_handling' in active_dimensions:
        for node in nodes:
            node_type = _node_type(node)
            if node_type not in HTTP_NODE_TYPES:
                continue
            config = _node_config(node)
            has_retry = any(
                config.get(key) not in (None, '', 0, False)
                for key in ('retry', 'retries', 'maxRetries', 'retryPolicy', 'onError', 'errorHandling')
            )
            if not has_retry:
                label = _node_label(node)
                suggestions.append({
                    'type': 'error_handling',
                    'severity': 'critical',
                    'title': f'HTTP 节点「{label}」缺少错误处理',
                    'description': '请求失败时工作流可能直接终止，建议配置重试或错误分支。',
                    'affectedNodes': [_node_id(node)],
                    'expectedBenefit': '提高工作流健壮性',
                    'autoApplicable': False,
                    'fix': '建议添加重试策略（maxRetries）或连接错误处理分支节点。',
                })

        unreachable = _find_unreachable_nodes(nodes, edges)
        if unreachable:
            suggestions.append({
                'type': 'error_handling',
                'severity': 'warning',
                'title': '存在不可达节点',
                'description': f'检测到 {len(unreachable)} 个节点未与主执行路径连通，可能导致部分逻辑永不执行。',
                'affectedNodes': unreachable,
                'expectedBenefit': '避免遗漏业务分支',
                'autoApplicable': False,
            })

    if 'maintainability' in active_dimensions:
        for node in nodes:
            label = _node_label(node)
            if len(label) <= 2 or label in {'a', 'b', 'c', 'node', '未命名节点'}:
                suggestions.append({
                    'type': 'maintainability',
                    'severity': 'info',
                    'title': f'节点「{label}」命名不够清晰',
                    'description': '建议使用能表达业务含义的名称，便于团队协作与后续维护。',
                    'affectedNodes': [_node_id(node)],
                    'expectedBenefit': '提高可读性',
                    'autoApplicable': False,
                })

    if 'cost' in active_dimensions:
        ordered_ids = [_node_id(n) for n in nodes if _node_id(n)]
        consecutive_llm: List[str] = []
        for node_id in ordered_ids:
            node = node_map.get(node_id)
            if node and _node_type(node) in LLM_NODE_TYPES:
                consecutive_llm.append(node_id)
            elif len(consecutive_llm) >= 2:
                suggestions.append({
                    'type': 'cost',
                    'severity': 'warning',
                    'title': '检测到连续 LLM 节点',
                    'description': '连续的 LLM 调用可能增加 token 成本，可考虑合并提示词或减少调用次数。',
                    'affectedNodes': consecutive_llm.copy(),
                    'expectedBenefit': '降低 LLM 调用成本',
                    'autoApplicable': False,
                })
                consecutive_llm = []
            else:
                consecutive_llm = []
        if len(consecutive_llm) >= 2:
            suggestions.append({
                'type': 'cost',
                'severity': 'warning',
                'title': '检测到连续 LLM 节点',
                'description': '连续的 LLM 调用可能增加 token 成本，可考虑合并提示词或减少调用次数。',
                'affectedNodes': consecutive_llm,
                'expectedBenefit': '降低 LLM 调用成本',
                'autoApplicable': False,
            })

    if 'security' in active_dimensions:
        for node in nodes:
            config = _node_config(node)
            if _config_has_sensitive_values(config):
                label = _node_label(node)
                suggestions.append({
                    'type': 'security',
                    'severity': 'critical',
                    'title': f'节点「{label}」可能包含硬编码敏感信息',
                    'description': '检测到配置中存在疑似 API Key / Token / 密码字段，应改用凭证中心或环境变量引用。',
                    'affectedNodes': [_node_id(node)],
                    'expectedBenefit': '降低凭证泄露风险',
                    'autoApplicable': False,
                    'fix': '将敏感字段改为 {{secrets.xxx}} 或凭证引用，并从节点配置中移除明文。',
                })

    return suggestions
