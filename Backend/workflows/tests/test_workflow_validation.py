from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from workflows.services.workflow_validation import validate_imported_node, validate_workflow


def node(node_id, node_type, config=None):
    return SimpleNamespace(id=node_id, name=f'节点 {node_id}', node_type=node_type, config=config or {})


def workflow(nodes, links=()):
    return SimpleNamespace(owner_id=None, nodes=Mock(all=Mock(return_value=nodes)), edges=Mock(all=Mock(return_value=[
        SimpleNamespace(source_node_id=s, target_node_id=t) for s, t in links
    ])))


class WorkflowValidationTests(SimpleTestCase):
    def test_valid_native_graph(self):
        result = validate_workflow(workflow([node('a', 'start'), node('b', 'output'), node('c', 'end')], [('a', 'b'), ('b', 'c')]))
        self.assertTrue(result['valid'])

    def test_empty_unknown_cross_workflow_and_cycles_are_rejected(self):
        cases = [workflow([]), workflow([node('x', 'unknown')]), workflow([node('a', 'start')], [('a', 'other')]),
                 workflow([node('a', 'set'), node('b', 'set')], [('a', 'b'), ('b', 'a')])]
        for wf in cases:
            with self.subTest(wf=wf):
                self.assertFalse(validate_workflow(wf)['valid'])

    def test_disconnected_node_will_not_be_silently_ignored(self):
        result = validate_workflow(workflow([node('a', 'start'), node('b', 'end'), node('c', 'set')], [('a', 'b')]))
        self.assertFalse(result['valid'])
        self.assertIn('unreachable', [item['code'] for item in result['node_issues']])

    def test_input_false_and_zero_are_valid_but_missing_is_not(self):
        wf = workflow([node('a', 'input', {'variable_name': 'input'})])
        self.assertFalse(validate_workflow(wf, {})['valid'])
        self.assertTrue(validate_workflow(wf, {'input': 0})['valid'])
        self.assertTrue(validate_workflow(wf, {'input': False})['valid'])

    def test_n8n_gmail_read_must_not_send_email(self):
        errors = validate_imported_node('email', {'n8n_type': 'n8n-nodes-base.gmail', 'n8n_parameters': {'operation': 'get'}})
        self.assertTrue(errors)

    def test_n8n_complex_http_parameters_must_not_be_dropped(self):
        self.assertTrue(validate_imported_node('http_request', {
            'n8n_type': 'n8n-nodes-base.httpRequest', 'n8n_parameters': {'sendBody': True}, 'url': 'https://example.com',
        }))

    def test_manual_trigger_and_noop_preserve_payload(self):
        from workflows.services.langchain_service import LangChainService
        service = LangChainService()
        for typ, cfg in [('manual', {}), ('variable', {'n8n_type': 'n8n-nodes-base.noOp'})]:
            result = service.execute_node(typ, cfg, {'value': 42}, use_cache=False)
            self.assertTrue(result['success'])
            self.assertEqual(result['output']['value'], 42)

    def test_noop_chain_does_not_reembed_the_execution_history(self):
        from workflows.services.langchain_service import LangChainService
        service = LangChainService()
        cfg = {'n8n_type': 'n8n-nodes-base.noOp'}
        previous, outputs, variables = {'value': 42}, {}, {}
        for i in range(50):
            result = service.execute_node('variable', cfg, {
                'input_data': {'value': 42}, 'node_outputs': outputs,
                'variables': variables, '_branch_upstream': previous,
            }, use_cache=False)
            previous = result['output']
            self.assertEqual(previous, {'value': 42})
            outputs[str(i)] = previous
            variables[f'node_{i}_output'] = previous
