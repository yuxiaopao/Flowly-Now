"""Permission-scoped child executions with mapping, depth limits and queue truth."""
from config.application_messages import MESSAGES
import copy
import json
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.utils import timezone

MAX_SUBWORKFLOW_DEPTH = 8


class SubworkflowError(ValueError):
    pass


def configuration(config):
    result = dict(config or {})
    try:
        result['subworkflowId'] = str(UUID(str(result.get('subworkflowId', result.get('workflow_id', '')))))
    except (ValueError, TypeError):
        raise SubworkflowError(MESSAGES['select_child'])
    version = result.get('version', 'latest')
    if version != 'latest':
        if isinstance(version, bool) or not str(version).isdecimal() or int(version) < 1:
            raise SubworkflowError(MESSAGES['child_version'])
        version = int(version)
    result['version'] = version
    result.setdefault('executionMode', 'sync')
    result.setdefault('onError', 'stop')
    if result['executionMode'] not in ('sync', 'async') or result['onError'] not in ('stop', 'skip', 'fallback'):
        raise SubworkflowError(MESSAGES['child_mode'])
    try:
        timeout = float(result.get('timeout', 300))
        if not 0 < timeout <= 3600:
            raise ValueError
    except (ValueError, TypeError):
        raise SubworkflowError(MESSAGES['child_timeout'])
    result['timeout'] = timeout
    for key, names in (('inputMapping', ('parentVar', 'childParam')), ('outputMapping', ('childOutput', 'parentVar'))):
        mapping = result.get(key, [])
        if not isinstance(mapping, list) or len(mapping) > 100:
            raise SubworkflowError(MESSAGES['mapping_array'])
        destinations = set()
        for row in mapping:
            if not isinstance(row, dict) or set(row) != set(names) or any(not isinstance(row[name], str) or not row[name].strip() or len(row[name]) > 200 for name in names):
                raise SubworkflowError(MESSAGES['mapping_required'])
            if row[names[1]] in destinations or row[names[1]].startswith('_'):
                raise SubworkflowError(MESSAGES['mapping_destination'])
            destinations.add(row[names[1]])
        result[key] = copy.deepcopy(mapping)
    if result['onError'] == 'fallback':
        value = result.get('fallbackValue')
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                raise SubworkflowError(MESSAGES['fallback_json'])
        result['fallbackValue'] = value
    return result


def lookup(data, path):
    if isinstance(data, dict) and path in data:
        return data[path]
    value = data
    for part in path.split('.'):
        if not isinstance(value, dict) or part not in value:
            raise SubworkflowError(MESSAGES['mapped_missing'].format(path=path))
        value = value[part]
    return value


def mapped_input(context, mapping):
    original = context.get('input_data') if isinstance(context.get('input_data'), dict) else {}
    variables = context.get('variables') if isinstance(context.get('variables'), dict) else {}
    namespace = {**original, **context, **variables}
    if not mapping:
        return {**original, **variables}
    return {row['childParam']: copy.deepcopy(lookup(namespace, row['parentVar'])) for row in mapping}


def mapped_output(output, mapping):
    output = output if isinstance(output, dict) else {'result': output}
    variables = output.get('variables') if isinstance(output.get('variables'), dict) else {}
    namespace = {**output, **variables}
    return ({row['parentVar']: copy.deepcopy(lookup(namespace, row['childOutput'])) for row in mapping}
            if mapping else copy.deepcopy(variables or output))


def resolve_child(user, parent, config):
    from tenants.access import get_accessible_workflow_queryset
    child = get_accessible_workflow_queryset(user).filter(pk=config['subworkflowId']).first()
    if child is None:
        raise SubworkflowError(MESSAGES['child_unavailable'])
    if config['version'] != 'latest' and child.version != config['version']:
        raise SubworkflowError(MESSAGES['historical_version'])
    return child


def _trusted_child(parent_execution, config):
    """Hidden graph ids require a server-recorded manifest, never a user config flag."""
    from applications.models import ApplicationRequest
    from applications.access import request_authorized
    from applications.services import graph_definition, graph_digest
    from workflows.models import Workflow, WorkflowExecution
    request_id = (parent_execution.trigger_source or {}).get('application_request_id')
    root = ApplicationRequest.objects.select_related('application__owner', 'application__tenant', 'workflow_execution').filter(pk=request_id).first() if request_id else None
    if not root or not request_authorized(root):
        raise SubworkflowError(MESSAGES['app_child_revoked'])
    ancestor = parent_execution
    visited = set()
    while ancestor.pk != root.workflow_execution_id:
        if ancestor.pk in visited or len(visited) >= MAX_SUBWORKFLOW_DEPTH:
            raise SubworkflowError(MESSAGES['untrusted_ancestry'])
        visited.add(ancestor.pk)
        parent_id = (ancestor.trigger_source or {}).get('parent_execution_id')
        ancestor = WorkflowExecution.objects.filter(pk=parent_id).first() if parent_id else None
        if not ancestor:
            raise SubworkflowError(MESSAGES['child_root'])
    manifest = root.workflow_manifest or {}
    entry = manifest.get(config['subworkflowId'])
    parent_entry = manifest.get(str(parent_execution.workflow_id))
    if not entry or not parent_entry or config['subworkflowId'] not in parent_entry.get('children', []):
        raise SubworkflowError(MESSAGES['child_absent'])
    child = Workflow.all_objects.filter(pk=config['subworkflowId'], is_release_snapshot=True).first()
    if not child or graph_digest(graph_definition(child)) != entry['digest']:
        raise SubworkflowError(MESSAGES['child_integrity'])
    return child, entry['source_id'], entry.get('node_aliases', {})


