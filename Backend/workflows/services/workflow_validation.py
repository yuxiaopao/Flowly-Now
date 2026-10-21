"""Chinese preflight diagnostics shared by API, runtime and batch verification."""
from collections import Counter, defaultdict, deque


N8N_PAYLOAD_TRIGGERS = frozenset({
    'manualTrigger', 'start', 'executeWorkflowTrigger', 'workflowTrigger',
    'webhook', 'scheduleTrigger', 'cron', 'formTrigger',
})
N8N_HTTP_PARAMETERS = frozenset({'url', 'method', 'requestMethod', 'options'})
UNIMPLEMENTED_INTEGRATIONS = frozenset({
    'microsoft_teams', 'google_sheets', 'google_drive', 'gitlab', 'jira',
    'airtable', 'trello', 'elasticsearch', 'aws_s3', 'ftp', 'stripe',
    'twilio', 'sendgrid', 'push_notification',
})
from .data_transform import JSON_OPERATIONS as JSON_OPERATION_TYPES, CSV_OPERATIONS as CSV_OPERATION_TYPES


def validate_imported_node(node_type, config):
    """Preserved n8n parameters are not evidence of a working native adapter."""
    origin = config.get('n8n_type')
    if not origin:
        return []
    suffix = str(origin).rsplit('.', 1)[-1]
    errors = []
    if config.get('n8n_unmapped'):
        errors.append(f'原节点 {origin} 尚未完成兼容转换')
    elif origin == 'n8n-nodes-base.noOp':
        return []
    elif suffix in N8N_PAYLOAD_TRIGGERS and node_type in ('start', 'manual', 'webhook', 'schedule', 'form'):
        return []
    elif origin == 'n8n-nodes-base.httpRequest' and node_type in ('http', 'http_request'):
        params = config.get('n8n_parameters') or {}
        if not isinstance(params, dict):
            errors.append('原 HTTP 节点参数格式无效')
        else:
            unconverted = set(params) - N8N_HTTP_PARAMETERS
            if unconverted or params.get('options'):
                errors.append('原 HTTP 节点的请求头、认证、正文或选项尚未完整转换')
            if any(token in str(config.get('url', '')) for token in ('$json', '$node', '$input', '$(', '$env', '$vars')):
                errors.append('HTTP 地址含尚未兼容的 n8n 表达式')
    else:
        errors.append(f'原节点 {origin} 的业务操作尚未适配，不能直接作为 {node_type} 执行')
    if config.get('n8n_credentials') and not config.get('credentialId'):
        errors.append('n8n 凭据引用尚未绑定本项目凭据')
    return errors


def validate_workflow(workflow, input_data=None, service=None):
    """Check actual executors, links, reachability and required execution inputs."""
    if service is None:
        from .langchain_service import LangChainService
        service = LangChainService(user_id=getattr(workflow, 'owner_id', None))
    registry = service.get_node_executors()
    nodes = list(workflow.nodes.all())
    edges = list(workflow.edges.all())
    ids = {str(n.id) for n in nodes}
    adjacency, incoming = defaultdict(list), Counter()
    errors, warnings, node_issues = [], [], []

    def issue(message, node=None, code='configuration', severity='error'):
        text = f'节点「{node.name}」：{message}' if node else message
        (errors if severity == 'error' else warnings).append(text)
        node_issues.append({'node_id': str(node.id) if node else None, 'code': code, 'severity': severity, 'message': text})

    if not nodes:
        issue('工作流没有节点', code='empty_workflow')
    for edge in edges:
        source, target = str(edge.source_node_id), str(edge.target_node_id)
        if source not in ids or target not in ids:
            issue('连线引用了当前工作流中不存在的节点', code='invalid_edge')
            continue
        adjacency[source].append(target)
        incoming[target] += 1
    roots = [str(n.id) for n in nodes if not incoming[str(n.id)]]
    starts = [str(n.id) for n in nodes if n.node_type == 'start' and str(n.id) in roots]
    reachable, queue = set(), deque(starts or roots)
    while queue:
        cur = queue.popleft()
        if cur in reachable:
            continue
        reachable.add(cur)
        queue.extend(adjacency[cur])
    if nodes and not roots:
        issue('工作流没有可执行的入口，请检查循环连线', code='no_entry')
    degrees, remaining = incoming.copy(), set(ids)
    queue = deque(roots)
    while queue:
        cur = queue.popleft()
        remaining.discard(cur)
        for nxt in adjacency[cur]:
            degrees[nxt] -= 1
            if not degrees[nxt]:
                queue.append(nxt)
    if remaining:
        issue('存在循环依赖；请使用循环节点配置迭代，而不是回连节点', code='cycle')
    if nodes and not any(n.node_type == 'end' for n in nodes):
        issue('缺少结束节点', code='missing_end', severity='warning')
    for node in nodes:
        cfg = node.config if isinstance(node.config, dict) else {}
        if node.node_type not in registry:
            issue(f'不支持的节点类型 {node.node_type}，缺少执行器', node, 'unsupported_node')
        elif node.node_type in UNIMPLEMENTED_INTEGRATIONS:
            issue('此集成尚未实现执行器', node, 'unsupported_integration')
        for message in validate_imported_node(node.node_type, cfg):
            issue(message, node, 'n8n_compatibility')
        if cfg.get('n8n_type') == 'n8n-nodes-base.noOp':
            issue('原模板为空操作节点，仅传递输入，请确认它符合预期业务', node, 'n8n_noop', 'warning')
        if str(node.id) not in reachable:
            issue('从执行入口无法到达此节点', node, 'unreachable')
        if node.node_type in ('http', 'http_request') and not cfg.get('url'):
            issue('缺少 HTTP 请求地址', node, 'missing_url')
        if node.node_type == 'code' and not cfg.get('code'):
            issue('缺少执行代码', node, 'missing_code')
        if node.node_type in ('json_transform', 'csv_transform'):
            operation = cfg.get('operation') or cfg.get('transformType') or ('map' if node.node_type == 'json_transform' else 'filter')
            supported = JSON_OPERATION_TYPES if node.node_type == 'json_transform' else CSV_OPERATION_TYPES
            if operation not in supported:
                issue(f'操作 {operation} 尚未实现，不能执行', node, 'unsupported_operation')
        if input_data is not None and node.node_type == 'input':
            name = cfg.get('variable_name') or cfg.get('input_name') or 'input'
            value = input_data.get(name, input_data.get('input'))
            if value is None and name in ('input', 'user_input'):
                value = input_data.get('text')
            default = cfg.get('default') if cfg.get('default') is not None else cfg.get('default_value')
            if cfg.get('required', True) and value is None and default is None:
                issue(f'缺少必填输入 {name}', node, 'missing_input')
    return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'node_issues': node_issues, 'node_count': len(nodes), 'edge_count': len(edges)}
