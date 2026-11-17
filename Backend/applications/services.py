"""Delivery operations reuse real RAG and WorkflowExecution paths."""
from config.application_messages import MESSAGES
import copy
import hashlib
import json
import logging
import time
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .access import can_edit, can_publish, visible_applications, request_authorized
from .constants import MAX_OUTPUT_BYTES, RATE_PER_MINUTE, MAX_CONCURRENT, MAX_EXECUTION_SECONDS, LEASE_GRACE_SECONDS
from .models import Application, ApplicationRelease, ApplicationRequest

logger = logging.getLogger(__name__)


class ApplicationFailure(Exception):
    def __init__(self, message, code='invalid_source', status=409):
        super().__init__(message)
        self.code, self.status = code, status


def json_value(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder, allow_nan=False))


def resolve_source(application, configuration=None):
    configuration = configuration or application.draft
    if not application.owner.is_active:
        raise ApplicationFailure(MESSAGES['owner_inactive'], 'permission_revoked', 403)
    if application.tenant_id and not can_edit(application.owner, application):
        raise ApplicationFailure(MESSAGES['owner_team'], 'permission_revoked', 403)
    if application.kind == 'knowledge':
        from rag.models import DocumentCollection
        source = DocumentCollection.objects.select_related('vector_store', 'owner', 'tenant').filter(pk=configuration.get('collection_id')).first()
    else:
        from workflows.models import Workflow
        source = Workflow.objects.filter(pk=configuration.get('workflow_id'), is_deleted=False).first()
    if (source is None or source.tenant_id != application.tenant_id or
            not application.tenant_id and source.owner_id != application.owner_id):
        raise ApplicationFailure(MESSAGES['source_scope'], 'source_unavailable', 409)
    if application.kind == 'knowledge':
        store = source.vector_store
        if store.tenant_id != application.tenant_id or not application.tenant_id and store.owner_id != application.owner_id:
            raise ApplicationFailure(MESSAGES['source_scope'], 'source_unavailable', 409)
    return source


def graph_definition(workflow):
    """Capture all executable model fields, including fields omitted by editor serializers."""
    def fields(instance, excluded):
        return {field.attname: json_value(getattr(instance, field.attname))
                for field in instance._meta.concrete_fields if field.name not in excluded}
    nodes = [fields(node, {'workflow', 'created_at', 'updated_at'}) for node in workflow.nodes.order_by('id')]
    edges = [fields(edge, {'workflow', 'created_at', 'updated_at'}) for edge in workflow.edges.order_by('id')]
    return {'config': copy.deepcopy(workflow.config), 'nodes': nodes, 'edges': edges}


def draft_fingerprint(application):
    source = resolve_source(application)
    definition = capture_workflow_tree(application, source) if application.kind == 'workflow' else knowledge_definition(source)
    payload = {'kind': application.kind, 'draft': application.draft, 'graph': definition}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, cls=DjangoJSONEncoder, allow_nan=False).encode()).hexdigest()
    return digest, definition


def graph_digest(definition):
    return hashlib.sha256(json.dumps(definition, sort_keys=True, ensure_ascii=False, cls=DjangoJSONEncoder, allow_nan=False).encode()).hexdigest()


def capture_workflow_tree(application, workflow, chain=(), budget=None):
    from workflows.services.subworkflow import configuration, resolve_child, SubworkflowError, MAX_SUBWORKFLOW_DEPTH
    identity = str(workflow.pk)
    if identity in chain or len(chain) >= getattr(settings, 'WORKFLOW_MAX_SUBWORKFLOW_DEPTH', MAX_SUBWORKFLOW_DEPTH):
        raise ApplicationFailure(MESSAGES['child_cycle'], 'subworkflow_cycle', 409)
    result = graph_definition(workflow)
    budget = [0] if budget is None else budget
    budget[0] += len(result['nodes'])
    if budget[0] > getattr(settings, 'APPLICATION_MAX_SNAPSHOT_NODES', 500):
        raise ApplicationFailure(MESSAGES['graph_limit'], 'graph_limit', 413)
    result.update(source_id=identity, source_version=workflow.version, children={})
    for node in result['nodes']:
        if node['node_type'] == 'subworkflow':
            try:
                parsed = configuration(node['config'])
                child = resolve_child(application.owner, workflow, parsed)
            except SubworkflowError as exc:
                raise ApplicationFailure(str(exc), 'invalid_subworkflow', 409) from exc
            if child.tenant_id != application.tenant_id or not application.tenant_id and child.owner_id != application.owner_id:
                raise ApplicationFailure(MESSAGES['nested_scope'], 'source_unavailable', 409)
            result['children'][node['id']] = capture_workflow_tree(application, child, (*chain, identity), budget)
    return result


