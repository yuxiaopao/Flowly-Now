#!/usr/bin/env python
"""
M1 Site Factory smoke test — no Django DB required.

Generates a detection site scaffold, runs EP + QA + preview gate logic,
and writes report to test-reports/m1-smoke-result.json
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
REPO_ROOT = BACKEND_ROOT.parent
REPORT_PATH = REPO_ROOT / 'test-reports' / 'm1-smoke-result.json'


def main():
    from website_generator.generators.detection import DetectionGenerator
    from website_generator.site_factory.environment import run_environment_checks
    from website_generator.site_factory.qa_runner import run_site_qa

    tmp_base = tempfile.mkdtemp(prefix='flowly_m1_smoke_')
    yolo_like_dir = os.path.join(tmp_base, 'yolo_run')
    site_dir = os.path.join(yolo_like_dir, 'generated_site')
    os.makedirs(yolo_like_dir, exist_ok=True)
    # Simulate YOLO weights occupying parent dir
    with open(os.path.join(yolo_like_dir, 'best.pt'), 'w', encoding='utf-8') as f:
        f.write('fake')

    gen = DetectionGenerator({
        'output_dir': site_dir,
        'model_path': os.path.join(yolo_like_dir, 'best.pt'),
        'model_type': 'detection',
        'labels': ['helmet', 'no_helmet'],
        'framework': 'pytorch',
        'website_type': 'detection',
        'frontend_framework': 'vue',
        'backend_framework': 'flask',
        'port': 49152,
        'name': 'M1 Smoke Detection Site',
        'description': 'Automated M1 smoke',
    })
    gen_result = gen.generate()
    if not gen_result.get('success', True) and gen_result.get('error'):
        fail('generation', gen_result.get('error'))

    schema = os.path.join(site_dir, 'backend', 'db', 'schema.sql')
    assert os.path.isfile(schema), f'missing schema: {schema}'

    ep = run_environment_checks(
        output_dir=site_dir,
        model_path=os.path.join(yolo_like_dir, 'best.pt'),
        site_id='smoke-site',
        runtime_mode='desktop',
    )
    assert ep['assigned_port'] >= 49152, 'port out of range'

    qa = run_site_qa(
        output_dir=site_dir,
        model_path=os.path.join(yolo_like_dir, 'best.pt'),
        website_type='detection',
        qa_profile='default',
        metrics={'map50': 0.82},
        port=ep['assigned_port'],
        skip_playwright=True,
        generated_site_id='smoke-site',
    )
    assert os.path.isfile(qa['report_path']), 'qa_report.json missing'
    assert qa['gate'] in ('green', 'yellow', 'red')

    # Red gate: break schema
    broken_dir = os.path.join(tmp_base, 'broken_site')
    shutil.copytree(site_dir, broken_dir)
    os.remove(os.path.join(broken_dir, 'backend', 'db', 'schema.sql'))
    qa_red = run_site_qa(
        output_dir=broken_dir,
        website_type='detection',
        qa_profile='default',
        metrics={'map50': 0.1},
        skip_playwright=True,
    )
    assert qa_red['gate'] == 'red', f'expected red gate, got {qa_red["gate"]}'

    preview_blocked = qa_red['gate'] == 'red'
    preview_ok = qa['gate'] != 'red'

    db_path = os.path.join(site_dir, 'backend', 'db', 'app.db')
    inference_log_count = 0
    if os.path.isfile(db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        inference_log_count = conn.execute('SELECT COUNT(*) FROM inference_logs').fetchone()[0]
        conn.close()

    result = {
        'passed': True,
        'generation_files': len(gen.generated_files),
        'schema_exists': True,
        'inference_logs_count': inference_log_count,
        'environment_provision': {
            'ready': ep['ready'],
            'assigned_port': ep['assigned_port'],
            'checks_count': len(ep['checks']),
        },
        'site_qa_green_path': {
            'gate': qa['gate'],
            'layers': qa['layers'],
            'summary_zh': qa['summary_zh'],
            'report_path': qa['report_path'],
        },
        'site_qa_red_path': {
            'gate': qa_red['gate'],
            'summary_zh': qa_red['summary_zh'],
        },
        'site_preview': {
            'green_path_allowed': preview_ok,
            'red_path_blocked': preview_blocked,
            'preview_url': qa.get('preview_url'),
        },
        'output_dir_resolution': {
            'yolo_parent_has_weights': True,
            'site_subdir': site_dir,
        },
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f'\nOK — report written to {REPORT_PATH}')
    shutil.rmtree(tmp_base, ignore_errors=True)
    return 0


def fail(stage, message):
    out = {'passed': False, 'stage': stage, 'error': message}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
