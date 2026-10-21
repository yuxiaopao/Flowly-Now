# -*- coding: utf-8 -*-
import json
import os
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from celery.result import AsyncResult
from nl_to_workflow.models import NLSession

SID = "d55a412e-863f-4d70-a202-f105152d529e"
out = r"E:\Flowly-now\test-reports\nl_p2_async_final.json"

for i in range(60):
    s = NLSession.objects.get(id=SID)
    state = AsyncResult(s.celery_task_id).state if s.celery_task_id else None
    nodes = len((s.workflow_json or {}).get("nodes") or [])
    payload = {
        "i": i,
        "status": s.status,
        "celery": state,
        "nodes": nodes,
        "name": s.workflow_name,
        "err": s.error_message or "",
        "intelligent": (s.workflow_json or {}).get("_is_intelligent"),
        "agent_val": bool((s.workflow_json or {}).get("_agent_validation")),
    }
    print(payload)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    if s.status in ("completed", "failed"):
        break
    time.sleep(3)