def knowledge_definition(collection):
    fields = ('embedding_model', 'retrieval_mode', 'chunk_size', 'chunk_overlap', 'chunk_strategy')
    store_fields = ('store_type', 'host', 'port', 'collection', 'path', 'dimension', 'metric')
    return {'collection': {name: getattr(collection, name) for name in fields},
            'vector_store_id': str(collection.vector_store_id),
            'vector_store': {name: getattr(collection.vector_store, name) for name in store_fields}}


def clone_workflow(application, definition):
    """Real database graph; freeze only after its complete nodes/edges are inserted."""
    from workflows.models import Workflow, Node, Edge
    import uuid

    snapshot = Workflow.all_objects.create(owner=application.owner, tenant=application.tenant,
        name=f'[application snapshot] {application.name}'[:200], status='archived',
        is_public=False, config=copy.deepcopy(definition['config'] or {}), version=definition.get('source_version', 1))
    children = {node_id: clone_workflow(application, tree) for node_id, tree in definition.get('children', {}).items()}
    ids = {node['id']: str(uuid.uuid4()) for node in definition['nodes']}

    # Parent references can point forward. Create first, then populate them.
    for row in definition['nodes']:
        data = copy.deepcopy(row)
        data['id'] = ids[data['id']]
        data.pop('parent_node_id', None)
        if row['id'] in children:
            data['config']['subworkflowId'] = str(children[row['id']].pk)
            data['config']['version'] = children[row['id']].version
        Node.objects.create(workflow=snapshot, **data)
    for row in definition['nodes']:
        if row.get('parent_node_id'):
            Node.objects.filter(pk=ids[row['id']]).update(parent_node_id=ids[row['parent_node_id']])
    for row in definition['edges']:
        data = copy.deepcopy(row)
        data.pop('id')
        data['source_node_id'] = ids[data['source_node_id']]
        data['target_node_id'] = ids[data['target_node_id']]
        Edge.objects.create(workflow=snapshot, **data)
    Workflow.all_objects.filter(pk=snapshot.pk).update(is_release_snapshot=True)
    snapshot.is_release_snapshot = True
    manifest = {}
    for child in children.values():
        manifest.update(child._application_manifest)
    manifest[str(snapshot.pk)] = {'source_id': definition.get('source_id', str(snapshot.pk)),
        'version': snapshot.version, 'digest': graph_digest(graph_definition(snapshot)),
        'node_aliases': ids,
        'children': [str(child.pk) for child in children.values()]}
    snapshot._application_manifest = manifest
    return snapshot


@transaction.atomic
def publish_application(application, user):
    application = Application.objects.select_for_update().select_related('owner', 'tenant').get(pk=application.pk)
    if not visible_applications(user).filter(pk=application.pk).exists() or not can_publish(user, application):
        raise ApplicationFailure(MESSAGES['publisher_revoked'], 'permission_revoked', 403)
    if application.kind == 'knowledge':
        from rag.models import DocumentCollection
        source = resolve_source(application)
        # Ingestion and removal share this lock, so evidence stays current until commit.
        DocumentCollection.objects.select_for_update().get(pk=source.pk)
    fingerprint, definition = draft_fingerprint(application)
    from .evaluation_service import required_evaluation_evidence
    evaluation = required_evaluation_evidence(application, fingerprint, lock=True)
    if application.last_test_status != 'completed' or application.tested_fingerprint != fingerprint:
        raise ApplicationFailure(MESSAGES['test_required'], 'test_required', 409)
    validation = application.requests.filter(mode='test', status='completed', fingerprint=fingerprint,
        created_at=application.last_test_at).first()
    if not validation:
        raise ApplicationFailure(MESSAGES['test_required'], 'test_required', 409)
    last_version = application.releases.aggregate(number=Max('version'))['number'] or 0
    snapshot = clone_workflow(application, definition) if application.kind == 'workflow' else None
    configuration = copy.deepcopy(application.draft)
    if application.kind == 'knowledge':
        configuration['collection_settings'] = definition
    release = ApplicationRelease.objects.create(application=application, version=last_version + 1,
        fingerprint=fingerprint, configuration=configuration, workflow_snapshot=snapshot,
        workflow_manifest=snapshot._application_manifest if snapshot else {}, validated_by_request=validation,
        validated_by_evaluation=evaluation, created_by=user)
    application.active_release = release
    application.save(update_fields=['active_release', 'updated_at'])
    return release


