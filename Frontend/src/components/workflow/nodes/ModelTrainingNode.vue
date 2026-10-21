<template>
  <div
    :style="{ '--node-accent': nodeColor }"
    class="domain-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
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
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        name="node-label"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.framework || localConfig.modelType"
        class="info-row"
      >
        <span class="info-label">框架</span>
        <span class="info-value">{{ localConfig.framework || localConfig.modelType || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description, 35) }}</span>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning || isFailed"
      class="result-zone"
    >
      <div
        v-if="isRunning"
        class="result-running"
      >
        <Loader class="result-icon spinning" />
        <span>训练中...</span>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{ width: (nodeOutput?.progress || 0) + '%' }"
          />
        </div>
        <span class="progress-text">{{ nodeOutput?.progress || 0 }}%</span>
      </div>
      <div
        v-else-if="isCompleted"
        class="result-completed"
      >
        <div class="result-summary">
          {{ resultSummary }}
        </div>
        <div class="result-stats">
          <div
            v-if="nodeOutput?.best_val_acc || nodeOutput?.best_accuracy"
            class="stat-item"
          >
            <span class="stat-label">最佳准确率</span>
            <span class="stat-value">{{ formatAccuracy(nodeOutput?.best_val_acc || nodeOutput?.best_accuracy) }}</span>
          </div>
          <div
            v-if="nodeOutput?.total_epochs || nodeOutput?.epochs"
            class="stat-item"
          >
            <span class="stat-label">训练轮数</span>
            <span class="stat-value">{{ nodeOutput?.total_epochs || nodeOutput?.epochs }}</span>
          </div>
        </div>
        <div
          v-if="nodeOutput?.model_path"
          class="model-path"
        >
          <span class="path-label">模型路径</span>
          <span class="path-value">{{ truncate(nodeOutput.model_path, 30) }}</span>
        </div>
        <div
          v-if="nodeOutput?.training_history?.length"
          class="training-chart"
        >
          <div class="chart-header">
            <span>Loss 曲线</span>
            <div class="chart-legend">
              <span class="legend-item loss">Loss</span>
              <span class="legend-item val-acc">Val Acc</span>
            </div>
          </div>
          <canvas
            ref="chartCanvas"
            class="loss-chart"
            width="200"
            height="60"
          />
        </div>
      </div>
      <div
        v-else-if="isFailed"
        class="result-failed"
      >
        <AlertCircle class="result-icon" />
        <span>{{ nodeOutput?.error || '训练失败' }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">训练框架</label>
          <el-select
            v-model="localConfig.framework"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="pytorch"
              label="PyTorch"
            />
            <el-option
              value="tensorflow"
              label="TensorFlow"
            />
            <el-option
              value="jax"
              label="JAX"
            />
            <el-option
              value="sklearn"
              label="Scikit-learn"
            />
            <el-option
              value="huggingface"
              label="HuggingFace"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">模型类型</label>
          <el-input
            v-model="localConfig.modelType"
            size="small"
            placeholder="例如: CNN, Transformer, RNN"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">训练轮数</label>
          <el-input-number
            v-model="localConfig.epochs"
            :min="1"
            :max="10000"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">批次大小</label>
          <el-input-number
            v-model="localConfig.batchSize"
            :min="1"
            :max="1024"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">学习率</label>
          <el-input-number
            v-model="localConfig.learningRate"
            :min="0.0001"
            :max="1"
            :step="0.0001"
            :precision="4"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="训练任务描述..."
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, Loader, AlertCircle } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'model_training'
const { nodeColor } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const isExpanded = ref(false)

const localName = ref(props.data.label || '模型训练')
const localConfig = ref({
  framework: props.data.config?.framework || 'pytorch',
  modelType: props.data.config?.modelType || '',
  epochs: props.data.config?.epochs || 100,
  batchSize: props.data.config?.batchSize || 32,
  learningRate: props.data.config?.learningRate || 0.001,
  description: props.data.config?.description || ''
})

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const chartCanvas = ref(null)

const resultSummary = computed(() => {
  if (!nodeOutput.value) return '训练中'
  const acc = nodeOutput.value.best_val_acc || nodeOutput.value.best_accuracy
  const epochs = nodeOutput.value.total_epochs || nodeOutput.value.epochs
  return acc ? `最佳准确率: ${(acc * 100).toFixed(1)}% | ${epochs} 轮` : '训练完成'
})

function formatAccuracy(acc) {
  if (!acc) return '-'
  return (acc * 100).toFixed(1) + '%'
}

