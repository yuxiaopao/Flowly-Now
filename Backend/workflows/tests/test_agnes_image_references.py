"""Original design inputs reach the real provider boundary without leaking local paths."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import Mock, patch

from PIL import Image
from django.test import SimpleTestCase, override_settings
from workflows.services.langchain_service import LangChainService


class AgnesImageReferenceTests(SimpleTestCase):
    def test_uploaded_design_is_encoded_and_second_public_reference_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=Path(directory)):
            Image.new('RGB',(300,300)).save(Path(directory)/'board.png')
            service=LangChainService();client=Mock()
            client.images.generate.return_value=SimpleNamespace(data=[SimpleNamespace(url='https://media.test/output.png',b64_json=None,revised_prompt=None)])
            with patch.object(service,'_agnes_credential',return_value=('test-only-key','https://provider.test/v1')),patch('openai.OpenAI',return_value=client):
                result=service.run_image_generation_node({'provider':'agnes','model':'agnes-image-2.5-flash','size':'2K','ratio':'16:9','prompt':'use the original','referenceImages':['http://localhost/media/board.png','https://media.test/motif.png']},{})
            self.assertTrue(result['success'],result)
            payload=client.images.generate.call_args.kwargs
            self.assertEqual(payload['size'],'2K')
            self.assertEqual(payload['extra_body']['ratio'],'16:9')
            refs=payload['extra_body']['extra_body']['image']
            self.assertTrue(refs[0].startswith('data:image/png;base64,'))
            self.assertEqual(refs[1],'https://media.test/motif.png')

    def test_missing_template_and_media_traversal_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory,override_settings(MEDIA_ROOT=Path(directory)):
            service=LangChainService()
            for reference in ('{node_outputs.some-id.images.0.url}','http://localhost/media/../../outside.png'):
                with self.assertRaises(ValueError):
                    service._resolve_reference_images({'referenceImages':[reference]},{},encode_local=True)
