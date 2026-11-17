"""Personal exports and restores use real authenticated HTTP and isolated records."""

import json
from datetime import timedelta
from unittest.mock import patch

import pytest

from agents.models import Agent, AgentTool
from core.models.audit import DataExport
from django.utils import timezone
from django.db import connection, IntegrityError
from workflows.models import Edge, Node, Workflow, WorkflowExecution

pytestmark = pytest.mark.django_db
BASE = '/api/v1/data-export/'


@pytest.fixture
def personal_graph(user):
    agent = Agent.objects.create(owner=user, name='Backup agent', system_prompt='Keep this prompt')
    AgentTool.objects.create(agent=agent, name='Helper', tool_type='code', config={'code': 'return 42'})
    workflow = Workflow.objects.create(owner=user, name='Backup workflow', config={'variables': {'answer': 42}})
    first = Node.objects.create(workflow=workflow, node_type='start', name='Start', position_x=12)
    second = Node.objects.create(workflow=workflow, node_type='agent', name='Assistant', config={'agent_id': str(agent.pk)})
    Edge.objects.create(workflow=workflow, source_node=first, target_node=second, source_handle='success')
    return workflow, agent


def test_export_download_keeps_a_complete_immutable_personal_snapshot(authenticated_client, personal_graph):
    workflow, agent = personal_graph
    response = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full', 'format': 'json'}, format='json')
    assert response.status_code == 201, response.data
    export_id = response.data['id']
    first = authenticated_client.get(f'{BASE}{export_id}/download/')
    assert first.status_code == 200
    snapshot = json.loads(first.content)
    assert snapshot['schema_version'] == 1
    assert snapshot['workflows'][0]['nodes'][1]['config']['agent_id'] == str(agent.pk)
    assert snapshot['workflows'][0]['edges'][0]['source_handle'] == 'success'
    assert snapshot['agents'][0]['agent_tools'][0]['config']['code'] == 'return 42'
    workflow.name = 'Changed after backup'
    workflow.save(update_fields=['name'])
    again = authenticated_client.get(f'{BASE}{export_id}/download/')
    assert again.content == first.content
    assert json.loads(again.content)['workflows'][0]['name'] == 'Backup workflow'


def test_restore_preview_then_confirmation_copies_graph_and_agent_without_overwriting(authenticated_client, personal_graph):
    workflow, agent = personal_graph
    export = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    preview = authenticated_client.post(f"{BASE}{export['id']}/restore_preview/", {}, format='json')
    assert preview.status_code == 200, preview.data
    assert preview.data['summary'] == {'workflows': 1, 'nodes': 2, 'edges': 1, 'agents': 1, 'agent_tools': 1,
                                       'variables': 0, 'triggers': 0, 'webhooks': 0}
    workflow.name = 'Original remains edited'
    workflow.save(update_fields=['name'])
    confirmation = {'confirmation_token': preview.data['confirmation_token'], 'confirm': True}
    restored = authenticated_client.post(f"{BASE}{export['id']}/restore/", confirmation, format='json')
    assert restored.status_code == 201, restored.data
    workflow_id = restored.data['mapping']['workflows'][str(workflow.pk)]
    agent_id = restored.data['mapping']['agents'][str(agent.pk)]
    assert workflow_id != str(workflow.pk) and agent_id != str(agent.pk)
    detail = authenticated_client.get(f'/api/v1/workflows/{workflow_id}/')
    assert detail.status_code == 200, detail.data
    assert detail.data['status'] == 'draft' and not detail.data['is_public']
    nodes = {node['name']: node for node in detail.data['nodes']}
    assert nodes['Assistant']['config']['agent_id'] == agent_id
    edge = detail.data['edges'][0]
    assert str(edge['source_node']) == str(nodes['Start']['id'])
    assert str(edge['target_node']) == str(nodes['Assistant']['id'])
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').data['name'] == 'Original remains edited'
    replay = authenticated_client.post(f"{BASE}{export['id']}/restore/", confirmation, format='json')
    assert replay.status_code == 200 and replay.data['mapping'] == restored.data['mapping']


