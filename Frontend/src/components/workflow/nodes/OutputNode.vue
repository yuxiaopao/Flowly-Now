<template>
  <div
    class="output-node"
    :class="{ selected, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <div class="node-inner">
      <div class="node-icon-wrapper">
        <LogOut class="node-icon" />
      </div>
      <div class="node-text">
        <span class="node-type-label">输出</span>
        <span class="node-label">{{ localLabel || data.label || '输出结果' }}</span>
      </div>
    </div>

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
        <span>{{ truncate(String(nodeOutput?.data || '完成'), 20) }}</span>
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
import { ref, computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { LogOut, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const localLabel = ref(props.data?.label || '')

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function handleSelect() {
  emit('select')
}
</script>

<style lang="scss" scoped>
.output-node {
  background: linear-gradient(145deg, #14532d 0%, #000 100%);
  border: 2px solid #84cc16;
  border-radius: 12px;
  min-width: 140px;
  box-shadow:
    0 0 0 1px rgba(132, 204, 22, 0.15),
    0 4px 16px rgba(0, 0, 0, 0.5);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.selected {
    transform: scale(1.03);
    box-shadow: 0 8px 24px rgba(132, 204, 22, 0.2), 0 0 0 3px rgba(132, 204, 22, 0.2);
  }

  &:hover:not(.selected) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(132, 204, 22, 0.15);
  }

  :deep(.vue-flow__handle) {
    width: 10px; height: 10px;
    background: #0a0a0a;
    border: 2px solid #84cc16;
    border-radius: 50%;
    &:hover { background: #84cc16; transform: scale(1.3); }
  }
}

.node-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
}

.node-icon-wrapper {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(132, 204, 22, 0.15);
  border: 1px solid rgba(132, 204, 22, 0.3);
  border-radius: 8px;
  flex-shrink: 0;
}

.node-icon {
  width: 16px; height: 16px;
  color: #84cc16;
}

.node-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.node-type-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #84cc16;
  opacity: 0.8;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: #e5e5e5;
}

:global(.light) {
  .output-node {
    background: linear-gradient(145deg, #f7fee7 0%, #fff 100%);
    border-color: #84cc16;
    box-shadow: 0 2px 8px rgba(132, 204, 22, 0.15);
    .node-label { color: #111827; }
    :deep(.vue-flow__handle) { background: #fff; }
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