def validate_child_execution(execution):
    """Recheck queued and running children, including children with no nested nodes."""
    from users.models import User
    from workflows.models import WorkflowExecution
    source = execution.trigger_source if isinstance(execution.trigger_source, dict) else {}
    parent_id = source.get('parent_execution_id')
    if not parent_id:
        return
    user = User.objects.filter(pk=execution.triggered_by_id, is_active=True).first()
    parent = WorkflowExecution.objects.select_related('workflow').filter(pk=parent_id).first()
    if not parent or not user or parent.triggered_by_id != user.pk:
        raise SubworkflowError(MESSAGES['child_identity'])
    if execution.workflow.is_release_snapshot:
        child, _, _ = _trusted_child(parent, {'subworkflowId': str(execution.workflow_id)})
        if child.pk != execution.workflow_id:
            raise SubworkflowError(MESSAGES['child_identity_manifest'])
    else:
        resolve_child(user, parent.workflow, {'subworkflowId': str(execution.workflow_id), 'version': execution.version})


def validate_application_execution(execution):
    from applications.models import ApplicationRequest
    from applications.access import request_authorized
    source = execution.trigger_source if isinstance(execution.trigger_source, dict) else {}
    request_id = source.get('application_request_id')
    if not request_id or source.get('parent_execution_id'):
        return
    record = ApplicationRequest.objects.select_related('application__owner', 'application__tenant', 'caller', 'api_key__created_by').filter(pk=request_id, workflow_execution=execution).first()
    if not record or not request_authorized(record):
        raise SubworkflowError(MESSAGES['application_permission'])


def execute_subworkflow(service, config, context):
    from users.models import User
    from workflows.models import WorkflowExecution
    from .workflow_executor import WorkflowExecutor
    parsed = configuration(config)
    parent_id = (context.get('metadata') or {}).get('execution_id')
    parent = WorkflowExecution.objects.select_related('workflow').filter(pk=parent_id).first() if parent_id else None
    user = User.objects.filter(pk=service.user_id, is_active=True).first()
    if not parent or not user or parent.triggered_by_id != user.pk:
        raise SubworkflowError(MESSAGES['trusted_parent'])
    chain = list((parent.trigger_source or {}).get('workflow_chain') or [str(parent.workflow_id)])
    if parent.workflow.is_release_snapshot:
        child, identity, node_aliases = _trusted_child(parent, parsed)
    else:
        child = resolve_child(user, parent.workflow, parsed)
        identity = str(child.pk)
        node_aliases = {}
    if identity in chain or len(chain) >= getattr(settings, 'WORKFLOW_MAX_SUBWORKFLOW_DEPTH', MAX_SUBWORKFLOW_DEPTH):
        raise SubworkflowError(MESSAGES['child_cycle'])
    if parent.status in ('cancelled', 'timeout', 'failed'):
        raise SubworkflowError(MESSAGES['parent_stopped'])
    inputs = mapped_input(context, parsed['inputMapping'])
    deadline = timezone.now() + timedelta(seconds=parsed['timeout'])
    from datetime import datetime
    inherited = config.get('_execution_deadline_at') or (parent.trigger_source or {}).get('deadline_at')
    if inherited:
        deadline = min(deadline, datetime.fromisoformat(inherited))
    metadata = {'parent_execution_id': str(parent.pk), 'workflow_chain': [*chain, identity],
                'node_aliases': node_aliases,
                'subworkflow_mode': parsed['executionMode'],
                'deadline_at': deadline.isoformat(), 'subworkflow_output_mapping': parsed['outputMapping'],
                'subworkflow_on_error': parsed['onError'], 'subworkflow_fallback': parsed.get('fallbackValue')}
    if (parent.trigger_source or {}).get('application_request_id'):
        metadata['application_request_id'] = parent.trigger_source['application_request_id']
    execution = WorkflowExecution.objects.create(workflow=child, tenant=child.tenant, triggered_by=user,
        input_data=inputs, version=child.version, trigger_type='api', trigger_source=metadata, status='pending')
    try:
        if parsed['executionMode'] == 'async':
            from workflows.tasks import execute_workflow_task
            try:
                task = execute_workflow_task.delay(str(execution.pk))
            except Exception:
                execution.mark_failed(error_message=MESSAGES['queue_failed_record'])
                raise SubworkflowError(MESSAGES['queue_failed'])
            WorkflowExecution.objects.filter(pk=execution.pk).update(task_id=task.id)
            WorkflowExecution.objects.filter(pk=execution.pk, status='pending').update(status='queued')
            execution.refresh_from_db()
            return {'success': True, 'output': {'child_execution_id': str(execution.pk), 'child_status': execution.status,
                    'task_id': task.id, 'output_mapping_status': 'ready' if execution.status == 'completed' else 'pending'}}
        WorkflowExecutor(child, execution, deadline_at=deadline).execute()
        execution.refresh_from_db()
        if execution.status != 'completed':
            raise SubworkflowError(MESSAGES['child_status'].format(status=execution.status))
        output = mapped_output(execution.output_data, parsed['outputMapping'])
        return {'success': True, 'output': {**output, 'child_execution_id': str(execution.pk), 'child_status': execution.status}}
    except Exception as exc:
        if execution.status in ('pending', 'queued', 'running'):
            execution.mark_failed(error_message=str(exc))
        if parsed['onError'] == 'skip':
            return {'success': True, 'skipped': True, 'output': {'child_execution_id': str(execution.pk), 'child_status': execution.status}}
        if parsed['onError'] == 'fallback':
            return {'success': True, 'used_fallback': True, 'output': parsed.get('fallbackValue')}
        return {'success': False, 'error': str(exc), 'error_type': 'subworkflow', 'child_execution_id': str(execution.pk)}
