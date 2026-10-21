<template>
  <div class="profiler-config">
    <el-form
      label-position="top"
      size="small"
    >
      <el-form-item label="网站类型">
        <el-select
          :model-value="config.websiteType || 'detection'"
          @update:model-value="patch('websiteType', $event)"
        >
          <el-option
            label="目标检测"
            value="detection"
          />
          <el-option
            label="图像分类"
            value="classification"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="LLM 文案润色">
        <el-switch
          :model-value="Boolean(config.useLlmEnrich)"
          @update:model-value="patch('useLlmEnrich', $event)"
        />
        <p class="hint">
          可选；无 API Key 时自动跳过
        </p>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const config = computed(() => props.modelValue || {})

function patch(key, value) {
  const next = { ...props.modelValue, [key]: value }
  emit('update:modelValue', next)
  emit('change', next)
}
</script>

<style scoped>
.hint { margin: 4px 0 0; font-size: 12px; color: var(--text-secondary, #a1a1aa); }
</style>
