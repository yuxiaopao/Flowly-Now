<template>
  <div
    class="core-node merge-node"
    :class="{ selected }"
    @click="$emit('select')"
  >
    <Handle
      id="input1"
      type="target"
      :position="Position.Left"
      :style="{ top: '30%' }"
    />
    <Handle
      id="input2"
      type="target"
      :position="Position.Left"
      :style="{ top: '70%' }"
    />
    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" compact />
    </div>
    <div class="node-body">
      <div
        class="node-icon-wrapper"
        :style="{ backgroundColor: nodeColor + '15' }"
      >
        <component
          :is="nodeIcon"
          :size="18"
          :style="{ color: nodeColor }"
        />
      </div>
      <div class="node-info">
        <div class="node-label">
          {{ data.label || nodeLabel }}
        </div>
        <div class="node-mode">
          {{ modeLabel }}
        </div>
      </div>
    </div>
    <Handle
      id="output"
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { GitMerge } from 'lucide-vue-next'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'merge'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

defineEmits(['select'])

const config = computed(() => props.data.config || {})

const modeLabel = computed(() => {
  const mode = config.value.mode || 'combine'
  const modes = {
    combine: '合并',
    override: '覆盖',
    zip: '配对'
  }
  return modes[mode] || mode
})


</script>

<style lang="scss" scoped>
.core-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid v-bind(nodeColor);
  border-radius: 12px;
  min-width: 160px;
  max-width: 220px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;

  &.selected {
    border-color: v-bind(nodeColor);
    box-shadow: 0 0 0 3px v-bind(nodeColor + '40'), 0 8px 24px rgba(0, 0, 0, 0.4);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    border-color: v-bind(nodeColor);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.2);
    transform: translateY(-1px);
  }
}

.node-header {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.node-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border: 1px solid;
  border-radius: 12px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;

  .badge-icon {
    width: 10px;
    height: 10px;
  }
}

.node-body {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
}

.node-icon-wrapper {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--node-text, #e2e8f0);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-mode {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 2px;
}

:deep(.vue-flow__handle) {
  width: 8px;
  height: 8px;
  background: var(--node-bg, #1e1e2e);
  border: 2px solid v-bind(nodeColor);
  border-radius: 50%;

  &:hover {
    background: v-bind(nodeColor);
    transform: scale(1.3);
  }
}
</style>
