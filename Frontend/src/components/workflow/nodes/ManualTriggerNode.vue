<template>
  <div
    class="trigger-node manual-trigger-node"
    :class="{ selected }"
    @click="$emit('select')"
  >
    <div class="node-header">
      <NodeTypeBadge
        :node-type="NODE_TYPE"
        compact
      />
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
        <div
          v-if="config.description"
          class="node-desc"
        >
          {{ config.description }}
        </div>
        <div
          v-if="hasSchema"
          class="node-schema"
        >
          <span class="schema-badge">有输入参数</span>
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
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'manual'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

defineEmits(['select'])

const config = computed(() => props.data.config || {})
const hasSchema = computed(() => {
  const schema = config.value.inputSchema
  return schema && Object.keys(schema).length > 0
})


</script>

<style lang="scss" scoped>
.trigger-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid v-bind(nodeColor);
  border-radius: 12px;
  min-width: 180px;
  max-width: 260px;
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
    box-shadow: 0 6px 20px rgba(16, 185, 129, 0.2);
    transform: translateY(-1px);
  }
}

.node-header {
  padding: 8px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.node-type-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
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
  gap: 10px;
  padding: 10px 12px;
}

.node-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 8px;
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
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text, #e2e8f0);
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-desc {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-schema {
  margin-top: 4px;
}

.schema-badge {
  display: inline-block;
  font-size: 9px;
  padding: 2px 6px;
  background: rgba(16, 185, 129, 0.15);
  color: v-bind(nodeColor);
  border-radius: 4px;
  font-weight: 600;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: var(--node-bg, #1e1e2e);
  border: 2px solid v-bind(nodeColor);
  border-radius: 50%;

  &:hover {
    background: v-bind(nodeColor);
    transform: scale(1.3);
  }
}
</style>
