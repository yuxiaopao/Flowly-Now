<template>
  <div
    class="embedding-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <div
        class="node-type-badge"
        :style="{ backgroundColor: nodeColor + '22', borderColor: nodeColor }"
      >
        <Hash
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">向量化</span>
      </div>
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
        v-model="localName"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.model || localConfig.embeddingType"
        class="info-row"
      >
        <span class="info-label">模型</span>
        <span class="info-value">{{ localConfig.model || localConfig.embeddingType || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description, 35) }}</span>
      </div>
      <div
        class="status-bar"
        :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
      >
        <div
          v-if="isRunning"
          class="status-running"
        >
          <Loader class="status-icon spinning" />
          <span>向量化中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="embeddingCount > 0"
            class="result-count"
          >{{ embeddingCount }} 条</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>执行失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="embedding-zone"
    >
      <div class="embedding-header">
        <Hash class="embedding-icon" />
        <span class="embedding-label">向量输出</span>
        <div class="dim-badge">
          <span class="dim-value">{{ localConfig.dimensions || 1536 }}</span>
          <span class="dim-unit">dim</span>
        </div>
      </div>
      <div class="embedding-stats">
        <div class="stat-item">
          <span class="stat-value">{{ embeddingCount > 0 ? embeddingCount : '—' }}</span>
          <span class="stat-label">向量数</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ localConfig.embeddingType || 'openai' }}</span>
          <span class="stat-label">类型</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ localConfig.dimensions || 1536 }}</span>
          <span class="stat-label">维度</span>
        </div>
      </div>
      <div
        v-if="nodeOutput && nodeOutput.vectors && nodeOutput.vectors.length > 0"
        class="vector-preview"
      >
        <div class="vector-label">
          向量预览
        </div>
        <div class="vector-bars">
          <div
            v-for="(vec, vi) in nodeOutput.vectors.slice(0, 8)"
            :key="vi"
            class="vector-bar-row"
          >
            <span class="vec-index">#{{ vi }}</span>
            <div class="vec-dims">
              <span
                v-for="(val, di) in (Array.isArray(vec) ? vec.slice(0, 6) : []).map(v => typeof v === 'number' ? v : 0)"
                :key="di"
                class="vec-val"
                :class="getDimClass(val)"
              >{{ formatVal(val) }}</span>
              <span
                v-if="(Array.isArray(vec) ? vec.length : 0) > 6"
                class="vec-more"
              >...</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">嵌入模型</label>
          <el-input
            v-model="localConfig.model"
            size="small"
            placeholder="例如: text-embedding-ada-002"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">嵌入类型</label>
          <el-select
            v-model="localConfig.embeddingType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="openai"
              label="OpenAI"
            />
            <el-option
              value="huggingface"
              label="HuggingFace"
            />
            <el-option
              value="cohere"
              label="Cohere"
            />
            <el-option
              value="azure"
              label="Azure OpenAI"
            />
            <el-option
              value="local"
              label="本地模型"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">批次大小</label>
          <el-input-number
            v-model="localConfig.batchSize"
            :min="1"
            :max="1000"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">维度</label>
          <el-input-number
            v-model="localConfig.dimensions"
            :min="64"
            :max="4096"
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
            placeholder="嵌入任务描述..."
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
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Hash, ChevronDown, Loader } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const nodeColor = '#06b6d4'

const localName = ref(props.data.label || '向量化')
const localConfig = ref({
  model: props.data.config?.model || '',
  embeddingType: props.data.config?.embeddingType || 'openai',
  batchSize: props.data.config?.batchSize || 100,
  dimensions: props.data.config?.dimensions || 1536,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const embeddingCount = computed(() => {
  if (!nodeOutput.value) return 0
  if (nodeOutput.value.vectors && Array.isArray(nodeOutput.value.vectors)) return nodeOutput.value.vectors.length
  if (nodeOutput.value.count) return nodeOutput.value.count
  if (nodeOutput.value.n) return nodeOutput.value.n
  return 0
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function formatVal(v) {
  if (typeof v !== 'number') return '0.0'
  if (Math.abs(v) < 0.001) return '0'
  if (Math.abs(v) < 1) return v.toFixed(3)
  return v.toFixed(2)
}

function getDimClass(v) {
  if (typeof v !== 'number') return 'val-zero'
  if (v > 0.5) return 'val-high'
  if (v > 0) return 'val-pos'
  if (v < -0.5) return 'val-low'
  return 'val-neg'
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '向量化'
    localConfig.value = { model: d.config?.model || '', embeddingType: d.config?.embeddingType || 'openai', batchSize: d.config?.batchSize || 100, dimensions: d.config?.dimensions || 1536, description: d.config?.description || '', ...d.config }
  }
}, { deep: true })

function toggleExpand() { isExpanded.value = !isExpanded.value }

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.embedding-node {
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
    box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent);
    transform: translateY(-1px);
  }

  &.is-running { animation: embed-pulse 1.8s ease-in-out infinite; }
  &.is-completed .embedding-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes embed-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(6, 182, 212, 0); }
}

