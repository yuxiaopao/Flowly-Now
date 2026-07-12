<template>
  <div
    class="loop-node"
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
        name="node-label"
        v-model="localName"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div class="loop-mode-display">
        <span class="mode-label">模式</span>
        <span class="mode-value">{{ displayMode }}</span>
      </div>
      <div
        v-if="localConfig.maxIterations"
        class="loop-count-display"
      >
        <span class="count-label">最大次数</span>
        <span class="count-value">{{ localConfig.maxIterations }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">循环模式</label>
          <el-select
            v-model="localConfig.mode"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="for"
              label="For 循环"
            />
            <el-option
              value="while"
              label="While 循环"
            />
            <el-option
              value="foreach"
              label="ForEach 循环"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">最大迭代次数</label>
          <el-input-number
            v-model="localConfig.maxIterations"
            :min="1"
            :max="10000"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div
          v-if="localConfig.mode === 'for'"
          class="config-section"
        >
          <label class="config-label">起始值</label>
          <el-input-number
            v-model="localConfig.start"
            :min="0"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div
          v-if="localConfig.mode === 'for'"
          class="config-section"
        >
          <label class="config-label">结束值</label>
          <el-input-number
            v-model="localConfig.end"
            :min="0"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>

        <div
          v-if="localConfig.mode === 'while'"
          class="config-section"
        >
          <label class="config-label">循环条件</label>
          <el-input
            v-model="localConfig.condition"
            size="small"
            placeholder="例如: i < 10"
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      id="body"
      type="source"
      :position="Position.Right"
      style="top: 70%"
    />
    <Handle
      id="done"
      type="source"
      :position="Position.Right"
      style="top: 85%"
    />

    <!-- Result Zone -->
    <div
      v-if="isRunning || isCompleted || isFailed"
      class="result-zone"
      :class="{ 'zone-running': isRunning, 'zone-completed': isCompleted, 'zone-failed': isFailed }"
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
        class="result-summary"
      >
        <Check class="result-icon" />
        <span>{{ localConfig.maxIterations }} 次</span>
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
import { RefreshCw, ChevronDown, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'loop'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const isExpanded = ref(false)
const localName = ref(props.data.label || '循环')
const localConfig = ref({
  mode: props.data.config?.mode || 'for',
  maxIterations: props.data.config?.maxIterations || 10,
  start: props.data.config?.start || 0,
  end: props.data.config?.end || 10,
  condition: props.data.config?.condition || ''
})

const displayMode = computed(() => {
  const modes = { for: 'For 循环', while: 'While 循环', foreach: 'ForEach 循环' }
  return modes[localConfig.value.mode] || '循环'
})

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '循环'
    localConfig.value = {
      mode: d.config?.mode || 'for',
      maxIterations: d.config?.maxIterations || 10,
      start: d.config?.start || 0,
      end: d.config?.end || 10,
      condition: d.config?.condition || '',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
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
.loop-node {
  background: var(--node-bg, #1c1400);
  border: 2px solid var(--node-border, #f59e0b);
  border-radius: 12px;
  min-width: 180px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    border-color: var(--node-border, #f59e0b);
    box-shadow: 0 8px 32px rgba(245, 158, 11, 0.25), 0 0 0 2px rgba(245, 158, 11, 0.3);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    border-color: #fbbf24;
    box-shadow: 0 6px 24px rgba(245, 158, 11, 0.15);
    transform: translateY(-1px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(245, 158, 11, 0.08);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(245, 158, 11, 0.2);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #f59e0b;

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
    border-color: rgba(245, 158, 11, 0.5);
    background: rgba(245, 158, 11, 0.05);
  }
}

.compact-view {
  display: flex;
  gap: 8px;
  padding: 0 12px 10px;
}

.loop-mode-display,
.loop-count-display {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 5px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 6px;
}

.mode-label,
.count-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.35);
}

.mode-value {
  font-size: 11px;
  font-weight: 500;
  color: #f59e0b;
}

.count-value {
  font-size: 12px;
  font-weight: 600;
  color: #fbbf24;
  font-family: 'JetBrains Mono', monospace;
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
  background: var(--node-bg, #1c1400);
  border: 2px solid var(--node-border, #f59e0b);
  border-radius: 50%;

  &:hover {
    background: #f59e0b;
    transform: scale(1.3);
  }
}

:global(.dark) {
  .loop-node {
    --node-bg: #1c1400;
    --node-border: #f59e0b;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .loop-node {
    --node-bg: #fff;
    --node-border: #f59e0b;
    --node-text: #1c1400;
  }
}

// Result Zone
.result-zone {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;

  &.zone-running {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #3b82f6;
  }

  &.zone-completed {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
  }

  &.zone-failed {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
  }

  .result-icon {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }

  .result-summary, .result-error {
    display: flex;
    align-items: center;
    gap: 6px;
    word-break: break-all;
    font-family: 'JetBrains Mono', monospace;
  }
}

.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
