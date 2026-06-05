# -*- coding: utf-8 -*-
"""
Agents API Tests
Tests for Agent, AgentConversation, AgentTool, and AgentExecution views.
"""

import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.django_db


class TestAgentSerializerValidation:
    """Test Agent serializers validation rules."""

    def test_create_agent_requires_name(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/',
            data={
                'description': 'A test agent',
                'agent_type': 'conversational',
                'system_prompt': 'You are helpful.',
            },
            format='json'
        )
        assert response.status_code == 400
        assert 'name' in response.data or 'detail' in response.data

    def test_create_agent_validates_agent_type(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/',
            data={
                'name': 'Test Agent',
                'agent_type': 'invalid_type',
            },
            format='json'
        )
        assert response.status_code == 400

    def test_create_agent_temperature_range(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/',
            data={
                'name': 'Test Agent',
                'temperature': 3.0,
            },
            format='json'
        )
        assert response.status_code == 400

    def test_create_agent_max_tokens_positive(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/',
            data={
                'name': 'Test Agent',
                'max_tokens': -100,
            },
            format='json'
        )
        assert response.status_code == 400

    def test_update_agent_partial(self, authenticated_client, user):
        from agents.models import Agent
        agent = Agent.objects.create(
            name='Old Name',
            owner=user,
            agent_type='conversational',
        )
        response = authenticated_client.patch(
            f'/api/v1/agents/{agent.id}/',
            data={'name': 'New Name'},
            format='json'
        )
        assert response.status_code == 200

    def test_agent_chat_requires_message(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/chat/',
            data={},
            format='json'
        )
        assert response.status_code == 400
        assert 'message' in str(response.data)

    def test_agent_chat_requires_agent_id_or_conversation_id(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/chat/',
            data={'message': 'Hello'},
            format='json'
        )
        assert response.status_code == 400

    def test_agent_tools_action_requires_tools_list(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/tools/',
            data={},
            format='json'
        )
        assert response.status_code == 400

    def test_agent_tools_remove_requires_tool(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/tools_remove/',
            data={},
            format='json'
        )
        assert response.status_code == 400

    def test_agent_reset_memory_requires_session_id(self, authenticated_client):
        response = authenticated_client.delete(
            '/api/v1/agents/debug/history/',
            format='json'
        )
        assert response.status_code == 400


class TestAgentConversationValidation:
    """Test AgentConversation views validation."""

    def test_add_message_requires_role(self, authenticated_client, user):
        from agents.models import Agent, AgentConversation
        agent = Agent.objects.create(name='Test', owner=user, agent_type='conversational')
        conversation = AgentConversation.objects.create(agent=agent, user=user)

        response = authenticated_client.post(
            f'/api/v1/agents/conversations/{conversation.id}/add_message/',
            data={'content': 'Hello'},
            format='json'
        )
        assert response.status_code == 400
        assert 'role' in str(response.data)

    def test_add_message_requires_content(self, authenticated_client, user):
        from agents.models import Agent, AgentConversation
        agent = Agent.objects.create(name='Test', owner=user, agent_type='conversational')
        conversation = AgentConversation.objects.create(agent=agent, user=user)

        response = authenticated_client.post(
            f'/api/v1/agents/conversations/{conversation.id}/add_message/',
            data={'role': 'user'},
            format='json'
        )
        assert response.status_code == 400
        assert 'content' in str(response.data)

    def test_add_message_validates_role(self, authenticated_client, user):
        from agents.models import Agent, AgentConversation
        agent = Agent.objects.create(name='Test', owner=user, agent_type='conversational')
        conversation = AgentConversation.objects.create(agent=agent, user=user)

        response = authenticated_client.post(
            f'/api/v1/agents/conversations/{conversation.id}/add_message/',
            data={'role': 'moderator', 'content': 'Hello'},
            format='json'
        )
        assert response.status_code == 400


class TestAgentToolViewSet:
    """Test AgentTool ViewSet (ReadOnly)."""

    def test_tools_read_only_cannot_create(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/tools/',
            data={'name': 'New Tool'},
            format='json'
        )
        assert response.status_code == 405

    def test_tools_read_only_cannot_delete(self, authenticated_client):
        response = authenticated_client.delete('/api/v1/agents/tools/')
        assert response.status_code == 405

    def test_tools_available_action(self, authenticated_client):
        response = authenticated_client.get('/api/v1/agents/tools/available/')
        assert response.status_code == 200


class TestAgentExecutionViewSet:
    """Test AgentExecution ViewSet (ReadOnly)."""

    def test_execution_read_only_cannot_create(self, authenticated_client):
        response = authenticated_client.post(
            '/api/v1/agents/executions/',
            data={'agent': 'test'},
            format='json'
        )
        assert response.status_code == 405

    def test_execution_list(self, authenticated_client, user):
        response = authenticated_client.get('/api/v1/agents/executions/')
        assert response.status_code == 200

    def test_execution_filter_by_status(self, authenticated_client):
        response = authenticated_client.get('/api/v1/agents/executions/', {'status': 'completed'})
        assert response.status_code == 200
