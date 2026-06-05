<template>
  <div
    class="domain-node memory-node"
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
        <MemoryStick
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">记忆管理</span>
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
        v-if="localConfig.memoryType || localConfig.storeType"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.memoryType || localConfig.storeType || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description || localConfig.memoryScope"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description || localConfig.memoryScope, 35) }}</span>
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
          <span>处理中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="memoryTokens > 0"
            class="token-badge"
          >{{ formatTokens(memoryTokens) }}</span>
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
      class="memory-preview"
    >
      <div class="memory-header">
        <Brain class="memory-icon" />
        <span class="memory-label">记忆摘要</span>
        <span class="memory-type-badge">{{ localConfig.memoryType || 'buffer' }}</span>
      </div>
      <div class="memory-stats">
        <div class="stat-item">
          <span class="stat-value">{{ memoryTokens > 0 ? formatTokens(memoryTokens) : '—' }}</span>
          <span class="stat-label">Token</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ memoryCount > 0 ? memoryCount : '—' }}</span>
          <span class="stat-label">记忆条</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ localConfig.memoryScope || 'session' }}</span>
          <span class="stat-label">范围</span>
        </div>
      </div>
      <div
        v-if="memoryPreview"
        class="memory-preview-text"
      >
        <span class="preview-snippet">{{ truncate(memoryPreview, 100) }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">记忆类型</label>
          <el-select
            v-model="localConfig.memoryType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="buffer"
              label="Buffer Memory"
            />
            <el-option
              value="buffer_window"
              label="Buffer Window"
            />
            <el-option
              value="entity"
              label="Entity Memory"
            />
            <el-option
              value="kg"
              label="Knowledge Graph"
            />
            <el-option
              value="summary"
              label="Summary Memory"
            />
            <el-option
              value="vectorstore"
              label="Vector Store"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">存储类型</label>
          <el-input
            v-model="localConfig.storeType"
            size="small"
            placeholder="存储类型"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">记忆范围</label>
          <el-input
            v-model="localConfig.memoryScope"
            size="small"
            placeholder="例如: session, user, global"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">最大历史数</label>
          <el-input-number
            v-model="localConfig.maxHistory"
            :min="1"
            :max="1000"
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
            placeholder="记忆描述..."
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
import { MemoryStick, ChevronDown, Brain, Loader } from 'lucide-vue-next'
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
const nodeColor = '#8b5cf6'

const localName = ref(props.data.label || '记忆管理')
const localConfig = ref({
  memoryType: props.data.config?.memoryType || 'buffer',
  storeType: props.data.config?.storeType || '',
  memoryScope: props.data.config?.memoryScope || '',
  maxHistory: props.data.config?.maxHistory || 50,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const memoryTokens = computed(() => {
  if (!nodeOutput.value) return 0
  return nodeOutput.value.tokens || nodeOutput.value.tokenCount || nodeOutput.value.token_count || 0
})

const memoryCount = computed(() => {
  if (!nodeOutput.value) return 0
  return nodeOutput.value.count || nodeOutput.value.memoryCount || nodeOutput.value.memories || 0
})

const memoryPreview = computed(() => {
  if (!nodeOutput.value) return null
  const text = nodeOutput.value.summary || nodeOutput.value.preview || nodeOutput.value.text || nodeOutput.value.content || ''
  return text || null
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function formatTokens(n) {
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return n.toString()
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '记忆管理'
    localConfig.value = { memoryType: d.config?.memoryType || 'buffer', storeType: d.config?.storeType || '', memoryScope: d.config?.memoryScope || '', maxHistory: d.config?.maxHistory || 50, description: d.config?.description || '', ...d.config }
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
.memory-node {
  &.is-running { animation: mem-pulse 1.8s ease-in-out infinite; }
  &.is-completed .memory-preview { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes mem-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(139, 92, 246, 0); }
}

.memory-preview {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(139, 92, 246, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.memory-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.15);
  background: rgba(139, 92, 246, 0.05);

  .memory-icon { width: 11px; height: 11px; color: rgba(139, 92, 246, 0.6); }
  .memory-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(139, 92, 246, 0.7); flex: 1; }
}

.memory-type-badge {
  font-size: 9px;
  font-weight: 600;
  background: rgba(139, 92, 246, 0.15);
  color: #a78bfa;
  padding: 1px 6px;
  border-radius: 10px;
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.memory-stats {
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

  .stat-value { font-size: 14px; font-weight: 700; color: #a78bfa; font-family: 'JetBrains Mono', monospace; }
  .stat-label { font-size: 8px; color: rgba(255, 255, 255, 0.3); text-transform: uppercase; letter-spacing: 0.08em; }
}

.memory-preview-text {
  padding: 8px 10px;

  .preview-snippet { font-size: 10px; color: rgba(255, 255, 255, 0.6); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
}

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.token-badge { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(139, 92, 246, 0.6); margin-left: auto; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

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

  &.selected { box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent); transform: translateY(-1px); }
}

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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #8b5cf6; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #8b5cf6; --node-text: #1e1e2e; } }
</style>
