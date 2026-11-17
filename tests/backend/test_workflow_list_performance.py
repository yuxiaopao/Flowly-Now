"""Behavior and query budgets for workflow cards and their detail pages."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from workflows.models import Edge, Node, Workflow, WorkflowExecution


@pytest.mark.django_db
def test_workflow_list_queries_do_not_grow_with_page_size(authenticated_client, user):
    workflows = [Workflow.objects.create(owner=user, name=f'Card {index}') for index in range(8)]
    for workflow in workflows:
        first = Node.objects.create(workflow=workflow, node_type='start', name='Start')
        second = Node.objects.create(workflow=workflow, node_type='end', name='End')
        Edge.objects.create(workflow=workflow, source_node=first, target_node=second)
        WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='completed')
        WorkflowExecution.objects.create(workflow=workflow, version=1, triggered_by=user, status='failed')

    with CaptureQueriesContext(connection) as small_queries:
        small = authenticated_client.get('/api/v1/workflows/', {'page_size': 1})
    with CaptureQueriesContext(connection) as large_queries:
        large = authenticated_client.get('/api/v1/workflows/', {'page_size': 8})

    assert small.status_code == large.status_code == 200
    assert len(large.data['data']['results']) == 8
    assert {(item['node_count'], item['execution_count']) for item in large.data['data']['results']} == {(2, 2)}
    assert len(large_queries) <= len(small_queries) + 1, (
        f'One card used {len(small_queries)} queries, eight cards used {len(large_queries)}'
    )


@pytest.mark.django_db
def test_cards_send_preview_once_and_keep_full_config_on_detail(authenticated_client, user):
    preview = 'data:image/jpeg;base64,' + 'YWJj' * 30_000
    config = {
        'canvas_preview': preview,
        'canvasPreview': preview,
        'viewport': {'x': 10, 'y': 20, 'zoom': 0.75},
        'variables': {'language': 'zh'},
    }
    workflow = Workflow.objects.create(owner=user, name='Saved preview', config=config)

    response = authenticated_client.get('/api/v1/workflows/')
    assert response.status_code == 200
    card = response.data['data']['results'][0]
    assert card['canvas_preview'] == preview
    assert card['config'] == {
        'viewport': {'x': 10, 'y': 20, 'zoom': 0.75},
        'variables': {'language': 'zh'},
    }
    assert response.content.count(preview.encode()) == 1
    assert len(response.content) < 125_000

    detail = authenticated_client.get(f'/api/v1/workflows/{workflow.id}/')
    assert detail.status_code == 200
    assert detail.data['config'] == config


@pytest.mark.django_db
def test_card_queries_leave_node_payloads_for_full_detail(authenticated_client, user):
    workflow = Workflow.objects.create(owner=user, name='Large canvas')
    nodes = [
        Node.objects.create(
            workflow=workflow, node_type='code', name=f'Node {index}', sort_order=index,
            position_x=index * 100, config={'code': 'large-script-' * 1_000},
        )
        for index in range(35)
    ]
    for index in range(55):
        Edge.objects.create(
            workflow=workflow, source_node=nodes[index % 35], target_node=nodes[(index + 1) % 35],
            source_handle=f'branch-{index}',
            condition_expression='expensive-condition-' * 100,
        )

    with CaptureQueriesContext(connection) as queries:
        response = authenticated_client.get('/api/v1/workflows/')
    assert response.status_code == 200
    card = response.data['data']['results'][0]
    assert card['node_count'] == 35
    assert card['execution_count'] == 0
    assert len(card['nodes_preview']) == 30
    assert len(card['edges_preview']) == 50

    quote = connection.ops.quote_name
    for model, field in ((Node, 'config'), (Edge, 'condition_expression')):
        column = f'{quote(model._meta.db_table)}.{quote(field)}'
        assert all(column not in query['sql'] for query in queries), (
            f'Workflow cards fetched the full {model.__name__}.{field} payload'
        )

    detail = authenticated_client.get(f'/api/v1/workflows/{workflow.id}/')
    assert detail.status_code == 200
    assert len(detail.data['nodes']) == 35
    assert len(detail.data['edges']) == 55
    assert detail.data['nodes'][0]['config']['code'] == 'large-script-' * 1_000
    assert detail.data['edges'][0]['condition_expression'] == 'expensive-condition-' * 100


@pytest.mark.django_db
@pytest.mark.parametrize(('role', 'expected_can_edit'), [('admin', True), ('viewer', False)])
def test_team_card_permissions_do_not_add_a_query_per_workflow(authenticated_client, user, admin_user, role, expected_can_edit):
    from tenants.models import Tenant, TenantMembership

    tenant = Tenant.objects.create(owner=admin_user, name='Shared cards', slug='shared-cards')
    TenantMembership.objects.create(tenant=tenant, user=user, role=role)
    for index in range(8):
        Workflow.objects.create(owner=admin_user, tenant=tenant, name=f'Shared {index}', is_public=True)

    with CaptureQueriesContext(connection) as small_queries:
        small = authenticated_client.get('/api/v1/workflows/', {'page_size': 1})
    with CaptureQueriesContext(connection) as large_queries:
        large = authenticated_client.get('/api/v1/workflows/', {'page_size': 8})

    assert small.status_code == large.status_code == 200
    cards = large.data['data']['results']
    assert len(cards) == 8
    assert {card['can_edit'] for card in cards} == {expected_can_edit}
    assert len(large_queries) <= len(small_queries) + 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    'preview', [{'corrupt': True}, 'data:image/jpeg;base64,' + 'x' * 300_000],
    ids=['invalid-object', 'oversized'],
)
def test_invalid_or_oversized_screenshot_keeps_graph_fallback(authenticated_client, user, preview):
    workflow = Workflow.objects.create(
        owner=user, name='Fallback card', config={'canvas_preview': preview, 'timeout': 45},
    )
    Node.objects.create(workflow=workflow, node_type='start', name='Start')

    response = authenticated_client.get('/api/v1/workflows/')
    assert response.status_code == 200
    card = response.data['data']['results'][0]
    assert card['canvas_preview'] == ''
    assert card['config'] == {'timeout': 45}
    assert card['nodes_preview'][0]['name'] == 'Start'
    assert card['node_count'] == 1


@pytest.mark.django_db
def test_legacy_preview_alias_and_empty_graph_remain_supported(authenticated_client, user):
    Workflow.objects.create(
        owner=user, name='Legacy preview', config={'canvasPreview': 'data:image/jpeg;base64,YWJj'},
    )
    response = authenticated_client.get('/api/v1/workflows/')
    assert response.status_code == 200
    card = response.data['data']['results'][0]
    assert card['canvas_preview'] == 'data:image/jpeg;base64,YWJj'
    assert card['config'] == {}
    assert card['node_count'] == card['execution_count'] == 0
    assert card['nodes_preview'] == card['edges_preview'] == []
