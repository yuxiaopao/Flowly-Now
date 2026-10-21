"""NL workspace persistence, history and save contracts, using the real API and DB."""
import copy
import json
import pytest
from nl_to_workflow.models import NLSession
from workflows.models import Workflow

pytestmark = pytest.mark.django_db
BASE = '/api/v1/nl-workflow/sessions/'


def test_history_paginates_and_searches_beyond_first_page(authenticated_client, user):
    for index in range(35):
        NLSession.objects.create(user=user, name=f'历史 {index}', status='active' if index else 'failed')
    first = authenticated_client.get(BASE, {'paginated': 'true', 'page_size': 30}).data
    second = authenticated_client.get(BASE, {'paginated': 'true', 'page_size': 30, 'page': 2}).data
    assert first['count'] == 35 and len(first['results']) == 30 and first['has_more']
    assert len(second['results']) == 5 and not second['has_more']
    assert not set(str(row['session_id']) for row in first['results']) & set(str(row['session_id']) for row in second['results'])
    filtered = authenticated_client.get(BASE, {'paginated': 'true', 'status': 'failed', 'search': '历史 0'}).data
    assert filtered['count'] == 1
    assert authenticated_client.get(BASE, {'paginated': 'true', 'page': 'oops'}).status_code == 400


@pytest.mark.parametrize('name', ['', '   ', None, [], 12, '长' * 201])
def test_rename_rejects_invalid_names(authenticated_client, nl_session_with_workflow, name):
    response = authenticated_client.patch(f'{BASE}{nl_session_with_workflow.id}/', {'name': name}, format='json')
    assert response.status_code == 400


def test_draft_config_round_trip_and_exact_save(authenticated_client, nl_session_with_workflow):
    session = nl_session_with_workflow
    draft = copy.deepcopy(session.workflow_json)
    draft['nodes'][2]['name'] = '修改后的节点'
    draft['nodes'][2]['config']['customCamelKey'] = {'keep_THIS': True}
    response = authenticated_client.patch(f'{BASE}{session.id}/', {'workflow_json': json.dumps(draft)}, format='json')
    assert response.status_code == 200
    restored = authenticated_client.get(f'{BASE}{session.id}/').data
    assert restored['workflow_json']['nodes'] == draft['nodes']
    assert restored['workflow_json']['edges'] == draft['edges']
    saved = authenticated_client.post(f'{BASE}{session.id}/confirm/', {'workflow_json': json.dumps(draft)}, format='json')
    assert saved.status_code == 200
    workflow = Workflow.objects.get(id=saved.data['workflow_id'])
    assert workflow.nodes.get(name='修改后的节点').config['customCamelKey'] == {'keep_THIS': True}
    repeated = authenticated_client.post(f'{BASE}{session.id}/confirm/', {'workflow_json': json.dumps(draft)}, format='json')
    assert repeated.data['workflow_id'] == saved.data['workflow_id']
    draft['name'] = '新版本'
    changed = authenticated_client.post(f'{BASE}{session.id}/confirm/', {'workflow_json': json.dumps(draft)}, format='json')
    assert changed.data['workflow_id'] != saved.data['workflow_id']
    assert Workflow.objects.get(id=saved.data['workflow_id']).name != '新版本'


@pytest.mark.parametrize('draft', [None, 'bad json', [], {'nodes': []}, {'nodes': [{'id': 'a', 'type': 'llm', 'config': []}]}, {'nodes': [{'id': 'a', 'type': 'llm'}], 'edges': [{'source': 'a', 'target': 'missing'}]}])
def test_invalid_drafts_do_not_mutate_session(authenticated_client, nl_session_with_workflow, draft):
    original = copy.deepcopy(nl_session_with_workflow.workflow_json)
    response = authenticated_client.patch(f'{BASE}{nl_session_with_workflow.id}/', {'workflow_json': draft}, format='json')
    assert response.status_code == 400
    nl_session_with_workflow.refresh_from_db()
    assert nl_session_with_workflow.workflow_json == original


def test_ownership_and_processing_protection(authenticated_client, nl_session_with_workflow, admin_user):
    session = nl_session_with_workflow
    session.status = 'processing'
    session.save()
    assert authenticated_client.patch(f'{BASE}{session.id}/', {'workflow_json': session.workflow_json}, format='json').status_code == 409
    session.user = admin_user
    session.save()
    for method, suffix in [('get', ''), ('patch', ''), ('delete', ''), ('post', 'confirm/')]:
        response = getattr(authenticated_client, method)(f'{BASE}{session.id}/{suffix}')
        assert response.status_code == 404


def test_guidance_refreshes_after_config_edit(authenticated_client, nl_session_with_workflow):
    session = nl_session_with_workflow
    draft = copy.deepcopy(session.workflow_json)
    draft['_node_guidance'] = [{'node_type': 'llm', 'config': {'model': 'stale'}}]
    draft['nodes'][2]['config']['model'] = 'updated-model'
    result = authenticated_client.patch(f'{BASE}{session.id}/', {'workflow_json': json.dumps(draft)}, format='json')
    assert result.status_code == 200
    guidance = result.data['workflow_json']['_node_guidance']
    assert next(item for item in guidance if item['node_type'] == 'llm')['config']['model'] == 'updated-model'


def test_email_guidance_keeps_all_missing_fields_and_smtp_warnings():
    from nl_to_workflow.services import get_email_config_guidance
    result = get_email_config_guidance({'nodes': [
        {'type': 'email', 'name': '邮件一', 'config': {}},
        {'type': 'email', 'name': '邮件二', 'config': {'to': 'qa@example.test'}},
    ]})
    assert len(result['missing_fields']) == 5
    assert '邮件一' in result['warning'] and '邮件二' in result['warning']
    assert result['configured_fields']['收件人 (to)'] is False
    complete = get_email_config_guidance({'nodes': [{'type': 'email', 'config': {'to': 'qa@example.test', 'subject': '测试', 'body': '测试'}}]})
    assert complete['missing_fields'] == []
    assert complete['configured_fields']['收件人 (to)'] is True


def test_confirm_rejects_unsupported_node_without_partial_save(authenticated_client, nl_session_with_workflow):
    draft = copy.deepcopy(nl_session_with_workflow.workflow_json)
    draft['nodes'][1]['type'] = 'unsupported-fake-type'
    count = Workflow.objects.count()
    result = authenticated_client.post(f'{BASE}{nl_session_with_workflow.id}/confirm/', {'workflow_json': json.dumps(draft)}, format='json')
    assert result.status_code == 400
    assert Workflow.objects.count() == count
