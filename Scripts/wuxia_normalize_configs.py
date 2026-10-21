"""Re-normalize saved epic workflow configs onto executable schemas."""
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'Backend'
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django

django.setup()

from nl_to_workflow.node_config_normalize import normalize_node_config  # noqa: E402
from workflows.models import Node, Workflow  # noqa: E402

WF_ID = 'c5d77c0f-8571-42a5-b111-4446f72e3c27'


def main():
    wf = Workflow.objects.get(id=WF_ID)
    changed = []
    for node in Node.objects.filter(workflow=wf).order_by('sort_order'):
        before = json.dumps(node.config or {}, sort_keys=True, ensure_ascii=False)
        after_cfg = normalize_node_config(node.node_type, node.config or {})
        after = json.dumps(after_cfg, sort_keys=True, ensure_ascii=False)
        if before != after:
            node.config = after_cfg
            node.save(update_fields=['config', 'updated_at'])
            changed.append({
                'id': str(node.id),
                'type': node.node_type,
                'name': node.name,
                'keys': sorted(after_cfg.keys()),
            })
    report = {
        'workflow_id': WF_ID,
        'name': wf.name,
        'changed_count': len(changed),
        'changed': changed,
        'nodes': [
            {
                'type': n.node_type,
                'name': n.name,
                'config': n.config,
            }
            for n in Node.objects.filter(workflow=wf).order_by('sort_order')
        ],
    }
    out = Path(__file__).resolve().parents[1] / 'test-reports' / 'wuxia_epic_normalized.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': True, 'changed_count': len(changed), 'report': str(out)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
