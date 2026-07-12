<template>
  <VideoPipelineStepNode
    :id="id"
    :data="data"
    :selected="selected"
    node-type="subtitle_translate"
    default-label="字幕翻译"
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
