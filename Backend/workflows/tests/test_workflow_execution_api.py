from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from workflows.models import Edge, Node, Workflow, WorkflowExecution


@override_settings(CHANNEL_LAYERS={'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}})
class WorkflowExecutionApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='workflow-integrity-test', password='test-password')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.workflow = Workflow.objects.create(owner=self.user, name='中文数据通路验证')

    def graph(self, configs):
        previous = None
        for typ, cfg in configs:
            node = Node.objects.create(workflow=self.workflow, name=typ, node_type=typ, config=cfg)
            if previous:
                Edge.objects.create(workflow=self.workflow, source_node=previous, target_node=node)
            previous = node

    def execute(self, inputs=None):
        return self.client.post(f'/api/v1/workflows/{self.workflow.id}/execute/', {'input_data': inputs or {}, 'is_async': False}, format='json')

    def test_native_input_output_executes_and_records_output(self):
        self.graph([('start', {}), ('input', {'variable_name': 'input'}), ('output', {'template': '{input}'}), ('end', {})])
        response = self.execute({'input': '中文测试内容'})
        self.assertEqual(response.status_code, 200, response.data)
        execution = WorkflowExecution.objects.get(workflow=self.workflow)
        self.assertEqual(execution.status, 'completed')
        self.assertIn('中文测试内容', str(execution.output_data))
        self.assertEqual(execution.node_executions.filter(status='failed').count(), 0)
        self.assertEqual(execution.node_executions.filter(status='completed').count(), 4)
        self.assertEqual(execution.progress, 100)
        from workflows.services.partial_retry import analyze_continue
        self.assertFalse(analyze_continue(execution)['can_continue'])

    def test_unknown_and_n8n_business_mismatch_fail_before_execution(self):
        for typ, cfg in [('missing_type', {}), ('email', {'n8n_type': 'n8n-nodes-base.gmail', 'n8n_parameters': {'operation': 'get'}})]:
            self.workflow.nodes.all().delete()
            self.graph([(typ, cfg)])
            response = self.execute()
            self.assertEqual(response.status_code, 400)
            self.assertFalse(WorkflowExecution.objects.filter(workflow=self.workflow).exists())

    def test_parallel_boundary_nodes_have_execution_records(self):
        start = Node.objects.create(workflow=self.workflow, name='开始', node_type='start')
        for name in ('分支一结束', '分支二结束'):
            end = Node.objects.create(workflow=self.workflow, name=name, node_type='end')
            Edge.objects.create(workflow=self.workflow, source_node=start, target_node=end)
        response = self.execute()
        self.assertEqual(response.status_code, 200, response.data)
        execution = WorkflowExecution.objects.get(workflow=self.workflow)
        self.assertEqual(execution.node_executions.filter(status='completed').count(), 3)
        self.assertEqual(execution.progress, 100)

    def test_streaming_records_boundary_nodes_and_final_progress(self):
        from workflows.services.workflow_executor import WorkflowExecutor
        self.graph([('start', {}), ('input', {'variable_name': 'input'}), ('output', {'template': '{input}'}), ('end', {})])
        execution = WorkflowExecution.objects.create(workflow=self.workflow, triggered_by=self.user, version=self.workflow.version, input_data={'input': '流式中文输入'})
        events = list(WorkflowExecutor(self.workflow, execution).stream_execute())
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'completed', execution.error_message)
        self.assertEqual(execution.progress, 100)
        self.assertEqual(execution.node_executions.filter(status='completed').count(), 4)
        self.assertTrue(any(event['type'] == 'execution_complete' for event in events))

    def test_actual_node_failure_returns_failed_status_and_error(self):
        self.graph([('start', {}), ('code', {'code': "raise ValueError('验证异常')"}), ('end', {})])
        response = self.execute()
        self.assertEqual(response.status_code, 400, response.data)
        execution = WorkflowExecution.objects.get(workflow=self.workflow)
        self.assertEqual(execution.status, 'failed')
        self.assertTrue(execution.error_message)
        rendered = response.json()
        self.assertEqual(rendered['data']['execution_id'], str(execution.id))
        self.assertEqual(rendered['data']['status'], 'failed')
        self.assertIn('验证异常', rendered['message'])

    def test_chinese_registry_contains_real_availability(self):
        response = self.client.get('/api/v1/workflows/nodes/available_types/')
        self.assertEqual(response.status_code, 200)
        data = response.data.get('data', response.data) if isinstance(response.data, dict) else response.data
        nodes = {item['type']: item for item in data}
        self.assertEqual(nodes['manual']['label'], '手动触发')
        self.assertTrue(nodes['manual']['supported'])
        self.assertFalse(nodes['google_sheets']['supported'])

    def test_save_preserves_json_csv_types_and_execution_configuration(self):
        self.graph([
            ('start', {}),
            ('json_transform', {'operation': 'map', 'schema': {'mappings': {'out': 'a'}}}),
            ('csv_transform', {'operation': 'aggregate', 'params': {'column': '数量', 'aggFunc': 'sum'}}),
            ('end', {}),
        ])
        expected = {str(node.id): (node.node_type, node.config) for node in self.workflow.nodes.all()}
        payload = {
            'nodes': [{'id': str(node.id), 'node_type': node.node_type, 'name': node.name, 'config': node.config} for node in self.workflow.nodes.all()],
            'edges': [{'id': str(edge.id), 'source_node': str(edge.source_node_id), 'target_node': str(edge.target_node_id)} for edge in self.workflow.edges.all()],
        }
        response = self.client.patch(f'/api/v1/workflows/{self.workflow.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        actual = {str(node.id): (node.node_type, node.config) for node in self.workflow.nodes.all()}
        self.assertEqual(actual, expected)
        self.assertEqual(self.workflow.edges.count(), 3)

    def test_json_chain_receives_direct_predecessor_output(self):
        self.graph([
            ('start', {}), ('input', {'variable_name': 'data'}),
            ('json_transform', {'operation': 'map', 'schema': '{"mappings":{"中间值":"原始值"}}'}),
            ('json_transform', {'operation': 'map', 'schema': '{"mappings":{"结果":"中间值"}}'}),
            ('end', {}),
        ])
        response = self.execute({'data': {'原始值': 42}})
        self.assertEqual(response.status_code, 200, response.data)
        from workflows.models import NodeExecution
        results = list(NodeExecution.objects.filter(node__node_type='json_transform').order_by('node__created_at'))
        self.assertEqual(results[0].output_data['data'], {'中间值': 42})
        self.assertEqual(results[1].output_data['data'], {'结果': 42})

    def test_source_namespace_and_json_types_survive_the_real_executor(self):
        self.graph([
            ('start', {}),
            ('json_transform', {'operation': 'json_to_object', 'source': '{{input_data.data}}'}),
            ('end', {}),
        ])
        response = self.execute({'data': {'中文': True, '零': 0}})
        self.assertEqual(response.status_code, 200, response.data)
        from workflows.models import NodeExecution
        result = NodeExecution.objects.get(node__node_type='json_transform')
        self.assertEqual(result.output_data['data'], {'中文': True, '零': 0})

    def test_form_fallback_data_executes_when_upstream_has_no_payload(self):
        self.graph([
            ('start', {}),
            ('json_transform', {'operation': 'json_to_object', 'data': '{"名字":"中文"}'}),
            ('end', {}),
        ])
        response = self.execute()
        self.assertEqual(response.status_code, 200, response.data)
        from workflows.models import NodeExecution
        result = NodeExecution.objects.get(node__node_type='json_transform')
        self.assertEqual(result.output_data['data'], {'名字': '中文'})
