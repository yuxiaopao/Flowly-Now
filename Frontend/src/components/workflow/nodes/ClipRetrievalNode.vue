<template>
  <SiteFactoryNodeShell
    :id="id"
    :data="data"
    :selected="selected"
    node-type="clip_retrieval"
  >
    <template #expanded>
      <div v-if="isRunning" class="progress-zone">
        <Loader class="spin-icon" />
        <span>{{ progressLabel }}</span>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: displayProgress + '%' }" />
        </div>
        <span class="progress-pct">{{ displayProgress }}%</span>
        <p v-if="gpuLabel" class="gpu-hint">{{ gpuLabel }}</p>
      </div>
      <div v-if="metrics.r_at_5 != null" class="metrics-card">
        <p>R@1 {{ pct(metrics.r_at_1) }} · R@5 {{ pct(metrics.r_at_5) }} · R@10 {{ pct(metrics.r_at_10) }}</p>
        <p v-if="encoderLabel">编码器：{{ encoderLabel }}</p>
        <p v-if="indexDir">索引：{{ indexDir }}</p>
      </div>

      <div v-if="isDesktop && indexMode === 'desktop'" class="desktop-panel">
        <el-tag size="small" type="success">Desktop GPU</el-tag>
        <div v-if="desktopRunning" class="progress-zone">
          <Loader class="spin-icon" />
          <span>本地索引 {{ desktopProgress }}%</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: desktopProgress + '%' }" />
          </div>
        </div>
        <div class="panel-actions">
          <el-button
            size="small"
            type="primary"
            :loading="desktopRunning"
            @click.stop="buildLocalIndex"
          >
            本地 GPU 构建
          </el-button>
          <el-button v-if="desktopRunning" size="small" @click.stop="stopLocalIndex">停止</el-button>
        </div>
        <p v-if="desktopError" class="error">{{ desktopError }}</p>
      </div>
    </template>
  </SiteFactoryNodeShell>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { Search, Loader } from 'lucide-vue-next'
import SiteFactoryNodeShell from './SiteFactoryNodeShell.vue'
import trainingApi from '@/api/training'
import { useClipIndexDesktop } from '@/composables/useClipIndexDesktop'
import { useAppStore } from '@/stores/app'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['change'])
const appStore = useAppStore()
const clipDesktop = useClipIndexDesktop()

const nodeConfig = computed(() => props.data.config || {})
const indexMode = computed(() => nodeConfig.value.indexMode || 'server')
const isDesktop = computed(() => clipDesktop.isDesktop)
const desktopRunning = computed(() => clipDesktop.running.value)
const desktopProgress = computed(() => clipDesktop.progress.value)
const desktopError = computed(() => clipDesktop.errorMessage.value)

const nodeOutput = computed(() => props.data.output || props.data.result || {})
const metrics = computed(() => nodeOutput.value.metrics || {})
const indexDir = computed(() => nodeOutput.value.index_dir || nodeOutput.value.indexDir || '')
const encoderLabel = computed(() => nodeOutput.value.encoder || '')

const isRunning = computed(() => {
  if (props.data.status === 'running') return true
  const st = nodeOutput.value.training_status || nodeOutput.value.trainingStatus
  return st === 'running'
})

const trainingRunId = computed(() => {
  return nodeOutput.value.training_run_id || nodeOutput.value.trainingRunId || null
})

const wsProgress = ref(0)
const wsPhase = ref('')
let ws = null

function disconnectWs() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function connectWs(jobId) {
  disconnectWs()
  if (!jobId) return
  try {
    ws = new WebSocket(trainingApi.getYoloWebSocketUrl(jobId))
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.progress_percent != null) wsProgress.value = data.progress_percent
        else if (data.progress != null) wsProgress.value = data.progress
        if (data.phase) wsPhase.value = data.phase
      } catch {
        /* ignore parse errors */
      }
    }
  } catch {
    /* ignore connection errors */
  }
}

watch([trainingRunId, isRunning], ([id, running]) => {
  if (id && running) connectWs(id)
  else disconnectWs()
}, { immediate: true })

onUnmounted(disconnectWs)

const displayProgress = computed(() => {
  if (wsProgress.value) return Math.round(wsProgress.value)
  if (nodeOutput.value.progress != null) return Math.round(nodeOutput.value.progress)
  return isRunning.value ? 0 : 100
})

const progressLabel = computed(() => {
  if (wsPhase.value === 'indexing') return '正在构建向量索引…'
  return '索引进度'
})

const gpuLabel = computed(() => {
  const g = nodeOutput.value.gpu_info || nodeOutput.value.gpuInfo
  if (!g) return ''
  if (g.available) return `GPU：${g.name || '可用'}`
  return 'CPU 模式（未检测到 GPU）'
})

function pct(v) {
  if (v == null) return '-'
  return `${(Number(v) * 100).toFixed(0)}%`
}

function resolveDatasetPath() {
  return nodeConfig.value.datasetPath
    || nodeOutput.value.dataset_path
    || ''
}

async function buildLocalIndex() {
  const datasetPath = resolveDatasetPath()
  if (!datasetPath) {
    appStore.warning('缺少 dataset_path，请先运行上游 dataset_upload')
    return
  }
  const outputDir = nodeConfig.value.outputDir || `${String(datasetPath).replace(/\\/g, '/')}/index`
  clipDesktop.bindListeners()
  const start = await clipDesktop.startIndex({
    jobId: `clip-ret-${props.id}-${Date.now()}`,
    dataset_path: datasetPath,
    datasetPath,
    output_dir: outputDir,
    outputDir,
    base_model: nodeConfig.value.baseModel || 'simple-bow',
  })
  if (!start?.success) {
    appStore.error(start?.error || '启动本地索引失败')
    return
  }
  const result = await clipDesktop.waitForCompletion()
  if (!result?.success) {
    appStore.error(result?.error || '本地索引构建失败')
    return
  }
  appStore.success('本地 CLIP 索引构建完成')
  emit('change', {
    config: {
      ...nodeConfig.value,
      prebuiltIndexDir: result.index_dir,
    },
    output: {
      index_dir: result.index_dir,
      metrics: result.metrics || {},
      encoder: result.encoder,
      built_on: 'desktop',
    },
  })
}

async function stopLocalIndex() {
  await clipDesktop.stopIndex()
}
</script>

<style scoped lang="scss">
.metrics-card {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-secondary, #a1a1aa);
  p { margin: 0 0 4px; }
}

.progress-zone {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--text-secondary, #a1a1aa);
  margin-bottom: 8px;

  .spin-icon {
    width: 14px;
    height: 14px;
    animation: spin 1s linear infinite;
  }

  .progress-bar {
    flex: 1;
    min-width: 80px;
    height: 6px;
    background: #2e2e42;
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: #06b6d4;
    transition: width 0.3s;
  }

  .progress-pct { min-width: 32px; text-align: right; }
  .gpu-hint { width: 100%; margin: 0; font-size: 10px; opacity: 0.85; }
}

.desktop-panel {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-primary, #e5e7eb);

  .panel-actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }

  .error {
    margin: 6px 0 0;
    font-size: 11px;
    color: var(--danger, #ef4444);
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
