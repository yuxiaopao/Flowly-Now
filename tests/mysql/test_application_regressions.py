"""Application evaluation admission and gate changes under actual InnoDB locks."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

import pytest
from django.db import connection, connections
from django.utils import timezone
from django.test import override_settings
from rest_framework.test import APIClient
from applications.models import Application, ApplicationTestSuite, ApplicationTestCase, ApplicationEvaluationRun
from users.models import User
from workflows.models import Workflow, Node, Edge

pytestmark = pytest.mark.django_db(transaction=True)


def client(user):
    value = APIClient()
    value.force_authenticate(user)
    return value


@pytest.fixture
def evaluation_source(user):
    assert connection.vendor == 'mysql', 'This suite requires the isolated MySQL test settings.'
    workflow = Workflow.objects.create(owner=user, name='Concurrent regression')
    start = Node.objects.create(workflow=workflow, name='start', node_type='start')
    end = Node.objects.create(workflow=workflow, name='end', node_type='end')
    Edge.objects.create(workflow=workflow, source_node=start, target_node=end)
    app = Application.objects.create(owner=user, name='Regression admission', kind='workflow', draft={'workflow_id': str(workflow.pk)})
    suite = ApplicationTestSuite.objects.create(application=app, created_by=user, name='Core cases')
    ApplicationTestCase.objects.create(suite=suite, name='Exists', assertions=[{'type': 'json_exists', 'path': ''}])
    return app, suite


def parallel(user, actions):
    barrier = Barrier(len(actions))
    def call(action):
        try:
            actor = User.objects.get(pk=user.pk)
            barrier.wait(timeout=10)
            return action(client(actor))
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        return [future.result(timeout=30) for future in [pool.submit(call, action) for action in actions]]


def test_parallel_distinct_batches_only_admit_one(user, evaluation_source):
    app, suite = evaluation_source
    url = f'/api/v1/applications/{app.pk}/evaluation-runs/'
    payload = {'suite_id': str(suite.pk), 'target': 'draft'}
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async') as dispatch:
        responses = parallel(user, [lambda api: api.post(url, payload, format='json') for _ in range(2)])
    assert sorted(response.status_code for response in responses) == [202, 409]
    assert ApplicationEvaluationRun.objects.filter(application=app).count() == dispatch.call_count == 1


def test_parallel_idempotent_retries_dispatch_exactly_once(user, evaluation_source):
    app, suite = evaluation_source
    url = f'/api/v1/applications/{app.pk}/evaluation-runs/'
    payload = {'suite_id': str(suite.pk), 'target': 'draft'}
    with override_settings(CELERY_TASK_ALWAYS_EAGER=False), patch('applications.evaluation_tasks.execute_application_evaluation.apply_async') as dispatch:
        responses = parallel(user, [lambda api: api.post(url, payload, format='json', HTTP_IDEMPOTENCY_KEY='concurrent-batch') for _ in range(2)])
    assert [response.status_code for response in responses] == [202, 202]
    assert len({response.json()['data']['id'] for response in responses}) == 1
    assert ApplicationEvaluationRun.objects.filter(application=app).count() == dispatch.call_count == 1


def test_gate_assignment_and_suite_deletion_cannot_leave_a_deleted_required_suite(user, evaluation_source):
    app, suite = evaluation_source
    url = f'/api/v1/applications/{app.pk}/'
    responses = parallel(user, [
        lambda api: api.patch(url, {'required_evaluation_suite_id': str(suite.pk)}, format='json'),
        lambda api: api.delete(url + f'test-suites/{suite.pk}/'),
    ])
    assert [response.status_code for response in responses] in ([200, 409], [400, 204])
    app.refresh_from_db(); suite.refresh_from_db()
    assert not (app.required_evaluation_suite_id == suite.pk and suite.is_deleted)


def test_knowledge_publication_and_real_ingestion_share_a_corpus_commit_boundary(user):
    from applications.models import ApplicationRequest
    from applications.services import draft_fingerprint
    from applications.evaluation_service import corpus_signature, required_evaluation_evidence
    from rag.models import VectorStore, DocumentCollection, Document, Chunk
    from rag.pipeline import DocumentProcessor
    assert connection.vendor == 'mysql'
    store = VectorStore.objects.create(owner=user, name='Concurrent corpus', store_type='memory')
    collection = DocumentCollection.objects.create(owner=user, name='Concurrent corpus', vector_store=store, retrieval_mode='keyword')
    document = Document.objects.create(collection=collection, title='Release', content='Release evidence', status='completed')
    Chunk.objects.create(document=document, content='Release evidence', vector_id='original')
    app = Application.objects.create(owner=user, name='Corpus boundary', kind='knowledge', draft={
        'collection_id': str(collection.pk), 'system_prompt': 'Use evidence', 'top_k': 5, 'min_similarity': 0})
    suite = ApplicationTestSuite.objects.create(application=app, created_by=user, name='Corpus gate')
    ApplicationTestCase.objects.create(suite=suite, name='Evidence', assertions=[{'type': 'grounded', 'expected': True}])
    fingerprint = draft_fingerprint(app)[0]
    signature = corpus_signature(app)
    proof = ApplicationRequest.objects.create(application=app, caller=user, mode='test', status='completed',
        fingerprint=fingerprint, input_data={'query': 'release'}, output_data={'grounded': True}, completed_at=timezone.now())
    app.required_evaluation_suite = suite
    app.tested_fingerprint, app.last_test_status, app.last_test_at = fingerprint, 'completed', proof.created_at
    app.save()
    ApplicationEvaluationRun.objects.create(application=app, suite=suite, suite_revision=suite.revision,
        suite_name=suite.name, created_by=user, fingerprint=fingerprint, target='draft', configuration=app.draft,
        corpus_signature=signature, final_corpus_signature=signature, status='completed', total=1, passed=1,
        lease_expires_at=timezone.now(), completed_at=timezone.now())
    checked, writer_started, writer_finished = Event(), Event(), Event()
    def verify(*args, **kwargs):
        result = required_evaluation_evidence(*args, **kwargs)
        checked.set()
        assert writer_started.wait(5)
        assert not writer_finished.wait(.4), 'Ingestion committed after evidence verification but before publication'
        return result
    def publish():
        try:
            return client(User.objects.get(pk=user.pk)).post(f'/api/v1/applications/{app.pk}/publish/', {}, format='json')
        finally:
            connections.close_all()
    def ingest():
        try:
            assert checked.wait(5)
            current = DocumentCollection.objects.get(pk=collection.pk)
            writer_started.set()
            result = DocumentProcessor(current).process_text('Additional live release evidence', {'title': 'After publication'})
            writer_finished.set()
            return result
        finally:
            connections.close_all()
    with patch('applications.evaluation_service.required_evaluation_evidence', side_effect=verify):
        with ThreadPoolExecutor(max_workers=2) as pool:
            publishing, writing = pool.submit(publish), pool.submit(ingest)
            response, ingested = publishing.result(timeout=15), writing.result(timeout=15)
    assert response.status_code == 201, response.content
    assert ingested['success'] and writer_finished.is_set()
    app.refresh_from_db()
    assert app.active_release.validated_by_evaluation.corpus_signature == signature
    assert corpus_signature(app) != signature
