/**
 * 节点执行成果持久化工具（纯函数，避免 execution store 循环依赖）
 */

const STORAGE_PREFIX = 'flowly_node_runtime:'

function buildStorageKey(workflowId, nodeId) {
  return `${STORAGE_PREFIX}${workflowId}:${nodeId}`
}

/** 保存后节点 UUID 变更时，迁移 sessionStorage 中的执行成果缓存 */
export function migrateNodeRuntimeCache(workflowId, idMap = {}) {
  if (!workflowId || !idMap || typeof idMap !== 'object') return

  Object.entries(idMap).forEach(([oldId, newId]) => {
    if (!oldId || !newId || oldId === newId) return
    const oldKey = buildStorageKey(workflowId, oldId)
    const newKey = buildStorageKey(workflowId, newId)
    try {
      const raw = sessionStorage.getItem(oldKey)
      if (raw) {
        sessionStorage.setItem(newKey, raw)
        sessionStorage.removeItem(oldKey)
      }
    } catch {
      // ignore
    }
  })
}

/** 按 idMap 重映射 { nodeId: value } 结构 */
export function remapRecordByIdMap(record = {}, idMap = {}) {
  if (!idMap || typeof idMap !== 'object') return { ...(record || {}) }

  const next = { ...(record || {}) }
  Object.entries(idMap).forEach(([oldId, newId]) => {
    if (!oldId || !newId || oldId === newId) return
    if (Object.prototype.hasOwnProperty.call(next, oldId)) {
      next[newId] = next[oldId]
      delete next[oldId]
    }
  })
  return next
}

/** 保存后迁移 execution store 中的节点执行态 */
export function remapExecutionStoreNodeIds(executionStore, idMap = {}) {
  if (!executionStore || !idMap || typeof idMap !== 'object') return

  if (typeof executionStore.remapNodeIds === 'function') {
    executionStore.remapNodeIds(idMap)
    return
  }

  executionStore.$patch({
    nodeStatusMap: remapRecordByIdMap(executionStore.nodeStatusMap, idMap),
    nodeOutputs: remapRecordByIdMap(executionStore.nodeOutputs, idMap),
    nodeInputs: remapRecordByIdMap(executionStore.nodeInputs, idMap),
    canvasNodeRuntime: remapRecordByIdMap(executionStore.canvasNodeRuntime, idMap),
    ...(executionStore.currentNodeId && idMap[executionStore.currentNodeId]
      ? { currentNodeId: idMap[executionStore.currentNodeId] }
      : {}),
  })
}

export function readSessionNodeRuntime(workflowId, nodeId) {
  if (!workflowId || !nodeId) return null
  try {
    const raw = sessionStorage.getItem(buildStorageKey(workflowId, nodeId))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function writeSessionNodeRuntime(workflowId, nodeId, runtime) {
  if (!workflowId || !nodeId || !runtime) return
  try {
    sessionStorage.setItem(buildStorageKey(workflowId, nodeId), JSON.stringify(runtime))
  } catch {
    // ignore
  }
}
