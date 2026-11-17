"""Create immutable, owner-scoped export snapshots and genuine export files."""

import csv
import json
from io import BytesIO, StringIO

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.data_constants import (
    AGENT_FIELDS, AGENT_TOOL_FIELDS, DEFAULT_MAX_SNAPSHOT_BYTES,
    DEFAULT_MAX_SNAPSHOT_RECORDS, EDGE_FIELDS, NODE_FIELDS, SNAPSHOT_TYPE,
    SNAPSHOT_VERSION, WORKFLOW_FIELDS,
    VARIABLE_FIELDS, TRIGGER_FIELDS, WEBHOOK_FIELDS,
    EXCEL_MAX_CELL_CHARACTERS,
)
from core.models.audit import AuditLog, DataExport


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, cls=DjangoJSONEncoder, allow_nan=False).encode('utf-8')


def _record(instance, fields):
    return {name: getattr(instance, name) for name in fields}


def _dated(queryset, export, field='created_at'):
    if export.date_from:
        queryset = queryset.filter(**{f'{field}__gte': export.date_from})
    if export.date_to:
        queryset = queryset.filter(**{f'{field}__lte': export.date_to})
    return queryset


def build_snapshot(export):
    from agents.models import Agent
    from workflows.models import Workflow, WorkflowExecution

    user = export.user
    payload = {
        'type': SNAPSHOT_TYPE, 'schema_version': SNAPSHOT_VERSION,
        'export_type': export.export_type, 'exported_at': timezone.now().isoformat(),
        'user_id': user.pk, 'username': user.username,
    }
    if export.export_type in ('full', 'workflows'):
        workflows = _dated(Workflow.objects.filter(owner=user, tenant__isnull=True, is_deleted=False), export)
        payload['workflows'] = [
            {**_record(workflow, WORKFLOW_FIELDS),
             'nodes': [_record(node, NODE_FIELDS) for node in workflow.nodes.all()],
             'edges': [_record(edge, EDGE_FIELDS) for edge in workflow.edges.all()],
             'variables': [_record(variable, VARIABLE_FIELDS) for variable in workflow.variables.all()],
             'triggers': [_record(trigger, TRIGGER_FIELDS) for trigger in workflow.triggers.all()],
             'webhooks': [_record(webhook, WEBHOOK_FIELDS) for webhook in workflow.webhooks.all()]}
            for workflow in workflows.order_by('created_at', 'id').prefetch_related('nodes', 'edges', 'variables', 'triggers', 'webhooks')
        ]
    if export.export_type in ('full', 'agents'):
        agents = _dated(Agent.objects.filter(owner=user, tenant__isnull=True), export)
        payload['agents'] = [
            {**_record(agent, AGENT_FIELDS),
             'agent_tools': [_record(tool, AGENT_TOOL_FIELDS) for tool in agent.agent_tools.all()]}
            for agent in agents.order_by('created_at', 'id').prefetch_related('agent_tools')
        ]
    if export.export_type in ('full', 'executions'):
        executions = WorkflowExecution.objects.filter(workflow__owner=user, workflow__tenant__isnull=True)
        payload['executions'] = list(_dated(executions, export, 'queued_at').order_by('queued_at', 'id').values(
            'id', 'workflow_id', 'status', 'queued_at', 'started_at', 'completed_at',
            'duration_ms', 'input_data', 'output_data', 'error_message',
        ))
    if export.export_type in ('full', 'audit_logs'):
        payload['audit_logs'] = list(_dated(AuditLog.objects.filter(user=user), export).order_by('created_at', 'id').values(
            'id', 'action', 'level', 'description', 'target_type', 'target_id', 'created_at',
        ))
    if export.export_type == 'usage':
        from billing.models import UsageRecord
        from billing.serializers import UsageRecordSerializer
        records = _dated(UsageRecord.objects.filter(user=user), export, 'period_start').order_by('period_start')
        payload['usage'] = UsageRecordSerializer(records, many=True).data
    total = sum(len(value) for value in payload.values() if isinstance(value, list))
    total += sum(sum(len(w[key]) for key in ('nodes', 'edges', 'variables', 'triggers', 'webhooks')) for w in payload.get('workflows', []))
    total += sum(len(a['agent_tools']) for a in payload.get('agents', []))
    if total > getattr(settings, 'PERSONAL_DATA_MAX_RECORDS', DEFAULT_MAX_SNAPSHOT_RECORDS):
        raise ValidationError('导出记录超过上限，请按类型或日期分批导出。')
    content = json_bytes(payload)
    if len(content) > getattr(settings, 'PERSONAL_DATA_MAX_BYTES', DEFAULT_MAX_SNAPSHOT_BYTES):
        raise ValidationError('导出数据超过大小限制，请按类型或日期分批导出。')
    return json.loads(content)


def _cell(value):
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value if value is not None else '')
    return "'" + text if text.startswith(('=', '+', '-', '@', '\t', '\r')) else text


def render_export(export):
    if not export.snapshot:
        raise ValidationError('此旧导出未保存历史快照，请重新导出。')
    if export.format == 'json':
        return json_bytes(export.snapshot), 'application/json'
    rows = [('section', 'record', 'field', 'value')]
    for section, values in export.snapshot.items():
        if isinstance(values, list):
            for index, record in enumerate(values):
                for key, value in record.items():
                    rows.append((section, index + 1, key, _cell(value)))
        else:
            rows.append(('metadata', '', section, _cell(values)))
    if export.format == 'csv':
        stream = StringIO(newline='')
        csv.writer(stream).writerows(rows)
        return stream.getvalue().encode('utf-8-sig'), 'text/csv; charset=utf-8'
    from openpyxl import Workbook
    if any(isinstance(cell, str) and len(cell) > EXCEL_MAX_CELL_CHARACTERS for row in rows for cell in row):
        raise ValidationError('导出字段超过 Excel 单元格限制，请选择 JSON 或 CSV，避免内容截断。')
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet('Export')
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@transaction.atomic
def create_export(user, validated_data, *, is_backup=False):
    export = DataExport.objects.create(user=user, status='processing', is_backup=is_backup, **validated_data)
    export.snapshot = build_snapshot(export)
    export.file_name = f'export_{export.pk}.{export.format}'
    content, _ = render_export(export)
    export.file_size = len(content)
    export.status = 'completed'
    export.completed_at = timezone.now()
    export.save(update_fields=['snapshot', 'file_name', 'file_size', 'status', 'completed_at'])
    return export
