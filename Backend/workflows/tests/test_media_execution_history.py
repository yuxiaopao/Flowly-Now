from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from rest_framework.test import APIClient

from workflows.models import Node, NodeExecution, Workflow, WorkflowExecution
from workflows.services.media_execution import (
    begin_media_execution, complete_media_execution, fail_media_execution,
    report_media_progress,
)


class MediaExecutionHistoryTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='media-owner')
        self.other = get_user_model().objects.create_user(username='media-other')
        self.workflow = Workflow.objects.create(owner=self.owner, name='蝶羽演示')
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_job_is_visible_while_running_and_after_completion(self):
        execution = begin_media_execution(self.workflow, self.owner, source_details={'label': '本地成片'})
        report_media_progress(execution, 40)
        response = self.client.get(f'/api/v1/workflows/executions/{execution.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'running')
        self.assertEqual(response.data['progress'], 40)
        outputs = {'video_url': '/media/final.mp4', 'images': [{'url': '/media/keyframe.png'}]}
        complete_media_execution(execution, outputs)
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'completed')
        self.assertEqual(execution.progress, 100)
        self.assertEqual(execution.output_data, outputs)
        self.assertFalse(execution.node_executions.exists())
        response = self.client.get(f'/api/v1/workflows/executions/?workflow={self.workflow.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(str(execution.pk), str(response.data))

    def test_archive_is_idempotent_and_keeps_failed_provider_record(self):
        cloud = WorkflowExecution.objects.create(workflow=self.workflow, version=1, status='failed')
        first = begin_media_execution(self.workflow, self.owner, archive_key='film-v1')
        complete_media_execution(first, {'video_url': '/media/v1.mp4'})
        second = begin_media_execution(self.workflow, self.owner, archive_key='film-v1')
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.workflow.executions.count(), 2)
        cloud.refresh_from_db()
        self.assertEqual(cloud.status, 'failed')

    def test_other_user_cannot_register_or_read_owner_job(self):
        with self.assertRaises(PermissionDenied):
            begin_media_execution(self.workflow, self.other)
        execution = begin_media_execution(self.workflow, self.owner)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/v1/workflows/executions/{execution.pk}/').status_code, 404)

    def test_failure_preserves_partial_artifacts_and_cannot_complete(self):
        execution = begin_media_execution(self.workflow, self.owner)
        fail_media_execution(execution, '编码失败', partial_outputs={'images': [{'url': '/media/source.png'}]})
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'failed')
        self.assertEqual(execution.output_data['images'][0]['url'], '/media/source.png')
        with self.assertRaises(ValueError):
            complete_media_execution(execution, {'video_url': '/media/final.mp4'})

    def test_empty_output_does_not_mark_job_completed(self):
        execution = begin_media_execution(self.workflow, self.owner)
        with self.assertRaises(ValueError):
            complete_media_execution(execution, {})
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'running')

    def test_service_cannot_modify_native_workflow_execution(self):
        execution = WorkflowExecution.objects.create(workflow=self.workflow, version=1, status='running')
        with self.assertRaises(ValueError):
            complete_media_execution(execution, {'video_url': '/media/final.mp4'})
        with self.assertRaises(ValueError):
            fail_media_execution(execution, 'not a media job')
        with self.assertRaises(ValueError):
            report_media_progress(execution, 20)

    def test_failed_runs_expose_successful_node_artifacts_in_history(self):
        execution = WorkflowExecution.objects.create(workflow=self.workflow, version=1, status='failed')
        node = Node.objects.create(workflow=self.workflow, name='已生成关键帧', node_type='image_generation')
        NodeExecution.objects.create(execution=execution, node=node, node_version=1, status='completed', output_data={'images': [{'url': '/media/keyframe.png'}]})
        response = self.client.get(f'/api/v1/workflows/executions/{execution.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['artifact_outputs'][0]['output_data']['images'][0]['url'], '/media/keyframe.png')
