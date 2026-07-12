/**
 * 多模态节点执行结果持久化：
 * - 刷新后仍显示上次成果（sessionStorage + node.data._runtime）
 * - 仅在新一次执行产生新输出时覆盖
 * - 本节点 running 时显示执行中，不展示旧图/旧视频
 */
import { computed, unref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { useVueFlow } from '@vue-flow/core'
import { useExecutionStore } from '@/stores/execution'
import { unwrapNodeExecutionOutput } from '@/utils/workflowTransform'
import {
  readSessionNodeRuntime,
  writeSessionNodeRuntime,
} from '@/utils/nodeRuntimePersistence'

export function usePersistedMultimodalResult(nodeIdRef, dataRef) {
  const route = useRoute()
  const { updateNodeData } = useVueFlow()
  const executionStore = useExecutionStore()
  const { nodeOutputs, nodeStatusMap } = storeToRefs(executionStore)

  const workflowId = computed(() => String(route.params.id || ''))
  const nodeId = computed(() => unref(nodeIdRef) || '')

  const cachedRuntime = computed(() => {
    const data = unref(dataRef)
    if (data?._runtime?.output != null) return data._runtime
    return readSessionNodeRuntime(workflowId.value, nodeId.value)
  })

  const storeStatus = computed(() => {
    const id = nodeId.value
    if (!id) return null
    return nodeStatusMap.value[id] ?? null
  })

  const storeOutput = computed(() => {
    const id = nodeId.value
    if (!id) return null
    return unwrapNodeExecutionOutput(nodeOutputs.value[id])
  })

  const isRunning = computed(() => ['running', 'pending', 'queued'].includes(storeStatus.value))
  const isFailed = computed(() => storeStatus.value === 'failed')

  const nodeOutput = computed(() => {
    if (storeStatus.value != null) {
      return storeOutput.value ?? null
    }
    return unwrapNodeExecutionOutput(cachedRuntime.value?.output ?? null)
  })

  const hasCachedResult = computed(() => cachedRuntime.value?.output != null)

  const isCompleted = computed(() => {
    if (storeStatus.value === 'completed') return true
    if (isRunning.value || isFailed.value) return false
    return hasCachedResult.value && nodeOutput.value != null
  })

  function persistRuntime(status, output) {
    const id = nodeId.value
    const wfId = workflowId.value
    if (!id || output == null) return

    const runtime = {
      status: status || 'completed',
      output: unwrapNodeExecutionOutput(output),
      updatedAt: Date.now(),
    }

    writeSessionNodeRuntime(wfId, id, runtime)
    updateNodeData(id, { _runtime: runtime })
  }

  watch(
    [storeStatus, storeOutput],
    ([status, output]) => {
      if (!nodeId.value || output == null) return
      if (status === 'completed' || status === 'failed') {
        persistRuntime(status, output)
      }
    },
    { deep: true },
  )

  watch(
    [workflowId, nodeId, () => unref(dataRef)?._runtime],
    ([wfId, id, dataRuntime]) => {
      if (!wfId || !id || dataRuntime?.output != null) return
      const sessionRuntime = readSessionNodeRuntime(wfId, id)
      if (sessionRuntime?.output != null) {
        updateNodeData(id, { _runtime: sessionRuntime })
      }
    },
    { immediate: true },
  )

  return {
    nodeOutput,
    storeStatus,
    isRunning,
    isCompleted,
    isFailed,
    hasCachedResult,
    cachedRuntime,
    persistRuntime,
  }
}
