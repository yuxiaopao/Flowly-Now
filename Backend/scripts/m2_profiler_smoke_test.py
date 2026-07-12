#!/usr/bin/env python
"""M2 profiler + wizard smoke tests."""
import json
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))
REPORT = REPO / 'test-reports' / 'm2-smoke-result.json'


def main():
    from website_generator.site_factory.project_profiler import build_project_profile
    from website_generator.generators.detection import DetectionGenerator

    profile = build_project_profile(
        class_names=['helmet', 'no_helmet'],
        website_type='detection',
    )
    assert profile['domain'] == '工业安全', profile
    assert '安全帽' in profile['scenario']
    assert profile['class_display_names'].get('helmet') == '已佩戴安全帽'

    tmp = tempfile.mkdtemp(prefix='flowly_m2_')
    site_dir = os.path.join(tmp, 'site')
    wizard = {
        'siteName': '安全帽智能检测平台',
        'usageDescription': '工地现场安全帽佩戴实时检测',
        'primaryColor': '#ef4444',
        'disclaimer': '本系统仅供参考，不构成安全合规承诺。',
        'wizardCompleted': True,
    }
    gen = DetectionGenerator({
        'output_dir': site_dir,
        'model_path': '',
        'labels': ['helmet', 'no_helmet'],
        'framework': 'pytorch',
        'website_type': 'detection',
        'port': 49152,
        'name': 'fallback',
        'description': '',
        'profile': profile,
        'wizard': wizard,
    })
    gen.generate()
    index_path = os.path.join(site_dir, 'frontend', 'index.html')
    html = Path(index_path).read_text(encoding='utf-8')
    checks = {
        'title_injected': '安全帽智能检测平台' in html,
        'subtitle_injected': '工地现场安全帽佩戴实时检测' in html,
        'disclaimer_injected': '不构成安全合规承诺' in html,
        'upload_hint': '上传现场照片' in html,
        'schema_unchanged': Path(site_dir, 'backend/db/schema.sql').is_file(),
    }
    result = {
        'passed': all(checks.values()),
        'profile': profile,
        'checks': checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
