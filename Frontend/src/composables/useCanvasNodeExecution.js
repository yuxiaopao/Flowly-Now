/**
 * 画布节点执行态 — 合并 Editor runtimeState、node.data._runtime 与 execution store，
 * 通过 watch 写入本地快照，避免 Vue Flow 自定义节点不重渲染导致 UI 滞后。
 */

import { ref, watch, computed, unref } from 'vue'
import { useExecutionStore } from '@/stores/execution'
import { resolveNodeDisplayContent } from '@/composables/useNodeResultDisplay'

function pickRuntime(nodeId, runtimeState, dataRuntime, store) {
  const fromProp = unref(runtimeState)
  const fromData = unref(dataRuntime)
  const status =
    fromProp?.status ??
    fromData?.status ??
    store.nodeStatusMap[nodeId] ??
    null
  const output =
    fromProp?.output ??
    fromData?.output ??
    store.nodeOutputs[nodeId] ??
    null
  const error =
    fromProp?.error ??
    fromData?.error ??
    null

  return { status, output, error }
}

/**
 * @param {import('vue').MaybeRefOrGetter<string>} nodeId
 * @param {import('vue').MaybeRefOrGetter<object|null|undefined>} runtimeStateProp
 * @param {import('vue').MaybeRefOrGetter<object|null|undefined>} dataRuntimeProp
 */
export function useCanvasNodeExecution(nodeId, runtimeStateProp = null, dataRuntimeProp = null) {
  const executionStore = useExecutionStore()

  const snapshot = ref({
    status: null,
    output: null,
    error: null,
    content: resolveNodeDisplayContent(null),
  })

  function syncSnapshot() {
    const id = typeof nodeId === 'function' ? nodeId() : unref(nodeId)
    if (!id) return

    const runtime = pickRuntime(
      id,
      typeof runtimeStateProp === 'function' ? runtimeStateProp() : runtimeStateProp,
      typeof dataRuntimeProp === 'function' ? dataRuntimeProp() : dataRuntimeProp,
      executionStore,
    )

    snapshot.value = {
      ...runtime,
      content: resolveNodeDisplayContent(runtime.output),
    }
  }

  watch(
    [
      () => (typeof nodeId === 'function' ? nodeId() : unref(nodeId)),
      () => (typeof runtimeStateProp === 'function' ? runtimeStateProp() : unref(runtimeStateProp)),
      () => (typeof dataRuntimeProp === 'function' ? dataRuntimeProp() : unref(dataRuntimeProp)),
      () => executionStore.nodeStatusMap,
      () => executionStore.nodeOutputs,
      () => executionStore.canvasNodeRuntime,
    ],
    syncSnapshot,
    { immediate: true, deep: true },
  )

  const nodeStatus = computed(() => snapshot.value.status)
  const nodeOutput = computed(() => snapshot.value.output)
  const isRunning = computed(() => nodeStatus.value === 'running')
  const isCompleted = computed(() => nodeStatus.value === 'completed')
  const isFailed = computed(() => nodeStatus.value === 'failed')
  const displayContent = computed(() => snapshot.value.content)

  const outputText = computed(() => {
    if (displayContent.value.text) return displayContent.value.text
    if (!nodeOutput.value) return ''
    if (typeof nodeOutput.value === 'string') return nodeOutput.value
    try {
      return JSON.stringify(nodeOutput.value, null, 2)
    } catch {
      return String(nodeOutput.value)
    }
  })

  const errorMessage = computed(() => {
    if (snapshot.value.error) return String(snapshot.value.error)
    if (!nodeOutput.value || typeof nodeOutput.value !== 'object') return ''
    return nodeOutput.value.error || nodeOutput.value.message || nodeOutput.value.error_message || ''
  })

  const hasDisplayContent = computed(() =>
    Boolean(
      outputText.value ||
      displayContent.value.imageUrl ||
      displayContent.value.videoUrl ||
      displayContent.value.audioUrl ||
      displayContent.value.chartOption,
    ),
  )

  return {
    snapshot,
    nodeStatus,
    nodeOutput,
    isRunning,
    isCompleted,
    isFailed,
    displayContent,
    outputText,
    errorMessage,
    hasDisplayContent,
    syncSnapshot,
  }
}
