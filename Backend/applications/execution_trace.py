"""Minimal read-only evidence for the main execution linked by an application request."""
import re

from django.shortcuts import get_object_or_404
from workflows.models import WorkflowExecution

MAX_ERROR_CHARS = 300
URL_PATTERN = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
CREDENTIAL_PATTERN = re.compile(
    r'''\b(?:api[-_ ]?key|access[-_ ]?token|refresh[-_ ]?token|token|password|secret|authorization)["']?\s*[:=]\s*(?:(?:Bearer|Basic)\s+)?(?:"[^"]*"|'[^']*'|[^\s,;]+)''',
    re.IGNORECASE)
BEARER_PATTERN = re.compile(r'\b(?:Bearer|Basic)\s+[^\s,;]+', re.IGNORECASE)


def short_error(value):
    if not value:
        return ''
    line = str(value).splitlines()[0]
    line = URL_PATTERN.sub('[URL]', line)
    line = CREDENTIAL_PATTERN.sub('[凭据已隐藏]', line)
    line = BEARER_PATTERN.sub('[凭据已隐藏]', line)
    return ' '.join(line.split())[:MAX_ERROR_CHARS]


def execution_summary(record):
    execution = get_object_or_404(WorkflowExecution.objects.only('id', 'workflow_id', 'status', 'started_at', 'completed_at'),
        pk=record.workflow_execution_id, application_requests=record)
    manifest = record.workflow_manifest if isinstance(record.workflow_manifest, dict) else {}
    entry = manifest.get(str(execution.workflow_id), {})
    aliases = entry.get('node_aliases', {}) if isinstance(entry, dict) else {}
    source_ids = {target: source for source, target in aliases.items() if isinstance(source, str) and isinstance(target, str)} if isinstance(aliases, dict) else {}
    rows = execution.node_executions.order_by('created_at', 'id').values('node_id', 'node__name', 'node__node_type',
        'status', 'started_at', 'completed_at', 'error_message')
    return {'id': execution.pk, 'status': execution.status, 'started_at': execution.started_at,
        'completed_at': execution.completed_at, 'nodes': [
            {'node_id': source_ids.get(str(row['node_id']), str(row['node_id'])), 'node_name': row['node__name'],
             'node_type': row['node__node_type'], 'status': row['status'], 'started_at': row['started_at'],
             'completed_at': row['completed_at'], 'error_message': short_error(row['error_message'])}
            for row in rows]}