@pytest.mark.parametrize('change', ['schema', 'foreign_owner', 'broken_edge', 'unknown_field'])
def test_invalid_backup_is_rejected_before_any_copies(authenticated_client, personal_graph, change):
    created = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    export = DataExport.objects.get(pk=created['id'])
    if change == 'schema':
        export.snapshot['schema_version'] = 99
    elif change == 'foreign_owner':
        export.snapshot['user_id'] += 1
    elif change == 'broken_edge':
        export.snapshot['workflows'][0]['edges'][0]['target_node_id'] = '00000000-0000-0000-0000-000000000000'
    else:
        export.snapshot['agents'][0]['is_superuser'] = True
    export.save(update_fields=['snapshot'])
    response = authenticated_client.post(f"{BASE}{created['id']}/restore_preview/", {}, format='json')
    assert response.status_code == 400
    listing = authenticated_client.get('/api/v1/workflows/')
    assert listing.status_code == 200 and len(listing.data['data']['results']) == 1


def test_backup_owner_isolation_and_confirmation_are_enforced(api_client, authenticated_client, personal_graph, django_user_model):
    created = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    export_id = created['id']
    other = django_user_model.objects.create_user(username='backup-other', email='backup-other@example.test', password='testpass123')
    api_client.force_authenticate(user=other)
    for url in [f'{BASE}{export_id}/download/', f'{BASE}{export_id}/restore_preview/']:
        response = api_client.get(url) if url.endswith('download/') else api_client.post(url, {}, format='json')
        assert response.status_code == 404
    assert authenticated_client.post(f'{BASE}{export_id}/restore/', {'confirm': True}, format='json').status_code == 400
    preview = authenticated_client.post(f'{BASE}{export_id}/restore_preview/', {}, format='json').data
    bad = authenticated_client.post(f'{BASE}{export_id}/restore/', {
        'confirm': True, 'confirmation_token': preview['confirmation_token'] + 'tampered',
    }, format='json')
    assert bad.status_code == 400
    assert authenticated_client.patch(f'{BASE}{export_id}/', {'status': 'failed'}, format='json').status_code == 405


def test_backup_policy_is_persisted_and_scheduled_worker_applies_owner_retention(authenticated_client, personal_graph):
    current = authenticated_client.get(BASE + 'backup_settings/')
    assert current.status_code == 200 and not current.data['enabled']
    saved = authenticated_client.patch(BASE + 'backup_settings/', {
        'enabled': True, 'frequency': 'daily', 'keep_count': 3,
    }, format='json')
    assert saved.status_code == 200, saved.data
    assert authenticated_client.get(BASE + 'backup_settings/').data['keep_count'] == 3
    from core.tasks import run_due_personal_backups
    now = timezone.now()
    for day in range(1, 5):
        with patch('django.utils.timezone.now', return_value=now + timedelta(days=day, minutes=1)):
            result = run_due_personal_backups.run()
            assert result['completed'] == 1
            assert run_due_personal_backups.run()['completed'] == 0
    history = authenticated_client.get(BASE)
    data = history.data.get('data', history.data)
    rows = data.get('results', data)
    backups = [row for row in rows if row['is_backup']]
    assert len(backups) == 3
    assert all(row['status'] == 'completed' for row in backups)
    policy = authenticated_client.get(BASE + 'backup_settings/').data
    assert policy['last_run_at'] and not policy['last_error']


