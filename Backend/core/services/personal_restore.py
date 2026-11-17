"""Validate backup graphs and restore private copies with expiring confirmation."""

import hashlib
import copy
import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import models, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from jsonschema import Draft202012Validator, FormatChecker
from rest_framework.exceptions import APIException, ValidationError

from core.data_constants import (
    AGENT_FIELDS, AGENT_TOOL_FIELDS, DEFAULT_CONFIRMATION_MAX_AGE,
    DEFAULT_MAX_SNAPSHOT_BYTES, DEFAULT_MAX_SNAPSHOT_RECORDS, EDGE_FIELDS,
    NODE_FIELDS, RESTORED_NAME_SUFFIX, RESTORE_SIGNING_SALT, SNAPSHOT_TYPE,
    SNAPSHOT_VERSION, WORKFLOW_FIELDS,
    VARIABLE_FIELDS, TRIGGER_FIELDS, WEBHOOK_FIELDS,
    RESTORED_NODE_ALIASES_KEY,
)
from core.models.audit import AuditAction, AuditLog, DataExport, DataRestoreOperation
from core.services.personal_exports import json_bytes

class DataConflict(APIException):
    status_code = 409
    default_detail = '数据已变化，请重新预览后确认。'


def _row_schema(model, fields, nested=None):
    properties = {}
    for name in fields:
        field = model._meta.get_field(name[:-3] if name.endswith('_id') else name)
        if isinstance(field, (models.UUIDField, models.ForeignKey)):
            spec = {'type': 'string', 'format': 'uuid'}
        elif isinstance(field, models.BooleanField):
            spec = {'type': 'boolean'}
        elif isinstance(field, models.IntegerField):
            spec = {'type': 'integer'}
        elif isinstance(field, models.FloatField):
            spec = {'type': 'number'}
        elif isinstance(field, models.DecimalField):
            spec = {'type': ['string', 'number']}
        elif isinstance(field, models.JSONField):
            default = field.get_default()
            spec = {'type': 'array'} if isinstance(default, list) else {'type': 'object'} if isinstance(default, dict) else {}
        else:
            spec = {'type': 'string'}
            if field.max_length:
                spec['maxLength'] = field.max_length
        if field.null and spec.get('type'):
            types = spec['type'] if isinstance(spec['type'], list) else [spec['type']]
            spec['type'] = [*types, 'null']
        properties[name] = spec
    properties.update(nested or {})
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def validate_snapshot(export):
    from agents.models import Agent, AgentTool
    from workflows.models import Edge, Node, Workflow, Variable
    from workflows.scheduling import WorkflowTrigger, Webhook

    snapshot = export.snapshot
    try:
        content = json_bytes(snapshot)
    except (ValueError, TypeError) as exc:
        raise ValidationError('备份不是有效的 JSON 数据。') from exc
    if len(content) > getattr(settings, 'PERSONAL_DATA_MAX_BYTES', DEFAULT_MAX_SNAPSHOT_BYTES):
        raise ValidationError('备份超过恢复大小限制。')
    array = lambda item: {'type': 'array', 'items': item}
    schema = {
        'type': 'object', 'additionalProperties': False,
        'required': ['type', 'schema_version', 'export_type', 'exported_at', 'user_id', 'username'],
        'properties': {
            'type': {'const': SNAPSHOT_TYPE}, 'schema_version': {'const': SNAPSHOT_VERSION},
            'export_type': {'enum': ['full', 'workflows', 'agents']},
            'exported_at': {'type': 'string', 'format': 'date-time'},
            'user_id': {'const': export.user_id}, 'username': {'type': 'string'},
            'workflows': array(_row_schema(Workflow, WORKFLOW_FIELDS, {
                'nodes': array(_row_schema(Node, NODE_FIELDS)),
                'edges': array(_row_schema(Edge, EDGE_FIELDS)),
                'variables': array(_row_schema(Variable, VARIABLE_FIELDS)),
                'triggers': array(_row_schema(WorkflowTrigger, TRIGGER_FIELDS)),
                'webhooks': array(_row_schema(Webhook, WEBHOOK_FIELDS)),
            })),
            'agents': array(_row_schema(Agent, AGENT_FIELDS, {
                'agent_tools': array(_row_schema(AgentTool, AGENT_TOOL_FIELDS)),
            })),
            'executions': {'type': 'array'}, 'audit_logs': {'type': 'array'},
        },
    }
    if next(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(snapshot), None):
        raise ValidationError('备份格式、版本或字段不符合恢复规范，请重新导出 JSON 备份。')
    records = {name: [] for name in ('workflows', 'nodes', 'edges', 'agents', 'agent_tools', 'variables', 'triggers', 'webhooks')}
    for workflow in snapshot.get('workflows', []):
        records['workflows'].append(workflow)
        records['nodes'].extend(workflow['nodes'])
        records['edges'].extend(workflow['edges'])
        for key in ('variables', 'triggers', 'webhooks'):
            records[key].extend(workflow[key])
        node_ids = {node['id'] for node in workflow['nodes']}
        parents = {node['id']: node['parent_node_id'] for node in workflow['nodes']}
        for node in workflow['nodes']:
            if node['parent_node_id'] and node['parent_node_id'] not in node_ids:
                raise ValidationError('备份中的父节点不属于同一工作流。')
            seen, current = set(), node['id']
            while current:
                if current in seen:
                    raise ValidationError('备份中的父节点存在循环引用。')
                seen.add(current)
                current = parents.get(current)
        for edge in workflow['edges']:
            if edge['source_node_id'] not in node_ids or edge['target_node_id'] not in node_ids:
                raise ValidationError('备份连线引用了工作流以外的节点。')
    for agent in snapshot.get('agents', []):
        records['agents'].append(agent)
        records['agent_tools'].extend(agent['agent_tools'])
    if sum(map(len, records.values())) > getattr(settings, 'PERSONAL_DATA_MAX_RECORDS', DEFAULT_MAX_SNAPSHOT_RECORDS):
        raise ValidationError('备份记录超过单次恢复上限。')
    for kind, rows in records.items():
        if len({row['id'] for row in rows}) != len(rows):
            raise ValidationError(f'备份包含重复的 {kind} ID。')
    if not records['workflows'] and not records['agents']:
        raise ValidationError('备份中没有可恢复的个人工作流或 Agent。')
    return snapshot, {kind: len(rows) for kind, rows in records.items()}, hashlib.sha256(content).hexdigest()


