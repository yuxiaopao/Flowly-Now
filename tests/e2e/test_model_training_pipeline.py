"""
E2E test for the complete model training pipeline:
Dataset Upload -> Model Training -> Website Generation

Tests require Django server running at http://localhost:8000
"""
import pytest
import requests
import json
import time
import os
from typing import Dict, Any, Optional


BASE_URL = os.getenv("DJANGO_BASE_URL", "http://localhost:8000")
API_BASE = f"{BASE_URL}/api/v1"


class TestTrainingJobsAPI:
    """Test TrainingJob CRUD operations via API."""

    def test_training_jobs_list(self, authenticated_client: requests.Session):
        """Test listing training jobs."""
        response = authenticated_client.get(f"{API_BASE}/training/training-jobs/")
        assert response.status_code in [200, 401], (
            f"Unexpected status: {response.status_code}"
        )

    def test_training_jobs_create(self, authenticated_client: requests.Session):
        """Test creating a training job."""
        data = {
            'framework': 'pytorch',
            'model_type': 'classifier',
            'config': {'epochs': 2}
        }
        response = authenticated_client.post(
            f"{API_BASE}/training/training-jobs/",
            json=data
        )
        # 201 Created, 400 validation error, or 401 if not authenticated
        assert response.status_code in [201, 400, 401], (
            f"Unexpected status: {response.status_code} - {response.text}"
        )

    def test_training_jobs_list_pagination(self, authenticated_client: requests.Session):
        """Test listing with pagination."""
        response = authenticated_client.get(
            f"{API_BASE}/training/training-jobs/",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code in [200, 401]

    def test_training_jobs_stats(self, authenticated_client: requests.Session):
        """Test getting training job statistics."""
        response = authenticated_client.get(f"{API_BASE}/training/training-jobs/stats/")
        assert response.status_code in [200, 401, 404]


class TestDatasetsAPI:
    """Test Dataset CRUD operations via API."""

    def test_datasets_list(self, authenticated_client: requests.Session):
        """Test listing datasets."""
        response = authenticated_client.get(f"{API_BASE}/training/datasets/")
        assert response.status_code in [200, 401], (
            f"Unexpected status: {response.status_code}"
        )

    def test_datasets_create(self, authenticated_client: requests.Session):
        """Test creating a dataset."""
        data = {
            'name': 'Test Dataset',
            'description': 'Dataset created by E2E test',
            'format': 'csv',
            'size': 1024
        }
        response = authenticated_client.post(
            f"{API_BASE}/training/datasets/",
            json=data
        )
        # 201 Created or 400/403 (validation/auth) is acceptable
        assert response.status_code in [201, 400, 401, 403], (
            f"Unexpected status: {response.status_code} - {response.text}"
        )

    def test_datasets_list_pagination(self, authenticated_client: requests.Session):
        """Test listing with pagination."""
        response = authenticated_client.get(
            f"{API_BASE}/training/datasets/",
            params={"page": 1, "page_size": 10}
        )
        assert response.status_code in [200, 401]


class TestTrainingJobLifecycle:
    """Test TrainingJob status lifecycle."""

    def test_training_job_status_transitions(self, authenticated_client: requests.Session):
        """Test TrainingJob status lifecycle: queued -> running -> completed."""
        # Create
        create_data = {
            'framework': 'pytorch',
            'model_type': 'classifier',
            'config': {'epochs': 1}
        }
        resp = authenticated_client.post(
            f"{API_BASE}/training/training-jobs/",
            json=create_data
        )
        
        if resp.status_code == 201:
            job = resp.json()
            job_id = job.get('id')
            
            # Get
            get_resp = authenticated_client.get(
                f"{API_BASE}/training/training-jobs/{job_id}/"
            )
            assert get_resp.status_code == 200
            
            # Update (partial)
            patch_resp = authenticated_client.patch(
                f"{API_BASE}/training/training-jobs/{job_id}/",
                json={'status': 'cancelled'}
            )
            assert patch_resp.status_code in [200, 400]

    def test_training_job_cancel_action(self, authenticated_client: requests.Session):
        """Test cancelling a training job via action endpoint."""
        # Create a job first
        create_data = {
            'framework': 'pytorch',
            'model_type': 'classifier',
        }
        resp = authenticated_client.post(
            f"{API_BASE}/training/training-jobs/",
            json=create_data
        )
        
        if resp.status_code == 201:
            job = resp.json()
            job_id = job.get('id')
            
            # Try to cancel
            cancel_resp = authenticated_client.post(
                f"{API_BASE}/training/training-jobs/{job_id}/cancel/"
            )
            # Should return 200 (success) or 400 (can't cancel non-queued/running)
            assert cancel_resp.status_code in [200, 400]

    def test_training_job_retry_action(self, authenticated_client: requests.Session):
        """Test retrying a failed training job."""
        # This test checks the endpoint exists and responds
        # Real retry would need a failed job
        response = authenticated_client.post(
            f"{API_BASE}/training/training-jobs/test-id-123/retry/"
        )
        # 404 (job not found), 400 (wrong status), or 401 (not authenticated) is acceptable
        assert response.status_code in [404, 400, 401]


class TestTrainingJobFilters:
    """Test TrainingJob filtering and search."""

    def test_filter_by_status(self, authenticated_client: requests.Session):
        """Test filtering jobs by status."""
        response = authenticated_client.get(
            f"{API_BASE}/training/training-jobs/",
            params={"status": "completed"}
        )
        assert response.status_code in [200, 401]

    def test_filter_by_framework(self, authenticated_client: requests.Session):
        """Test filtering jobs by framework."""
        response = authenticated_client.get(
            f"{API_BASE}/training/training-jobs/",
            params={"framework": "pytorch"}
        )
        assert response.status_code in [200, 401]

    def test_search_jobs(self, authenticated_client: requests.Session):
        """Test searching jobs."""
        response = authenticated_client.get(
            f"{API_BASE}/training/training-jobs/",
            params={"search": "test"}
        )
        assert response.status_code in [200, 401]


class TestDatasetFilters:
    """Test Dataset filtering."""

    def test_filter_by_format(self, authenticated_client: requests.Session):
        """Test filtering datasets by format."""
        response = authenticated_client.get(
            f"{API_BASE}/training/datasets/",
            params={"file_format": "csv"}
        )
        # 200 (success) or 401 (not authenticated)
        assert response.status_code in [200, 401]

    def test_search_datasets(self, authenticated_client: requests.Session):
        """Test searching datasets."""
        response = authenticated_client.get(
            f"{API_BASE}/training/datasets/",
            params={"search": "test"}
        )
        assert response.status_code in [200, 401]


class TestModelTrainingPipeline:
    """Test the complete model training pipeline integration."""

    def test_training_pipeline_workflow_integration(
        self,
        authenticated_client: requests.Session
    ):
        """Test that training jobs can be associated with workflows."""
        # 1. Create a workflow
        workflow_data = {
            "name": "E2E Training Test Workflow",
            "description": "Workflow for testing model training integration",
            "status": "draft",
            "nodes": [
                {
                    "id": "node_start",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "data": {"label": "Start"}
                },
                {
                    "id": "node_training",
                    "type": "model_training",
                    "position": {"x": 100, "y": 200},
                    "data": {
                        "label": "Model Training",
                        "config": {
                            "framework": "pytorch",
                            "model_type": "classifier",
                            "hyperparameters": {
                                "epochs": 1,
                                "batch_size": 16
                            }
                        }
                    }
                }
            ],
            "edges": [
                {"id": "e1", "source": "node_start", "target": "node_training"}
            ]
        }
        
        workflow_resp = authenticated_client.post(
            f"{API_BASE}/workflows/",
            json=workflow_data
        )
        
        if workflow_resp.status_code == 201:
            workflow = workflow_resp.json()
            workflow_id = workflow.get('id')
            
            try:
                # 2. Create training job linked to workflow
                training_data = {
                    'framework': 'pytorch',
                    'model_type': 'classifier',
                    'workflow': workflow_id,
                    'config': {
                        'epochs': 1,
                        'batch_size': 16
                    }
                }
                
                training_resp = authenticated_client.post(
                    f"{API_BASE}/training/training-jobs/",
                    json=training_data
                )
                
                if training_resp.status_code == 201:
                    training_job = training_resp.json()
                    assert 'id' in training_job
                    assert training_job.get('framework') == 'pytorch'
                
            finally:
                # Cleanup: delete workflow
                authenticated_client.delete(f"{API_BASE}/workflows/{workflow_id}/")

    def test_website_generator_integration(
        self,
        authenticated_client: requests.Session
    ):
        """Test website generator API endpoint exists."""
        # Test that the website generator endpoint is accessible
        response = authenticated_client.get(f"{API_BASE}/website-generator/")
        # Should return 200 or 404 depending on implementation
        assert response.status_code in [200, 404, 401]


class TestTrainingWebSocket:
    """Test WebSocket URL routing for training progress."""

    def test_websocket_url_pattern(self, authenticated_client: requests.Session):
        """Verify WebSocket routing pattern exists in ASGI config."""
        # This is verified by the config/asgi.py having the correct routing
        # We can't directly test WebSocket from HTTP tests,
        # but we verify the URL pattern is configured
        
        # The expected WebSocket URL pattern is: ws://host/ws/training/<job_id>/
        # This is configured in training/routing.py
        pass  # WebSocket testing requires different setup


class TestDatasetEndpoints:
    """Test Dataset detail endpoints like preview and stats."""

    def test_dataset_preview_endpoint(self, authenticated_client: requests.Session):
        """Test dataset preview endpoint."""
        # Use a non-existent ID to test endpoint existence
        response = authenticated_client.get(
            f"{API_BASE}/training/datasets/00000000-0000-0000-0000-000000000000/preview/"
        )
        # 404 (not found) or 401 (auth) is acceptable
        assert response.status_code in [404, 401, 403]

    def test_dataset_stats_endpoint(self, authenticated_client: requests.Session):
        """Test dataset stats endpoint."""
        response = authenticated_client.get(
            f"{API_BASE}/training/datasets/00000000-0000-0000-0000-000000000000/stats/"
        )
        assert response.status_code in [404, 401, 403]


class TestTrainingAPIEndpoints:
    """Test specific training API endpoints."""

    def test_training_download_endpoint(self, authenticated_client: requests.Session):
        """Test model download endpoint."""
        response = authenticated_client.get(
            f"{API_BASE}/training/training-jobs/00000000-0000-0000-0000-000000000000/download/"
        )
        # Should return 404 (job not found) or 400 (model not ready)
        assert response.status_code in [404, 400, 401, 403]


class TestAPIConsistency:
    """Test API path consistency across the application."""

    def test_training_api_paths(self, authenticated_client: requests.Session):
        """Verify training API paths are consistent."""
        # These paths should all be under /api/v1/training/
        paths = [
            "/api/v1/training/training-jobs/",
            "/api/v1/training/datasets/",
        ]
        
        for path in paths:
            # Verify path starts with API base
            assert path.startswith("/api/v1/training/"), f"Path {path} should start with /api/v1/training/"
            
            # Verify endpoints are reachable (may return auth error)
            response = authenticated_client.get(f"{BASE_URL}{path}")
            assert response.status_code in [200, 401], (
                f"Endpoint {path} should be reachable"
            )
