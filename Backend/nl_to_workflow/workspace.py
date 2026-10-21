"""Validation and stable identity for editable NL workflow drafts."""
import hashlib
import json

from rest_framework.exceptions import ValidationError
from workflows.models import Node

SESSION_PAGE_SIZE = 30
WORKSPACE_API_VERSION = 1
SESSION_PAGE_SIZE_MAX = 100
SESSION_NAME_MAX_LENGTH = 200
SUPPORTED_DRAFT_NODE_TYPES = frozenset(value for value, _ in Node.NODE_TYPE_CHOICES)


def read_workflow_draft(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValidationError({'workflow_json': '工作流不是有效的 JSON'}) from exc
    if not isinstance(value, dict):
        raise ValidationError({'workflow_json': '工作流必须是对象'})
    nodes, edges = value.get('nodes'), value.get('edges', [])
    if not isinstance(nodes, list) or not nodes or not isinstance(edges, list):
        raise ValidationError({'workflow_json': '请提供非空节点列表和连线列表'})
    identifiers = set()
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get('id'), str) or not node['id']:
            raise ValidationError({'workflow_json': '每个节点必须有非空字符串 ID'})
        if node['id'] in identifiers:
            raise ValidationError({'workflow_json': '节点 ID 不能重复'})
        identifiers.add(node['id'])
        if not isinstance(node.get('config', {}), dict):
            raise ValidationError({'workflow_json': '节点配置必须是对象'})
        if not isinstance(node.get('type'), str) or not node['type']:
            raise ValidationError({'workflow_json': '节点类型不能为空'})
        if node['type'] not in SUPPORTED_DRAFT_NODE_TYPES:
            raise ValidationError({'workflow_json': '工作流包含不支持的节点类型'})
        if not isinstance(node.get('name', ''), str) or len(node.get('name', '')) > SESSION_NAME_MAX_LENGTH:
            raise ValidationError({'workflow_json': '节点名称无效或过长'})
    for edge in edges:
        if not isinstance(edge, dict) or not isinstance(edge.get('source'), str) or not isinstance(edge.get('target'), str):
            raise ValidationError({'workflow_json': '连线端点必须是节点 ID'})
        if edge['source'] not in identifiers or edge['target'] not in identifiers:
            raise ValidationError({'workflow_json': '连线引用了不存在的节点'})
    if not isinstance(value.get('name', ''), str) or len(value.get('name', '')) > SESSION_NAME_MAX_LENGTH:
        raise ValidationError({'workflow_json': '工作流名称无效或过长'})
    return value


def workflow_fingerprint(workflow):
    executable = {key: value for key, value in workflow.items() if key not in ('_node_guidance', '_email_guidance')}
    return hashlib.sha256(json.dumps(executable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
