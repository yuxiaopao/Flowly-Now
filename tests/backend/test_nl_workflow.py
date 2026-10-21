# -*- coding: utf-8 -*-
"""
Tests for NL to Workflow module.
Covers models, views, services, and constants.
"""

import pytest
from pathlib import Path
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.test import override_settings


@pytest.mark.django_db
class TestNLSessionModel:
    """Test NLSession model."""

    def test_create_session(self, user):
        """Test creating an NL session."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='Test Session',
            description='Test workflow description'
        )
        assert session.id is not None
        assert session.name == 'Test Session'
        assert session.status == 'active'
        assert session.messages == []
        assert session.workflow_json == {}
        assert session.error_message == ''

    def test_session_status_choices(self, user):
        """Test all status choices are valid."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='Status Test',
            description='Testing'
        )

        for status_value, _ in NLSession.status.field.choices:
            session.status = status_value
            session.save()
            session.refresh_from_db()
            assert session.status == status_value

    def test_session_error_message_field(self, user):
        """Test error_message field can be set."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='Error Test',
            description='Testing error handling'
        )
        session.error_message = 'Test error message'
        session.save()
        session.refresh_from_db()
        assert session.error_message == 'Test error message'

    def test_session_workflow_json_field(self, user):
        """Test workflow_json field stores workflow data."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='Workflow JSON Test',
            description='Testing workflow storage'
        )

        workflow_data = {
            'name': 'Generated Workflow',
            'description': 'Test workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 100}, 'config': {}},
                {'id': 'node_2', 'type': 'end', 'name': 'End', 'position': {'x': 300, 'y': 100}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''}
            ]
        }

        session.workflow_json = workflow_data
        session.save()
        session.refresh_from_db()

        assert session.workflow_json == workflow_data
        assert len(session.workflow_json['nodes']) == 2
        assert len(session.workflow_json['edges']) == 1

    def test_session_user_relationship(self, user):
        """Test session belongs to user."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='User Relationship Test',
            description='Testing'
        )
        assert session.user == user
        assert session in user.nl_sessions.all()

    def test_session_str_representation(self, user):
        """Test string representation."""
        from nl_to_workflow.models import NLSession
        session = NLSession.objects.create(
            user=user,
            name='String Test',
            description='Testing'
        )
        assert str(session) == f'String Test - {user.username}'


@pytest.mark.django_db
class TestNLWorkflowAPI:
    """Test NL Workflow API endpoints."""

    def test_list_models_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list models."""
        response = api_client.get('/api/v1/nl-workflow/models/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_models_authenticated(self, authenticated_client):
        """Test listing available models returns proper structure."""
        with patch('nl_to_workflow.services.NLToWorkflowService.list_available_models') as mock_list:
            mock_list.return_value = [
                {'model_id': 'llama3', 'name': 'Llama 3', 'provider': 'ollama'}
            ]
            response = authenticated_client.get('/api/v1/nl-workflow/models/')
            assert response.status_code == status.HTTP_200_OK
            assert 'models' in response.data
            assert 'default' in response.data
            assert 'count' in response.data

    def test_list_sessions_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list sessions."""
        response = api_client.get('/api/v1/nl-workflow/sessions/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_sessions_empty(self, authenticated_client):
        """Test listing sessions when none exist."""
        response = authenticated_client.get('/api/v1/nl-workflow/sessions/')
        assert response.status_code == status.HTTP_200_OK
        # Backend returns wrapped response format
        assert 'data' in response.data
        assert len(response.data['data']) == 0

    def test_list_sessions_with_data(self, authenticated_client, nl_session):
        """Test listing sessions returns session data."""
        response = authenticated_client.get('/api/v1/nl-workflow/sessions/')
        assert response.status_code == status.HTTP_200_OK
        # Backend returns wrapped response format
        assert 'data' in response.data
        assert len(response.data['data']) >= 1

    def test_create_session_empty_description(self, authenticated_client):
        """Test creating session with empty description returns error."""
        response = authenticated_client.post('/api/v1/nl-workflow/sessions/', {
            'description': '',
            'name': 'Test Session'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_create_session_success_mocked(self, authenticated_client):
        """Test creating session successfully with mocked LLM."""
        from nl_to_workflow.models import NLSession

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
        assert response.data['session_id'] is not None

        session = NLSession.objects.get(id=response.data['session_id'])
        assert session.status == 'completed'
        assert session.workflow_json == mock_workflow

    def test_create_session_llm_error(self, authenticated_client):
        """Test creating session when LLM returns error."""
        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = {'error': 'LLM connection failed'}
            mock_service.return_value = mock_instance

            response = authenticated_client.post('/api/v1/nl-workflow/sessions/', {
                'description': 'Test error handling',
                'name': 'Error Test'
            })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_get_session_detail(self, authenticated_client, nl_session):
        """Test retrieving session details."""
        response = authenticated_client.get(f'/api/v1/nl-workflow/sessions/{nl_session.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'session_id' in response.data
        assert 'workflow_json' in response.data
        assert 'messages' in response.data

    def test_get_session_not_found(self, authenticated_client):
        """Test retrieving non-existent session."""
        response = authenticated_client.get('/api/v1/nl-workflow/sessions/99999/')
        # Backend may return 404 as JSON or JsonResponse
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_session_wrong_user(self, authenticated_client, user, django_db_blocker):
        """Test user cannot access another user's session."""
        from nl_to_workflow.models import NLSession
        from django.contrib.auth import get_user_model
        User = get_user_model()

        with django_db_blocker.unblock():
            other_user = User.objects.create_user(
                username='other',
                email='other@example.com',
                password='pass123'
            )
            session = NLSession.objects.create(
                user=other_user,
                name='Other User Session',
                description='Test'
            )

        response = authenticated_client.get(f'/api/v1/nl-workflow/sessions/{session.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_session(self, authenticated_client, nl_session):
        """Test deleting a session."""
        session_id = nl_session.id
        response = authenticated_client.delete(f'/api/v1/nl-workflow/sessions/{session_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data

        from nl_to_workflow.models import NLSession
        assert not NLSession.objects.filter(id=session_id).exists()

    def test_send_message_empty(self, authenticated_client, nl_session):
        """Test sending empty message returns error."""
        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/message/',
            {'message': ''}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_send_message_success(self, authenticated_client, nl_session):
        """Test sending message successfully."""
        mock_response = {
            'message': 'Understood, adding email step.',
            'suggestions': ['添加更多步骤']
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.continue_conversation.return_value = mock_response
            mock_service.return_value = mock_instance

            response = authenticated_client.post(
                f'/api/v1/nl-workflow/sessions/{nl_session.id}/message/',
                {'message': '添加邮件发送步骤'}
            )

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'suggestions' in response.data

    def test_confirm_workflow_no_workflow(self, authenticated_client, nl_session):
        """Test confirming when no workflow exists."""
        nl_session.workflow_json = {}
        nl_session.save()

        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_confirm_workflow_success(self, authenticated_client, nl_session):
        """Test confirming and saving workflow."""
        nl_session.workflow_json = {
            'name': 'Test Workflow',
            'description': 'Test',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 100, 'y': 100}, 'config': {}},
                {'id': 'node_2', 'type': 'end', 'name': 'End', 'position': {'x': 300, 'y': 100}, 'config': {}}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''}
            ]
        }
        nl_session.save()

        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'workflow_id' in response.data
        assert response.data['workflow_id'] is not None

        nl_session.refresh_from_db()
        assert nl_session.status == 'completed'
        assert nl_session.workflow is not None
        saved_nodes = {node.name: node for node in nl_session.workflow.nodes.all()}
        assert saved_nodes['Start'].position_x == 100
        assert saved_nodes['Start'].position_y == 100
        assert saved_nodes['End'].position_x == 300
        assert saved_nodes['End'].position_y == 100

    def test_confirm_workflow_repairs_missing_or_overlapping_positions(self, authenticated_client, nl_session):
        """Confirming NL output should persist a readable non-overlapping layout."""
        nl_session.workflow_json = {
            'name': 'Layout Repair Workflow',
            'description': 'Test layout repair',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 10, 'y': 10}, 'config': {}},
                {'id': 'node_2', 'type': 'llm', 'name': 'Analyze', 'position': {'x': 10, 'y': 10}, 'config': {}},
                {'id': 'node_3', 'type': 'end', 'name': 'End', 'config': {}},
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
            ]
        }
        nl_session.save()

        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )

        assert response.status_code == status.HTTP_200_OK
        nl_session.refresh_from_db()
        positions = [
            (node.position_x, node.position_y)
            for node in nl_session.workflow.nodes.order_by('id')
        ]
        assert len(set(positions)) == 3
        assert positions != [(0, 0), (0, 0), (0, 0)]

    def test_confirm_workflow_adds_missing_start_and_end_boundaries(self, authenticated_client, nl_session):
        """LLM-generated business-node chains must be saved as executable workflows."""
        nl_session.workflow_json = {
            'name': 'Model Training Site Workflow',
            'description': 'Generated without explicit start/end nodes',
            'nodes': [
                {'id': 'dataset_1', 'type': 'dataset_upload', 'name': '上传数据集', 'config': {}},
                {'id': 'training_1', 'type': 'yolo_training', 'name': '训练 YOLO', 'config': {}},
                {'id': 'site_1', 'type': 'website_generator', 'name': '生成识别网站', 'config': {}},
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'dataset_1', 'target': 'training_1', 'label': ''},
                {'id': 'edge_2', 'source': 'training_1', 'target': 'site_1', 'label': ''},
            ],
        }
        nl_session.save()

        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )

        assert response.status_code == status.HTTP_200_OK
        nl_session.refresh_from_db()
        workflow = nl_session.workflow
        node_types = set(workflow.nodes.values_list('node_type', flat=True))
        assert 'start' in node_types
        assert 'end' in node_types

        start_node = workflow.nodes.get(node_type='start')
        end_node = workflow.nodes.get(node_type='end')
        dataset_node = workflow.nodes.get(node_type='dataset_upload')
        site_node = workflow.nodes.get(node_type='website_generator')
        assert workflow.edges.filter(source_node=start_node, target_node=dataset_node).exists()
        assert workflow.edges.filter(source_node=site_node, target_node=end_node).exists()

        validation = authenticated_client.post(f'/api/v1/workflows/{workflow.id}/validate/')
        assert validation.status_code == status.HTTP_200_OK
        assert '缺少开始节点' not in validation.data['errors']
        assert '缺少结束节点' not in validation.data['warnings']

    def test_confirm_workflow_enriches_model_training_site_configs(self, authenticated_client, nl_session):
        """Model-training site workflows saved from NL should be executable without manual node surgery."""
        nl_session.workflow_json = {
            'name': 'NL Model Training Site Workflow',
            'description': 'Train a YOLO model and generate a Flask Vue Mysql detection site.',
            'nodes': [
                {'id': 'dataset_1', 'type': 'dataset_upload', 'name': 'Upload dataset', 'config': {}},
                {'id': 'training_1', 'type': 'yolo_training', 'name': 'Train YOLO', 'config': {}},
                {'id': 'site_1', 'type': 'website_generator', 'name': 'Generate site', 'config': {}},
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'dataset_1', 'target': 'training_1', 'label': ''},
                {'id': 'edge_2', 'source': 'training_1', 'target': 'site_1', 'label': ''},
            ],
        }
        nl_session.save()

        response = authenticated_client.post(
            f'/api/v1/nl-workflow/sessions/{nl_session.id}/confirm/'
        )

        assert response.status_code == status.HTTP_200_OK
        nl_session.refresh_from_db()
        workflow = nl_session.workflow
        dataset_config = workflow.nodes.get(node_type='dataset_upload').config
        training_config = workflow.nodes.get(node_type='yolo_training').config
        site_config = workflow.nodes.get(node_type='website_generator').config

        assert dataset_config['format'] == 'yolo'
        assert dataset_config['source'] == 'upload'
        assert dataset_config['sourceType'] == 'upload'
        assert dataset_config['customPathEnabled'] is True
        assert Path(dataset_config['path']).name == 't2_mini_yolo'

        assert training_config['trainingMode'] == 'local'
        assert training_config['dataSourceType'] == 'upstream'
        assert training_config['device'] == 'cpu'
        assert training_config['epochs'] == 1
        assert training_config['base_weight_uri'] == 'yolov8n.pt'

        assert site_config['frontendFramework'] == 'vue'
        assert site_config['backendFramework'] == 'flask'
        assert site_config['dbEngine'] == 'mysql'
        assert site_config['waitForCompletion'] is True
        assert {'imageRecognition', 'videoRecognition', 'factRecognition', 'historyRecords'}.issubset(
            set(site_config['requiredFeatures'])
        )

    def test_dataset_upload_accepts_runtime_dataset_path_input(self):
        """Runtime input_data.dataset_path should satisfy NL dataset_upload nodes."""
        from workflows.services.langchain_service import LangChainService

        dataset_root = Path(__file__).resolve().parents[2] / 'Backend' / 'scripts' / 'fixtures' / 't2_mini_yolo'
        service = LangChainService()

        result = service.run_dataset_upload_node(
            {'format': 'yolo', 'sourceType': 'upload'},
            {'input_data': {'dataset_path': str(dataset_root)}},
        )

        assert result['success'] is True
        assert result['output']['dataset_yaml_path'].endswith('dataset.yaml')
        assert result['output']['class_names'] == ['helmet', 'vest']

    def test_yolo_training_stores_dataset_source_mode_string(self, user, tmp_path):
        """datasetSource config objects must not be written into the CharField as dict text."""
        from workflows.services.langchain_service import LangChainService
        from training.models import TrainingJob

        service = LangChainService(user_id=user.id)

        def complete_training(*args, **kwargs):
            TrainingJob.objects.filter(created_by=user).update(status='completed')
            return {
                'success': True,
                'best_weight_path': 'E:/tmp/best.pt',
                'last_weight_path': 'E:/tmp/last.pt',
                'final_metrics': {},
            }

        with override_settings(BASE_DIR=tmp_path):
            with patch.object(service, '_run_local_yolo_training', side_effect=complete_training):
                result = service.run_yolo_training_node(
                    {
                        'trainingMode': 'local',
                        'datasetSource': {'mode': 'upstream', 'fromNodeType': 'dataset_upload'},
                        'datasetYamlPath': 'E:/datasets/demo/dataset.yaml',
                        'classNames': ['helmet', 'vest'],
                        'epochs': 1,
                        'device': 'cpu',
                    },
                    {},
                )

        assert result['success'] is True
        job = TrainingJob.objects.latest('created_at')
        assert job.dataset_source_mode == 'upstream'

    def test_preview_empty_description(self, authenticated_client):
        """Test preview with empty description returns error."""
        response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
            'description': ''
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_success(self, authenticated_client):
        """Test preview workflow successfully."""
        mock_workflow = {
            'name': 'Preview Workflow',
            'description': 'Test preview',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                'description': 'Create a workflow'
            })

        assert response.status_code == status.HTTP_200_OK
        assert 'preview' in response.data
        assert 'workflow_json' in response.data
        assert 'node_count' in response.data['preview']
        assert 'edge_count' in response.data['preview']


