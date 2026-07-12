"""DAG auto-layout for NL2WF / editor assistant."""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Set


LAYOUT_X_GAP = 240
LAYOUT_Y_GAP = 160
LAYOUT_START_X = 80
LAYOUT_START_Y = 120


def is_layout_intent(message: str) -> bool:
    text = (message or '').lower()
    keywords = (
        '排布', '布局', '排列', '整理节点', '自动布局', '对齐节点', '整理画布',
        'layout', 'arrange', 'auto-layout', 'auto layout', 'rearrange',
    )
    return any(k in text for k in keywords)


def auto_layout_workflow(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """Assign positions to nodes in topological layers (left → right)."""
    if not workflow or not workflow.get('nodes'):
        return workflow

    result = deepcopy(workflow)
    nodes: List[Dict[str, Any]] = result.get('nodes') or []
    edges: List[Dict[str, Any]] = result.get('edges') or []

    node_ids = [str(n.get('id')) for n in nodes if n.get('id')]
    id_set: Set[str] = set(node_ids)

    adj: Dict[str, List[str]] = {nid: [] for nid in node_ids}
    indegree: Dict[str, int] = {nid: 0 for nid in node_ids}

    for edge in edges:
        src = str(edge.get('source') or '')
        tgt = str(edge.get('target') or '')
        if src in id_set and tgt in id_set and tgt not in adj[src]:
            adj[src].append(tgt)
            indegree[tgt] = indegree.get(tgt, 0) + 1

    queue = deque([nid for nid in node_ids if indegree.get(nid, 0) == 0])
    if not queue:
        queue = deque(node_ids)

    layer_map: Dict[str, int] = {}
    layer_nodes: Dict[int, List[str]] = {}

    while queue:
        nid = queue.popleft()
        layer = layer_map.get(nid, 0)
        layer_nodes.setdefault(layer, []).append(nid)
        for nxt in adj.get(nid, []):
            proposed = layer + 1
            if proposed > layer_map.get(nxt, 0):
                layer_map[nxt] = proposed
            indegree[nxt] -= 1
            if indegree[nxt] <= 0:
                queue.append(nxt)

    for nid in node_ids:
        if nid not in layer_map:
            orphan_layer = max(layer_nodes.keys(), default=-1) + 1
            layer_map[nid] = orphan_layer
            layer_nodes.setdefault(orphan_layer, []).append(nid)

    for layer, nids in layer_nodes.items():
        for row, nid in enumerate(nids):
            for node in nodes:
                if str(node.get('id')) == nid:
                    node['position'] = {
                        'x': LAYOUT_START_X + layer * LAYOUT_X_GAP,
                        'y': LAYOUT_START_Y + row * LAYOUT_Y_GAP,
                    }
                    break

    result['nodes'] = nodes
    return result