def preview_restore(export):
    if export.status != 'completed' or export.format != 'json':
        raise ValidationError('仅已完成的 JSON 备份可以恢复。')
    _, summary, digest = validate_snapshot(export)
    expiry = getattr(settings, 'PERSONAL_DATA_CONFIRMATION_SECONDS', DEFAULT_CONFIRMATION_MAX_AGE)
    operation = DataRestoreOperation.objects.create(
        user=export.user, export=export, snapshot_digest=digest,
        expires_at=timezone.now() + timedelta(seconds=expiry),
    )
    token = signing.dumps({'operation': str(operation.pk), 'user': export.user_id, 'export': export.pk}, salt=RESTORE_SIGNING_SALT)
    return {'summary': summary, 'confirmation_token': token, 'expires_at': operation.expires_at,
            'mode': 'private_copies', 'notice': '创建私有草稿副本；触发器和 Webhook 禁用且重新生成入口。原数据保留，执行及审计记录仅归档，不会重放。'}


def _values(model, row, fields):
    values = {}
    for name in fields:
        if name == 'id' or name.endswith('_id'):
            continue
        field = model._meta.get_field(name)
        value = copy.deepcopy(row[name])
        try:
            # Empty JSON collections are valid persisted defaults even when the
            # model field has blank=False (Django's form-level empty check).
            values[name] = value if isinstance(field, models.JSONField) and value in ({}, []) else field.clean(value, model())
        except ModelValidationError as exc:
            raise ValidationError(f'备份字段 {name} 无效。') from exc
    return values


def _node_values(row, mapping):
    from workflows.models import Node
    values = _values(Node, row, NODE_FIELDS)
    references = {
        'agent': ('agents', ('agent_id', 'agentId')),
        'subworkflow': ('workflows', ('subworkflowId', 'workflow_id', 'workflowId')),
    }
    if row['node_type'] in references and isinstance(values['config'], dict):
        group, keys = references[row['node_type']]
        for key in keys:
            original = values['config'].get(key)
            if isinstance(original, str) and original in mapping[group]:
                values['config'][key] = mapping[group][original]
    return values


