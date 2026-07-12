<template>
  <component
    :is="nodeComponent"
    :id="id"
    :data="data"
    :selected="selected"
    v-bind="extraProps"
    @select="forwardSelect"
  />
</template>

<script setup>
import { inject } from 'vue'
import { WORKFLOW_SELECT_NODE_KEY } from '@/config/workflowCanvas'

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