def _knowledge_input(input_data):
    if set(input_data) - {'query', 'filters'}:
        raise ApplicationFailure(MESSAGES['knowledge_input'], 'invalid_input', 422)
    query = input_data.get('query')
    if not isinstance(query, str) or not query.strip() or len(query) > 4000:
        raise ApplicationFailure(MESSAGES['invalid_query'], 'invalid_input', 422)
    filters = input_data.get('filters', {})
    if not isinstance(filters, dict) or any(not isinstance(k, str) or isinstance(v, (dict, list)) for k, v in filters.items()):
        raise ApplicationFailure(MESSAGES['filters'], 'invalid_input', 422)
    return query, filters


def execute_record(record, application, configuration, definition=None, snapshot=None):
    if application.kind == 'knowledge':
        from rag.services import RAGService
        source = resolve_source(application, configuration)
        pinned = configuration.get('collection_settings') or definition
        if pinned:
            from rag.models import VectorStore
            source = copy.copy(source)
            for name, value in pinned['collection'].items():
                setattr(source, name, value)
            store = VectorStore.objects.filter(pk=pinned['vector_store_id']).first()
            if not store:
                raise ApplicationFailure(MESSAGES['store_unavailable'], 'source_unavailable', 409)
            if store.tenant_id != application.tenant_id or not application.tenant_id and store.owner_id != application.owner_id:
                raise ApplicationFailure(MESSAGES['source_scope'], 'source_unavailable', 409)
            store = copy.copy(store)
            for name, value in pinned['vector_store'].items():
                setattr(store, name, value)
            source.vector_store = store
        query, filters = _knowledge_input(record.input_data)
        from workflows.services.execution_budget import remaining_seconds
        service = RAGService(source, configuration['top_k'], configuration['min_similarity'])
        service.embedding_service.timeout = remaining_seconds(record.deadline_at)
        retrieved = service.retrieve(query, filters)
        remaining = remaining_seconds(record.deadline_at)
        result = service.generate_response(query, retrieved, configuration['system_prompt'], timeout=remaining)
        if result.get('answer_status') != 'answered' or not result.get('grounded'):
            record.output_data = json_value(result)
            raise ApplicationFailure(MESSAGES['no_evidence'], 'no_evidence', 422)
        return json_value(result)
    from workflows.models import WorkflowExecution
    from workflows.services.workflow_validation import validate_workflow
    from workflows.services.workflow_executor import WorkflowExecutor
    if snapshot is None:
        with transaction.atomic():
            snapshot = clone_workflow(application, definition)
        record.workflow_manifest = snapshot._application_manifest
    elif record.release_id:
        record.workflow_manifest = copy.deepcopy(record.release.workflow_manifest)
    if not snapshot.is_release_snapshot:
        raise ApplicationFailure(MESSAGES['snapshot_unavailable'], 'snapshot_unavailable', 409)
    manifest_entry = record.workflow_manifest.get(str(snapshot.pk))
    if not manifest_entry or graph_digest(graph_definition(snapshot)) != manifest_entry['digest']:
        raise ApplicationFailure(MESSAGES['snapshot_integrity'], 'snapshot_unavailable', 409)
    preflight = validate_workflow(snapshot, record.input_data)
    if not preflight['valid']:
        raise ApplicationFailure(MESSAGES['workflow_validation'] + '; '.join(preflight['errors']), 'workflow_validation', 422)
    with transaction.atomic():
        current = ApplicationRequest.objects.select_for_update().get(pk=record.pk)
        if current.status != 'running':
            raise ApplicationFailure(current.error_message or MESSAGES['lease_stop'], current.error_code or 'execution_cancelled', current.http_status)
        execution = WorkflowExecution.objects.create(workflow=snapshot, tenant=application.tenant,
            triggered_by=application.owner, input_data=record.input_data, version=record.release.version if record.release_id else 1,
            trigger_type='api', trigger_source={'application_id': str(application.pk), 'application_request_id': str(record.pk),
                'node_aliases': manifest_entry.get('node_aliases', {}), 'workflow_chain': [manifest_entry['source_id']]}, status='pending')
        record.workflow_execution = execution
        record.save(update_fields=['workflow_execution', 'workflow_manifest'])
    WorkflowExecutor(snapshot, execution, deadline_at=record.deadline_at).execute()
    execution.refresh_from_db()
    if execution.status != 'completed':
        raise ApplicationFailure(MESSAGES['workflow_failed'], 'workflow_failed', 503)
    if isinstance(execution.token_usage, dict):
        total = execution.token_usage.get('total_tokens')
        if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            record.total_tokens = total
    if execution.cost_amount is not None:
        record.cost, record.currency = Decimal(execution.cost_amount), execution.cost_currency
    return json_value(execution.output_data)


