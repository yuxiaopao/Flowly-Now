"""Replace only visually rejected module requests and resume native downstream nodes."""
import argparse
import json
import shutil

if __package__:
    from .create_modular_embroidery_workflow import OUTPUT, FINAL_NAME, make_spec, make_graph
else:
    from create_modular_embroidery_workflow import OUTPUT, FINAL_NAME, make_spec, make_graph
from workflows.models import Workflow, WorkflowExecution
from workflows.services.partial_retry import prepare_partial_retry
from workflows.services.workflow_executor import WorkflowExecutor
from workflows.services.media_service import local_path_from_public_url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modules', nargs='+', required=True)
    parser.add_argument('--update-only', action='store_true')
    args = parser.parse_args()
    workflow = Workflow.objects.get(pk=(OUTPUT / 'workflow-id.txt').read_text().strip())
    execution = WorkflowExecution.objects.get(pk=(OUTPUT / 'execution-id.txt').read_text().strip(), workflow=workflow)
    replacement = {m['id']: m for m in make_spec()['modules']}
    selected = set(args.modules)
    if not selected <= replacement.keys():
        raise ValueError('Unknown module')
    spec = workflow.config['embroidery_spec']
    spec['modules'] = [replacement[m['id']] if m['id'] in selected else m for m in spec['modules']]
    workflow.save(update_fields=['config'])
    seeds = []
    for node in workflow.nodes.filter(node_type='tool'):
        module_id = node.config.get('parameters', {}).get('module_id')
        if module_id in selected:
            shot = replacement[module_id]['shot']
            node.config['parameters'].update(prompt=shot['prompt'], seed=shot['seed'])
            node.name = replacement[module_id]['caption']
            node.save(update_fields=['config', 'name'])
            seeds.append(str(node.pk))
    subtitle = workflow.nodes.get(node_type='subtitle_burn')
    subtitle.config = next(n['config'] for n in make_graph(spec)[0] if n['node_type'] == 'subtitle_burn')
    subtitle.save(update_fields=['config'])
    (OUTPUT / 'film-spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.update_only:
        print('Updated requests; current run is unchanged until the selected nodes are retried.')
        return
    prepare_partial_retry(execution, node_ids=seeds, include_downstream=True)
    WorkflowExecutor(workflow, execution, parallel_enabled=False).execute(resume=True)
    execution.refresh_from_db()
    result = {'workflow_id': str(workflow.pk), 'execution_id': str(execution.pk), 'status': execution.status,
              'error': execution.error_message, 'output': execution.output_data}
    (OUTPUT / 'execution-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'output'}), flush=True)
    if execution.status != 'completed':
        raise RuntimeError(execution.error_message)
    shutil.copy2(local_path_from_public_url(execution.output_data['variables']['final_video']), OUTPUT / FINAL_NAME)


if __name__ == '__main__':
    main()
