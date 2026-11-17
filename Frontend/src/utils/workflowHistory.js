import { WORKFLOW_HISTORY } from '@/config/workflowCanvas'

export function createWorkflowHistory() {
  return { entries: [], index: -1, totalBytes: 0, runtimeByNodeId: {} }
}

function editableNode(node) {
  const { _runtime: _nodeRuntime, ...definition } = node
  const { _runtime: _dataRuntime, ...data } = node.data || {}
  let style = node.style
  if (style && typeof style === 'object') {
    const { _runtime: _styleRuntime, ...editableStyle } = style
    style = editableStyle
  }
  return { ...definition, data, ...(style === undefined ? {} : { style }) }
}

export function serializeWorkflowHistory(nodes, edges) {
  return JSON.stringify({ nodes: nodes.map(editableNode), edges })
}

/** A current snapshot is retained even when a single document exceeds the undo budget. */
export function recordWorkflowHistory(state, nodes, edges, options = {}) {
  const { mergeKey = null, now = Date.now(), ...overrides } = options
  const budget = { ...WORKFLOW_HISTORY, ...overrides }
  const value = serializeWorkflowHistory(nodes, edges)
  let entries = state.entries.slice(0, state.index + 1)
  const previous = entries.at(-1)
  const nodeIds = nodes.map(node => String(node.id))
  const entry = { value, nodeIds, bytes: value.length * 2, mergeKey, recordedAt: now }
  const merge = previous?.value === value || (
    entries.length > 1 && mergeKey && previous?.mergeKey === mergeKey
    && state.index === state.entries.length - 1 && now - previous.recordedAt <= budget.mergeWindowMs
  )
  if (merge) entries = [...entries.slice(0, -1), entry]
  else entries = [...entries, entry]
  let totalBytes = entries.reduce((total, item) => total + item.bytes, 0)
  let first = 0
  while (entries.length - first > 1 && (entries.length - first > budget.maxEntries || totalBytes > budget.maxBytes)) {
    totalBytes -= entries[first++].bytes
  }
  if (first) entries = entries.slice(first)
  // Keep one reference to the latest runtime for deletion/undo, independently of serialized snapshots.
  const runtimeByNodeId = { ...state.runtimeByNodeId }
  for (const node of nodes) {
    const previousRuntime = runtimeByNodeId[String(node.id)] || {}
    runtimeByNodeId[String(node.id)] = {
      ...previousRuntime,
      ...(node._runtime === undefined ? {} : { node: node._runtime }),
      ...(node.data?._runtime === undefined ? {} : { data: node.data._runtime }),
      ...(node.style?._runtime === undefined ? {} : { style: node.style._runtime }),
    }
  }
  if (first || state.index < state.entries.length - 1) {
    const retainedIds = new Set(entries.flatMap(item => item.nodeIds))
    for (const id of Object.keys(runtimeByNodeId)) {
      if (!retainedIds.has(id)) delete runtimeByNodeId[id]
    }
  }
  return { entries, index: entries.length - 1, totalBytes, runtimeByNodeId }
}

/** Undo changes definitions, never the latest execution output attached to a live node. */
export function restoreWorkflowHistory(state, index, currentNodes) {
  const entry = state.entries[index]
  if (!entry) return null
  const document = JSON.parse(entry.value)
  const currentById = new Map(currentNodes.map(node => [String(node.id), node]))
  document.nodes = document.nodes.map(node => {
    const current = currentById.get(String(node.id))
    const runtime = state.runtimeByNodeId?.[String(node.id)] || {}
    const nodeRuntime = current?._runtime === undefined ? runtime.node : current._runtime
    const dataRuntime = current?.data?._runtime === undefined ? runtime.data : current.data._runtime
    const styleRuntime = current?.style?._runtime === undefined ? runtime.style : current.style._runtime
    return {
      ...node,
      ...(nodeRuntime === undefined ? {} : { _runtime: nodeRuntime }),
      data: { ...node.data, ...(dataRuntime === undefined ? {} : { _runtime: dataRuntime }) },
      ...(styleRuntime === undefined ? {} : { style: { ...node.style, _runtime: styleRuntime } }),
    }
  })
  return document
}
