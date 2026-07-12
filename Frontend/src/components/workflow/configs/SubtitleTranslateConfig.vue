<template>
  <div class="config-form">
    <el-form :model="localData" label-position="top" size="small">
      <el-form-item label="节点名称">
        <el-input v-model="localData.label" @change="syncEmit" />
      </el-form-item>
      <el-form-item label="源语言">
        <el-select v-model="localData.source_language" @change="syncEmit">
          <el-option v-for="o in langs" :key="o.v" :label="o.l" :value="o.v" />
        </el-select>
      </el-form-item>
      <el-form-item label="目标语言">
        <el-select v-model="localData.target_language" @change="syncEmit">
          <el-option v-for="o in langs" :key="o.v" :label="o.l" :value="o.v" />
        </el-select>
      </el-form-item>
      <el-form-item label="字幕格式">
        <el-select v-model="localData.subtitle_format" @change="syncEmit">
          <el-option label="SRT" value="srt" />
          <el-option label="VTT" value="vtt" />
        </el-select>
      </el-form-item>
    </el-form>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue', 'change'])
const langs = [
  { v: 'zh', l: '中文' }, { v: 'en', l: 'English' }, { v: 'ja', l: '日本語' },
  { v: 'ko', l: '한국어' }, { v: 'es', l: 'Español' }, { v: 'fr', l: 'Français' },
]
const localData = ref(normalize(props.modelValue))
function normalize(v) {
  return {
    label: v?.label || '字幕翻译',
    source_language: v?.source_language || 'zh',
    target_language: v?.target_language || 'en',
    subtitle_format: v?.subtitle_format || 'srt',
  }
}
watch(() => props.modelValue, (v) => { localData.value = normalize(v) }, { deep: true })
function syncEmit() { emit('update:modelValue', { ...localData.value }); emit('change', { ...localData.value }) }
</script>
