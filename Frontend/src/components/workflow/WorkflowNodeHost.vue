<template>
  <div class="workflow-node-host">
    <component
      :is="nodeComponent"
      :id="id"
      :data="data"
      :selected="selected"
      v-bind="extraProps"
      @select="forwardSelect"
    />
    <NodeExecutionResult
      :node-id="id"
      :data="data"
    />
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { WORKFLOW_SELECT_NODE_KEY } from '@/config/workflowCanvas'
import NodeExecutionResult from '@/components/workflow/NodeExecutionResult.vue'

const props = defineProps({
  nodeComponent: {
    type: [Object, Function],
    required: true,
  },
  id: {
    type: String,
    required: true,
  },
  data: {
    type: Object,
    default: () => ({}),
  },
  selected: {
    type: Boolean,
    default: false,
  },
  extraProps: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['select'])

const workflowSelectNode = inject(WORKFLOW_SELECT_NODE_KEY, null)

function forwardSelect(nodeId) {
  const resolvedId = nodeId || props.id
  if (!resolvedId) return

  if (workflowSelectNode) {
    workflowSelectNode(resolvedId)
    return
  }

  emit('select', resolvedId)
}
</script>

<style scoped>
.workflow-node-host {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}
</style>