.embedding-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(6, 182, 212, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.embedding-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(6, 182, 212, 0.15);
  background: rgba(6, 182, 212, 0.05);

  .embedding-icon { width: 11px; height: 11px; color: rgba(6, 182, 212, 0.6); }
  .embedding-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(6, 182, 212, 0.7); flex: 1; }
}

.dim-badge {
  display: flex;
  align-items: baseline;
  gap: 2px;
  background: rgba(6, 182, 212, 0.15);
  border: 1px solid rgba(6, 182, 212, 0.3);
  border-radius: 10px;
  padding: 1px 6px;

  .dim-value { font-size: 10px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace; }
  .dim-unit { font-size: 7px; font-weight: 600; color: rgba(6, 182, 212, 0.6); text-transform: uppercase; letter-spacing: 0.05em; }
}

.embedding-stats {
  display: flex;
  padding: 8px 10px;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;

  .stat-value { font-size: 13px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 8px; color: rgba(255, 255, 255, 0.3); text-transform: uppercase; letter-spacing: 0.08em; }
}

.vector-preview {
  padding: 6px 8px;

  .vector-label { font-size: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(6, 182, 212, 0.5); margin-bottom: 4px; }
}

.vector-bars { display: flex; flex-direction: column; gap: 2px; }

.vector-bar-row {
  display: flex;
  align-items: center;
  gap: 6px;

  .vec-index { font-size: 8px; font-weight: 700; color: rgba(6, 182, 212, 0.4); font-family: 'JetBrains Mono', monospace; min-width: 16px; }
  .vec-dims { display: flex; align-items: center; gap: 2px; flex: 1; }
  .vec-val { font-size: 8px; font-family: 'JetBrains Mono', monospace; padding: 1px 3px; border-radius: 2px; min-width: 28px; text-align: center; }
  .vec-more { font-size: 8px; color: rgba(6, 182, 212, 0.3); }
}

.val-high { color: #22d3ee; background: rgba(34, 211, 238, 0.1); }
.val-pos { color: rgba(34, 211, 238, 0.7); }
.val-neg { color: rgba(248, 113, 113, 0.7); }
.val-low { color: rgba(248, 113, 113, 0.4); }
.val-zero { color: rgba(255, 255, 255, 0.2); }

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(6, 182, 212, 0.1); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.result-count { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(6, 182, 212, 0.6); margin-left: auto; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; border: 1px solid; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; .badge-icon { width: 11px; height: 11px; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 10px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); } }
.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 4px; }
.info-row { display: flex; align-items: center; gap: 6px; .info-label { font-size: 10px; color: rgba(255, 255, 255, 0.4); } .info-value { font-size: 11px; color: rgba(255, 255, 255, 0.7); font-family: 'JetBrains Mono', monospace; } }
.preview-row .preview-text { font-size: 10px; color: rgba(255, 255, 255, 0.6); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
:deep(.el-select), :deep(.el-input), :deep(.el-input-number) { width: 100%; .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; border-radius: 6px; } .el-input__inner { color: var(--node-text, #e5e5e5) !important; font-size: 12px !important; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: rgba(10, 10, 18, 0.95); border: 2px solid v-bind(nodeColor); border-radius: 50%; &:hover { background: v-bind(nodeColor); transform: scale(1.3); } }
:global(.dark) { .embedding-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #06b6d4; --node-text: #e5e5e5; } }
:global(.light) { .embedding-node { --node-bg: #fff; --node-border: #06b6d4; --node-text: #1e1e2e; } }
</style>
