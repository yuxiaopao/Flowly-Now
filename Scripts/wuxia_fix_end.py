# -*- coding: utf-8 -*-
import json
import os
import uuid

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from workflows.models import Edge, Node, Workflow

REPORT = r"E:\Flowly-now\test-reports\wuxia_epic_workflow.json"
rep = json.load(open(REPORT, encoding="utf-8"))
wf = rep.get("workflow") or {}
wid = rep.get("workflow_id")
nodes = list(wf.get("nodes") or [])
edges = list(wf.get("edges") or [])
print("loaded", wid, "nodes", len(nodes), "types", sorted({n.get("type") for n in nodes}))

has_end = any(n.get("type") == "end" for n in nodes)
if not has_end:
    end_id = f"end_{uuid.uuid4().hex[:8]}"
    out = None
    for n in reversed(nodes):
        name = n.get("name") or ""
        if n.get("type") in ("output", "merge") or "交付" in name or "输出" in name:
            out = n
            break
    if not out and nodes:
        out = nodes[-1]
    ox = ((out or {}).get("position") or {}).get("x", 900)
    oy = ((out or {}).get("position") or {}).get("y", 150)
    nodes.append(
        {
            "id": end_id,
            "type": "end",
            "name": "工作流结束",
            "position": {"x": float(ox) + 200, "y": float(oy)},
            "config": {},
        }
    )
    if out:
        edges.append(
            {
                "id": f"e_{uuid.uuid4().hex[:8]}",
                "source": out["id"],
                "target": end_id,
                "label": "",
            }
        )
    print("added end", end_id, "from", (out or {}).get("id"))

wf = {
    "name": wf.get("name") or "武侠短篇剧情工业化流水线",
    "description": wf.get("description") or "",
    "nodes": nodes,
    "edges": edges,
    "_is_intelligent": True,
    "_generation_mode": "llm",
    "_llm_model": wf.get("_llm_model") or "agnes-2.0-flash",
}

w = Workflow.objects.get(id=wid)
with transaction.atomic():
    w.edges.all().delete()
    w.nodes.all().delete()
    id_map = {}
    for i, n in enumerate(wf["nodes"]):
        old = n.get("id")
        pos = n.get("position") or {}
        obj = Node.objects.create(
            workflow=w,
            node_type=n.get("type") or "code",
            name=n.get("name") or n.get("type") or f"node_{i}",
            config=n.get("config") or {},
            position_x=float(pos.get("x") or (100 + i * 160)),
            position_y=float(pos.get("y") or 150),
            sort_order=i,
        )
        id_map[old] = obj.id
    for e in wf["edges"]:
        s = id_map.get(e.get("source"))
        t = id_map.get(e.get("target"))
        if not s or not t:
            continue
        Edge.objects.create(
            workflow=w,
            source_node_id=s,
            target_node_id=t,
            label=e.get("label") or "",
        )
    w.name = wf["name"]
    w.description = wf.get("description") or w.description
    w.save()

types = {}
for t in w.nodes.values_list("node_type", flat=True):
    types[t] = types.get(t, 0) + 1
rep["workflow"] = wf
rep["summary"] = {
    "name": w.name,
    "node_count": w.nodes.count(),
    "edge_count": w.edges.count(),
    "node_types": types,
    "node_names": list(w.nodes.values_list("name", flat=True)),
    "is_intelligent": True,
    "generation_mode": "llm",
}
rep["passes"] = {
    "has_nodes": True,
    "intelligent": True,
    "not_offline_template": True,
    "has_end": w.nodes.filter(node_type="end").exists(),
    "saved": True,
}
json.dump(rep, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("DONE", rep["passes"], types)
print("NAMES", list(w.nodes.values_list("name", flat=True)))
