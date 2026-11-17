"""Stdlib-only checks for the isolated MCP provider and database seed guard."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from Scripts.isolated_model_configuration_fixtures import (
    MODEL_IDS, _private_root, create_model_configuration_provider,
)


class ModelConfigurationProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_model_configuration_provider()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def call(self, endpoint, data=None, authenticated=True):
        headers = {'Content-Type': 'application/json'}
        if authenticated:
            headers['Authorization'] = 'Bearer qa-test-secret-never-recorded'
        request = Request(self.base + endpoint, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, json.load(response)
        except HTTPError as response:
            return response.code, json.load(response)

    def test_actual_chat_embedding_and_catalog_protocol(self):
        status, chat = self.call('/v1/chat/completions', {'model': MODEL_IDS['normal'], 'messages': []})
        self.assertEqual(status, 200)
        self.assertEqual(chat['choices'][0]['message']['content'], 'Isolated provider connection confirmed.')
        status, embedding = self.call('/v1/embeddings', {'model': MODEL_IDS['embedding'], 'input': 'fixture'})
        self.assertEqual((status, embedding['data'][0]['embedding']), (200, [.25, .5]))
        status, catalog = self.call('/v1/models')
        self.assertEqual(status, 200)
        self.assertEqual({row['id'] for row in catalog['data']}, set(MODEL_IDS.values()))
        self.assertNotIn('qa-test-secret', json.dumps(self.server.requests_seen))

    def test_empty_and_embedded_error_remain_real_upstream_responses(self):
        status, empty = self.call('/v1/chat/completions', {'model': MODEL_IDS['empty']})
        self.assertEqual(status, 200)
        self.assertEqual(empty['choices'][0]['message']['content'], '')
        status, error = self.call('/v1/chat/completions', {'model': MODEL_IDS['error']})
        self.assertEqual(status, 200)
        self.assertEqual(error['error']['message'], 'Isolated provider fixture error')

    def test_authentication_unknown_model_and_wrong_endpoint_are_not_successes(self):
        self.assertEqual(self.call('/v1/models', authenticated=False)[0], 401)
        self.assertEqual(self.call('/v1/chat/completions', {'model': 'not-a-fixture'})[0], 400)
        self.assertEqual(self.call('/arbitrary', {'model': MODEL_IDS['normal']})[0], 404)

    def test_private_seed_guard_rejects_business_database_and_media_paths(self):
        with TemporaryDirectory(prefix='flowly-model-guard-') as directory:
            root = Path(directory)
            settings = SimpleNamespace(DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': root / 'qa.sqlite3'}}, MEDIA_ROOT=root / 'media')
            with patch.dict(os.environ, {'FLOWLY_ISOLATED_QA': '1'}):
                self.assertEqual(_private_root(settings, root), root.resolve())
                settings.DATABASES['default']['NAME'] = root.parent / 'business.sqlite3'
                with self.assertRaisesRegex(RuntimeError, 'outside'):
                    _private_root(settings, root)
                settings.DATABASES['default']['NAME'] = root / 'qa.sqlite3'
                settings.MEDIA_ROOT = root.parent / 'business-media'
                with self.assertRaisesRegex(RuntimeError, 'outside'):
                    _private_root(settings, root)
                settings.MEDIA_ROOT = root / 'media'
                settings.DATABASES['default']['ENGINE'] = 'django.db.backends.mysql'
                with self.assertRaisesRegex(RuntimeError, 'SQLite'):
                    _private_root(settings, root)
            with patch.dict(os.environ, {'FLOWLY_ISOLATED_QA': '0'}):
                with self.assertRaisesRegex(RuntimeError, 'isolated'):
                    _private_root(settings, root)
