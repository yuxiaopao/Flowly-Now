<template>
  <div class="clip-cls-config">
    <ClipClassificationWizard
      :model-value="config"
      @update:model-value="onWizardUpdate"
      @change="onWizardChange"
      @finished="onWizardFinished"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import ClipClassificationWizard from './ClipClassificationWizard.vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const config = computed(() => props.modelValue || {})

function onWizardUpdate(v) {
  emit('update:modelValue', v)
}

function onWizardChange(v) {
  emit('update:modelValue', v)
  emit('change', v)
}

function onWizardFinished() {
  ElMessage.success('CLIP 分类向导已完成')
}
</script>
