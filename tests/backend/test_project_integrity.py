"""实际接口的权限、参数校验与数据隔离回归。"""
import pytest
from django.contrib.auth import get_user_model
from agents.models import Agent, AgentConversation
from rag.models import VectorStore

pytestmark = pytest.mark.django_db


def test_profile_cannot_promote_own_role(authenticated_client, user):
    response = authenticated_client.patch('/api/v1/auth/user/', {'role': 'admin', 'is_staff': True, 'is_superuser': True, 'execution_limit': 999999}, format='json')
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.role == 'user'
    assert user.is_staff is False and user.is_superuser is False
    assert user.execution_limit != 999999


@pytest.mark.parametrize('message', [None, '', '   ', [], {'text': '你好'}])
def test_agent_rejects_invalid_message_before_mutating_history(authenticated_client, user, message):
    agent = Agent.objects.create(name='参数校验', owner=user, is_active=True)
    response = authenticated_client.post(f'/api/v1/agents/{agent.id}/chat/', {'message': message}, format='json')
    assert response.status_code == 400
    assert not AgentConversation.objects.filter(agent=agent).exists()


@pytest.mark.parametrize('payload', [{}, {'tools': 'http'}, {'tools': ['unsupported_tool']}, {'tools': [1]}])
def test_agent_rejects_invalid_tools(authenticated_client, user, payload):
    agent = Agent.objects.create(name='工具校验', owner=user, tools=[])
    response = authenticated_client.post(f'/api/v1/agents/{agent.id}/tools/', payload, format='json')
    assert response.status_code == 400
    agent.refresh_from_db()
    assert agent.tools == []


@pytest.mark.parametrize('field,value', [('port', 0), ('port', 65536), ('dimension', 0), ('dimension', -1)])
def test_vector_store_connection_values_validated(authenticated_client, field, value):
    response = authenticated_client.post('/api/v1/rag/vector-stores/', {'name': '无效连接', 'store_type': 'memory', field: value}, format='json')
    assert response.status_code == 400
    assert not VectorStore.objects.filter(name='无效连接').exists()


@pytest.mark.parametrize('chunk_size,chunk_overlap', [(0, 0), (100, -1), (100, 100), (100, 101)])
def test_collection_chunk_configuration_validated(authenticated_client, user, chunk_size, chunk_overlap):
    store = VectorStore.objects.create(name='本地向量', store_type='memory', owner=user)
    response = authenticated_client.post('/api/v1/rag/collections/', {'name': '分块校验', 'vector_store': str(store.id), 'chunk_size': chunk_size, 'chunk_overlap': chunk_overlap}, format='json')
    assert response.status_code == 400


def test_collection_cannot_use_private_store_of_other_user(authenticated_client):
    other = get_user_model().objects.create_user(username='private-store-owner', password='Temporary123!')
    store = VectorStore.objects.create(name='私有向量', store_type='memory', owner=other)
    response = authenticated_client.post('/api/v1/rag/collections/', {'name': '跨用户关联', 'vector_store': str(store.id)}, format='json')
    assert response.status_code in (400, 403)
    assert not store.collections.exists()


def test_vector_default_switch_and_string_false(authenticated_client, user):
    first = VectorStore.objects.create(name='当前默认', store_type='memory', owner=user, is_default=True)
    response = authenticated_client.post('/api/v1/rag/vector-stores/', {
        'name': '非默认', 'store_type': 'memory', 'is_default': 'false',
    }, format='json')
    assert response.status_code == 201
    first.refresh_from_db()
    assert first.is_default is True
    second_id = response.data['id']
    response = authenticated_client.patch(f'/api/v1/rag/vector-stores/{second_id}/', {
        'is_default': True,
    }, format='json')
    assert response.status_code == 200
    assert [str(pk) for pk in VectorStore.objects.filter(owner=user, is_default=True).values_list('id', flat=True)] == [second_id]


@pytest.mark.parametrize('method', ['patch', 'delete'])
def test_shared_vector_store_is_read_only_for_regular_user(authenticated_client, method):
    shared = VectorStore.objects.create(name='公共向量', store_type='memory', owner=None)
    call = getattr(authenticated_client, method)
    response = call(f'/api/v1/rag/vector-stores/{shared.id}/', {'name': '覆盖公共配置'} if method == 'patch' else None, format='json')
    assert response.status_code == 403
    shared.refresh_from_db()
    assert shared.name == '公共向量'


@pytest.mark.parametrize('plan,cycle', [('invalid', 'monthly'), ('pro', 'invalid')])
def test_subscription_action_validates_choices(authenticated_client, plan, cycle):
    from billing.models import Subscription
    response = authenticated_client.post('/api/v1/billing/subscriptions/subscribe/', {'plan_type': plan, 'billing_cycle': cycle}, format='json')
    assert response.status_code == 400
    assert not Subscription.objects.exists()


def test_intent_details_extract_targets_as_string():
    from nl_to_workflow.services import NLToWorkflowService
    result = NLToWorkflowService()._get_intent_details('把输入节点改成用户问题')
    assert result['intent'] == 'modify'
    assert result['targets']
