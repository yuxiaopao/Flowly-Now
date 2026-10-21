"""DAG auto-layout for NL2WF / editor assistant.

Supports:
- horizontal: layers left→right, siblings stacked vertically (simple chains)
- vertical: layers top→bottom, siblings side-by-side (wide fan-out / parallel shots)

Wide fan-out (≥3 siblings in a layer) prefers vertical so same-stage nodes sit in a row.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set, Tuple


LAYOUT_X_GAP = 240
LAYOUT_Y_GAP = 180
LAYOUT_NODE_GAP_X = 60
LAYOUT_NODE_GAP_Y = 60
LAYOUT_START_X = 80
LAYOUT_START_Y = 80
LAYOUT_NODE_WIDTH = 220
LAYOUT_NODE_HEIGHT = 140


def is_layout_intent(message: str) -> bool:
    text = (message or '').lower()
    keywords = (
        '排布', '布局', '排列', '整理节点', '自动布局', '对齐节点', '整理画布',
        'layout', 'arrange', 'auto-layout', 'auto layout', 'rearrange',
        '横着排', '横排', '并列排列',
    )
    return any(k in text for k in keywords)


def _compute_layers(
    node_ids: List[str],
    edges: List[Dict[str, Any]],
) -> Tuple[Dict[str, int], Dict[int, List[str]]]:
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

    return layer_map, layer_nodes


def pick_layout_direction(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    """Prefer vertical (siblings horizontal) when a layer fans out widely."""
    node_ids = [str(n.get('id')) for n in nodes if n.get('id')]
    if not node_ids:
        return 'horizontal'
    _, layer_nodes = _compute_layers(node_ids, edges)
    layer_count = len(layer_nodes)
    max_layer_size = max((len(v) for v in layer_nodes.values()), default=1)
    if max_layer_size >= 3:
        return 'vertical'
    if layer_count >= 6 and max_layer_size <= 2:
        return 'vertical'
    return 'horizontal'


def auto_layout_workflow(
    workflow: Dict[str, Any],
    *,
    direction: Optional[str] = None,
) -> Dict[str, Any]:
    """Assign positions to nodes in topological layers."""
    if not workflow or not workflow.get('nodes'):
        return workflow

    result = deepcopy(workflow)
    nodes: List[Dict[str, Any]] = result.get('nodes') or []
    edges: List[Dict[str, Any]] = result.get('edges') or []

    node_ids = [str(n.get('id')) for n in nodes if n.get('id')]
    if not node_ids:
        return result

    layer_map, layer_nodes = _compute_layers(node_ids, edges)
    resolved = direction or pick_layout_direction(nodes, edges)

    node_by_id = {str(n.get('id')): n for n in nodes if n.get('id')}

    for layer, nids in sorted(layer_nodes.items()):
        count = len(nids)
        if resolved == 'vertical':
            # layers top→bottom; siblings left→right (same-type horizontal rows)
            layer_y = LAYOUT_START_Y + layer * (LAYOUT_NODE_HEIGHT + LAYOUT_Y_GAP)
            total_w = count * LAYOUT_NODE_WIDTH + max(0, count - 1) * LAYOUT_NODE_GAP_X
            start_x = LAYOUT_START_X - total_w / 2.0 + LAYOUT_NODE_WIDTH / 2.0
            # Keep left-aligned for very wide rows so spine stays readable
            if count >= 3:
                start_x = LAYOUT_START_X
            for idx, nid in enumerate(nids):
                node = node_by_id.get(nid)
                if not node:
                    continue
                node['position'] = {
                    'x': int(start_x + idx * (LAYOUT_NODE_WIDTH + LAYOUT_NODE_GAP_X)),
                    'y': int(layer_y),
                }
        else:
            # layers left→right; siblings top→bottom
            layer_x = LAYOUT_START_X + layer * LAYOUT_X_GAP
            total_h = count * LAYOUT_NODE_HEIGHT + max(0, count - 1) * LAYOUT_NODE_GAP_Y
            start_y = LAYOUT_START_Y - total_h / 2.0 + LAYOUT_NODE_HEIGHT / 2.0
            for idx, nid in enumerate(nids):
                node = node_by_id.get(nid)
                if not node:
                    continue
                node['position'] = {
                    'x': int(layer_x),
                    'y': int(start_y + idx * (LAYOUT_NODE_HEIGHT + LAYOUT_NODE_GAP_Y)),
                }

    result['nodes'] = nodes
    return result
