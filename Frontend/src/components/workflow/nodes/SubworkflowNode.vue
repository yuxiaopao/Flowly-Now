<template>
  <div
    class="subworkflow-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <div class="node-type-badge">
        <GitMerge class="badge-icon" />
        <span>子工作流</span>
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
        v-if="localConfig.subworkflowName"
        class="subworkflow-info"
      >
        <Layers class="info-icon" />
        <span class="subworkflow-name">{{ localConfig.subworkflowName }}</span>
      </div>
      <div
        v-if="localConfig.version"
        class="version-display"
      >
        <Tag class="version-icon" />
        <span class="version-badge">v{{ localConfig.version }}</span>
      </div>
      <div
        class="execution-mode"
        :class="localConfig.executionMode || 'sync'"
      >
        {{ (localConfig.executionMode || 'sync') === 'sync' ? '同步' : '异步' }}
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">子工作流名称</label>
          <el-input
            v-model="localConfig.subworkflowName"
            size="small"
            placeholder="选择或输入子工作流"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">版本</label>
          <el-input-number
            v-model="localConfig.version"
            :min="1"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">执行模式</label>
          <el-select
            v-model="localConfig.executionMode"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="sync"
              label="同步"
            />
            <el-option
              value="async"
              label="异步"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">超时时间 (秒)</label>
          <el-input-number
            v-model="localConfig.timeout"
            :min="0"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />

    <!-- Result Zone -->
    <div
      v-if="isRunning || isCompleted || isFailed"
      class="result-zone"
    >
      <div
        v-if="isRunning"
        class="result-running"
      >
        <Loader class="result-icon spinning" />
        <span>执行中...</span>
      </div>
      <div
        v-else-if="isCompleted"
        class="result-done"
      >
        <Check class="result-icon" />
        <span>{{ resultSummary }}</span>
      </div>
      <div
        v-else-if="isFailed"
        class="result-error"
      >
        <X class="result-icon" />
        <span>{{ nodeOutput?.error || '执行失败' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { GitMerge, ChevronDown, Layers, Tag, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const resultSummary = computed(() => {
  if (!nodeOutput.value) return '完成'
  return nodeOutput.value.execution_id || '完成'
})

const isExpanded = ref(false)
const localName = ref(props.data.label || '子工作流')
const localConfig = ref({
  subworkflowName: props.data.config?.subworkflowName || '',
  version: props.data.config?.version || 1,
  executionMode: props.data.config?.executionMode || 'sync',
  timeout: props.data.config?.timeout || 0
})

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '子工作流'
    localConfig.value = {
      subworkflowName: d.config?.subworkflowName || '',
      version: d.config?.version || 1,
      executionMode: d.config?.executionMode || 'sync',
      timeout: d.config?.timeout || 0,
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  isExpanded.value = !isExpanded.value
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
.subworkflow-node {
  background: var(--node-bg, #1e1b4b);
  border: 2px solid var(--node-border, #8b5cf6);
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.2);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    border-color: var(--node-border, #8b5cf6);
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.3), 0 0 0 2px rgba(139, 92, 246, 0.3);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    border-color: #a78bfa;
    box-shadow: 0 6px 24px rgba(139, 92, 246, 0.25);
    transform: translateY(-1px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(139, 92, 246, 0.08);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(139, 92, 246, 0.2);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #a78bfa;

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
    border-color: rgba(139, 92, 246, 0.5);
    background: rgba(139, 92, 246, 0.05);
  }
}

.compact-view {
  padding: 0 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.subworkflow-info {
  display: flex;
  align-items: center;
  gap: 6px;

  .info-icon {
    width: 12px;
    height: 12px;
    color: #a78bfa;
  }

  .subworkflow-name {
    font-size: 11px;
    color: #c4b5fd;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.version-display {
  display: flex;
  align-items: center;
  gap: 4px;

  .version-icon {
    width: 10px;
    height: 10px;
    color: #a78bfa;
  }

  .version-badge {
    font-size: 10px;
    color: #a78bfa;
    background: rgba(139, 92, 246, 0.2);
    padding: 1px 4px;
    border-radius: 4px;
  }
}

.execution-mode {
  align-self: flex-start;
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;

  &.sync {
    background: rgba(139, 92, 246, 0.2);
    color: #a78bfa;
  }

  &.async {
    background: rgba(245, 158, 11, 0.2);
    color: #fbbf24;
  }
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
  max-height: 400px;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: var(--node-bg, #1e1b4b);
  border: 2px solid var(--node-border, #8b5cf6);
  border-radius: 50%;

  &:hover {
    background: #8b5cf6;
    transform: scale(1.3);
  }
}

:global(.dark) {
  .subworkflow-node {
    --node-bg: #1e1b4b;
    --node-border: #8b5cf6;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .subworkflow-node {
    --node-bg: #f5f3ff;
    --node-border: #8b5cf6;
    --node-text: #1e1b4b;
  }
}

.result-zone {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  .result-icon { width: 12px; height: 12px; flex-shrink: 0; }
  &.result-running { background: rgba(59,130,246,.1); border: 1px solid rgba(59,130,246,.3); color: #3b82f6; }
  &.result-done { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); color: #10b981; }
  &.result-error { background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); color: #ef4444; }
}
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