@transaction.atomic
def recover_expired_requests(application):
    """A lost owner becomes an explicit failed request, never a fabricated success."""
    from django.db.models import Q
    from workflows.models import WorkflowExecution
    locked = Application.objects.select_for_update().get(pk=application.pk)
    now = timezone.now()
    timeout = max(0.01, float(getattr(settings, 'APPLICATION_MAX_EXECUTION_SECONDS', MAX_EXECUTION_SECONDS)))
    grace = max(0, float(getattr(settings, 'APPLICATION_LEASE_GRACE_SECONDS', LEASE_GRACE_SECONDS)))
    stale = locked.requests.filter(status='running').filter(
        Q(lease_expires_at__lte=now) | Q(lease_expires_at__isnull=True, created_at__lte=now - timedelta(seconds=timeout + grace)))
    execution_ids = list(stale.exclude(workflow_execution_id=None).values_list('workflow_execution_id', flat=True))
    stale_test_ids = list(stale.filter(mode='test').values_list('pk', flat=True))
    changed = stale.update(status='failed', error_code='lease_expired', http_status=504,
        error_message=MESSAGES['lease_expired'], completed_at=now)
    if execution_ids:
        WorkflowExecution.objects.filter(pk__in=execution_ids, status__in=WorkflowExecution.ACTIVE_STATUSES).update(
            status='cancelled', error_message=MESSAGES['lease_stop'], completed_at=now)
    for record in ApplicationRequest.objects.filter(pk__in=stale_test_ids):
        _record_test_result(locked, record)
    return changed


def reconcile_pending_tests(application):
    """Publishing cannot treat successful queue admission as a passed child execution."""
    from workflows.models import WorkflowExecution
    pending = application.requests.filter(mode__in=('test', 'evaluation'), status='running', workflow_execution__status='completed')
    for record in pending:
        children = WorkflowExecution.objects.filter(trigger_source__application_request_id=str(record.pk)).exclude(pk=record.workflow_execution_id)
        if children.filter(status__in=WorkflowExecution.ACTIVE_STATUSES).exists():
            continue
        failed = children.filter(trigger_source__subworkflow_mode='async').exclude(status='completed').exists()
        now = timezone.now()
        updates = {'status': 'failed' if failed else 'completed', 'http_status': 503 if failed else 200,
                   'completed_at': now, 'latency_ms': max(0, int((now - record.created_at).total_seconds() * 1000))}
        if failed:
            updates.update(error_code='child_failed', error_message=MESSAGES['workflow_failed'])
        if ApplicationRequest.objects.filter(pk=record.pk, status='running').update(**updates):
            record.refresh_from_db()
            if record.mode == 'test':
                _record_test_result(application, record)


@transaction.atomic
def _record_test_result(application, record):
    current = Application.objects.select_for_update().select_related('owner', 'tenant').get(pk=application.pk)
    try:
        unchanged = draft_fingerprint(current)[0] == record.fingerprint
    except ApplicationFailure:
        unchanged = False
    if not current.last_test_at or current.last_test_at <= record.created_at:
        current.tested_fingerprint = record.fingerprint if unchanged and record.status == 'completed' else ''
        current.last_test_status = record.status if unchanged else 'stale'
        current.last_test_at = record.created_at
        current.save(update_fields=['tested_fingerprint', 'last_test_status', 'last_test_at', 'updated_at'])


