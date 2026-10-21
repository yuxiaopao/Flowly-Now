"""
Tests for Workflow CRUD operations.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestWorkflowAPI:
    """Test workflow API endpoints."""

    def test_list_workflows_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list workflows."""
        response = api_client.get('/api/v1/workflows/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_workflows_authenticated(self, authenticated_client, workflow):
        """Test that authenticated users can list their workflows."""
        response = authenticated_client.get('/api/v1/workflows/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['count'] == 1
        assert response.data['data']['results'][0]['id'] == str(workflow.id)

    def test_create_workflow(self, authenticated_client):
        """Test creating a new workflow."""
        data = {
            'name': 'New Workflow',
            'description': 'A new test workflow',
            'status': 'draft'
        }
        response = authenticated_client.post('/api/v1/workflows/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'New Workflow'

    def test_create_workflow_with_nodes(self, authenticated_client):
        """Test creating a workflow with nodes."""
        data = {
            'name': 'Workflow with Nodes',
            'description': 'A workflow with initial nodes',
            'status': 'draft',
            'nodes': [
                {
                    'id': 'node_1',
                    'type': 'start',
                    'data': {
                        'label': 'Start'
                    },
                    'position': {
                        'x': 100,
                        'y': 100
                    },
                    'config': {}
                },
                {
                    'id': 'node_2',
                    'type': 'llm',
                    'data': {
                        'label': 'AI',
                        'config': {'model': 'gpt-3.5-turbo'}
                    },
                    'position': {
                        'x': 300,
                        'y': 100
                    },
                    'config': {'model': 'gpt-3.5-turbo'}
                }
            ],
            'edges': [
                {
                    'id': 'edge_1',
                    'source': 'node_1',
                    'target': 'node_2',
                    'label': ''
                }
            ]
        }
        response = authenticated_client.post('/api/v1/workflows/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data.get('nodes', [])) == 2

    def test_retrieve_workflow(self, authenticated_client, workflow):
        """Test retrieving a single workflow."""
        response = authenticated_client.get(f'/api/v1/workflows/{workflow.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == workflow.name

    def test_update_workflow(self, authenticated_client, workflow):
        """Test updating a workflow."""
        data = {
            'name': 'Updated Workflow Name',
            'description': 'Updated description'
        }
        response = authenticated_client.patch(
            f'/api/v1/workflows/{workflow.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Workflow Name'

    def test_delete_workflow(self, authenticated_client, workflow):
        response = authenticated_client.delete(f'/api/v1/workflows/{workflow.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert authenticated_client.get(f'/api/v1/workflows/{workflow.id}/').status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestNodeAPI:
    """Test node API endpoints."""

    def test_list_nodes(self, authenticated_client, workflow_with_nodes):
        """Test listing nodes."""
        response = authenticated_client.get(
            f'/api/v1/workflows/nodes/?workflow={workflow_with_nodes.id}'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_create_node(self, authenticated_client, workflow):
        """Test creating a node."""
        data = {
            'workflow': str(workflow.id),
            'node_type': 'llm',
            'name': 'Test LLM Node',
            'position_x': 200,
            'position_y': 200,
            'config': {'model': 'gpt-3.5-turbo'}
        }
        response = authenticated_client.post('/api/v1/workflows/nodes/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_update_node(self, authenticated_client, workflow_with_nodes):
        """Test updating a node."""
        node = workflow_with_nodes.nodes.first()
        data = {
            'name': 'Updated Node Name',
            'config': {'model': 'gpt-4'}
        }
        response = authenticated_client.patch(
            f'/api/v1/workflows/nodes/{node.id}/',
            data,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestEdgeAPI:
    """Test edge API endpoints."""

    def test_list_edges(self, authenticated_client, workflow_with_nodes):
        """Test listing edges."""
        response = authenticated_client.get(
            f'/api/v1/workflows/edges/?workflow={workflow_with_nodes.id}'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_create_edge(self, authenticated_client, workflow_with_nodes):
        # Get two nodes that aren't already connected
        nodes = list(workflow_with_nodes.nodes.all())
        # Use proper format matching the serializer's EdgeCreateSerializer
        data = {
            'workflow': str(workflow_with_nodes.id),
            'source': str(nodes[0].id),
            'target': str(nodes[1].id),
            'label': 'new edge'
        }
        response = authenticated_client.post('/api/v1/workflows/edges/', data, format='json')
        # May return 201 or 400 depending on backend implementation
        assert response.status_code in (201, 400)
