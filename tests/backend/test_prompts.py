"""
Tests for Prompt templates.
"""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPromptTemplateAPI:
    """Test prompt template API endpoints."""

    def test_list_templates_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list templates."""
        response = api_client.get('/api/v1/prompts/templates/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_templates_authenticated(self, authenticated_client):
        """Test that authenticated users can list templates."""
        response = authenticated_client.get('/api/v1/prompts/templates/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_template(self, authenticated_client):
        """Test creating a new prompt template."""
        data = {
            'name': 'Test Template',
            'description': 'A test template',
            'category': 'general',
            'template': 'Hello ${name}, welcome to ${place}!',
            'is_public': False
        }
        response = authenticated_client.post('/api/v1/prompts/templates/', data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test Template'

    def test_create_template_with_variables(self, authenticated_client):
        """Test creating a template with variables."""
        data = {
            'name': 'Template with Variables',
            'description': 'A template with variables',
            'template': 'Summarize: ${text}',
            'variables': [
                {
                    'name': 'text',
                    'label': 'Input Text',
                    'variable_type': 'textarea',
                    'required': True
                }
            ]
        }
        response = authenticated_client.post('/api/v1/prompts/templates/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_render_template(self, authenticated_client, user):
        """Test rendering a template."""
        from prompts.models import PromptTemplate
        template = PromptTemplate.objects.create(
            name='Test Render',
            template='Hello {name}!',
            created_by=user
        )

        response = authenticated_client.post(
            f'/api/v1/prompts/templates/{template.id}/render/',
            {'variables': {'name': 'World'}},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['rendered'] == 'Hello World!'

    def test_get_categories(self, api_client):
        """Test getting template categories."""
        response = api_client.get('/api/v1/prompts/categories/')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED)

    def test_get_featured_templates(self, api_client):
        """Test getting featured templates."""
        response = api_client.get('/api/v1/prompts/templates/featured/')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED)

    @pytest.mark.parametrize('use_slug', [False, True])
    def test_filter_by_category(self, authenticated_client, user, use_slug):
        from prompts.models import PromptCategory, PromptTemplate
        category = PromptCategory.objects.create(name='数据分析', slug='analysis')
        included = PromptTemplate.objects.create(name='分析模板', template='分析 {text}', category=category, created_by=user)
        PromptTemplate.objects.create(name='其他模板', template='总结 {text}', created_by=user)
        key = category.slug if use_slug else str(category.id)
        response = authenticated_client.get('/api/v1/prompts/templates/', {'category': key})
        assert response.status_code == 200
        page = response.data.get('data', response.data)
        assert page['count'] == 1
        assert page['results'][0]['id'] == str(included.id)

    def test_search_templates(self, authenticated_client):
        """Test searching templates."""
        response = authenticated_client.get(
            '/api/v1/prompts/templates/?search=test'
        )
        assert response.status_code == status.HTTP_200_OK
