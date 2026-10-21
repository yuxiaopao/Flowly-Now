"""Execute a saved embroidery specification through Flowly's native graph."""
import argparse
import json
from pathlib import Path

if __package__:
    from .create_modular_embroidery_workflow import make_graph
else:
    from create_modular_embroidery_workflow import make_graph
from django.contrib.auth import get_user_model
from workflows.models import Edge, Node, Workflow, WorkflowExecution
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--username', default='nlwftest')
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    if abs(sum(module['edit']['seconds'] for module in spec['modules']) - spec['seconds']) > 0.001:
        raise ValueError('Module durations must equal the declared film duration')
    owner = get_user_model().objects.get(username=args.username)
    workflow = Workflow.objects.create(owner=owner, name=spec['title'], category='AI视频生成',
        description=spec['description'],
        config={'embroidery_spec': spec, 'timeout_seconds': spec['workflow_timeout_seconds']})
    nodes, edges = make_graph(spec)
    if len(spec['modules']) == 1:
        nodes = [node for node in nodes if node['node_type'] in ('start', 'tool', 'output', 'end')]
        edges = [{'source': left['id'], 'target': right['id']} for left, right in zip(nodes, nodes[1:])]
    for node in nodes:
        node['name'] = node['name'].replace('60秒', f"{spec['seconds']:g}秒")
        if node['node_type'] == 'end':
            node['name'] = '视频已生成｜需核实走线质量'
        Node.objects.create(workflow=workflow, **node)
    for edge in edges:
        Edge.objects.create(workflow=workflow, source_node_id=edge['source'], target_node_id=edge['target'])
    validation = validate_workflow(workflow)
    if not validation['valid']:
        raise ValueError(validation)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version,
        triggered_by=owner, trigger_type='api', trigger_source={'method': 'free_model_embroidery'})
    state = {'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'spec': spec}
    destination = args.spec.with_name(args.spec.stem + '-execution.json')
    destination.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: state[key] for key in ('workflow_id', 'execution_id')}), flush=True)
    WorkflowExecutor(workflow, execution, parallel_enabled=False).execute()
    execution.refresh_from_db()
    state.update(status=execution.status, error=execution.error_message, output=execution.output_data)
    destination.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'status': execution.status, 'error': execution.error_message}), flush=True)
    if execution.status != 'completed':
        raise RuntimeError(execution.error_message)


if __name__ == '__main__':
    main()
