"""Frozen application regression batches with real requests and durable cancellation."""
import copy
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from . import evaluation_constants as limits
from .access import can_edit, visible_applications
from .evaluation_assertions import check_assertions
from .models import (Application, ApplicationRelease, ApplicationRequest, ApplicationTestSuite,
                     ApplicationTestCase, ApplicationEvaluationRun, ApplicationEvaluationResult)
from .services import (ApplicationFailure, clone_workflow, draft_fingerprint, json_value,
                       resolve_source, run_application, recover_expired_requests, reconcile_pending_tests)


@dataclass(frozen=True)
class EvaluationTarget:
    application_id: object
    configuration: dict
    fingerprint: str
    snapshot_id: object = None
    manifest: dict = None
    release_id: object = None


def digest(value):
    return hashlib.sha256(json.dumps(json_value(value), sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def case_payload(case):
    return {'name': case.name, 'input_data': case.input_data, 'assertions': case.assertions}


def corpus_signature(application, configuration=None):
    if application.kind != 'knowledge':
        return ''
    from rag.models import Chunk, Document
    source = resolve_source(application, configuration)
    hasher = hashlib.sha256()
    for row in Document.objects.filter(collection=source).order_by('id').values('id', 'title', 'status', 'updated_at'):
        hasher.update(json.dumps(json_value(row), sort_keys=True, ensure_ascii=False).encode())
    for row in Chunk.objects.filter(document__collection=source, document__status='completed').order_by('id').values('id', 'document_id', 'content', 'metadata', 'vector_id'):
        hasher.update(json.dumps(json_value(row), sort_keys=True, ensure_ascii=False).encode())
    return hasher.hexdigest()


def required_evaluation_evidence(application, fingerprint, *, lock=False):
    if not application.required_evaluation_suite_id:
        return None
    query = ApplicationTestSuite.objects.select_for_update() if lock else ApplicationTestSuite.objects
    suite = query.get(pk=application.required_evaluation_suite_id)
    count = suite.cases.filter(enabled=True).count()
    candidates = suite.runs.filter(application=application, target='draft', status='completed',
        suite_revision=suite.revision, fingerprint=fingerprint, total=count, passed=count,
        failed=0, errors=0, skipped=0)
    signature = corpus_signature(application)
    evidence = candidates.filter(corpus_signature=signature, final_corpus_signature=signature).first() if count and not suite.is_deleted else None
    if not evidence:
        raise ApplicationFailure(limits.MESSAGES['gate'], 'evaluation_required', 409)
    return evidence


def run_is_stale(run, cache=None):
    cache = {} if cache is None else cache
    if run.suite.is_deleted or run.suite.revision != run.suite_revision:
        return True
    if run.target == 'draft':
        try:
            key = ('fingerprint', run.application_id)
            if key not in cache:
                cache[key] = draft_fingerprint(run.application)[0]
            if cache[key] != run.fingerprint:
                return True
        except ApplicationFailure:
            return True
    try:
        key = ('corpus', run.application_id, run.configuration.get('collection_id'))
        if key not in cache:
            cache[key] = corpus_signature(run.application, run.configuration)
        return cache[key] != run.corpus_signature
    except ApplicationFailure:
        return True


def _authorized(run):
    user = run.created_by
    return bool(user and user.is_active and visible_applications(user).filter(pk=run.application_id).exists()
                and can_edit(user, run.application) and can_edit(run.application.owner, run.application))


def _cancel_request(record, message, code='evaluation_cancelled', http_status=499):
    from workflows.models import WorkflowExecution
    ApplicationRequest.objects.filter(pk=record.pk, status='running').update(status='failed', http_status=http_status,
        error_code=code, error_message=message, output_data=None, completed_at=timezone.now())
    WorkflowExecution.objects.filter(trigger_source__application_request_id=str(record.pk),
        status__in=WorkflowExecution.ACTIVE_STATUSES).update(status='cancelled', error_message=message, completed_at=timezone.now())


@transaction.atomic
def stop_run(run_id, *, failed=False, code='cancelled', message=None):
    run = ApplicationEvaluationRun.objects.select_for_update().get(pk=run_id)
    if run.status not in limits.ACTIVE_RUN_STATUSES:
        return run
    if run.status == 'cancelling':
        failed, code, message = False, 'cancelled', limits.MESSAGES['cancelled']
    message = message or limits.MESSAGES['cancelled']
    final = 'failed' if failed else 'cancelled'
    for record in ApplicationRequest.objects.filter(evaluation_results__run=run, status='running'):
        _cancel_request(record, message, code if failed else 'evaluation_cancelled',
                        403 if code == 'permission_revoked' else 504 if code in ('evaluation_timeout', 'lease_expired') else 503 if failed else 499)
    now = timezone.now()
    run.results.filter(status='pending').update(status='skipped' if failed else 'cancelled',
        error_code=code, error_message=message, completed_at=now)
    run.results.filter(status='running').update(status='error' if failed else 'cancelled',
        error_code=code, error_message=message, completed_at=now)
    run.status, run.error_code, run.error_message, run.completed_at = final, code, message, now
    _counts(run)
    run.save()
    return run


def recover_run(run):
    if run.status in limits.ACTIVE_RUN_STATUSES and run.lease_expires_at <= timezone.now():
        if run.status == 'cancelling':
            return stop_run(run.pk)
        code = 'queue_expired' if run.status == 'queued' else 'lease_expired'
        return stop_run(run.pk, failed=True, code=code,
            message=limits.MESSAGES['queue_expired' if run.status == 'queued' else 'expired'])
    return run


@transaction.atomic
def cancel_run(run):
    # Keep "cancelling" visible until the worker acknowledges its in-flight call.
    run = ApplicationEvaluationRun.objects.select_for_update().get(pk=run.pk)
    if run.status == 'queued':
        return stop_run(run.pk)
    if run.status == 'running':
        run.status, run.error_code, run.error_message = 'cancelling', 'cancelled', limits.MESSAGES['cancelled']
        run.save(update_fields=['status', 'error_code', 'error_message'])
        run.results.filter(status='pending').update(status='cancelled', error_code='cancelled',
            error_message=limits.MESSAGES['cancelled'], completed_at=timezone.now())
        for record in ApplicationRequest.objects.filter(evaluation_results__run=run, status='running'):
            _cancel_request(record, limits.MESSAGES['cancelled'])
        _counts(run)
        run.save(update_fields=['passed', 'failed', 'errors', 'skipped'])
    return run


def _counts(run):
    counts = dict(run.results.values('status').annotate(count=Count('id')).values_list('status', 'count'))
    run.passed, run.failed, run.errors = (counts.get(key, 0) for key in ('passed', 'failed', 'error'))
    run.skipped = counts.get('skipped', 0) + counts.get('cancelled', 0)


def start_run(application, user, data, idempotency_token=None):
    parameters_hash = digest(data)
    token_hash = digest({'user': user.pk, 'key': idempotency_token}) if idempotency_token else None
    if not _can_start(user, application):
        raise ApplicationFailure(limits.MESSAGES['permission'], 'permission_revoked', 403)
    # Recover independently before locking the app/suite, preserving a single lock order.
    for previous in application.evaluation_runs.filter(status__in=limits.ACTIVE_RUN_STATUSES):
        recover_run(previous)
    with transaction.atomic():
        app = Application.objects.select_for_update().select_related('owner', 'tenant').get(pk=application.pk)
        if not _can_start(user, app):
            raise ApplicationFailure(limits.MESSAGES['permission'], 'permission_revoked', 403)
        if token_hash:
            previous = app.evaluation_runs.filter(idempotency_hash=token_hash).first()
            if previous:
                if previous.parameters_hash != parameters_hash:
                    raise ApplicationFailure(limits.MESSAGES['idempotency'], 'idempotency_conflict', 409)
                return previous, False
        if app.evaluation_runs.filter(status__in=limits.ACTIVE_RUN_STATUSES).count() >= getattr(settings, 'APPLICATION_MAX_ACTIVE_EVALUATIONS', limits.MAX_ACTIVE_RUNS):
            raise ApplicationFailure(limits.MESSAGES['busy'], 'evaluation_busy', 409)
        suite = ApplicationTestSuite.objects.select_for_update().filter(pk=data['suite_id'], application=app, is_deleted=False).first()
        if not suite:
            raise ApplicationFailure(limits.MESSAGES['suite_missing'], 'suite_unavailable', 404)
        cases = suite.cases.filter(enabled=True)
        selected = data.get('case_ids')
        if selected:
            cases = cases.filter(pk__in=selected)
        cases = list(cases)
        if not cases or selected and len(cases) != len(selected):
            raise ApplicationFailure(limits.MESSAGES['empty_suite'], 'empty_suite', 400)
        release, snapshot, manifest = None, None, {}
        if data['target'] == 'draft':
            fingerprint, definition = draft_fingerprint(app)
            configuration = copy.deepcopy(app.draft)
            if app.kind == 'workflow':
                snapshot = clone_workflow(app, definition)
                manifest = snapshot._application_manifest
            else:
                configuration['collection_settings'] = definition
        else:
            release = app.releases.select_related('workflow_snapshot').filter(pk=data.get('release_id')).first()
            if not release:
                raise ApplicationFailure(limits.MESSAGES['target'], 'target_unavailable', 404)
            configuration, fingerprint = copy.deepcopy(release.configuration), release.fingerprint
            snapshot, manifest = release.workflow_snapshot, copy.deepcopy(release.workflow_manifest)
            if app.kind == 'knowledge':
                resolve_source(app, configuration)
        run = ApplicationEvaluationRun.objects.create(application=app, suite=suite, suite_revision=suite.revision,
            suite_name=suite.name, created_by=user, target=data['target'], release=release,
            fingerprint=fingerprint, configuration=configuration, workflow_snapshot=snapshot,
            workflow_manifest=manifest, corpus_signature=corpus_signature(app, configuration), total=len(cases),
            runner_mode='eager' if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False) else 'celery',
            lease_expires_at=timezone.now() + timedelta(seconds=getattr(settings, 'APPLICATION_EVALUATION_QUEUE_SECONDS', limits.QUEUE_LEASE_SECONDS)),
            parameters_hash=parameters_hash, idempotency_hash=token_hash)
        ApplicationEvaluationResult.objects.bulk_create([ApplicationEvaluationResult(run=run, case=case,
            case_id_snapshot=case.pk, case_name=case.name, case_hash=digest(case_payload(case)), position=index,
            input_data=copy.deepcopy(case.input_data), assertions=copy.deepcopy(case.assertions)) for index, case in enumerate(cases)])
    def dispatch():
        if not ApplicationEvaluationRun.objects.filter(pk=run.pk, status='queued').exists():
            return
        try:
            from .evaluation_tasks import execute_application_evaluation
            if run.runner_mode == 'eager':
                execute_application_evaluation.apply(args=[str(run.pk)], throw=False)
            else:
                execute_application_evaluation.apply_async(args=[str(run.pk)], retry=False)
        except Exception:
            stop_run(run.pk, failed=True, code='queue_unavailable', message=limits.MESSAGES['queue_failed'])
    transaction.on_commit(dispatch)
    run.refresh_from_db()
    return run, True


def _can_start(user, app):
    return visible_applications(user).filter(pk=app.pk).exists() and can_edit(user, app)


def _check_control(run_id):
    run = ApplicationEvaluationRun.objects.select_related('created_by', 'application__owner', 'application__tenant').get(pk=run_id)
    if run.status == 'cancelling':
        stop_run(run.pk)
        return None
    if run.status != 'running':
        return None
    if timezone.now() >= run.deadline_at:
        stop_run(run_id, failed=True, code='evaluation_timeout', message=limits.MESSAGES['expired'])
        return None
    if not _authorized(run):
        stop_run(run_id, failed=True, code='permission_revoked', message=limits.MESSAGES['permission'])
        return None
    return run


def _wait_for_capacity(run):
    from .constants import RATE_PER_MINUTE, MAX_CONCURRENT
    while _check_control(run.pk):
        reconcile_pending_tests(run.application)
        recover_expired_requests(run.application)
        recent = run.application.requests.filter(created_at__gte=timezone.now() - timedelta(minutes=1))
        if recent.count() < getattr(settings, 'APPLICATION_RATE_PER_MINUTE', RATE_PER_MINUTE) and run.application.requests.filter(status='running').count() < getattr(settings, 'APPLICATION_MAX_CONCURRENT', MAX_CONCURRENT):
            return True
        time.sleep(limits.POLL_SECONDS)
    return False


@transaction.atomic
def _admit_result(run_id, result_id, record):
    run = ApplicationEvaluationRun.objects.select_for_update().get(pk=run_id)
    result = run.results.select_for_update().get(pk=result_id)
    result.request = record
    result.save(update_fields=['request'])
    if run.status != 'running' or result.status != 'running':
        _cancel_request(record, limits.MESSAGES['cancelled'])
        return False
    authorized = _authorized(run)
    if timezone.now() >= run.deadline_at or not authorized:
        stop_run(run.pk, failed=True, code='permission_revoked' if not authorized else 'evaluation_timeout',
            message=limits.MESSAGES['permission'] if not authorized else limits.MESSAGES['expired'])
        return False
    return True


@transaction.atomic
def _settle_result(run_id, result_id, record):
    run = ApplicationEvaluationRun.objects.select_for_update().get(pk=run_id)
    result = run.results.select_for_update().get(pk=result_id)
    if run.status != 'running' or result.status != 'running':
        return
    result.assertion_results = check_assertions(record, result.assertions)
    unexpected = record.status != 'completed' and not any(row['type'] == 'error_code' for row in result.assertions)
    result.status = 'error' if unexpected else 'passed' if all(row['passed'] for row in result.assertion_results) else 'failed'
    if unexpected:
        result.error_code, result.error_message = record.error_code, record.error_message or limits.MESSAGES['unexpected_error']
    result.completed_at = timezone.now()
    result.save()
    _counts(run)
    run.save(update_fields=['passed', 'failed', 'errors', 'skipped'])


def execute_run(run_id):
    with transaction.atomic():
        run = ApplicationEvaluationRun.objects.select_for_update().get(pk=run_id)
        if run.status != 'queued':
            return
        if run.lease_expires_at <= timezone.now():
            stop_run(run.pk, failed=True, code='queue_expired', message=limits.MESSAGES['queue_expired'])
            return
        seconds = max(.01, float(getattr(settings, 'APPLICATION_EVALUATION_MAX_SECONDS', limits.MAX_RUN_SECONDS)))
        run.status, run.started_at = 'running', timezone.now()
        run.deadline_at = run.started_at + timedelta(seconds=seconds)
        run.lease_expires_at = run.deadline_at + timedelta(seconds=limits.LEASE_GRACE_SECONDS)
        run.save(update_fields=['status', 'started_at', 'deadline_at', 'lease_expires_at'])
    for result_id in run.results.values_list('pk', flat=True):
        current = _check_control(run_id)
        if not current or not _wait_for_capacity(current):
            return
        result = ApplicationEvaluationResult.objects.get(pk=result_id)
        if not ApplicationEvaluationResult.objects.filter(pk=result_id, status='pending').update(status='running', started_at=timezone.now()):
            continue
        target = EvaluationTarget(current.application_id, current.configuration, current.fingerprint,
            current.workflow_snapshot_id, current.workflow_manifest, current.release_id)
        try:
            record, _ = run_application(current.application, current.created_by, result.input_data, 'evaluation',
                idempotency_token=f'evaluation:{current.pk}:{result.pk}', evaluation_target=target,
                on_admitted=lambda row: _admit_result(run_id, result_id, row),
                timeout_seconds=(current.deadline_at - timezone.now()).total_seconds())
            if not _check_control(run_id):
                _cancel_request(record, limits.MESSAGES['cancelled'])
                return
            while record.status == 'running':
                if not _check_control(run_id):
                    _cancel_request(record, limits.MESSAGES['cancelled'])
                    return
                reconcile_pending_tests(current.application)
                recover_expired_requests(current.application)
                record.refresh_from_db()
                if record.status == 'running':
                    time.sleep(limits.POLL_SECONDS)
            _settle_result(run_id, result_id, record)
        except ApplicationFailure as exc:
            if exc.code == 'permission_revoked':
                stop_run(run_id, failed=True, code='permission_revoked', message=limits.MESSAGES['permission'])
                return
            with transaction.atomic():
                locked = ApplicationEvaluationRun.objects.select_for_update().get(pk=run_id)
                if locked.status == 'running':
                    ApplicationEvaluationResult.objects.filter(pk=result_id, status='running').update(status='error', error_code=exc.code,
                        error_message=str(exc), completed_at=timezone.now())
                    _counts(locked)
                    locked.save(update_fields=['passed', 'failed', 'errors', 'skipped'])
    with transaction.atomic():
        current = ApplicationEvaluationRun.objects.select_for_update().select_related('application__owner', 'application__tenant').get(pk=run_id)
        if current.status != 'running':
            return
        if not _authorized(current):
            stop_run(run_id, failed=True, code='permission_revoked', message=limits.MESSAGES['permission'])
            return
        try:
            current.final_corpus_signature = corpus_signature(current.application, current.configuration)
        except ApplicationFailure:
            current.final_corpus_signature = 'unavailable'
        current.status, current.completed_at = 'completed', timezone.now()
        _counts(current)
        current.save()


def compare_runs(current, baseline):
    if current.application_id != baseline.application_id or current.suite_id != baseline.suite_id or current.status in limits.ACTIVE_RUN_STATUSES or baseline.status in limits.ACTIVE_RUN_STATUSES:
        raise ApplicationFailure(limits.MESSAGES['compare'], 'invalid_comparison', 400)
    corpus_matches = (current.corpus_signature == current.final_corpus_signature == baseline.corpus_signature == baseline.final_corpus_signature)
    before = {str(row.case_id_snapshot): row for row in baseline.results.all()}
    after = {str(row.case_id_snapshot): row for row in current.results.all()}
    rows = []
    for identity in dict.fromkeys([*before, *after]):
        old, new = before.get(identity), after.get(identity)
        if not old:
            change = 'added'
        elif not new:
            change = 'removed'
        elif old.case_hash != new.case_hash:
            change = 'modified'
        elif not corpus_matches or current.status != 'completed' or baseline.status != 'completed':
            change = 'inconclusive'
        elif old.status == 'passed' and new.status != 'passed':
            change = 'regressed'
        elif old.status != 'passed' and new.status == 'passed':
            change = 'improved'
        else:
            change = 'unchanged'
        rows.append({'case_id': identity, 'name': (new or old).case_name, 'baseline_status': old.status if old else None,
                     'current_status': new.status if new else None, 'change': change})
    return {'baseline_id': str(baseline.pk), 'current_id': str(current.pk), 'corpus_matches': corpus_matches,
            'warning': '' if corpus_matches else limits.MESSAGES['corpus_changed'], 'results': rows}
