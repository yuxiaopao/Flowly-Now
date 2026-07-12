<template>
  <VideoPipelineStepNode
    :id="id"
    :data="data"
    :selected="selected"
    node-type="segment_dubbing"
    default-label="分段配音"
    @select="$emit('select')"
  />
</template>
<script setup>
import VideoPipelineStepNode from './VideoPipelineStepNode.vue'
defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})
defineEmits(['select'])
</script>