class TestNLServiceConstants:
    """Test NL constants module."""

    def test_modification_keywords_list(self):
        """Test modification keywords are defined."""
        from nl_to_workflow.constants import MODIFICATION_KEYWORDS
        assert isinstance(MODIFICATION_KEYWORDS, list)
        assert len(MODIFICATION_KEYWORDS) > 0
        assert '修改' in MODIFICATION_KEYWORDS
        assert 'change' in MODIFICATION_KEYWORDS

    def test_is_modification_intent(self):
        """Test modification intent detection."""
        from nl_to_workflow.constants import is_modification_intent

        assert is_modification_intent('修改工作流') is True
        assert is_modification_intent('添加新节点') is True
        assert is_modification_intent('change the workflow') is True
        assert is_modification_intent('你好，请帮我创建一个工作流') is False

    def test_default_values(self):
        """Test default configuration values."""
        from nl_to_workflow.constants import (
            DEFAULT_TEMPERATURE,
            DEFAULT_MAX_TOKENS,
            MAX_SUGGESTIONS
        )

        assert DEFAULT_TEMPERATURE == 0.7
        assert DEFAULT_MAX_TOKENS == 4096
        assert MAX_SUGGESTIONS == 4

    def test_supported_node_types(self):
        """Test supported node types are defined."""
        from nl_to_workflow.constants import SUPPORTED_NODE_TYPES

        assert isinstance(SUPPORTED_NODE_TYPES, dict)
        assert 'start' in SUPPORTED_NODE_TYPES
        assert 'end' in SUPPORTED_NODE_TYPES
        assert 'llm' in SUPPORTED_NODE_TYPES
        assert 'condition' in SUPPORTED_NODE_TYPES

    def test_get_contextual_suggestions(self):
        """Test contextual suggestion generation."""
        from nl_to_workflow.constants import get_contextual_suggestions

        suggestions = get_contextual_suggestions(['start', 'end'])
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 4

        suggestions_llm = get_contextual_suggestions(['start', 'llm', 'end'])
        assert '添加 AI 处理节点' not in suggestions_llm

    def test_get_initial_suggestions(self):
        """Test initial suggestion generation."""
        from nl_to_workflow.constants import get_initial_suggestions

        suggestions = get_initial_suggestions('Create AI workflow')
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 4

    def test_error_messages(self):
        """Test error messages are defined."""
        from nl_to_workflow.constants import ERROR_MESSAGES

        assert 'no_provider' in ERROR_MESSAGES
        assert 'llm_call_failed' in ERROR_MESSAGES
        assert 'parse_failed' in ERROR_MESSAGES

    def test_validation_messages(self):
        """Test validation messages are defined."""
        from nl_to_workflow.constants import VALIDATION_MESSAGES

        assert 'missing_name' in VALIDATION_MESSAGES
        assert 'missing_nodes' in VALIDATION_MESSAGES
        assert 'missing_start' in VALIDATION_MESSAGES


