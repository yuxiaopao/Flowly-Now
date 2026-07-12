"""Unit tests for site-factory role agents."""

import json
import os
import tempfile
import unittest

from website_generator.site_factory.role_agents.design_tokens import (
    build_design_tokens,
    tokens_to_css_variables,
    write_design_tokens,
)
from website_generator.site_factory.role_agents.scopes import can_write_path
from website_generator.site_factory.role_agents.patch import apply_file_patches
from website_generator.site_factory.role_agents.backend_agent import run_backend_setup
from website_generator.site_factory.role_agents.frontend_agent import run_frontend_setup
from website_generator.site_factory.role_agents.ui_agent import run_ui_beautify
from website_generator.site_factory.role_agents.review_agent import run_site_code_review


class RoleAgentScopeTests(unittest.TestCase):
    def test_backend_cannot_write_frontend(self):
        ok, reason = can_write_path('backend_setup', 'frontend/index.html')
        self.assertFalse(ok)
        self.assertTrue(reason)

    def test_ui_can_write_css(self):
        ok, _ = can_write_path('ui_beautify', 'frontend/src/styles/theme.css')
        self.assertTrue(ok)


class RoleAgentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, 'backend'), exist_ok=True)
        os.makedirs(os.path.join(self.tmp, 'frontend'), exist_ok=True)
        with open(os.path.join(self.tmp, 'backend', 'app.py'), 'w', encoding='utf-8') as f:
            f.write('from flask import Flask, jsonify\napp = Flask(__name__)\n@app.route("/predict")\ndef predict():\n    return jsonify({})\n')
        with open(os.path.join(self.tmp, 'backend', 'config.json'), 'w', encoding='utf-8') as f:
            json.dump({'port': 5000, 'labels': ['a'], 'model_type': 'detection'}, f)
        with open(os.path.join(self.tmp, 'frontend', 'index.html'), 'w', encoding='utf-8') as f:
            f.write('<html><head><style></style></head><body><div class="upload-zone">上传</div></body></html>')

    def test_design_tokens(self):
        tokens = build_design_tokens({'ui_tone': 'alert_red'}, {'primaryColor': '#ef4444'})
        self.assertEqual(tokens['colors']['primary'], '#ef4444')
        css = tokens_to_css_variables(tokens)
        self.assertIn('--color-primary', css)
        path = write_design_tokens(self.tmp, tokens)
        self.assertTrue(os.path.isfile(path))

    def test_backend_setup_rules(self):
        result = run_backend_setup(self.tmp, agent_mode='rules', allow_core_edit=True, auto_qa=False)
        self.assertTrue(result.get('backend_ready'))
        with open(os.path.join(self.tmp, 'backend', 'app.py'), encoding='utf-8') as f:
            content = f.read()
        self.assertIn('/health', content)

    def test_frontend_setup_rules(self):
        result = run_frontend_setup(self.tmp, agent_mode='rules', auto_qa=False)
        self.assertTrue(result.get('frontend_ready'))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, 'frontend', 'src', 'App.vue')))

    def test_ui_beautify_rules(self):
        write_design_tokens(self.tmp, build_design_tokens({}, {}))
        result = run_ui_beautify(self.tmp, agent_mode='rules', auto_qa=False)
        self.assertGreaterEqual(result.get('ui_score', 0), 60)

    def test_site_code_review(self):
        run_backend_setup(self.tmp, agent_mode='rules', allow_core_edit=True, auto_qa=False)
        result = run_site_code_review(self.tmp, website_type='detection', agent_mode='rules', max_rounds=1)
        self.assertIn(result.get('review_gate'), ('green', 'yellow', 'red'))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, '.flowly', 'review', 'review_report.json')))

    def test_patch_denies_cross_scope(self):
        result = apply_file_patches(
            self.tmp,
            'ui_beautify',
            [{'path': 'backend/app.py', 'content': 'bad'}],
        )
        self.assertEqual(result['files_changed'], [])
        self.assertTrue(result['errors'])


if __name__ == '__main__':
    unittest.main()