def run_application(application, user, input_data, mode, api_key=None, idempotency_token=None,
                    *, evaluation_target=None, on_admitted=None, timeout_seconds=None):
    """Commit admission before running; persistent running rows enforce multi-process capacity."""
    started = time.monotonic()
    if mode not in ('test', 'invoke', 'evaluation'):
        raise ApplicationFailure(MESSAGES['execution_unavailable'], 'invalid_mode', 400)
    if mode == 'evaluation':
        from .evaluation_service import EvaluationTarget
        if not isinstance(evaluation_target, EvaluationTarget) or str(evaluation_target.application_id) != str(application.pk):
            raise ApplicationFailure(MESSAGES['execution_unavailable'], 'invalid_evaluation_target', 400)
    with transaction.atomic():
        locked = Application.objects.select_for_update().select_related('owner', 'tenant', 'active_release__workflow_snapshot').get(pk=application.pk)
        if not visible_applications(user).filter(pk=locked.pk).exists() or not can_edit(user, locked):
            raise ApplicationFailure(MESSAGES['invocation_revoked'], 'permission_revoked', 403)
        if api_key:
            api_key = type(api_key).objects.select_for_update().get(pk=api_key.pk)
            if not api_key.is_active or not can_publish(user, locked):
                raise ApplicationFailure(MESSAGES['revoked_key'], 'permission_revoked', 401)
        if mode == 'invoke' and not locked.active_release_id:
            raise ApplicationFailure(MESSAGES['not_published'], 'not_published', 409)
        now = timezone.now()
        timeout = max(0.01, float(getattr(settings, 'APPLICATION_MAX_EXECUTION_SECONDS', MAX_EXECUTION_SECONDS)))
        if timeout_seconds is not None:
            timeout = min(timeout, max(.01, float(timeout_seconds)))
        grace = max(0, float(getattr(settings, 'APPLICATION_LEASE_GRACE_SECONDS', LEASE_GRACE_SECONDS)))
        recover_expired_requests(locked)
        reconcile_pending_tests(locked)
        idempotency_hash = None
        if idempotency_token is not None:
            actor = f'key:{api_key.pk}' if api_key else f'user:{user.pk}'
            idempotency_hash = hashlib.sha256(f'{actor}:{mode}:{idempotency_token}'.encode()).hexdigest()
            existing = locked.requests.filter(idempotency_hash=idempotency_hash).first()
            if existing:
                if existing.input_data != input_data:
                    raise ApplicationFailure(MESSAGES['idempotency_conflict'], 'idempotency_conflict', 409)
                return existing, 202 if existing.status == 'running' else existing.http_status
        release = locked.active_release if mode == 'invoke' else None
        if mode == 'evaluation' and evaluation_target.release_id:
            release = ApplicationRelease.objects.filter(pk=evaluation_target.release_id, application=locked).first()
            if not release:
                raise ApplicationFailure(MESSAGES['snapshot_unavailable'], 'snapshot_unavailable', 409)
        recent = locked.requests.filter(created_at__gte=timezone.now() - timedelta(minutes=1))
        rejection = None
        if recent.count() >= getattr(settings, 'APPLICATION_RATE_PER_MINUTE', RATE_PER_MINUTE):
            rejection = ('rate_limit', MESSAGES['rate_limit'])
        elif locked.requests.filter(status='running').count() >= getattr(settings, 'APPLICATION_MAX_CONCURRENT', MAX_CONCURRENT):
            rejection = ('concurrency_limit', MESSAGES['concurrency_limit'])
        record = ApplicationRequest.objects.create(application=locked, caller=user, api_key=api_key, release=release,
            mode=mode, input_data=input_data, status='rejected' if rejection else 'running',
            deadline_at=now + timedelta(seconds=timeout), lease_expires_at=now + timedelta(seconds=timeout + grace), idempotency_hash=idempotency_hash)
        if rejection:
            record.error_code, record.error_message = rejection
            record.latency_ms, record.completed_at = 0, timezone.now()
            record.http_status = 429
            record.save()
            return record, 429
        if mode == 'test':
            locked.tested_fingerprint = ''
            locked.last_test_status, locked.last_test_at = 'running', record.created_at
            locked.save(update_fields=['tested_fingerprint', 'last_test_status', 'last_test_at', 'updated_at'])
        if api_key:
            type(api_key).objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
    status_code = 200
    try:
        if on_admitted is not None and not on_admitted(record):
            record.refresh_from_db()
            return record, record.http_status
        if mode == 'evaluation':
            from workflows.models import Workflow
            configuration = copy.deepcopy(evaluation_target.configuration)
            definition = None
            snapshot = Workflow.all_objects.filter(pk=evaluation_target.snapshot_id).first() if evaluation_target.snapshot_id else None
            record.fingerprint = evaluation_target.fingerprint
            record.workflow_manifest = copy.deepcopy(evaluation_target.manifest)
            ApplicationRequest.objects.filter(pk=record.pk, status='running').update(fingerprint=record.fingerprint, workflow_manifest=record.workflow_manifest)
            if locked.kind == 'knowledge':
                resolve_source(locked, configuration)
            elif snapshot is None:
                raise ApplicationFailure(MESSAGES['snapshot_unavailable'], 'snapshot_unavailable', 409)
        elif mode == 'test':
            record.fingerprint, definition = draft_fingerprint(locked)
            ApplicationRequest.objects.filter(pk=record.pk, status='running').update(fingerprint=record.fingerprint)
            configuration = copy.deepcopy(locked.draft)
            snapshot = None
        else:
            configuration = copy.deepcopy(release.configuration)
            definition, snapshot = None, release.workflow_snapshot
            record.fingerprint = release.fingerprint
            if locked.kind == 'workflow':
                if not locked.owner.is_active or locked.tenant_id and not can_edit(locked.owner, locked):
                    raise ApplicationFailure(MESSAGES['resource_revoked'], 'permission_revoked', 403)
            else:
                resolve_source(locked, configuration)
        record.output_data = execute_record(record, locked, configuration, definition, snapshot)
        if not request_authorized(record):
            record.output_data = None
            raise ApplicationFailure(MESSAGES['result_revoked'], 'permission_revoked', 403)
        if locked.kind == 'knowledge':
            resolve_source(locked, configuration)
        if timezone.now() >= record.deadline_at:
            record.output_data = None
            raise ApplicationFailure(MESSAGES['deadline_effects'], 'execution_timeout', 504)
        if len(json.dumps(record.output_data, ensure_ascii=False).encode()) > MAX_OUTPUT_BYTES:
            record.output_data = None
            raise ApplicationFailure(MESSAGES['output_limit'], 'output_limit', 413)
        record.status = 'completed'
        if mode in ('test', 'evaluation') and locked.kind == 'workflow':
            from workflows.models import WorkflowExecution
            children = WorkflowExecution.objects.filter(trigger_source__application_request_id=str(record.pk)).exclude(pk=record.workflow_execution_id)
            if children.filter(status__in=WorkflowExecution.ACTIVE_STATUSES).exists():
                record.status, status_code = 'running', 202
            elif children.filter(trigger_source__subworkflow_mode='async').exclude(status='completed').exists():
                raise ApplicationFailure(MESSAGES['workflow_failed'], 'child_failed', 503)
    except ApplicationFailure as exc:
        record.status, record.error_code, record.error_message = 'failed', exc.code, str(exc)
        status_code = exc.status
    except Exception as exc:
        from rag.pipeline import RAGUnavailable
        record.status, record.error_code = 'failed', 'upstream_unavailable' if isinstance(exc, RAGUnavailable) else 'execution_failed'
        record.error_message = str(exc) if isinstance(exc, RAGUnavailable) else MESSAGES['execution_unavailable']
        status_code = 503
        logger.warning('Application request %s failed (%s)', record.pk, type(exc).__name__)
    record.latency_ms = max(0, int((time.monotonic() - started) * 1000))
    record.completed_at = None if record.status == 'running' else timezone.now()
    if record.completed_at and record.completed_at >= record.deadline_at and record.status != 'completed':
        status_code, record.error_code = 504, 'execution_timeout'
        record.error_message = MESSAGES['deadline_effects']
    record.http_status = status_code
    updates = {field.attname: getattr(record, field.attname) for field in record._meta.concrete_fields
               if field.name not in ('id', 'application', 'release', 'caller', 'api_key', 'created_at', 'input_data', 'idempotency_hash')}
    if not ApplicationRequest.objects.filter(pk=record.pk, status='running').update(**updates):
        record.refresh_from_db()
        return record, record.http_status
    if mode == 'test':
        _record_test_result(application, record)
    return record, status_code
