"""Media module contracts using explicit dependencies at provider boundaries."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from workflows.services.execution_errors import LocalImageModelError
from workflows.services.langchain_service import LangChainService
from workflows.services.media_nodes import MediaNodeExecutor, _normalize_image_size, _resolve_zimage_dtype


class MediaNodeModuleTests(SimpleTestCase):
    def executor(self, **overrides):
        dependencies = {
            'user_id': 17,
            'credential': lambda provider: 'test-only-provider-key',
            'render_template': lambda template, context: template,
            'report_progress': lambda event: None,
            'run_llm': lambda config, context: {'success': False, 'error': 'chat unavailable'},
        }
        return MediaNodeExecutor(**{**dependencies, **overrides})

    def test_image_provider_uses_explicit_identity_credentials_and_context(self):
        credential = Mock(return_value='test-only-provider-key')
        client = Mock()
        client.images.generate.return_value = SimpleNamespace(data=[SimpleNamespace(url='https://media.test/output.png')])
        executor = self.executor(credential=credential)
        with patch('openai.OpenAI', return_value=client) as sdk:
            result = executor.run_image_generation_node({'provider': 'openai'}, {'prompt': 'branch-local image'})
        self.assertTrue(result['success'])
        credential.assert_called_once_with('openai')
        self.assertEqual(sdk.call_args.kwargs['api_key'], 'test-only-provider-key')
        self.assertEqual(client.images.generate.call_args.kwargs['prompt'], 'branch-local image')
        self.assertEqual(result['output']['images'][0]['url'], 'https://media.test/output.png')

    def test_subtitle_translation_uses_injected_chat_and_preserves_timestamps(self):
        chat = Mock(return_value={
            'success': True,
            'output': {'text': '[{"index":0,"translated_text":"Hello"}]'},
        })
        result = self.executor(run_llm=chat).run_subtitle_translate_node(
            {'target_language': 'en'}, {'segments': [{'start': 0.25, 'end': 1.75, 'text': '你好'}]},
        )
        self.assertTrue(result['success'], result)
        translated = result['output']['segments'][0]
        self.assertEqual(translated['translated_text'], 'Hello')
        self.assertEqual((translated['start'], translated['end']), (0.25, 1.75))
        self.assertIn('Hello', result['output']['subtitles_srt'])
        chat.assert_called_once()

    def test_translation_failure_propagates_from_injected_chat(self):
        result = self.executor().run_subtitle_translate_node(
            {'target_language': 'en'}, {'segments': [{'start': 0, 'end': 1, 'text': '你好'}]},
        )
        self.assertFalse(result['success'])
        self.assertIn('chat unavailable', result['error'])

    def test_local_image_dimensions_are_validated_without_loading_a_model(self):
        self.assertEqual(_normalize_image_size('512x768'), (512, 768))
        for invalid in ('512', '0x768', 'wide', '512x768x3'):
            with self.subTest(invalid=invalid), self.assertRaises(LocalImageModelError):
                _normalize_image_size(invalid)

    def test_cpu_image_dtype_does_not_require_gpu_modules(self):
        torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False), float32='cpu-float32')
        self.assertEqual(_resolve_zimage_dtype(torch, 'auto'), 'cpu-float32')
        with self.assertRaises(LocalImageModelError):
            _resolve_zimage_dtype(torch, 'unsupported')

    def test_lazy_facade_observes_current_credential_and_progress_callbacks(self):
        service = LangChainService(user_id=17)
        media = service.media
        progress = Mock()
        service.set_progress_reporter(progress)
        with patch.object(service, '_get_credential', return_value='updated-test-key'):
            self.assertEqual(media._get_credential('openai'), 'updated-test-key')
        media._report_progress({'progress': 42})
        progress.assert_called_once_with({'progress': 42})
        self.assertIs(service.media, media)
