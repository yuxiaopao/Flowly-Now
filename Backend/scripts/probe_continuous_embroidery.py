"""Render one registered stitching trial through native Flowly before a new film."""
import copy
import json
import argparse

if __package__:
    from .create_modular_embroidery_workflow import OUTPUT as PREVIOUS, MODEL_CONFIG, ENCODING, make_graph
else:
    from create_modular_embroidery_workflow import OUTPUT as PREVIOUS, MODEL_CONFIG, ENCODING, make_graph
from workflows.models import Workflow, WorkflowExecution, Node, Edge
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.workflow_validation import validate_workflow

OUTPUT = PREVIOUS.parent / 'flowly_continuous_60'
TITLE = '蝶羽共生纹｜连续走线试镜'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--guided', action='store_true')
    args = parser.parse_args()
    previous = Workflow.objects.get(pk=(PREVIOUS / 'workflow-id.txt').read_text().strip())
    prompt = (
        'A rapid continuous time-lapse of one indigo silk filament sewing the upper left wing '
        'on ivory linen. The thread is already moving in the first frame and keeps advancing '
        'throughout the whole shot. The small working loop runs along the faint dotted S-shaped '
        'guide, dips into the cloth, pulls taut, then immediately emerges at the next hole. '
        'One connected chain-stitch trail extends behind this moving tip, wrapping around the '
        'upper left diamond in three nested curves. Each new stitch stays sewn flat in its '
        'exact position; the working tip moves steadily toward the outer left curl. '
        'The butterfly body and all four diamond centers remain perfectly motionless. '
        'The other three wings remain bare dotted guides, unchanged. No pauses, no freeze, '
        'no dissolves, no fade-in of entire shapes, no floating ornament, no reverse movement. '
        'Only the slender silk thread moves, driven from below the cloth. Empty scene with '
        'no people, no hands, no fingers and no tools anywhere. Stationary cloth and camera, '
        'realistic fine twisted silk fibers, slight raised stitches, soft contact shadows. '
        'Photoreal textile motion study, crisp continuous visible progress at every moment.'
    )
    module = {
        'id': 'upper-left-continuous', 'caption': '连续走线试镜',
        'source_directory': 'flowly_continuous_60',
        'shot': {'id': 'upper-left-continuous', 'image': 'upper-left-start.png',
                 'end_image': 'upper-left-end.png', 'seed': 58141, 'prompt': prompt, 'conditions': []},
        'model_spec': copy.deepcopy(MODEL_CONFIG),
        'edit': {'seconds': 5, 'start_frame': 0, 'end_frame': 150, 'retiming_factor': 1,
                 'zoom': [1.7, 1.8], 'x': [0.35, 0.1], 'y': [0.1, 0.3]},
    }
    if args.guided:
        module['shot'].update(seed=58142, conditions=[{'image': 'upper-left-mid.png', 'frame_index': 72}],
            prompt='MACRO MATERIAL ANIMATION. An indigo silk filament continuously advances over an EMPTY ivory textile. '
            'A tiny active arc contracts into the surface and immediately reforms just ahead. Small tight chain links '
            'extend behind it along the upper-left dotted curve. The moving tip traverses the upper sweep, doubles '
            'back along the middle sweep, and continues around the diamond. Exactly one slender active loop. '
            'All deposited chain links stay still and firmly attached. The completed center and four diamonds stay '
            'absolutely unchanged. Everything moves in a continuous brisk rhythm from the first frame to the last. '
            'All unfilled areas remain empty cloth. The cloth itself stays perfectly stationary. The only animated '
            'object is this thin silky blue strand. No pause or sudden appearance of whole curves. Fine fibers '
            'and soft contact shadows, a controlled tabletop material-motion study.')
        module['model_spec'].update(guidance_scale=2.5, guidance_rescale=0.7,
            negative_prompt='hands, human skin, fingers, fingernails, people, arms, sewing person, needle, tools, '
            'large object entering frame, melting ornament, floating whole shape, fading drawing, pause, still frame, '
            'thick rope, moving butterfly body, camera rotation, changing motif shape')
    spec = {'title': TITLE, 'seconds': 5, 'modules': [module], 'disclosure': '',
            'encoding': ENCODING, 'workflow_timeout_seconds': 1800}
    workflow = Workflow.objects.create(owner=previous.owner, name=TITLE, category='AI视频生成',
        description='连续走线效果验证，尚未作为60秒成片交付。',
        config={'embroidery_spec': spec, 'timeout_seconds': spec['workflow_timeout_seconds']})
    nodes, edges = make_graph(spec)
    nodes = [node for node in nodes if node['node_type'] in ('start', 'tool', 'output', 'end')]
    edges = [{'source': left['id'], 'target': right['id']} for left, right in zip(nodes, nodes[1:])]
    for node in nodes:
        node['name'] = node['name'].replace('60秒', f"{spec['seconds']}秒")
        if node['node_type'] == 'end':
            node['name'] = '试镜输出｜等待画面审核'
        Node.objects.create(workflow=workflow, **node)
    for edge in edges:
        Edge.objects.create(workflow=workflow, source_node_id=edge['source'], target_node_id=edge['target'])
    validation = validate_workflow(workflow)
    if not validation['valid']:
        raise ValueError(validation)
    execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version,
        triggered_by=workflow.owner, trigger_type='api', trigger_source={'method': 'continuous_embroidery_trial'})
    state = {'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'spec': spec}
    suffix = 'guided' if args.guided else 'unguided'
    (OUTPUT / f'trial-{suffix}.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: state[k] for k in ('workflow_id', 'execution_id')}), flush=True)
    WorkflowExecutor(workflow, execution, parallel_enabled=False).execute()
    execution.refresh_from_db()
    state.update(status=execution.status, error=execution.error_message, output=execution.output_data)
    (OUTPUT / f'trial-{suffix}-result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({'status': execution.status, 'error': execution.error_message}), flush=True)
    if execution.status != 'completed':
        raise RuntimeError(execution.error_message)


if __name__ == '__main__':
    main()
