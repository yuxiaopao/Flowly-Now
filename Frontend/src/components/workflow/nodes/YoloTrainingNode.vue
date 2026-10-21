<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...(isExpanded ? resize.sizeStyle.value : {}) }"
    class="domain-node yolo-training-node"
    :class="{
      selected,
      expanded: isExpanded,
      'is-running': isRunning,
      'is-completed': isCompleted,
      'is-failed': isFailed
    }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
      <button
        class="action-btn"
        @click.stop="toggleExpand"
      >
        <ChevronDown
          class="action-icon"
          :class="{ rotated: isExpanded }"
        />
      </button>
    </div>

    <div class="node-name-section">
      <input
        :id="`node-label-${id}`"
        v-model="localName"
        class="node-name-input"
        name="node-label"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div class="info-row">
        <span class="info-label">模型</span>
        <span class="info-value">
          {{ localConfig.yoloVersion || 'v8' }}{{ localConfig.modelVariant || 'n' }}
        </span>
      </div>
      <div
        v-if="localConfig.epochs"
        class="info-row"
      >
        <span class="info-label">轮次</span>
        <span class="info-value">{{ localConfig.epochs }}ep</span>
      </div>
      <div
        v-if="isRunning && monitor.etaFormatted.value"
        class="info-row eta-row"
      >
        <span class="info-label">剩余</span>
        <span class="info-value">{{ monitor.etaFormatted.value }}</span>
      </div>
    </div>

    <div
      v-if="isRunning"
      class="result-zone"
    >
      <div class="result-running">
        <Loader class="result-icon spinning" />
        <span>Epoch {{ monitor.currentEpoch.value || 0 }}/{{ monitor.totalEpochs.value || localConfig.epochs || '?' }}</span>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: displayProgress + '%' }"
          />
        </div>
        <span class="progress-text">{{ displayProgress }}%</span>
      </div>
    </div>

    <div
      v-else-if="isCompleted"
      class="result-zone result-completed"
    >
      <div class="result-summary">
        训练完成
      </div>
      <div class="result-stats">
        <div
          v-if="displayFitness"
          class="stat-item"
        >
          <span class="stat-label">Fitness</span>
          <span class="stat-value">{{ displayFitness }}</span>
        </div>
        <div
          v-if="displayWeightPath"
          class="stat-item"
        >
          <span class="stat-label">权重</span>
          <span
            class="stat-value small copyable"
            title="点击复制路径"
            @click.stop="copyPath(displayWeightPath)"
          >{{ basename(displayWeightPath) }}</span>
        </div>
      </div>
    </div>

    <div
      v-else-if="isFailed"
      class="result-zone result-failed"
    >
      <div class="result-summary">
        {{ nodeOutput?.error || props.data.error || '训练失败' }}
      </div>
    </div>

    <div
      v-if="hasLocalMonitor"
      class="panel-actions nodrag"
    >
      <el-button
        :disabled="!isDesktop"
        :data-testid="`yolo-training-details-${id}`"
        @click.stop="detailsVisible = true"
      >
        查看训练详情
      </el-button>
      <span v-if="!isDesktop">请在桌面端查看本地记录</span>
    </div>

    <el-dialog
      v-if="hasLocalMonitor"
      v-model="detailsVisible"
      :title="`${localName} · 训练详情`"
      width="min(1320px, 96vw)"
      class="yolo-run-dialog"
      append-to-body
      destroy-on-close
      @keydown.stop
    >
      <LocalYoloRunMonitor
        v-if="detailsVisible"
        :binding="runBinding"
        @snapshot="localSnapshot = $event"
      />
    </el-dialog>

    <div
      v-if="isExpanded && !hasLocalMonitor"
      class="expanded-panel"
      @click.stop
    >
      <div class="panel-actions">
        <el-button
          size="small"
          @click.stop="checkEnvironment"
        >
          环境检测
        </el-button>
        <el-tag
          v-if="monitor.wsConnected.value"
          size="small"
          type="success"
        >
          实时连接
        </el-tag>
      </div>

      <ul
        v-if="monitor.envChecks.value.length"
        class="env-checklist"
      >
        <li
          v-for="item in monitor.envChecks.value"
          :key="item.key"
          :class="{ ok: item.ok, warn: !item.ok }"
        >
          <strong>{{ item.label }}</strong> — {{ item.detail }}
        </li>
      </ul>

      <div class="metrics-grid">
        <YoloProgressRing
          :percent="displayProgress"
          label="训练进度"
          :status="props.data.status"
        />
        <YoloGpuCard
          v-if="gpuInfoForCard"
          :gpu-info="gpuInfoForCard"
        />
      </div>

      <div
        v-if="hasLiveCharts"
        class="charts-section"
      >
        <div class="charts-section-title">
          实时训练曲线（原生数据）
        </div>
        <div class="charts-grid">
          <YoloChartPanel
            v-if="monitor.lossBoxHistory.value.length"
            title="Box Loss"
            :data="monitor.lossBoxHistory.value"
            color="#409eff"
            :latest-value="monitor.lossBoxHistory.value.at(-1)"
          />
          <YoloChartPanel
            v-if="monitor.lossClsHistory.value.length"
            title="Cls Loss"
            :data="monitor.lossClsHistory.value"
            color="#e6a23c"
            :latest-value="monitor.lossClsHistory.value.at(-1)"
          />
          <YoloChartPanel
            v-if="monitor.lossDflHistory.value.length"
            title="DFL Loss"
            :data="monitor.lossDflHistory.value"
            color="#f56c6c"
            :latest-value="monitor.lossDflHistory.value.at(-1)"
          />
          <YoloChartPanel
            v-if="monitor.map50History.value.length"
            title="mAP50"
            :data="monitor.map50History.value"
            color="#67c23a"
            :latest-value="monitor.map50History.value.at(-1)"
          />
          <YoloChartPanel
            v-if="monitor.precisionHistory.value.length"
            title="Precision"
            :data="monitor.precisionHistory.value"
            color="#8b5cf6"
            :latest-value="monitor.precisionHistory.value.at(-1)"
          />
          <YoloChartPanel
            v-if="monitor.recallHistory.value.length"
            title="Recall"
            :data="monitor.recallHistory.value"
            color="#06b6d4"
            :latest-value="monitor.recallHistory.value.at(-1)"
          />
        </div>
      </div>

      <YoloNativePlotsPanel
        v-if="monitor.nativePlots.value.length && trainingRunId"
        :plots="monitor.nativePlots.value"
        :job-id="trainingRunId"
        :fetch-plot-blob="monitor.fetchPlotBlob"
      />

      <YoloLogPanel
        v-if="monitor.logLines.value.length"
        :lines="monitor.logLines.value"
      />

      <div
        class="resize-handle"
        title="拖拽调整节点大小"
        @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
      />
    </div>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Handle, Position } from '@vue-flow/core'
