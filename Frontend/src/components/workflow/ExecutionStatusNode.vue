<template>
  <div
    class="exec-status-node"
    :class="[`is-${status}`, { selected: selected }]"
  >
    <Handle
      type="target"
      :position="Position.Left"
      :connectable="false"
    />
    <span class="exec-status-node__pulse" />
    <span class="exec-status-node__dot" />
    <div class="exec-status-node__body">
      <span
        class="exec-status-node__label"
        :title="label"
      >{{ label }}</span>
      <span class="exec-status-node__meta">
        <span>{{ statusLabel }}</span>
        <span v-if="duration">{{ duration }}s</span>
      </span>
    </div>
    <Handle
      type="source"
      :position="Position.Right"
      :connectable="false"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'

const props = defineProps({
  id: {
    type: String,
    default: '',
  },
  data: {
    type: Object,
    default: () => ({}),
  },
  selected: {
    type: Boolean,
    default: false,
  },
})

const label = computed(() => props.data.label || props.data.name || props.id || '节点')
const status = computed(() => props.data.status || 'pending')
const duration = computed(() => props.data.duration || '')

const statusLabel = computed(() => {
  const map = {
    pending: '等待',
    queued: '排队',
    running: '运行',
    completed: '完成',
    failed: '失败',
    skipped: '跳过',
    cancelled: '取消',
  }
  return map[status.value] || status.value
})
</script>

<style lang="scss" scoped>
.exec-status-node {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 148px;
  max-width: 196px;
  padding: 8px 10px;
  border-radius: 10px;
  background: var(--bg-secondary, #16161e);
  border: 1px solid var(--border-primary, #2a2a36);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.28);
  color: var(--text-primary);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;

  &.selected {
    box-shadow: 0 0 0 1px color-mix(in srgb, var(--color-primary, #3b82f6) 55%, transparent),
      0 8px 20px rgba(0, 0, 0, 0.28);
  }

  &:hover {
    border-color: color-mix(in srgb, var(--text-primary) 28%, var(--border-primary));
  }
}

.exec-status-node__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background: #64748b;
}

.exec-status-node__pulse {
  display: none;
  position: absolute;
  left: 10px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.exec-status-node__body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.exec-status-node__label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.25;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exec-status-node__meta {
  display: flex;
  gap: 8px;
  font-size: 10px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
}

.is-pending .exec-status-node__dot { background: #64748b; }
.is-queued .exec-status-node__dot { background: #94a3b8; }

.is-running {
  border-color: #f59e0b;
  background: color-mix(in srgb, #f59e0b 12%, var(--bg-secondary, #16161e));

  .exec-status-node__dot {
    background: #f59e0b;
  }

  .exec-status-node__pulse {
    display: block;
    background: #f59e0b;
    animation: exec-pulse 1.4s ease-out infinite;
  }
}

.is-completed {
  border-color: #22c55e;

  .exec-status-node__dot { background: #22c55e; }
}

.is-failed {
  border-color: #ef4444;
  background: color-mix(in srgb, #ef4444 12%, var(--bg-secondary, #16161e));

  .exec-status-node__dot { background: #ef4444; }
}

.is-skipped .exec-status-node__dot,
.is-cancelled .exec-status-node__dot {
  background: #94a3b8;
}

@keyframes exec-pulse {
  0% { transform: scale(1); opacity: 0.7; }
  100% { transform: scale(3.4); opacity: 0; }
}
</style>
