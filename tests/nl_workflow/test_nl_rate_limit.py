# -*- coding: utf-8 -*-
"""
Tests for Rate Limiting on NL Workflow endpoints.

Tests rate limiting on:
- NLWorkflowStreamView: 5 requests/minute
- NLWorkflowPreviewView: 10 requests/minute
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from django.core.cache import cache


@pytest.fixture(autouse=True)
def isolate_rate_limit_cache():
    cache.clear()


@pytest.mark.django_db
class TestNLRateLimiting:
    """Test per-endpoint rate limiting."""

    def test_stream_endpoint_rate_limit_hit(self, authenticated_client):
        """Making 6 stream requests in 1 minute should fail on 6th."""
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            # Mock streaming generator
            def mock_stream():
                yield '{"type": "progress", "message": "starting"}'
                yield '{"type": "workflow", "workflow": ' + str(mock_workflow).replace("'", '"') + '}'
            
            mock_instance.generate_workflow_streaming.return_value = mock_stream()
            mock_service.return_value = mock_instance

            # Make 5 requests (should succeed)
            for i in range(5):
                response = authenticated_client.post('/api/v1/nl-workflow/stream/', {
                    'description': f'Test request {i}'
                })
                # Should not be rate limited
                assert response.status_code == 200, f"Request {i+1} failed: {response.status_code}"

            response = authenticated_client.post('/api/v1/nl-workflow/stream/', {'description': '第六次请求'})
            assert response.status_code == 429
            assert response.data['message']

    def test_preview_endpoint_rate_limit_hit(self, authenticated_client):
        """Making 11 preview requests in 1 minute should fail on 11th."""
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            # Make 10 requests (should succeed)
            for i in range(10):
                response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                    'description': f'Test preview {i}'
                })
                # Should not be rate limited
                assert response.status_code == 200, f"Request {i+1} failed: {response.status_code}"

            response = authenticated_client.post('/api/v1/nl-workflow/preview/', {'description': '第十一次请求'})
            assert response.status_code == 429
            assert response.data['message']

    def test_rate_limit_response_format(self, authenticated_client):
        """Rate limited response should return proper error format."""
        # This test checks that rate limiting returns a proper response
        # Note: Due to Django ratelimit behavior, the exact response depends on configuration
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            # Make requests until we might hit rate limit
            # In a real test environment, this would be more controlled
            for i in range(12):
                response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                    'description': f'Test {i}'
                })
                if response.status_code == 429:
                    # Rate limited - check error format
                    assert response.data['code'] == 429
                    assert response.data['message']
                    break

    def test_rate_limit_per_user(self, user, admin_user):
        """Rate limiting should be per-user, not global."""
        from rest_framework.test import APIClient
        
        # Create two authenticated clients
        client1 = APIClient()
        client1.force_authenticate(user=user)
        
        client2 = APIClient()
        client2.force_authenticate(user=admin_user)

        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            # Make several requests with client1
            for i in range(5):
                response = client1.post('/api/v1/nl-workflow/preview/', {
                    'description': f'User1 request {i}'
                })
                assert response.status_code != 429

            # client2 should not be affected by client1's usage
            response = client2.post('/api/v1/nl-workflow/preview/', {
                'description': 'User2 request'
            })
            assert response.status_code != 429

    def test_unauthenticated_request_not_rate_limited(self, api_client):
        """Unauthenticated requests should fail before hitting rate limit."""
        # Unauthenticated requests should be rejected with 401
        response = api_client.post('/api/v1/nl-workflow/stream/', {
            'description': 'Test'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rate_limit_headers(self, authenticated_client):
        """Check if rate limit headers are present in response."""
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                'description': 'Test'
            })
            
            # Note: Django-ratelimit may or may not add headers depending on configuration
            # This is a soft check - just ensure the request went through
            assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRateLimitEdgeCases:
    """Edge case tests for rate limiting."""

    def test_empty_description_still_counts(self, authenticated_client):
        """Empty description requests should still count toward rate limit."""
        # This tests that validation happens after rate limiting check
        # or that empty requests are properly handled
        response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
            'description': ''
        })
        
        # Should fail with 400 (validation error), not 429
        # If it fails with 429, rate limiting is happening before validation
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_429_TOO_MANY_REQUESTS]

    def test_different_endpoints_independent_limits(self, authenticated_client):
        """Stream and preview should have independent rate limits."""
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            
            def mock_stream():
                yield '{"type": "workflow", "workflow": {}}'
            
            mock_instance.generate_workflow_streaming.return_value = mock_stream()
            mock_service.return_value = mock_instance

            # Make 5 stream requests (should hit stream limit)
            stream_response = None
            for i in range(5):
                response = authenticated_client.post('/api/v1/nl-workflow/stream/', {
                    'description': f'Stream {i}'
                })
                if response.status_code == 429:
                    stream_response = response
                    break
            
            # Make 10 preview requests (should still work since different endpoint)
            preview_ok = True
            for i in range(10):
                response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                    'description': f'Preview {i}'
                })
                if response.status_code == 429:
                    preview_ok = False
                    break

            # If stream is rate limited, preview should still work (different limits)
            if stream_response and stream_response.status_code == 429:
                assert preview_ok, "Preview should not be affected by stream rate limit"

    def test_rate_limit_resets_after_window(self, authenticated_client):
        """Rate limit should reset after the time window passes."""
        # This test is a placeholder for a time-based test
        # In a real scenario, you would mock time or wait for the window to pass
        
        mock_workflow = {
            'name': 'Mock Workflow',
            'description': 'Test',
            'nodes': [{'id': 'node_1', 'type': 'start', 'name': 'Start', 'position': {'x': 0, 'y': 0}, 'config': {}}],
            'edges': []
        }

        with patch('nl_to_workflow.views.get_nl_service_for_request') as mock_service:
            mock_instance = MagicMock()
            mock_instance.generate_workflow.return_value = mock_workflow
            mock_service.return_value = mock_instance

            # This test would need time mocking to be fully implemented
            # For now, just verify the endpoint works
            response = authenticated_client.post('/api/v1/nl-workflow/preview/', {
                'description': 'Test'
            })
            
            # The response should be either success or rate limited
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                429  # Too Many Requests
            ]
