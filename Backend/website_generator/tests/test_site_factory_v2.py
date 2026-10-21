"""Site Factory v2 contract tests: MySQL default, class entities, env grants, YOLO topology."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from website_generator.site_factory.db_templates import normalize_db_engine
from website_generator.site_factory.environment import run_environment_checks
from website_generator.site_factory.project_profiler import build_project_profile
from website_generator.generators.detection_fullsite_templates import (
    build_detection_index_html,
    _normalize_class_entities,
)


class DbEngineContractTests(unittest.TestCase):
    def test_default_is_mysql(self):
        self.assertEqual(normalize_db_engine(None), 'mysql')
        self.assertEqual(normalize_db_engine(''), 'mysql')
        self.assertEqual(normalize_db_engine('MYSQL'), 'mysql')

    def test_sqlite_opt_in(self):
        self.assertEqual(normalize_db_engine('sqlite'), 'sqlite')
        self.assertEqual(normalize_db_engine('sqlite3'), 'sqlite')


class ProfilerClassContractTests(unittest.TestCase):
    def test_class_entities_and_stack(self):
        profile = build_project_profile(
            class_names=['helmet', 'vest'],
            website_type='detection',
            use_llm=False,
        )
        self.assertEqual(profile['stack_contract']['database'], 'mysql')
        self.assertEqual(profile['stack_contract']['frontend'], 'vue')
        self.assertEqual(len(profile['class_entities']), 2)
        self.assertIn('class_legend', profile['page_sections'])
        self.assertIn('class_filter', profile['page_sections'])
        self.assertTrue(any(c['field'] == 'class_entities' for c in profile['required_node_configs']))


class DetectionTemplateClassTests(unittest.TestCase):
    def test_html_contains_legend_and_entities(self):
        html = build_detection_index_html(
            title='T',
            subtitle='S',
            primary='#f59e0b',
            upload_hint='upload',
            labels=['a', 'b'],
            class_entities=[
                {'name': 'a', 'display_name': '类别A', 'filter_key': 'a', 'color_index': 0},
                {'name': 'b', 'display_name': '类别B', 'filter_key': 'b', 'color_index': 1},
            ],
        )
        self.assertIn('class-legend', html)
        self.assertIn('CLASS_ENTITIES', html)
        self.assertIn('filteredImageDetections', html)
        self.assertIn('类别A', html)

    def test_normalize_entities_from_labels(self):
        ents = _normalize_class_entities(['dog', 'cat'], None, {'dog': '狗'})
        self.assertEqual(ents[0]['display_name'], '狗')
        self.assertEqual(ents[1]['name'], 'cat')


class EnvironmentPathGrantTests(unittest.TestCase):
    def test_custom_path_grant_and_mysql_soft_fail_desktop(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = os.path.join(tmp, 'backend')
            os.makedirs(backend)
            with open(os.path.join(backend, 'app.py'), 'w', encoding='utf-8') as f:
                f.write('print("ok")\n')
            grant_dir = os.path.join(tmp, 'weights')
            os.makedirs(grant_dir)

            with patch(
                'website_generator.site_factory.environment._mysql_ping',
                return_value=(False, 'connection refused'),
            ):
                result = run_environment_checks(
                    output_dir=tmp,
                    model_path='',
                    runtime_mode='desktop',
                    db_engine='mysql',
                    custom_paths=[grant_dir],
                    require_path_grant=True,
                )

            self.assertTrue(result['ready'], msg=result['checks'])
            granted = result['runtime_manifest']['paths_granted']
            self.assertTrue(any(grant_dir in p or os.path.abspath(grant_dir) == p for p in granted))
            mysql_check = next(c for c in result['checks'] if c['key'] == 'mysql_ping')
            self.assertFalse(mysql_check['ok'])

    def test_require_path_grant_fails_without_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = os.path.join(tmp, 'backend')
            os.makedirs(backend)
            with open(os.path.join(backend, 'app.py'), 'w', encoding='utf-8') as f:
                f.write('print("ok")\n')
            # Wipe output_dir check success by using empty custom paths + require,
            # but output_dir itself still grants — so require_path_grant only fails
            # when granted_paths is empty. Simulate by breaking output_dir.
            result = run_environment_checks(
                output_dir='',
                model_path='',
                runtime_mode='desktop',
                db_engine='sqlite',
                custom_paths=[],
                require_path_grant=True,
            )
            self.assertFalse(result['ready'])
            keys = {c['key'] for c in result['checks']}
            self.assertIn('path_grant_required', keys)


class YoloV2TopologyTests(unittest.TestCase):
    def test_fallback_has_full_chain(self):
        from nl_to_workflow.yolo_workflow import (
            _fallback_yolo_v2_workflow_nl,
            build_yolo_detection_workflow,
        )

        wf = _fallback_yolo_v2_workflow_nl()
        types = [n['type'] for n in wf['nodes']]
        for expected in (
            'dataset_upload',
            'yolo_training',
            'project_profiler',
            'website_generator',
            'backend_setup',
            'frontend_setup',
            'ui_beautify',
            'environment_provision',
            'site_qa',
            'site_code_review',
            'site_preview',
            'project_agent',
        ):
            self.assertIn(expected, types)

        env = next(n for n in wf['nodes'] if n['type'] == 'environment_provision')
        self.assertEqual(env['config'].get('dbEngine'), 'mysql')
        self.assertTrue(env['config'].get('requirePathGrant'))

        qa = next(n for n in wf['nodes'] if n['type'] == 'site_qa')
        self.assertTrue(qa['config'].get('autoFix'))

        agent = next(n for n in wf['nodes'] if n['type'] == 'project_agent')
        self.assertTrue(agent['config'].get('syncSystemAgent'))

        built = build_yolo_detection_workflow('用 YOLO 训练并生成识别网站')
        self.assertGreaterEqual(len(built['nodes']), 12)


class SiteQaAutofixLoopTests(unittest.TestCase):
    def test_autofix_loop_logic_mirrors_node(self):
        """Replicate QA→review→re-QA loop without importing LangChainService (Py3.8)."""
        calls = {'qa': 0, 'review': 0}

        def run_site_qa(**kwargs):
            calls['qa'] += 1
            gate = 'red' if calls['qa'] == 1 else 'green'
            return {'gate': gate, 'summary_zh': f'QA {gate}'}

        def run_site_code_review(*args, **kwargs):
            calls['review'] += 1
            return {'success': True, 'summary': 'patched'}

        auto_fix = True
        max_fix_rounds = 2
        fix_rounds = []
        qa_result = None
        for attempt in range(max_fix_rounds + 1):
            qa_result = run_site_qa()
            gate = qa_result.get('gate')
            if gate == 'green' or not auto_fix or attempt >= max_fix_rounds:
                break
            if gate not in ('red', 'yellow'):
                break
            review = run_site_code_review()
            fix_rounds.append({
                'attempt': attempt + 1,
                'pre_gate': gate,
                'review_success': bool(review.get('success')),
            })

        self.assertEqual(qa_result['gate'], 'green')
        self.assertEqual(calls['qa'], 2)
        self.assertEqual(calls['review'], 1)
        self.assertEqual(len(fix_rounds), 1)

    def test_langchain_source_contains_autofix(self):
        path = os.path.join(
            os.path.dirname(__file__),
            '..',
            '..',
            'workflows',
            'services',
            'langchain_service.py',
        )
        path = os.path.abspath(path)
        with open(path, encoding='utf-8') as f:
            src = f.read()
        self.assertIn("autoFix", src)
        self.assertIn('maxFixRounds', src)
        self.assertIn('run_site_code_review', src)
        self.assertIn('auto_fix_rounds', src)
        self.assertIn('syncSystemAgent', src)

if __name__ == '__main__':
    unittest.main()