function drawTrainingChart() {
  nextTick(() => {
    const canvas = chartCanvas.value
    if (!canvas || !nodeOutput.value?.training_history) return
    const ctx = canvas.getContext('2d')
    const history = nodeOutput.value.training_history
    const w = canvas.width
    const h = canvas.height
    ctx.clearRect(0, 0, w, h)
    
    if (history.length > 0) {
      const losses = history.map(h => h.train_loss || 0)
      const maxLoss = Math.max(...losses, 1)
      ctx.beginPath()
      ctx.strokeStyle = '#f97316'
      ctx.lineWidth = 2
      losses.forEach((loss, i) => {
        const x = (i / (losses.length - 1 || 1)) * w
        const y = h - (loss / maxLoss) * (h - 10) - 5
        if (i === 0) ctx.moveTo(x, y)
        else ctx.lineTo(x, y)
      })
      ctx.stroke()
      
      const valAccs = history.map(h => h.val_acc || 0).filter(v => v > 0)
      if (valAccs.length > 0) {
        ctx.beginPath()
        ctx.strokeStyle = '#10b981'
        ctx.lineWidth = 1.5
        ctx.setLineDash([4, 2])
        valAccs.forEach((acc, i) => {
          const x = (i / (valAccs.length - 1)) * w
          const y = h - acc * (h - 10) - 5
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        })
        ctx.stroke()
        ctx.setLineDash([])
      }
    }
  })
}

watch(() => nodeOutput.value?.training_history, () => {
  if (nodeOutput.value?.training_history?.length) {
    drawTrainingChart()
  }
}, { deep: true })

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '模型训练'
    localConfig.value = {
      framework: d.config?.framework || 'pytorch',
      modelType: d.config?.modelType || '',
      epochs: d.config?.epochs || 100,
      batchSize: d.config?.batchSize || 32,
      learningRate: d.config?.learningRate || 0.001,
      description: d.config?.description || '',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
}

function handleChange() {
  if (props.id) {
    updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
  }
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.domain-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    border-color: var(--node-border, v-bind(nodeColor));
    box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent);
    transform: translateY(-1px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border: 1px solid;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;

  .badge-icon {
    width: 11px;
    height: 11px;
  }
}

.action-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }

  .action-icon {
    width: 14px;
    height: 14px;
    transition: transform 0.2s ease;

    &.rotated {
      transform: rotate(180deg);
    }
  }
}

.node-name-section {
  padding: 10px 12px 6px;
}

.node-name-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text, #e5e5e5);
  outline: none;
  transition: all 0.15s ease;

  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }

  &:focus {
    border-color: v-bind(nodeColor);
    background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent);
  }
}

.compact-view {
  padding: 0 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;

  .info-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
  }

  .info-value {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
  }
}

.preview-row {
  .preview-text {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.6);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.result-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(245, 158, 11, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.result-running {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 10px;
  font-size: 11px;
  color: #f59e0b;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(245, 158, 11, 0.15);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(245, 158, 11, 0.6), #f59e0b);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
}

.result-completed {
  padding: 8px 10px;
}

.result-summary {
  font-size: 10px;
  color: #10b981;
  margin-bottom: 6px;
  font-weight: 600;
}

.result-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .stat-label {
    font-size: 9px;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
  }

  .stat-value {
    font-size: 12px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: #10b981;
  }
}

.model-path {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 6px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  margin-top: 4px;

  .path-label {
    font-size: 8px;
    color: rgba(255, 255, 255, 0.3);
    text-transform: uppercase;
  }

  .path-value {
    font-size: 9px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.6);
  }
}

.training-chart {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 9px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
}

.chart-legend {
  display: flex;
  gap: 8px;
}

.legend-item {
  font-size: 8px;
  padding: 1px 4px;
  border-radius: 2px;

  &.loss {
    background: rgba(249, 115, 22, 0.2);
    color: #f97316;
  }

  &.val-acc {
    background: rgba(16, 185, 129, 0.2);
    color: #10b981;
  }
}

.loss-chart {
  width: 100%;
  height: 60px;
  display: block;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.result-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 10px;
  color: #ef4444;
}

.result-icon {
  width: 14px;
  height: 14px;

  &.spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.domain-node {
  &.is-running {
    animation: train-pulse 1.8s ease-in-out infinite;
  }

  &.is-completed .result-zone {
    border-color: rgba(16, 185, 129, 0.4);
  }

  &.is-failed {
    border-color: rgba(239, 68, 68, 0.6) !important;
  }
}

@keyframes train-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(245, 158, 11, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(245, 158, 11, 0); }
}

.expanded-config {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 8px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.config-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.4);
}

:deep(.el-select),
:deep(.el-input),
:deep(.el-input-number) {
  width: 100%;

  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: none !important;
    border-radius: 6px;
  }

  .el-input__inner {
    color: var(--node-text, #e5e5e5) !important;
    font-size: 12px !important;
  }
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 500px;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: rgba(10, 10, 18, 0.95);
  border: 2px solid v-bind(nodeColor);
  border-radius: 50%;

  &:hover {
    background: v-bind(nodeColor);
    transform: scale(1.3);
  }
}

:global(.dark) {
  .domain-node {
    --node-bg: rgba(20, 20, 30, 0.95);
    --node-border: #f59e0b;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .domain-node {
    --node-bg: #fff;
    --node-border: #f59e0b;
    --node-text: #1e1e2e;
  }
}
</style>
