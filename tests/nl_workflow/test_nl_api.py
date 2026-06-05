# -*- coding: utf-8 -*-
"""
Tests for NL Session API with UUID primary keys.

Tests the following endpoints:
- POST /api/v1/nl-workflow/sessions/ - Create session
- GET /api/v1/nl-workflow/sessions/ - List sessions
- GET /api/v1/nl-workflow/sessions/{uuid}/ - Get session by UUID
- DELETE /api/v1/nl-workflow/sessions/{uuid}/ - Delete session by UUID
- POST /api/v1/nl-workflow/sessions/{uuid}/message/ - Send message
- POST /api/v1/nl-workflow/sessions/{uuid}/confirm/ - Confirm workflow
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from rest_framework import status


@pytest.mark.django_db
class TestNLSessionAPI:
    """Test NL Session CRUD API with UUID primary keys."""

    def test_create_session(self, authenticated_client):
        """POST /api/v1/nl-workflow/sessions/ creates a session with UUID id."""
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Generated workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 100}, 'config': {}}
            ],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            response = authenticated_client.post('/api/v1/nl-workflow/sessions/', {
                'description': 'Create a simple workflow',
                'name': 'Test Session'
            })

        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        
        # Verify the session_id is a valid UUID
        session_uuid = response.data['session_id']
        assert isinstance(session_uuid, uuid.UUID), "session_id should be UUID"

    def test_list_sessions_returns_correct_format(self, authenticated_client, nl_session_with_workflow):
        """GET /api/v1/nl-workflow/sessions/ returns {code, message, data, count} format."""
        response = authenticated_client.get('/api/v1/nl-workflow/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        # Verify the response format
        assert 'code' in response.data
        assert 'message' in response.data
        assert 'data' in response.data
        assert 'count' in response.data
        
        assert response.data['code'] == 0
        assert response.data['message'] == 'success'
        assert isinstance(response.data['data'], list)
        assert response.data['count'] >= 1

    def test_list_sessions_empty(self, authenticated_client):
        """GET /api/v1/nl-workflow/sessions/ returns empty list when no sessions."""
        response = authenticated_client.get('/api/v1/nl-workflow/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['code'] == 0
        assert response.data['data'] == []
        assert response.data['count'] == 0

    def test_get_session_by_uuid(self, authenticated_client, nl_session_with_workflow):
        """GET /api/v1/nl-workflow/sessions/{uuid}/ retrieves session by UUID."""
        session_id = nl_session_with_workflow.id
        
        # Verify the session_id is a UUID
        assert isinstance(session_id, uuid.UUID)
        
        response = authenticated_client.get(f'/api/v1/nl-workflow/sessions/{session_id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['session_id'] == session_id
        assert response.data['name'] == nl_session_with_workflow.name
        assert 'workflow_json' in response.data

    def test_get_session_by_uuid_string(self, authenticated_client, nl_session_with_workflow):
        """GET /api/v1/nl-workflow/sessions/{uuid}/ works with UUID string."""
        session_id = str(nl_session_with_workflow.id)
        
        response = authenticated_client.get(f'/api/v1/nl-workflow/sessions/{session_id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['session_id']) == session_id

    def test_delete_session_by_uuid(self, authenticated_client, nl_session_with_workflow):
        """DELETE /api/v1/nl-workflow/sessions/{uuid}/ deletes session by UUID."""
        from nl_to_workflow.models import NLSession
        session_id = nl_session_with_workflow.id
        
        # Verify session exists
        assert NLSession.objects.filter(id=session_id).exists()
        
        response = authenticated_client.delete(f'/api/v1/nl-workflow/sessions/{session_id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        
        # Verify session is deleted
        assert not NLSession.objects.filter(id=session_id).exists()

    def test_delete_session_not_found(self, authenticated_client):
        """DELETE /api/v1/nl-workflow/sessions/{uuid}/ returns 404 for non-existent UUID."""
        non_existent_uuid = uuid.uuid4()
        
        response = authenticated_client.delete(f'/api/v1/nl-workflow/sessions/{non_existent_uuid}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_send_message(self, authenticated_client, nl_session_with_workflow):
        """POST /api/v1/nl-workflow/sessions/{uuid}/message/ appends message to conversation."""
        session_id = nl_session_with_workflow.id
        initial_message_count = len(nl_session_with_workflow.messages)
        
        mock_response = {
            'message': 'Understood, adding email step.',
            'suggestions': ['添加更多步骤'],
            'workflow': nl_session_with_workflow.workflow_json
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.continue_conversation.return_value = mock_response
            mock_service.return_value = mock_instance

            response = authenticated_client.post(
                f'/api/v1/nl-workflow/sessions/{session_id}/message/',
                {'message': '添加邮件发送步骤'}
            )

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        
        # Verify message was added to session
        nl_session_with_workflow.refresh_from_db()
        assert len(nl_session_with_workflow.messages) == initial_message_count + 2  # user + assistant

    def test_send_message_empty(self, authenticated_client, nl_session):
        """POST /api/v1/nl-workflow/sessions/{uuid}/message/ with empty message returns error."""
        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/message/',
            {'message': ''}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_send_message_session_not_found(self, authenticated_client):
        """POST /api/v1/nl-workflow/sessions/{uuid}/message/ returns 404 for non-existent session."""
        non_existent_uuid = uuid.uuid4()
        
        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{non_existent_uuid}/message/',
            {'message': 'Test message'}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_confirm_workflow(self, authenticated_client, nl_session_with_workflow):
        """POST /api/v1/nl-workflow/sessions/{uuid}/confirm/ saves workflow to database."""
        session_id = nl_session_with_workflow.id
        
        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{session_id}/confirm/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'workflow_id' in response.data
        assert 'workflow_json' in response.data
        
        # Verify session is updated
        nl_session_with_workflow.refresh_from_db()
        assert nl_session_with_workflow.status == 'completed'
        assert nl_session_with_workflow.workflow is not None

    def test_confirm_workflow_no_workflow(self, authenticated_client, nl_session):
        """POST /api/v1/nl-workflow/sessions/{uuid}/confirm/ returns error when no workflow exists."""
        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_patch_session_rename(self, authenticated_client, nl_session):
        """PATCH /api/v1/nl-workflow/sessions/{uuid}/ updates session name."""
        new_name = 'Renamed Session'
        
        response = authenticated_client.patch(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/',
            {'name': new_name}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == new_name
        
        nl_session.refresh_from_db()
        assert nl_session.name == new_name

    def test_user_isolation(self, authenticated_client, user):
        """Users cannot access other users' sessions."""
        from nl_to_workflow.models import NLSession
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Create another user and their session
        other_user = User.objects.create_user(
            username='other_user',
            email='other@example.com',
            password='pass123'
        )
        other_session = NLSession.objects.create(
            user=other_user,
            name='Other User Session',
            description='Test'
        )
        
        # Try to access the other user's session
        response = authenticated_client.get(f'/api/v1/nl-workflow/sessions/{other_session.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_intent_analysis_endpoint(self, authenticated_client):
        """POST /api/v1/nl-workflow/analyze-intent/ analyzes user intent."""
        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance._get_intent_details.return_value = {'intent': 'create', 'targets': []}
            mock_service.return_value = mock_instance

            response = authenticated_client.post(
                '/api/v1/nl-workflow/analyze-intent/',
                {'message': '创建一个问答机器人'}
            )

        assert response.status_code == status.HTTP_200_OK
        assert 'intent' in response.data
        assert 'details' in response.data

    def test_suggest_endpoint(self, authenticated_client):
        """POST /api/v1/nl-workflow/suggest/ returns suggestions."""
        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance._generate_suggestions_from_description.return_value = [
                '添加 AI 处理节点',
                '添加条件分支'
            ]
            mock_service.return_value = mock_instance

            response = authenticated_client.post(
                '/api/v1/nl-workflow/suggest/',
                {'description': 'Create a workflow'}
            )

        assert response.status_code == status.HTTP_200_OK
        assert 'suggestions' in response.data
        assert 'count' in response.data