def test_password_confirmed_cleanup_only_removes_previewed_personal_workspaces(authenticated_client, personal_graph, user):
    from tenants.models import Tenant
    from billing.models import Invoice
    workflow, agent = personal_graph
    team = Tenant.objects.create(owner=user, name='Preserved team', slug='preserved-personal-cleanup')
    team_workflow = Workflow.objects.create(owner=user, tenant=team, name='Team workflow remains')
    team_agent = Agent.objects.create(owner=user, tenant=team, name='Team agent remains')
    now = timezone.now()
    invoice = Invoice.objects.create(user=user, invoice_number='TEST-CLEANUP-PRESERVED', subtotal=10, total=10,
                                     period_start=now, period_end=now + timedelta(days=30), due_date=now)
    WorkflowExecution.objects.create(workflow=workflow, version=1, status='completed', triggered_by=user)
    preview = authenticated_client.get(BASE + 'delete_preview/')
    assert preview.status_code == 200, preview.data
    assert preview.data['summary']['workflows'] == 1
    assert preview.data['summary']['agents'] == 1
    assert preview.data['summary']['workflow_executions'] == 1
    data = {'confirmation_token': preview.data['confirmation_token'], 'confirmation': '删除个人工作流和Agent', 'password': 'wrong'}
    assert authenticated_client.post(BASE + 'delete_personal_data/', data, format='json').status_code == 400
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').status_code == 200
    data['password'] = 'testpass123'
    deleted = authenticated_client.post(BASE + 'delete_personal_data/', data, format='json')
    assert deleted.status_code == 200, deleted.data
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').status_code == 404
    assert authenticated_client.get(f'/api/v1/agents/{agent.pk}/').status_code == 404
    assert authenticated_client.get(f'/api/v1/workflows/{team_workflow.pk}/').status_code == 200
    assert authenticated_client.get(f'/api/v1/agents/{team_agent.pk}/').status_code == 200
    assert authenticated_client.get(f'/api/v1/billing/invoices/{invoice.pk}/').status_code == 200
    assert authenticated_client.get('/api/v1/auth/user/').status_code == 200
    assert authenticated_client.post(BASE + 'delete_personal_data/', data, format='json').status_code == 409


@pytest.mark.parametrize('status', ['queued', 'running'])
def test_cleanup_rejects_active_tasks_and_keeps_originals(authenticated_client, personal_graph, user, status):
    workflow, _ = personal_graph
    WorkflowExecution.objects.create(workflow=workflow, version=1, status=status, triggered_by=user)
    response = authenticated_client.get(BASE + 'delete_preview/')
    assert response.status_code == 409
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').status_code == 200


def test_changed_workspace_requires_a_new_cleanup_preview(authenticated_client, personal_graph, user):
    preview = authenticated_client.get(BASE + 'delete_preview/').data
    workflow = Workflow.objects.create(owner=user, name='Created after preview')
    response = authenticated_client.post(BASE + 'delete_personal_data/', {
        'confirmation_token': preview['confirmation_token'], 'confirmation': '删除个人工作流和Agent', 'password': 'testpass123',
    }, format='json')
    assert response.status_code == 409
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').status_code == 200