import { ChevronDown, Loader } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import { useYoloTrainingMonitor } from '@/composables/useYoloTrainingMonitor'
import { useNodeResize } from '@/composables/useNodeResize'
import YoloProgressRing from '@/components/workflow/yolo/YoloProgressRing.vue'
import YoloGpuCard from '@/components/workflow/yolo/YoloGpuCard.vue'
import YoloChartPanel from '@/components/workflow/yolo/YoloChartPanel.vue'
import YoloNativePlotsPanel from '@/components/workflow/yolo/YoloNativePlotsPanel.vue'
import YoloLogPanel from '@/components/workflow/yolo/YoloLogPanel.vue'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import LocalYoloRunMonitor from '@/components/workflow/yolo/LocalYoloRunMonitor.vue'
import trainingApi from '@/api/training'


const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  type: { type: String, default: 'yolo_training' },
})

const NODE_TYPE = 'yolo_training'
const { nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select', 'change'])
const appStore = useAppStore()
const route = useRoute()
const isDesktop = Boolean(window.flowlyDesktop?.training?.monitor)
const detailsVisible = ref(false)
const localSnapshot = ref(null)
const linkedRun = ref(null)

const isExpanded = ref(false)
const localName = ref(props.data.label || props.data.name || nodeLabel)
const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 320,
  minHeight: 240,
  maxWidth: 900,
  maxHeight: 900,
})

watch(() => props.data.label, (v) => { localName.value = v || nodeLabel })

const localConfig = computed(() => props.data.config || {})
const nodeOutput = computed(() => props.data.output || props.data.result || {})

const hasLocalMonitor = computed(() => Boolean(localConfig.value.localMonitor || localConfig.value.local_monitor))
const runStatus = computed(() => hasLocalMonitor.value ? linkedRun.value?.status || props.data.status : props.data.status)
const isRunning = computed(() => localSnapshot.value ? localSnapshot.value.running : runStatus.value === 'running')
const isCompleted = computed(() => localSnapshot.value ? localSnapshot.value.trainingFinished : runStatus.value === 'completed')
const isFailed = computed(() => localSnapshot.value ? localSnapshot.value.stage === 'failed' : runStatus.value === 'failed')

const trainingRunId = computed(() => {
  const out = nodeOutput.value
  return out.training_run_id || out.job_id || out.trainingRunId || props.data.trainingRunId
    || localConfig.value.reuseTrainingJobId || null
})
const runBinding = computed(() => ({ jobId: trainingRunId.value, nodeId: props.id, workflowId: String(route.params.id || '') }))
watch(trainingRunId, async jobId => {
  linkedRun.value = null
  localSnapshot.value = null
  if (!jobId || !hasLocalMonitor.value) return
  try {
    const run = await trainingApi.getYoloRun(jobId)
    if (trainingRunId.value === jobId) linkedRun.value = run
  } catch (error) {
    appStore.error(error.message || '训练记录加载失败')
  }
}, { immediate: true })

const remoteRunId = computed(() => hasLocalMonitor.value ? null : trainingRunId.value)
const monitor = useYoloTrainingMonitor(remoteRunId)

