<template>
  <VideoPipelineStepNode
    :id="id"
    :data="data"
    :selected="selected"
    node-type="subtitle_burn"
    default-label="字幕烧录"
    :show-video-preview="true"
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
