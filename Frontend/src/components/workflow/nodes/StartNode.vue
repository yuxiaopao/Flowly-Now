<template>
  <div
    class="start-end-node"
    :class="[nodeType, { selected }]"
    @click.stop="handleSelect"
  >
    <Handle
      type="source"
      :position="Position.Right"
    />
    <div class="node-inner">
      <div class="node-icon-wrapper">
        <component
          :is="icon"
          class="node-icon"
        />
      </div>
      <div class="node-text">
        <span class="node-label">{{ displayLabel }}</span>
        <span class="node-sub">{{ subText }}</span>
      </div>
    </div>
    <Handle
      type="target"
      :position="Position.Left"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { PlayCircle, Circle } from 'lucide-vue-next'
import { getBoundaryNodeLabel } from '@/config/dataTransformOperations'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const nodeType = computed(() => props.data?.nodeType || 'start')
const icon = computed(() => nodeType.value === 'start' ? PlayCircle : Circle)
const subText = computed(() => nodeType.value === 'start' ? '工作流入口' : '工作流终点')
const displayLabel = computed(() => getBoundaryNodeLabel(props.data?.label, nodeType.value))

function handleSelect() {
  emit('select')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.start-end-node {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 140px;
  min-height: 48px;
  border-radius: 12px;
  border: 2px solid;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.start {
    background: linear-gradient(145deg, #052e16 0%, #000 100%);
    border-color: #10b981;
    box-shadow:
      0 0 0 1px rgba(16, 185, 129, 0.15),
      0 4px 16px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);

    .node-icon { color: #10b981; }
    .node-label { color: #e5e5e5; }
    .node-sub { color: rgba(16, 185, 129, 0.6); }
  }

  &.end {
    background: linear-gradient(145deg, #450a0a 0%, #000 100%);
    border-color: #ef4444;
    box-shadow:
      0 0 0 1px rgba(239, 68, 68, 0.15),
      0 4px 16px rgba(0, 0, 0, 0.5),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);

    .node-icon { color: #ef4444; }
    .node-label { color: #e5e5e5; }
    .node-sub { color: rgba(239, 68, 68, 0.6); }
  }

  &.selected {
    transform: scale(1.03);
    box-shadow:
      0 8px 24px rgba(0, 0, 0, 0.5),
      0 0 0 3px rgba(255, 255, 255, 0.1);
  }

  &:hover:not(.selected) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
  }
}

.node-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
}

.node-icon-wrapper {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.node-icon {
  width: 18px;
  height: 18px;
}

.node-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.node-label {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.node-sub {
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: #0a0a0a;
  border: 2px solid;
  border-radius: 50%;

  .start & { border-color: #10b981; }
  .end & { border-color: #ef4444; }

  &:hover { transform: scale(1.3); }
}

// Theme: light
:global(.light) {
  .start-end-node.start {
    background: linear-gradient(145deg, #ecfdf5 0%, #fff 100%);
    border-color: #10b981;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15);
    .node-label { color: #111827; }
    .node-sub { color: rgba(16, 185, 129, 0.7); }
    .node-icon { color: #10b981; }
  }
  .start-end-node.end {
    background: linear-gradient(145deg, #fef2f2 0%, #fff 100%);
    border-color: #ef4444;
    box-shadow: 0 2px 8px rgba(239, 68, 68, 0.15);
    .node-label { color: #111827; }
    .node-sub { color: rgba(239, 68, 68, 0.7); }
    .node-icon { color: #ef4444; }
  }
  :deep(.vue-flow__handle) { background: #fff; }
}
</style>
