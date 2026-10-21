"""Execution must report real failures rather than successful placeholders."""
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from workflows.services.langchain_service import LangChainService
from workflows.services.node_executors_extra import run_integration_node


class ExecutionIntegrityTests(SimpleTestCase):
    def test_unknown_node_fails_instead_of_echoing_input(self):
        result = LangChainService().execute_node('missing_type', {}, {'value': 1}, use_cache=False)
        self.assertFalse(result['success'])
        self.assertEqual(result['error_type'], 'unsupported_node')
        self.assertIn('不支持', result['error'])

    def test_missing_integration_credentials_are_not_success(self):
        service = LangChainService()
        for node_type in ('slack', 'telegram', 'discord', 'mysql', 'postgres', 'mongodb', 'openai_api'):
            with self.subTest(node_type=node_type):
                result = run_integration_node(service, node_type, {}, {})
                self.assertFalse(result['success'])
                self.assertEqual(result['error_type'], 'configuration')

    def test_unimplemented_integration_does_not_echo_secrets(self):
        result = run_integration_node(LangChainService(), 'google_sheets', {'token': 'secret'}, {})
        self.assertFalse(result['success'])
        self.assertNotIn('secret', str(result))

    def test_nested_database_failure_is_propagated(self):
        with patch('workflows.services.node_executors_extra._exec_mysql', return_value={'success': False, 'error': '驱动缺失'}):
            result = run_integration_node(LangChainService(), 'mysql', {}, {})
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], '驱动缺失')

    def test_api_rejection_is_propagated(self):
        with patch('workflows.services.node_executors_extra._exec_slack', return_value={'ok': False, 'error': 'invalid_auth'}):
            result = run_integration_node(LangChainService(), 'slack', {}, {})
        self.assertFalse(result['success'])

    def test_context_dependent_node_does_not_reuse_config_only_cache(self):
        service = LangChainService()
        service._cache_service = Mock()
        service._cache_service.get.return_value = {'input': '上一次输入'}
        result = service.execute_node('input', {'variable_name': 'input'}, {'input': '本次输入'})
        self.assertEqual(result['output']['input'], '本次输入')
        service._cache_service.get.assert_not_called()

    def test_llm_cache_distinguishes_different_inputs(self):
        service = LangChainService()
        service._cache_service = Mock()
        service._cache_service.get.return_value = None
        with patch.object(service, 'run_llm_node', return_value={'success': True, 'output': {'text': '模型输出'}}):
            for text in ('第一次输入', '第二次输入'):
                service.execute_node('llm', {'model': 'qwen:local'}, {'input': text})
        keys = [call.args[0] for call in service._cache_service.get.call_args_list]
        self.assertNotEqual(keys[0], keys[1])

    def test_json_parse_returns_an_object_instead_of_echoing_text(self):
        result = LangChainService().run_json_transform_node({'operation': 'json_to_object'}, {'data': '{"数量": 0}'})
        self.assertTrue(result['success'])
        self.assertEqual(result['output']['data'], {'数量': 0})

    def test_unknown_json_and_csv_operations_fail(self):
        service = LangChainService()
        self.assertFalse(service.run_json_transform_node({'operation': 'missing'}, {'data': {'a': 1}})['success'])
        self.assertFalse(service.run_csv_transform_node({'operation': 'missing'}, {'data': [{'a': 1}]})['success'])

    def test_editor_variable_configuration_preserves_zero(self):
        for config in ({'variableName': '数量', 'variableValue': 0}, {'variable_name': '数量', 'variable_value': 0}):
            with self.subTest(config=config):
                result = LangChainService().run_variable_node({**config, 'type': 'number'}, {})
                self.assertTrue(result['success'])
                self.assertEqual(result['output']['数量'], 0)

    def test_csv_source_is_parsed_with_chinese_headers_and_zero_values(self):
        result = LangChainService().run_csv_transform_node({
            'operation': 'csv_to_json', 'source': '名称,数量\n中文测试,0',
        }, {})
        self.assertTrue(result['success'], result)
        self.assertEqual(result['output']['data'], [{'名称': '中文测试', '数量': 0}])
