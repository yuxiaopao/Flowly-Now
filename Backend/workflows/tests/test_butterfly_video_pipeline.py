"""Run the real graph, gates and FFmpeg finishing without provider charges."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from scripts.create_butterfly_video_workflow import make_graph
from workflows.models import Edge, Node, Workflow, WorkflowExecution
from workflows.services.langchain_service import LangChainService
from workflows.services.media_service import local_path_from_public_url
from workflows.services.video_postprocess import probe_media
from workflows.services.workflow_executor import WorkflowExecutor


class ButterflyVideoPipelineTests(TestCase):
    def test_real_graph_produces_labelled_fifteen_second_video(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg and FFprobe required for media integration")
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=Path(directory)):
            root = Path(directory)
            clips = []
            for index, colour in enumerate(("navy", "gray", "white")):
                clip = root / f"test_{index}.mp4"
                subprocess.run([
                    "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"color=c={colour}:s=320x180:r=24", "-t", "0.5", "-c:v", "libx264", str(clip),
                ], check=True, capture_output=True, timeout=30)
                clips.append(str(clip))
            owner = get_user_model().objects.create_user(username="butterfly_test")
            workflow = Workflow.objects.create(name="test-only butterfly video", owner=owner)
            nodes, edges = make_graph("https://example.test/reference.png", "test")
            for item in nodes:
                Node.objects.create(workflow=workflow, **item)
            for edge in edges:
                Edge.objects.create(workflow=workflow, source_node_id=edge["source"], target_node_id=edge["target"])
            execution = WorkflowExecution.objects.create(workflow=workflow, triggered_by=owner, input_data={}, version=workflow.version)
            image_result = {"success": True, "output": {"images": [{"url": "https://example.test/frame.png"}]}}
            video_results = [{"success": True, "output": {"video_url": clip, "provider": "agnes"}} for clip in clips]
            with patch.object(LangChainService, "run_image_generation_node", return_value=image_result), \
                 patch.object(LangChainService, "run_video_generation_node", side_effect=video_results):
                WorkflowExecutor(workflow, execution, parallel_enabled=False).execute()
            execution.refresh_from_db()
            self.assertEqual(execution.status, "completed", execution.error_message)
            result = execution.output_data["variables"]
            path = local_path_from_public_url(result["final_video"])
            self.assertTrue(path.exists())
            media = probe_media(path)
            self.assertAlmostEqual(media["duration"], 15, places=1)
            self.assertTrue(result["burn_subtitles_applied"])
            self.assertIn("非实物成品", result["subtitles"])
            self.assertEqual(execution.node_executions.filter(status="completed").count(), len(nodes))
