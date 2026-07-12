/**
 * Per-job YOLO training monitor for workflow nodes.
 * Subscribes to ws/training/{jobId}/ for live metrics.
 */
import { ref, computed, watch, onUnmounted } from 'vue'
import trainingApi from '@/api/training'

const WS_RECONNECT_DELAY_MS = 3000
const MAX_LOG_LINES = 300

function formatEta(seconds) {
  if (!seconds || seconds <= 0) return '计算中…'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `约 ${h} 小时 ${m} 分钟`
  return `约 ${m} 分钟`
}

export function estimateTrainingDuration({ epochs = 50, imageSize = 640, datasetSize = 1000, hasGpu = true }) {
  const baseSecPerEpoch = hasGpu ? 45 : 180
  const sizeFactor = Math.max(0.5, imageSize / 640)
  const dataFactor = Math.max(0.3, Math.min(2, datasetSize / 1000))
  const total = Math.round(epochs * baseSecPerEpoch * sizeFactor * dataFactor)
  return { etaSeconds: total, etaFormatted: formatEta(total) }
}

export function useYoloTrainingMonitor(jobIdRef) {
  const wsConnected = ref(false)
  const lossBoxHistory = ref([])
  const lossClsHistory = ref([])
  const lossDflHistory = ref([])
  const map50History = ref([])
  const precisionHistory = ref([])
  const recallHistory = ref([])
  const gpuSnapshot = ref({})
  const logLines = ref([])
  const etaSeconds = ref(0)
  const etaFormatted = ref('')
  const elapsedSeconds = ref(0)
  const currentEpoch = ref(0)
  const totalEpochs = ref(0)
  const progressPercent = ref(0)
  const bestFitness = ref(0)
  const bestWeightPath = ref('')
  const envChecks = ref([])
  const envReady = ref(false)
  const nativePlots = ref([])
  const metricsHydrated = ref(false)

  let ws = null
  let reconnectTimer = null
  let elapsedTimer = null

  const hasJob = computed(() => Boolean(jobIdRef.value))

  function appendLog(line) {
    logLines.value.push(line)
    if (logLines.value.length > MAX_LOG_LINES) {
      logLines.value.splice(0, logLines.value.length - MAX_LOG_LINES)
    }
  }

  function resetLive() {
    lossBoxHistory.value = []
    lossClsHistory.value = []
    lossDflHistory.value = []
    map50History.value = []
    precisionHistory.value = []
    recallHistory.value = []
    gpuSnapshot.value = {}
    logLines.value = []
    etaSeconds.value = 0
    etaFormatted.value = ''
    elapsedSeconds.value = 0
    currentEpoch.value = 0
    totalEpochs.value = 0
    progressPercent.value = 0
    bestFitness.value = 0
    bestWeightPath.value = ''
    nativePlots.value = []
    metricsHydrated.value = false
  }

  function disconnect() {
    if (ws) {
      ws.close()
      ws = null
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
    stopPlotsPolling()
    wsConnected.value = false
  }

  function handleMessage(msg) {
    const payload = msg.data || msg
    const event = payload.event || msg.type || 'unknown'
    appendLog(`${new Date().toLocaleTimeString()} [${event}]`)

    const data = payload.data || payload
    if (data.gpu) gpuSnapshot.value = data.gpu
    if (data.timing) {
      etaSeconds.value = data.timing.eta_seconds || 0
      etaFormatted.value = data.timing.eta_formatted || formatEta(etaSeconds.value)
      elapsedSeconds.value = data.timing.elapsed_seconds || elapsedSeconds.value
    }
    if (data.epoch != null) currentEpoch.value = data.epoch
    if (data.total_epochs != null) totalEpochs.value = data.total_epochs
    if (data.progress_percent != null) progressPercent.value = data.progress_percent
    else if (data.progress != null) progressPercent.value = data.progress

    const loss = data.loss || {}
    const metrics = data.metrics || {}
    if (loss.box != null) lossBoxHistory.value.push(loss.box)
    if (loss.cls != null) lossClsHistory.value.push(loss.cls)
    if (loss.dfl != null) lossDflHistory.value.push(loss.dfl)
    if (metrics.mAP50 != null) map50History.value.push(metrics.mAP50)
    if (metrics.precision != null) precisionHistory.value.push(metrics.precision)
    if (metrics.recall != null) recallHistory.value.push(metrics.recall)
    if (metrics.fitness != null && metrics.fitness > bestFitness.value) {
      bestFitness.value = metrics.fitness
    }

    const artifacts = data.artifacts || {}
    if (artifacts.best_weight_path) bestWeightPath.value = artifacts.best_weight_path
    if (data.message) appendLog(`  ${data.message}`)
  }

  function connect(jobId) {
    disconnect()
    if (!jobId) return

    const wsUrl = trainingApi.getYoloWebSocketUrl(jobId)
    try {
      ws = new WebSocket(wsUrl)
      ws.onopen = () => {
        wsConnected.value = true
        appendLog('WebSocket 已连接')
      }
      ws.onmessage = (event) => {
        try {
          handleMessage(JSON.parse(event.data))
        } catch {
          appendLog(event.data)
        }
      }
      ws.onclose = () => {
        wsConnected.value = false
        reconnectTimer = setTimeout(() => connect(jobId), WS_RECONNECT_DELAY_MS)
      }
      ws.onerror = () => {
        wsConnected.value = false
      }
      elapsedTimer = setInterval(() => {
        elapsedSeconds.value += 1
      }, 1000)
    } catch (err) {
      appendLog(`连接失败: ${err.message}`)
    }
  }

  async function runEnvironmentCheck(config = {}) {
    envChecks.value = []
    envReady.value = false
    const checks = []

    try {
      const gpu = await trainingApi.getGpuInfo()
      const available = gpu?.available || gpu?.cuda_available
      checks.push({
        key: 'gpu',
        label: 'GPU / CUDA',
        ok: Boolean(available),
        detail: available ? (gpu?.device_name || gpu?.name || '可用') : '未检测到 GPU，将使用 CPU（较慢）'
      })
    } catch {
      checks.push({ key: 'gpu', label: 'GPU / CUDA', ok: false, detail: '无法获取 GPU 信息' })
    }

    const mode = config.trainingMode || 'local'
    checks.push({
      key: 'mode',
      label: '训练模式',
      ok: true,
      detail: mode === 'local' ? '本地训练（权重保存至客户机）' : '云端训练'
    })

    if (config.datasetPath || config.dataset_yaml_path) {
      checks.push({ key: 'dataset', label: '数据集路径', ok: true, detail: config.datasetPath || config.dataset_yaml_path })
    } else {
      checks.push({ key: 'dataset', label: '数据集', ok: false, detail: '请连接上游 dataset_upload 或配置数据集路径' })
    }

    const estimate = estimateTrainingDuration({
      epochs: config.epochs || 50,
      imageSize: config.imageSize || 640,
      datasetSize: config.datasetSize || 1000,
      hasGpu: checks.find(c => c.key === 'gpu')?.ok
    })
    checks.push({
      key: 'eta',
      label: '预估耗时',
      ok: true,
      detail: estimate.etaFormatted
    })
    etaFormatted.value = estimate.etaFormatted
    etaSeconds.value = estimate.etaSeconds

    envChecks.value = checks
    envReady.value = checks.filter(c => c.key !== 'gpu').every(c => c.ok)
    return { checks, ready: envReady.value, estimate }
  }

  function applyMetricsSeries(series = {}) {
    if (Array.isArray(series.loss_box) && series.loss_box.length) {
      lossBoxHistory.value = [...series.loss_box]
    }
    if (Array.isArray(series.loss_cls) && series.loss_cls.length) {
      lossClsHistory.value = [...series.loss_cls]
    }
    if (Array.isArray(series.loss_dfl) && series.loss_dfl.length) {
      lossDflHistory.value = [...series.loss_dfl]
    }
    if (Array.isArray(series.mAP50) && series.mAP50.length) {
      map50History.value = [...series.mAP50]
    }
    if (Array.isArray(series.precision) && series.precision.length) {
      precisionHistory.value = [...series.precision]
    }
    if (Array.isArray(series.recall) && series.recall.length) {
      recallHistory.value = [...series.recall]
    }
  }

  async function hydrateMetricsHistory(jobId, force = false) {
    if (!jobId) return
    const hasData = lossBoxHistory.value.length > 0 || map50History.value.length > 0
    if (!force && metricsHydrated.value && hasData) return
    try {
      const resp = await trainingApi.getYoloMetricsHistory(jobId)
      const payload = resp?.data?.data ?? resp?.data ?? resp
      const series = payload?.series || {}
      applyMetricsSeries(series)
      if (payload?.total_epochs) totalEpochs.value = payload.total_epochs
      if (series.mAP50?.length) {
        currentEpoch.value = series.mAP50.length
        progressPercent.value = payload.total_epochs
          ? Math.min(100, Math.round((series.mAP50.length / payload.total_epochs) * 100))
          : 100
      }
      metricsHydrated.value = true
      appendLog('已从训练记录加载原生指标曲线')
    } catch (err) {
      appendLog(`加载指标历史失败: ${err.message}`)
    }
  }

  async function loadNativePlots(jobId) {
    if (!jobId) return
    try {
      const resp = await trainingApi.getYoloTrainingPlots(jobId)
      const payload = resp?.data?.data ?? resp?.data ?? resp
      const nextPlots = payload?.plots || []
      // Preserve already-resolved blob URLs for plots that haven't changed,
      // so the image grid doesn't flicker/reload on every poll tick.
      const prevByName = new Map(nativePlots.value.map((p) => [p.name, p]))
      nativePlots.value = nextPlots.map((p) => {
        const prev = prevByName.get(p.name)
        if (prev && prev.url && prev.modified_at === p.modified_at) {
          return { ...p, url: prev.url }
        }
        return p
      })
    } catch (err) {
      appendLog(`加载训练图表失败: ${err.message}`)
    }
  }

  let plotsPollTimer = null

  function startPlotsPolling(jobId, intervalMs = 4000) {
    stopPlotsPolling()
    if (!jobId) return
    plotsPollTimer = setInterval(() => {
      loadNativePlots(jobId)
    }, intervalMs)
  }

  function stopPlotsPolling() {
    if (plotsPollTimer) {
      clearInterval(plotsPollTimer)
      plotsPollTimer = null
    }
  }

  async function fetchPlotBlob(jobId, plotName) {
    const resp = await trainingApi.getYoloPlotImage(jobId, plotName)
    const blob = resp?.data instanceof Blob ? resp.data : resp
    return URL.createObjectURL(blob)
  }

  watch(jobIdRef, (id, prev) => {
    if (id === prev) return
    resetLive()
    if (id) connect(id)
    else disconnect()
  }, { immediate: true })

  onUnmounted(disconnect)

  return {
    wsConnected,
    lossBoxHistory,
    lossClsHistory,
    lossDflHistory,
    map50History,
    precisionHistory,
    recallHistory,
    gpuSnapshot,
    logLines,
    etaSeconds,
    etaFormatted,
    elapsedSeconds,
    currentEpoch,
    totalEpochs,
    progressPercent,
    bestFitness,
    bestWeightPath,
    envChecks,
    envReady,
    nativePlots,
    metricsHydrated,
    hasJob,
    runEnvironmentCheck,
    hydrateMetricsHistory,
    loadNativePlots,
    startPlotsPolling,
    stopPlotsPolling,
    fetchPlotBlob,
    disconnect,
    resetLive,
    formatEta,
  }
}
