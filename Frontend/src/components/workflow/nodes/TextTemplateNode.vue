<template>
  <div
    class="core-node text-template-node"
    :class="{ selected, 'is-completed': isCompleted }"
    @click.stop="$emit('select')"
  >
    <Handle
      type="target"
      :position="Position.Left"
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
        <div class="node-preview">
          {{ preview }}
        </div>
      </div>
    </div>
    <div
      v-if="renderedText"
      class="result-preview"
    >
      {{ renderedText }}
    </div>
    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position, useNodeId } from '@vue-flow/core'
import { FileCode } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import { truncateText } from '@/composables/useNodeResultDisplay'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const NODE_TYPE = 'text_template'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

defineEmits(['select'])

const flowNodeId = useNodeId()
const executionStore = useExecutionStore()
const nodeKey = computed(() => flowNodeId || props.id || '')

const config = computed(() => props.data?.config || {})
const preview = computed(() => truncateText(config.value.template || '{input}', 40))

const nodeStatus = computed(() => executionStore.nodeStatusMap[nodeKey.value])
const nodeOutput = computed(() => executionStore.nodeOutputs[nodeKey.value])
const isCompleted = computed(() => nodeStatus.value === 'completed')
const renderedText = computed(() => {
  const out = nodeOutput.value
  if (!out) return ''
  if (typeof out === 'string') return truncateText(out, 80)
  return truncateText(out.text || out.result || '', 80)
})
</script>

<style lang="scss" scoped>
.core-node {
  background: linear-gradient(145deg, #1e1b4b 0%, #0f172a 100%);
  border: 2px solid v-bind(nodeColor);
  border-radius: 12px;
  min-width: 180px;
  max-width: 260px;
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.15);
  cursor: pointer;
  transition: all 0.25s ease;

  &.selected {
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.35), 0 0 24px rgba(99, 102, 241, 0.25);
  }

  &.is-completed {
    border-color: #22c55e;
    box-shadow: 0 0 16px rgba(34, 197, 94, 0.2);
  }
}

.node-header { padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.node-type-badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px;
  border: 1px solid; border-radius: 12px; font-size: 9px; font-weight: 700;
  .badge-icon { width: 10px; height: 10px; }
}
.node-body { display: flex; gap: 8px; padding: 8px 10px; align-items: center; }
.node-icon-wrapper { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; }
.node-label { font-size: 12px; font-weight: 600; color: #e2e8f0; }
.node-preview { font-size: 10px; color: #94a3b8; margin-top: 2px; font-family: monospace; }
.result-preview {
  margin: 0 10px 10px; padding: 6px 8px; border-radius: 8px;
  background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.25);
  font-size: 10px; color: #c7d2fe; line-height: 1.4;
}
</style>