def test_restore_database_failure_rolls_back_all_copies_and_allows_retry(authenticated_client, personal_graph):
    created = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    preview = authenticated_client.post(f"{BASE}{created['id']}/restore_preview/", {}, format='json').data
    confirmation = {'confirm': True, 'confirmation_token': preview['confirmation_token']}
    quote = connection.ops.quote_name

    def unavailable_node_table(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith('INSERT INTO') and quote(Node._meta.db_table) in sql:
            raise IntegrityError('isolated fixture database failure')
        return execute(sql, params, many, context)

    authenticated_client.raise_request_exception = False
    with connection.execute_wrapper(unavailable_node_table):
        failed = authenticated_client.post(f"{BASE}{created['id']}/restore/", confirmation, format='json')
    assert failed.status_code == 500
    listed = authenticated_client.get('/api/v1/workflows/').data['data']['results']
    assert len(listed) == 1 and listed[0]['name'] == 'Backup workflow'
    agents = authenticated_client.get('/api/v1/agents/').data
    agents = agents.get('data', agents)
    assert len(agents.get('results', agents)) == 1
    retried = authenticated_client.post(f"{BASE}{created['id']}/restore/", confirmation, format='json')
    assert retried.status_code == 201


@pytest.mark.parametrize('format', ['csv', 'xlsx'])
def test_export_formats_contain_real_records_in_the_advertised_format(authenticated_client, personal_graph, format):
    from io import BytesIO
    from openpyxl import load_workbook
    created = authenticated_client.post(BASE + 'request_export/', {'export_type': 'workflows', 'format': format}, format='json').data
    download = authenticated_client.get(f"{BASE}{created['id']}/download/")
    assert download.status_code == 200
    if format == 'csv':
        assert 'text/csv' in download['Content-Type']
        assert 'Backup workflow' in download.content.decode('utf-8-sig')
    else:
        assert download.content.startswith(b'PK')
        workbook = load_workbook(BytesIO(download.content), read_only=True)
        try:
            assert any('Backup workflow' in row for row in workbook.active.iter_rows(values_only=True))
        finally:
            workbook.close()


def test_restore_preserves_workflow_variables_and_disabled_trigger_configuration(authenticated_client, personal_graph, user):
    from workflows.models import Variable
    from workflows.scheduling import WorkflowTrigger, Webhook
    workflow, _ = personal_graph
    Variable.objects.create(workflow=workflow, name='COLOR', default_value='blue')
    trigger = WorkflowTrigger.objects.create(workflow=workflow, name='Daily schedule', trigger_type='schedule',
                                             schedule_type='recurring', interval_seconds=3600, created_by=user)
    Webhook.objects.create(workflow=workflow, name='Original endpoint', path='fixture-original-webhook', created_by=user)
    export = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    preview = authenticated_client.post(f"{BASE}{export['id']}/restore_preview/", {}, format='json')
    assert preview.status_code == 200
    restored = authenticated_client.post(f"{BASE}{export['id']}/restore/", {
        'confirm': True, 'confirmation_token': preview.data['confirmation_token'],
    }, format='json')
    assert restored.status_code == 201, restored.data
    restored_id = restored.data['mapping']['workflows'][str(workflow.pk)]
    variables = authenticated_client.get('/api/v1/variables/', {'workflow': restored_id}).data
    variables = variables.get('data', variables)
    rows = variables.get('results', variables)
    assert any(row['name'] == 'COLOR' and row['default_value'] == 'blue' for row in rows)
    response = authenticated_client.get('/api/v1/workflows/triggers/', {'workflow': restored_id})
    assert response.status_code == 200
    copied = response.data
    copied = copied.get('data', copied)
    rows = copied.get('results', copied)
    assert len(rows) == 1 and rows[0]['interval_seconds'] == 3600
    assert not rows[0]['is_enabled'] and rows[0]['status'] == 'disabled'
    assert authenticated_client.get(f'/api/v1/workflows/triggers/{trigger.pk}/').data['is_enabled']


def test_scheduled_backup_failure_is_visible_and_can_retry_without_fake_completed_history(authenticated_client, personal_graph, settings):
    from core.tasks import run_due_personal_backups
    authenticated_client.patch(BASE + 'backup_settings/', {'enabled': True}, format='json')
    tomorrow = timezone.now() + timedelta(days=1, minutes=1)
    settings.PERSONAL_DATA_MAX_BYTES = 1
    with patch('django.utils.timezone.now', return_value=tomorrow):
        assert run_due_personal_backups.run() == {'completed': 0, 'failed': 1}
    policy = authenticated_client.get(BASE + 'backup_settings/').data
    assert policy['last_error'] and policy['last_run_at'] is None
    assert DataExport.objects.count() == 0
    settings.PERSONAL_DATA_MAX_BYTES = 20 * 1024 * 1024
    with patch('django.utils.timezone.now', return_value=tomorrow + timedelta(hours=1)):
        assert run_due_personal_backups.run() == {'completed': 1, 'failed': 0}
    assert authenticated_client.get(BASE + 'backup_settings/').data['last_error'] == ''


def test_unconfigured_scheduler_cannot_persist_a_false_enabled_state(authenticated_client, settings):
    settings.CELERY_BEAT_SCHEDULE = {}
    saved = authenticated_client.patch(BASE + 'backup_settings/', {'enabled': True}, format='json')
    assert saved.status_code == 400
    policy = authenticated_client.get(BASE + 'backup_settings/').data
    assert not policy['enabled'] and not policy['scheduler_configured']


def test_excel_rejects_oversized_cells_instead_of_silently_truncating(authenticated_client, personal_graph):
    workflow, _ = personal_graph
    workflow.config = {'large': 'x' * 33000}
    workflow.save(update_fields=['config'])
    response = authenticated_client.post(BASE + 'request_export/', {'export_type': 'workflows', 'format': 'xlsx'}, format='json')
    assert response.status_code == 400
    assert DataExport.objects.count() == 0


@pytest.mark.parametrize('path,method', [('backup_settings/', 'patch'), ('delete_preview/', 'get'), ('delete_personal_data/', 'post'), ('request_export/', 'post')])
def test_personal_data_management_requires_login(api_client, path, method):
    response = getattr(api_client, method)(BASE + path, {}, format='json')
    assert response.status_code == 401


def test_restore_preview_expiry_and_changed_snapshots_require_preview_again(authenticated_client, personal_graph):
    from core.models.audit import DataRestoreOperation
    created = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
    preview = authenticated_client.post(f"{BASE}{created['id']}/restore_preview/", {}, format='json').data
    DataRestoreOperation.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert authenticated_client.post(f"{BASE}{created['id']}/restore/", {
        'confirm': True, 'confirmation_token': preview['confirmation_token'],
    }, format='json').status_code == 400
    preview = authenticated_client.post(f"{BASE}{created['id']}/restore_preview/", {}, format='json').data
    export = DataExport.objects.get(pk=created['id'])
    export.snapshot['workflows'][0]['name'] = 'Changed snapshot'
    export.save(update_fields=['snapshot'])
    assert authenticated_client.post(f"{BASE}{created['id']}/restore/", {
        'confirm': True, 'confirmation_token': preview['confirmation_token'],
    }, format='json').status_code == 409


def test_cleanup_refuses_a_cascade_into_another_owners_workflow(authenticated_client, personal_graph, django_user_model):
    workflow, _ = personal_graph
    other = django_user_model.objects.create_user(username='cascade-other')
    foreign = Workflow.objects.create(owner=other, name='Unrelated foreign workflow')
    Node.objects.create(workflow=foreign, node_type='code', name='Legacy cross-workflow child', parent_node=workflow.nodes.first())
    response = authenticated_client.get(BASE + 'delete_preview/')
    assert response.status_code == 409
    assert authenticated_client.get(f'/api/v1/workflows/{workflow.pk}/').status_code == 200


def test_cleanup_refuses_to_delete_another_users_private_agent_conversation(authenticated_client, personal_graph, django_user_model):
    from agents.models import AgentConversation
    _, agent = personal_graph
    other = django_user_model.objects.create_user(username='conversation-other')
    AgentConversation.objects.create(agent=agent, user=other, messages=[{'role': 'user', 'content': 'fixture private chat'}])
    response = authenticated_client.get(BASE + 'delete_preview/')
    assert response.status_code == 409


def test_repeated_restore_preserves_uuid_business_literals_and_executes_original_output_references(authenticated_client, user):
    workflow = Workflow.objects.create(owner=user, name='Literal and references')
    nodes = []
    for kind, config in [('start', {}), ('input', {'variable_name': 'input'}), ('output', {}), ('end', {})]:
        node = Node.objects.create(workflow=workflow, node_type=kind, name=kind, config=config)
        if nodes:
            Edge.objects.create(workflow=workflow, source_node=nodes[-1], target_node=node)
        nodes.append(node)
    original_id = str(nodes[1].pk)
    literal = 'unchanged literal: ' + original_id
    workflow.config = {original_id: {'business_ID': original_id}}
    workflow.save(update_fields=['config'])
    nodes[2].config = {'template': '{{node_outputs.' + original_id + '.input}}', 'business_literal': literal, original_id: original_id}
    nodes[2].save(update_fields=['config'])
    for generation in range(2):
        export = authenticated_client.post(BASE + 'request_export/', {'export_type': 'full'}, format='json').data
        preview = authenticated_client.post(f"{BASE}{export['id']}/restore_preview/", {}, format='json').data
        result = authenticated_client.post(f"{BASE}{export['id']}/restore/", {
            'confirm': True, 'confirmation_token': preview['confirmation_token'],
        }, format='json')
        assert result.status_code == 201, result.data
        restored_id = result.data['mapping']['workflows'][str(workflow.pk)]
        detail = authenticated_client.get(f'/api/v1/workflows/{restored_id}/').data
        assert detail['config'][original_id] == {'business_ID': original_id}
        output = next(node for node in detail['nodes'] if node['name'] == 'output')
        assert output['config']['business_literal'] == literal
        assert output['config'][original_id] == original_id
        executed = authenticated_client.post(f'/api/v1/workflows/{restored_id}/execute/', {
            'input_data': {'input': f'generation-{generation}'}, 'is_async': False,
        }, format='json')
        assert executed.status_code == 200, executed.data
        assert executed.data['output_data']['variables']['result'] == f'generation-{generation}'
        workflow = Workflow.objects.get(pk=restored_id)
