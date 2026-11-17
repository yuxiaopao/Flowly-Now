#!/usr/bin/env python
"""Run the small CPU retrieval chain with an explicit actor and real provenance.

Website generation is submitted without waiting for its full build. The workflow,
execution and artifacts remain available for inspection by the selected user.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / 'Backend'
SAMPLES = (
    ('cat.jpg', '一只橘猫', (220, 120, 40)),
    ('dog.jpg', '金毛犬', (180, 160, 60)),
    ('shoe.jpg', '红色运动鞋', (200, 40, 40)),
)
IMAGE_SIZE = (32, 32)


def seed_template_present(source):
    return any(
        isinstance(node, ast.Call) and any(
            keyword.arg == 'name' and isinstance(keyword.value, ast.Constant)
            and keyword.value.value == 'CLIP 检索项目' for keyword in node.keywords
        ) for node in ast.walk(ast.parse(source))
    )


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    actor = parser.add_mutually_exclusive_group(required=True)
    actor.add_argument('--user-id', type=int, help='Existing active user who owns this smoke workflow')
    actor.add_argument('--user-email', help='Email of the existing active workflow owner')
    parser.add_argument('--output-dir', type=Path, help='Parent directory for a new isolated artifact directory')
    parser.add_argument('--report', type=Path, default=REPO / 'test-reports' / 'm4-chain-smoke-result.json')
    return parser


def run_smoke(user, output_root):
    from django.contrib.auth import get_user_model
    from PIL import Image
    from website_generator.models import GeneratedSite
    from workflows.models import Workflow, WorkflowExecution, Node, Edge
    from workflows.services.workflow_executor import WorkflowExecutor

    user = get_user_model().objects.filter(pk=user.pk, is_active=True).first()
    if user is None:
        raise ValueError('An existing active workflow owner is required.')
    workspace = Path(output_root).resolve() / uuid.uuid4().hex
    image_dir = workspace / 'dataset' / 'images'
    image_dir.mkdir(parents=True)
    with (workspace / 'dataset' / 'pairs.jsonl').open('w', encoding='utf-8') as pairs:
        for name, caption, color in SAMPLES:
            Image.new('RGB', IMAGE_SIZE, color=color).save(image_dir / name, format='JPEG')
            pairs.write(json.dumps({'image': f'images/{name}', 'text': caption}, ensure_ascii=False) + '\n')
    workflow = Workflow.objects.create(owner=user, name='M4 CLIP retrieval smoke', status='draft', is_public=False)
    specifications = (
        ('start', {}),
        ('dataset_upload', {'source': 'upload', 'path': str(image_dir.parent), 'format': 'image_text_pairs', 'label': 'ChainDataset'}),
        ('clip_retrieval', {'label': 'ChainIndex', 'outputDir': str(workspace / 'index'), 'baseModel': 'simple-bow',
                            'config': {'trainingMode': 'sync'}}),
        ('project_profiler', {'websiteType': 'clip_retrieval', 'useLlmEnrich': False}),
        ('website_generator', {'websiteType': 'clip_retrieval', 'outputDir': str(workspace / 'site_out'),
                               'waitForCompletion': False,
                               'wizard': {'siteName': '链式检索演示', 'usageDescription': '文本搜图', 'wizardCompleted': True}}),
        ('end', {}),
    )
    previous, nodes = None, {}
    for order, (kind, configuration) in enumerate(specifications):
        node = Node.objects.create(workflow=workflow, node_type=kind, name=kind, config=configuration, sort_order=order)
        if previous:
            Edge.objects.create(workflow=workflow, source_node=previous, target_node=node)
        previous, nodes[kind] = node, node
    execution = WorkflowExecution.objects.create(workflow=workflow, version=workflow.version, triggered_by=user, trigger_type='manual')
    WorkflowExecutor(workflow, execution).execute()
    execution.refresh_from_db()
    results = {str(row.node_id): row.output_data or {} for row in execution.node_executions.all()}
    upload = results.get(str(nodes['dataset_upload'].pk), {})
    retrieval = results.get(str(nodes['clip_retrieval'].pk), {})
    profiler = results.get(str(nodes['project_profiler'].pk), {})
    website = results.get(str(nodes['website_generator'].pk), {})
    site = GeneratedSite.objects.filter(pk=website['site_id']).first() if website.get('site_id') else None
    template = (REPO / 'Frontend/src/config/clipRetrievalWorkflowTemplate.js').read_text(encoding='utf-8')
    seed = (BACKEND / 'workflows/management/commands/seed_domain_templates.py').read_text(encoding='utf-8')
    checks = {
        'workflow_completed': execution.status == 'completed',
        'dataset_upload': bool(upload.get('dataset_path')),
        'index_built': bool(retrieval.get('index_dir')) and (Path(retrieval['index_dir']) / 'metadata.json').is_file(),
        'profiler_retrieval': profiler.get('recommended_template') == 'clip_retrieval' and profiler.get('domain') == '多模态检索',
        'website_submitted': bool(site and site.status in ('profiling', 'generating', 'completed')),
        'website_provenance': bool(site and site.created_by_id == user.pk and site.source_workflow_id == workflow.pk
                                   and site.source_execution_id == execution.pk and site.source_node_id == nodes['website_generator'].pk),
        'retrieval_endpoint': '/search/text' in website.get('inference_endpoint', ''),
        'frontend_template': 'clip_retrieval_1' in template,
        'seed_template': seed_template_present(seed),
    }
    return {'passed': all(checks.values()), 'checks': checks, 'workflow_id': str(workflow.pk),
            'execution_id': str(execution.pk), 'training_run_id': retrieval.get('training_run_id'),
            'site_id': str(site.pk) if site else None, 'site_status': site.status if site else None,
            'artifact_directory': str(workspace), 'error': execution.error_message if execution.status != 'completed' else ''}


def main(argv=None):
    args = build_parser().parse_args(argv)
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.auth import get_user_model

    selector = {'pk': args.user_id} if args.user_id is not None else {'email__iexact': args.user_email}
    users = list(get_user_model().objects.filter(is_active=True, **selector)[:2])
    if len(users) != 1:
        print('Select exactly one existing active user with --user-id or --user-email.', file=sys.stderr)
        return 1
    output_root = args.output_dir or Path(settings.BASE_DIR) / 'outputs' / 'm4_chain_smoke'
    report = run_smoke(users[0], output_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