@transaction.atomic
def confirm_restore(user, export_id, token):
    from agents.models import Agent, AgentTool
    from workflows.models import Edge, Node, Workflow, Variable
    from workflows.scheduling import WorkflowTrigger, Webhook, TriggerStatus

    try:
        claims = signing.loads(token, salt=RESTORE_SIGNING_SALT,
                              max_age=getattr(settings, 'PERSONAL_DATA_CONFIRMATION_SECONDS', DEFAULT_CONFIRMATION_MAX_AGE))
    except signing.BadSignature as exc:
        raise ValidationError('恢复确认已失效，请重新预览。') from exc
    if claims.get('user') != user.pk or claims.get('export') != export_id:
        raise ValidationError('恢复确认不属于当前用户或备份。')
    operation = get_object_or_404(DataRestoreOperation.objects.select_for_update(), pk=claims.get('operation'), user=user, export_id=export_id)
    if operation.expires_at <= timezone.now():
        raise ValidationError('恢复预览已过期，请重新预览。')
    if operation.result is not None:
        return operation.result, False
    export = get_object_or_404(DataExport.objects.select_for_update(), pk=export_id, user=user)
    snapshot, summary, digest = validate_snapshot(export)
    if operation.snapshot_digest != digest:
        raise DataConflict()
    mapping = {key: {} for key in summary}
    for workflow in snapshot.get('workflows', []):
        mapping['workflows'][workflow['id']] = str(uuid.uuid4())
        for node in workflow['nodes']:
            mapping['nodes'][node['id']] = str(uuid.uuid4())
        for edge in workflow['edges']:
            mapping['edges'][edge['id']] = str(uuid.uuid4())
        for variable in workflow['variables']:
            mapping['variables'][variable['id']] = str(uuid.uuid4())
    for agent in snapshot.get('agents', []):
        mapping['agents'][agent['id']] = str(uuid.uuid4())
        for tool in agent['agent_tools']:
            mapping['agent_tools'][tool['id']] = str(uuid.uuid4())
    for row in snapshot.get('agents', []):
        values = _values(Agent, row, AGENT_FIELDS)
        values['name'] = values['name'][:Agent._meta.get_field('name').max_length - len(RESTORED_NAME_SUFFIX)] + RESTORED_NAME_SUFFIX
        agent = Agent.objects.create(id=mapping['agents'][row['id']], owner=user, tenant=None, is_public=False, **values)
        for tool in row['agent_tools']:
            AgentTool.objects.create(id=mapping['agent_tools'][tool['id']], agent=agent, **_values(AgentTool, tool, AGENT_TOOL_FIELDS))
    for row in snapshot.get('workflows', []):
        values = _values(Workflow, row, WORKFLOW_FIELDS)
        original_aliases = values['config'].get(RESTORED_NODE_ALIASES_KEY, {})
        aliases = {node['id']: mapping['nodes'][node['id']] for node in row['nodes']}
        if isinstance(original_aliases, dict):
            for original, current in original_aliases.items():
                if isinstance(original, str) and isinstance(current, str) and current in aliases:
                    aliases[original] = aliases[current]
        values['config'][RESTORED_NODE_ALIASES_KEY] = aliases
        values['name'] = values['name'][:Workflow._meta.get_field('name').max_length - len(RESTORED_NAME_SUFFIX)] + RESTORED_NAME_SUFFIX
        workflow = Workflow.objects.create(id=mapping['workflows'][row['id']], owner=user, tenant=None, status='draft', is_public=False, **values)
        nodes = [Node(id=mapping['nodes'][node['id']], workflow=workflow, **_node_values(node, mapping)) for node in row['nodes']]
        Node.objects.bulk_create(nodes)
        for node, source in zip(nodes, row['nodes']):
            node.parent_node_id = mapping['nodes'].get(source['parent_node_id'])
        if nodes:
            Node.objects.bulk_update(nodes, ['parent_node'])
        Edge.objects.bulk_create([
            Edge(id=mapping['edges'][edge['id']], workflow=workflow,
                 source_node_id=mapping['nodes'][edge['source_node_id']],
                 target_node_id=mapping['nodes'][edge['target_node_id']],
                 **_values(Edge, edge, EDGE_FIELDS))
            for edge in row['edges']
        ])
        for variable in row['variables']:
            Variable.objects.create(id=mapping['variables'][variable['id']], workflow=workflow,
                                    **_values(Variable, variable, VARIABLE_FIELDS))
        for source in row['triggers']:
            values = _values(WorkflowTrigger, source, TRIGGER_FIELDS)
            values['webhook_path'] = uuid.uuid4().hex if values['trigger_type'] == 'webhook' else ''
            if values['webhook_secret']:
                values['webhook_secret'] = uuid.uuid4().hex
            trigger = WorkflowTrigger.objects.create(workflow=workflow, created_by=user, is_enabled=False,
                                                      status=TriggerStatus.DISABLED, **values)
            mapping['triggers'][str(source['id'])] = str(trigger.pk)
        for source in row['webhooks']:
            values = _values(Webhook, source, WEBHOOK_FIELDS)
            values['path'] = uuid.uuid4().hex
            if values['auth_secret']:
                values['auth_secret'] = uuid.uuid4().hex
            webhook = Webhook.objects.create(workflow=workflow, created_by=user, is_active=False, **values)
            mapping['webhooks'][str(source['id'])] = str(webhook.pk)
    result = {'summary': summary, 'mapping': mapping, 'mode': 'private_copies'}
    operation.result = result
    operation.completed_at = timezone.now()
    operation.save(update_fields=['result', 'completed_at'])
    AuditLog.objects.create(user=user, action=AuditAction.OTHER, description='从个人备份恢复私有副本', metadata={'summary': summary, 'export_id': export.pk})
    return result, True
