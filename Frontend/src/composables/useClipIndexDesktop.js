/**
 * Desktop CLIP retrieval index builder (Electron IPC).
 */
import { ref, onUnmounted } from 'vue'
import { getAgentAPI, isElectron } from '@/utils/electron'

export function useClipIndexDesktop() {
  const running = ref(false)
  const progress = ref(0)
  const phase = ref('')
  const logs = ref([])
  const lastResult = ref(null)
  const errorMessage = ref('')

  let unsubProgress = null
  let unsubComplete = null
  let unsubError = null
  let unsubStarted = null

  function cleanupListeners() {
    unsubProgress?.()
    unsubComplete?.()
    unsubError?.()
    unsubStarted?.()
    unsubProgress = null
    unsubComplete = null
    unsubError = null
    unsubStarted = null
  }

  function bindListeners() {
    cleanupListeners()
    const api = getAgentAPI()
    if (!api) return

    if (api.onClipIndexProgress) {
      unsubProgress = api.onClipIndexProgress((payload) => {
        running.value = Boolean(payload?.running)
        progress.value = payload?.progress ?? progress.value
        phase.value = payload?.phase || phase.value
        if (Array.isArray(payload?.logs)) {
          logs.value = payload.logs.slice(-100)
        }
      })
    }
    if (api.onClipIndexComplete) {
      unsubComplete = api.onClipIndexComplete((payload) => {
        running.value = false
        progress.value = 100
        phase.value = 'completed'
        lastResult.value = payload?.result || null
      })
    }
    if (api.onClipIndexError) {
      unsubError = api.onClipIndexError((payload) => {
        running.value = false
        errorMessage.value = payload?.error || '索引构建失败'
      })
    }
    if (api.onClipIndexStarted) {
      unsubStarted = api.onClipIndexStarted((payload) => {
        running.value = true
        progress.value = payload?.progress ?? 0
        phase.value = payload?.phase || 'starting'
        errorMessage.value = ''
        lastResult.value = null
      })
    }
  }

  async function startIndex(jobConfig) {
    const api = getAgentAPI()
    if (!api?.startClipIndex) {
      return { success: false, error: 'Desktop CLIP 索引 API 不可用（请在 Flowly Desktop 中运行）' }
    }

    bindListeners()
    running.value = true
    progress.value = 0
    phase.value = 'starting'
    logs.value = []
    errorMessage.value = ''

    const result = await api.startClipIndex(jobConfig)
    if (!result?.success) {
      running.value = false
      errorMessage.value = result?.error || '启动失败'
    }
    return result
  }

  async function stopIndex() {
    const api = getAgentAPI()
    if (!api?.stopClipIndex) {
      return { success: false, error: 'Desktop CLIP 索引 API 不可用' }
    }
    const result = await api.stopClipIndex()
    running.value = false
    return result
  }

  async function refreshStatus() {
    const api = getAgentAPI()
    if (!api?.getClipIndexStatus) return null
    const status = await api.getClipIndexStatus()
    if (status) {
      running.value = Boolean(status.running)
      progress.value = status.progress ?? 0
      phase.value = status.phase || ''
      lastResult.value = status.result || lastResult.value
      if (Array.isArray(status.logs)) logs.value = status.logs
    }
    return status
  }

  async function waitForCompletion(timeoutMs = 600000) {
    const started = Date.now()
    while (Date.now() - started < timeoutMs) {
      const status = await refreshStatus()
      if (!status?.running) {
        if (status?.result?.success) return status.result
        if (errorMessage.value) {
          return { success: false, error: errorMessage.value }
        }
        if (lastResult.value) return lastResult.value
        return { success: false, error: '索引构建未完成' }
      }
      await new Promise((r) => setTimeout(r, 1000))
    }
    return { success: false, error: '索引构建超时' }
  }

  onUnmounted(cleanupListeners)

  return {
    isDesktop: isElectron(),
    running,
    progress,
    phase,
    logs,
    lastResult,
    errorMessage,
    startIndex,
    stopIndex,
    refreshStatus,
    waitForCompletion,
    bindListeners,
  }
}

/**
 * Resolve upstream dataset_path for a clip_retrieval node from workflow graph.
 */
export function resolveClipRetrievalDatasetPath(node, allNodes, edges) {
  const cfg = node.data?.config || node.config || {}
  if (cfg.datasetPath || cfg.dataset_path) {
    return cfg.datasetPath || cfg.dataset_path
  }

  const nodeId = node.id
  const incoming = (edges || []).filter((e) => e.target === nodeId)
  for (const edge of incoming) {
    const upstream = (allNodes || []).find((n) => n.id === edge.source)
    if (!upstream) continue
    const out = upstream.data?.output || upstream.data?.result || {}
    const cfgUp = upstream.data?.config || {}
    const pathVal = out.dataset_path || out.path || out.datasetPath
      || cfgUp.datasetPath || cfgUp.path || cfgUp.storagePath
    if (pathVal) return pathVal
  }
  return ''
}

/**
 * Before workflow execute: build indexes locally for nodes with indexMode=desktop.
 */
export async function prepareDesktopClipIndexes(nodes, edges, { onProgress } = {}) {
  if (!isElectron()) return { patched: false, nodes }

  const api = getAgentAPI()
  if (!api?.startClipIndex) return { patched: false, nodes }

  const clipNodes = (nodes || []).filter((n) => {
    const type = n.type || n.data?.type
    const mode = n.data?.config?.indexMode
    return type === 'clip_retrieval' && mode === 'desktop'
  })

  if (!clipNodes.length) return { patched: false, nodes }

  const desktop = useClipIndexDesktop()
  desktop.bindListeners()

  for (const node of clipNodes) {
    const cfg = { ...(node.data?.config || {}) }
    const datasetPath = resolveClipRetrievalDatasetPath(node, nodes, edges)
    if (!datasetPath) {
      throw new Error(`CLIP 检索节点「${node.data?.label || node.id}」缺少 dataset_path，请先连接 dataset_upload`)
    }

    const outputDir = cfg.outputDir || `${datasetPath.replace(/\\/g, '/')}/index`
    const jobId = `clip-ret-${node.id}-${Date.now()}`

    onProgress?.({ nodeId: node.id, progress: 0, phase: 'starting' })

    const start = await desktop.startIndex({
      jobId,
      dataset_path: datasetPath,
      datasetPath,
      output_dir: outputDir,
      outputDir,
      base_model: cfg.baseModel || 'simple-bow',
      baseModel: cfg.baseModel || 'simple-bow',
      device: cfg.device ?? 0,
    })

    if (!start?.success) {
      throw new Error(start?.error || 'Desktop 索引启动失败')
    }

    const result = await desktop.waitForCompletion()
    if (!result?.success) {
      throw new Error(result?.error || 'Desktop 索引构建失败')
    }

    if (!node.data) node.data = {}
    if (!node.data.config) node.data.config = {}
    node.data.config.prebuiltIndexDir = result.index_dir
    node.data.config.prebuilt_index_dir = result.index_dir
    onProgress?.({ nodeId: node.id, progress: 100, phase: 'completed', indexDir: result.index_dir })
  }

  return { patched: true, nodes }
}
