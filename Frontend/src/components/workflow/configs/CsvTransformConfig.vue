<template>
  <DataTransformConfig
    :kind="kind"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    @change="$emit('change', $event)"
  />
</template>

<script setup>
import DataTransformConfig from './DataTransformConfig.vue'

defineProps({ modelValue: { type: Object, default: () => ({}) } })
defineEmits(['update:modelValue', 'change'])
const kind = 'csv'
</script>
