"""Lock down the live 2.5 failure at the actual video-node HTTP boundary."""
from unittest.mock import Mock, patch

import httpx
from django.test import SimpleTestCase

from workflows.services.langchain_service import LangChainService


class AgnesVideoProtocolTests(SimpleTestCase):
    def run_video(self, config, creation=None, polls=None):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        client.post.return_value = httpx.Response(200, json=creation or {
            "id": "task_internal", "video_id": "video_public", "status": "queued",
        })
        client.get.side_effect = polls or [httpx.Response(200, json={
            "status": "completed", "seconds": "5", "metadata": {"url": "https://media.test/final.mp4"},
        })]
        service = LangChainService()
        with patch.object(service, "_agnes_credential", return_value=("test-secret", "https://provider.test/v1")), \
             patch.object(service, "_agnes_httpx_client", return_value=client), \
             patch("workflows.services.langchain_service.time.sleep"):
            result = service.run_video_generation_node({"provider": "agnes", "prompt": "animate", "duration": 5, **config}, {})
        return result, client

    def test_keyframe_uses_modern_fields_and_public_video_id(self):
        result, client = self.run_video({"model": "agnes-video-2.5", "input_image": "https://media.test/frame.png"})
        self.assertTrue(result["success"], result)
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["mode"], "keyframe")
        self.assertEqual(payload["first_frame"], "https://media.test/frame.png")
        self.assertEqual(payload["seconds"], "5")
        self.assertEqual(payload["size"], "720P")
        self.assertNotIn("image", payload)
        self.assertEqual(client.get.call_args.args[0], "https://provider.test/agnesapi")
        self.assertEqual(client.get.call_args.kwargs["params"], {"video_id": "video_public", "model_name": "agnes-video-2.5"})
        self.assertEqual(result["output"]["video_url"], "https://media.test/final.mp4")

    def test_text_mode_and_1080p(self):
        result, client = self.run_video({"model": "agnes-video-2.5", "resolution": "1080p"})
        self.assertTrue(result["success"])
        payload = client.post.call_args.kwargs["json"]
        self.assertEqual(payload["mode"], "text")
        self.assertEqual(payload["size"], "1080P")
        self.assertNotIn("first_frame", payload)

    def test_reference_mode_sends_all_public_images_and_preserves_seed(self):
        references=['https://media.test/motif.png','https://media.test/garment.png']
        result,client=self.run_video({'model':'agnes-video-2.5','mode':'reference','duration':10,'referenceImages':references,'seed':26841})
        self.assertTrue(result['success'],result)
        payload=client.post.call_args.kwargs['json']
        self.assertEqual(payload['mode'],'reference')
        self.assertEqual(payload['images'],references)
        self.assertEqual(payload['seed'],26841)
        self.assertNotIn('first_frame',payload)
        self.assertEqual(result['output']['generation_mode'],'reference')
        self.assertEqual(result['output']['video_id'],'video_public')

    def test_invalid_reference_configuration_fails_before_api_submission(self):
        for extra in ({'mode':'reference'}, {'mode':'reference','referenceImages':['http://a']*6,'model':'agnes-video-2.5-flash'}, {'mode':'text','referenceImages':['http://a']}, {'mode':'reference','referenceImages':'not-an-array'}):
            result,client=self.run_video({'model':'agnes-video-2.5',**extra})
            self.assertFalse(result['success'],result)
            client.post.assert_not_called()

    def test_owner_submission_slot_waits_for_shared_account_window(self):
        from workflows.services.agnes_video import reserve_submission
        waited=Mock()
        with patch('django.core.cache.cache.add',side_effect=[False,True]) as reserve,patch('time.sleep') as sleep:
            reserve_submission(1036,65,waited)
            waited.assert_called_once()
            sleep.assert_called_once()
            self.assertEqual(reserve.call_args.kwargs['timeout'],65)

    def test_flash_and_legacy_contracts_remain_distinct(self):
        for model in ("agnes-video-2.5-flash", "agnes-video-v2.0"):
            with self.subTest(model=model):
                result, client = self.run_video({"model": model, "input_image": "https://media.test/frame.png"})
                self.assertTrue(result["success"])
                if model.endswith("v2.0"):
                    self.assertIn("image", client.post.call_args.kwargs["json"])
                    self.assertNotIn("mode", client.post.call_args.kwargs["json"])
                    self.assertEqual(client.get.call_args.args[0], "https://provider.test/v1/videos/task_internal")
                else:
                    self.assertEqual(client.get.call_args.kwargs["params"]["model_name"], model)

    def test_invalid_duration_and_resolution_fail_before_submission(self):
        for extra in ({"duration": 15}, {"duration": 4.5}, {"duration": None}, {"resolution": "4k"}, {"model": "agnes-video-2.5-flash", "resolution": "1080p"}):
            with self.subTest(extra=extra):
                result, client = self.run_video({"model": "agnes-video-2.5", **extra})
                self.assertFalse(result["success"])
                client.post.assert_not_called()

    def test_missing_public_id_does_not_poll_internal_task(self):
        result, client = self.run_video({"model": "agnes-video-2.5"}, creation={"id": "task_internal"})
        self.assertFalse(result["success"])
        client.get.assert_not_called()

    def test_processing_then_completion_and_failure(self):
        result, client = self.run_video({"model": "agnes-video-2.5"}, polls=[
            httpx.Response(200, json={"status": "processing", "progress": 30}),
            httpx.Response(200, json={"status": "completed", "url": "https://media.test/final.mp4"}),
        ])
        self.assertTrue(result["success"])
        self.assertEqual(client.get.call_count, 2)
        result, _ = self.run_video({"model": "agnes-video-2.5"}, polls=[httpx.Response(200, json={"status": "failed", "error": "provider failure"})])
        self.assertFalse(result["success"])
        self.assertIn("provider failure", result["error"])