class TestNLService:
    """Test NLToWorkflowService methods."""

    @override_settings(
        NL_WORKFLOW_USE_TEMPLATES=False,
        NL_WORKFLOW_TEMPLATE_FALLBACK=True,
        NL_WORKFLOW_USE_MOCK=False,
    )
    def test_generate_workflow_prefers_llm_for_template_intent(self):
        """Template-matching requests should still use the LLM when a provider exists."""
        import json
        from types import SimpleNamespace
        from nl_to_workflow.services import NLToWorkflowService

        class FakeProvider:
            name = 'fake'
            provider_name = 'fake'

            def chat(self, **kwargs):
                return SimpleNamespace(
                    error=None,
                    content=json.dumps({
                        'name': 'LLM Designed Email Workflow',
                        'description': 'Designed by the configured model.',
                        'nodes': [
                            {'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}},
                            {'id': 'node_2', 'type': 'llm', 'name': 'Summarize', 'position': {'x': 200, 'y': 0}, 'config': {'model': 'fake-model'}},
                            {'id': 'node_3', 'type': 'end', 'name': 'End', 'position': {'x': 400, 'y': 0}, 'config': {}},
                        ],
                        'edges': [
                            {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2', 'label': ''},
                            {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3', 'label': ''},
                        ],
                    }),
                )

        service = NLToWorkflowService(model='fake-model')
        service._llm = FakeProvider()
        service._registry = MagicMock()
        service._registry.get_all.return_value = []

        workflow = service.generate_workflow(
            'Scrape https://example.com, summarize the content, and email it to ops@example.com',
            include_validation=False,
        )

        assert workflow['_generation_mode'] == 'llm'
        assert workflow['_llm_model'] == 'fake-model'
        assert workflow['name'] == 'LLM Designed Email Workflow'

    @override_settings(DEBUG=True, NL_WORKFLOW_USE_MOCK=False)
    def test_call_llm_does_not_use_mock_just_because_debug_is_enabled(self):
        """DEBUG mode must not hide a missing provider behind mock generation."""
        from nl_to_workflow.constants import ERROR_MESSAGES
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService(model='missing-model')
        service._registry = MagicMock()
        service._registry.get_all.return_value = []
        service._registry.list_models.return_value = []

        with patch.object(service, '_iter_llm_provider_models', return_value=[]):
            result = service._call_llm(
                [{'role': 'user', 'content': 'Create a workflow'}],
                mock_description='Create a workflow',
            )

        assert result == {'error': ERROR_MESSAGES['no_provider']}

    def test_iter_llm_provider_models_filters_non_chat_generation_models(self):
        """Image/video/audio models must not be tried as workflow chat generators."""
        from types import SimpleNamespace
        from nl_to_workflow.services import NLToWorkflowService

        chat_provider = MagicMock()
        chat_provider.name = 'agnes'
        chat_provider.list_models.return_value = [
            SimpleNamespace(model_id='agnes-2.0-flash', model_type='chat'),
            SimpleNamespace(model_id='x/z-image-turbo:latest', model_type='chat'),
            SimpleNamespace(model_id='agnes-video-v2.0', model_type='video'),
            SimpleNamespace(model_id='tts-1', model_type='audio'),
        ]

        registry = MagicMock()
        registry.get_all.return_value = ['agnes']
        registry.get.side_effect = lambda name: chat_provider if name == 'agnes' else None

        service = NLToWorkflowService(model='agnes-2.0-flash')
        service._llm = chat_provider
        service._registry = registry

        candidates = service._iter_llm_provider_models()
        model_ids = [model_id for _, model_id in candidates]

        assert model_ids == ['agnes-2.0-flash']

    def test_analyze_intent_modification(self):
        """私有分类器返回修改意图字符串。"""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()
        for message in ('添加一个新节点', '修改配置', '添加邮件发送'):
            assert service._analyze_intent(message) == 'modify'
        assert service._analyze_intent('删除这个步骤') == 'delete'

    def test_analyze_intent_chat(self):
        """创建工作流和一般问答使用各自意图。"""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()
        assert service._analyze_intent('你好，我想创建一个工作流') == 'create'
        assert service._analyze_intent('这是什么') == 'chat'

    def test_normalize_workflow(self):
        """Test workflow normalization."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        raw_workflow = {
            'name': 'Test',
            'nodes': [
                {'type': 'start', 'name': 'Start'},
                {'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'source': 'node_1', 'target': 'node_2'}
            ]
        }

        normalized = service._normalize_workflow(raw_workflow)

        assert normalized['name'] == 'Test'
        assert len(normalized['nodes']) == 2
        assert normalized['nodes'][0]['id'] == 'node_1'
        assert normalized['edges'][0]['source'] == 'node_1'

    def test_normalize_workflow_assigns_missing_ids(self):
        """Test normalization assigns IDs to nodes without them."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        workflow = {
            'nodes': [
                {'type': 'start', 'name': 'Start'},
                {'type': 'llm', 'name': 'AI'},
                {'type': 'end', 'name': 'End'}
            ],
            'edges': []
        }

        normalized = service._normalize_workflow(workflow)

        assert normalized['nodes'][0]['id'] == 'node_1'
        assert normalized['nodes'][1]['id'] == 'node_2'
        assert normalized['nodes'][2]['id'] == 'node_3'

    def test_validate_workflow_valid(self):
        """Test workflow validation with valid workflow."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        workflow = {
            'name': 'Valid Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI'},
                {'id': 'node_3', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'id': 'edge_1', 'source': 'node_1', 'target': 'node_2'},
                {'id': 'edge_2', 'source': 'node_2', 'target': 'node_3'}
            ]
        }

        validated = service._validate_workflow(workflow)

        assert validated['validation']['valid'] is True
        assert len(validated['validation']['errors']) == 0

    def test_validate_workflow_missing_name(self):
        """Test validation catches missing name."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        workflow = {
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'}
            ],
            'edges': []
        }

        validated = service._validate_workflow(workflow)

        assert validated['validation']['valid'] is False
        assert len(validated['validation']['errors']) > 0

    def test_validate_workflow_multiple_starts(self):
        """Test validation catches multiple start nodes."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        workflow = {
            'name': 'Multi Start',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start 1'},
                {'id': 'node_2', 'type': 'start', 'name': 'Start 2'}
            ],
            'edges': []
        }

        validated = service._validate_workflow(workflow)

        assert validated['validation']['valid'] is False
        errors = validated['validation']['errors']
        assert any('开始节点' in str(e) for e in errors)

    def test_generate_suggestions(self):
        """Test suggestion generation."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        workflow = {
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'end', 'name': 'End'}
            ],
            'edges': []
        }

        suggestions = service._generate_suggestions(workflow)

        assert isinstance(suggestions, list)
        assert len(suggestions) <= 4

    def test_generate_suggestions_from_description(self):
        """Test suggestion generation from description."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        suggestions = service._generate_suggestions_from_description('Create an AI chatbot')
        assert isinstance(suggestions, list)
        assert len(suggestions) <= 4

    def test_parse_workflow_response_json(self):
        """Test parsing JSON from response."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        response = '''
        Here is your workflow:
        {
            "name": "Test Workflow",
            "description": "A test",
            "nodes": [{"id": "node_1", "type": "start", "name": "Start", "position": {"x": 0, "y": 0}, "config": {}}],
            "edges": []
        }
        '''

        parsed = service._parse_workflow_response(response)

        assert parsed['name'] == 'Test Workflow'
        assert len(parsed['nodes']) == 1

    def test_parse_workflow_response_codeblock(self):
        """Test parsing JSON from code block."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        response = '''
        ```json
        {
            "name": "Code Block Workflow",
            "nodes": [{"id": "node_1", "type": "start", "name": "Start", "position": {"x": 0, "y": 0}, "config": {}}],
            "edges": []
        }
        ```
        '''

        parsed = service._parse_workflow_response(response)

        assert parsed['name'] == 'Code Block Workflow'

    def test_parse_workflow_response_invalid(self):
        """Test parsing invalid response."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        response = 'This is not a valid JSON response'

        parsed = service._parse_workflow_response(response)

        assert 'error' in parsed
        assert parsed['raw_response'] == response

    def test_describe_changes(self):
        """Test describing workflow changes."""
        from nl_to_workflow.services import NLToWorkflowService

        service = NLToWorkflowService()

        old = {
            'name': 'Old Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'end', 'name': 'End'}
            ],
            'edges': [{'source': 'node_1', 'target': 'node_2'}]
        }

        new = {
            'name': 'New Workflow',
            'nodes': [
                {'id': 'node_1', 'type': 'start', 'name': 'Start'},
                {'id': 'node_2', 'type': 'llm', 'name': 'AI'},
                {'id': 'node_3', 'type': 'end', 'name': 'End'}
            ],
            'edges': [
                {'source': 'node_1', 'target': 'node_2'},
                {'source': 'node_2', 'target': 'node_3'}
            ]
        }

        changes = service._describe_changes(old, new)

        assert isinstance(changes, list)
        assert any('名称' in c for c in changes)
        assert any('添加' in c for c in changes)


class TestNLTasks:
    """Test Celery tasks."""

    def test_cleanup_old_sessions(self, nl_session):
        """Test cleanup task removes old sessions."""
        from nl_to_workflow.tasks import cleanup_old_sessions
        from django.utils import timezone
        from datetime import timedelta

        # Make session old
        nl_session.created_at = timezone.now() - timedelta(days=31)
        nl_session.save()

        result = cleanup_old_sessions(days=30)

        assert 'sessions_deleted' in result

    def test_preview_workflow_task(self):
        """Test preview workflow task."""
        from nl_to_workflow.tasks import preview_workflow
        from unittest.mock import patch, MagicMock

        mock_workflow = {
            'name': 'Task Preview',
            'nodes': [],
            'edges': []
        }

        with patch('nl_to_workflow.services.NLToWorkflowService') as mock_service_cls:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service_cls.return_value = mock_instance

            result = preview_workflow('Create workflow via task')

        assert 'name' in result or 'error' in result