const displayProgress = computed(() => {
  if (localSnapshot.value) return Math.round(localSnapshot.value.progress)
  if (linkedRun.value) return linkedRun.value.progress
  if (monitor.progressPercent.value) return Math.round(monitor.progressPercent.value)
  if (isRunning.value) return props.data.progress || 0
  return isCompleted.value ? 100 : 0
})

const displayFitness = computed(() => {
  const v = localSnapshot.value?.best?.top1 || linkedRun.value?.bestFitness
    || monitor.bestFitness.value || nodeOutput.value.best_fitness || nodeOutput.value.bestFitness
  return v ? Number(v).toFixed(4) : ''
})

const displayWeightPath = computed(() => {
  return monitor.bestWeightPath.value
    || linkedRun.value?.bestWeightPath
    || nodeOutput.value.best_weight_path
    || nodeOutput.value.bestWeightPath
    || ''
})

const gpuInfoForCard = computed(() => {
  const g = monitor.gpuSnapshot.value
  if (!g || !Object.keys(g).length) return null
  return {
    available: g.available ?? true,
    name: g.name || g.device_name || 'GPU',
    memory_free_mb: g.memory_free_mb ?? g.memoryFreeMb,
    memory_total_mb: g.memory_total_mb ?? g.memoryTotalMb,
    utilization_percent: g.utilization_percent ?? g.utilizationPercent,
  }
})

const hasLiveCharts = computed(() => (
  monitor.lossBoxHistory.value.length
  || monitor.lossClsHistory.value.length
  || monitor.lossDflHistory.value.length
  || monitor.map50History.value.length
  || monitor.precisionHistory.value.length
  || monitor.recallHistory.value.length
))

async function refreshTrainingArtifacts() {
  const jobId = trainingRunId.value
  if (!jobId) return
  await monitor.hydrateMetricsHistory(jobId)
  // Load once immediately; while running, val_batch/train_batch preview images
  // appear progressively so we keep polling for a live, ComfyUI-style reveal.
  await monitor.loadNativePlots(jobId)
}

watch(
  [trainingRunId, () => props.data.status],
  ([jobId, statusValue], [, prevStatus]) => {
    if (!jobId || hasLocalMonitor.value) return
    if (statusValue === 'running' || statusValue === 'completed') {
      refreshTrainingArtifacts()
    }
    if (statusValue === 'running' && isExpanded.value) {
      monitor.startPlotsPolling(jobId)
    } else {
      monitor.stopPlotsPolling()
    }
    if (statusValue === 'completed' && prevStatus !== 'completed') {
      monitor.loadNativePlots(jobId)
      monitor.hydrateMetricsHistory(jobId, true)
    }
  },
  { immediate: true },
)

watch(isExpanded, (expanded) => {
  if (!expanded) {
    monitor.stopPlotsPolling()
    return
  }
  if (trainingRunId.value) {
    refreshTrainingArtifacts()
    if (isRunning.value) {
      monitor.startPlotsPolling(trainingRunId.value)
    }
  }
})


function handleSelect() {
  emit('select', props.id)
}

function toggleExpand() {
  handleSelect()
  if (hasLocalMonitor.value) {
    detailsVisible.value = true
    return
  }
  isExpanded.value = !isExpanded.value
  if (isExpanded.value && !monitor.envChecks.value.length) {
    checkEnvironment()
  }
}

function handleChange() {
  emit('change', { label: localName.value })
}

function basename(path) {
  if (!path) return ''
  return path.split('/').pop().split('\\').pop()
}

async function checkEnvironment() {
  await monitor.runEnvironmentCheck({
    ...localConfig.value,
    datasetPath: localConfig.value.dataset_yaml_path || localConfig.value.datasetPath,
    datasetSize: localConfig.value.datasetSize || 1000,
  })
}

function copyPath(path) {
  navigator.clipboard.writeText(path).then(() => {
    appStore.success('权重路径已复制')
  }).catch(() => {
    appStore.error('复制失败')
  })
}
</script>

<style scoped>
.yolo-training-node.expanded {
  min-width: 320px;
}

.node-mode-badge {
  margin-left: 4px;
}

.eta-row .info-value {
  color: var(--warning, #f59e0b);
}

.expanded-panel {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border-primary, #e5e7eb);
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.resize-handle {
  position: absolute;
  right: -6px;
  bottom: -6px;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  border-radius: 3px;
  background:
    linear-gradient(135deg, transparent 0 45%, var(--node-accent, #8b5cf6) 45% 55%, transparent 55% 100%),
    linear-gradient(135deg, transparent 0 65%, var(--node-accent, #8b5cf6) 65% 75%, transparent 75% 100%);
  opacity: 0.5;
  transition: opacity 0.15s ease;
  z-index: 5;
}

.resize-handle:hover {
  opacity: 1;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.env-checklist {
  margin: 0;
  padding-left: 16px;
  font-size: 11px;
  line-height: 1.6;
}

.env-checklist .ok { color: var(--success, #10b981); }
.env-checklist .warn { color: var(--warning, #f59e0b); }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 8px;
}

.charts-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.charts-section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary, #9ca3af);
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.copyable {
  cursor: pointer;
  text-decoration: underline;
}
</style>
