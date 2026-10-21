<template>
  <div class="config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <el-form-item label="节点名称">
        <el-input
          v-model="localData.label"
          @change="syncEmit"
        />
      </el-form-item>
      <el-form-item label="目标语言">
        <el-select
          v-model="localData.target_language"
          @change="syncEmit"
        >
          <el-option
            v-for="o in langs"
            :key="o.v"
            :label="o.l"
            :value="o.v"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="视频绑定">
        <el-input
          v-model="localData.video_input"
          placeholder="{video_url}"
          @change="syncEmit"
        />
      </el-form-item>
      <el-form-item label="字幕格式">
        <el-select
          v-model="localData.subtitle_format"
          @change="syncEmit"
        >
          <el-option
            label="SRT"
            value="srt"
          />
          <el-option
            label="VTT"
            value="vtt"
          />
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
  { v: 'en', l: 'English' }, { v: 'ja', l: '日本語' }, { v: 'ko', l: '한국어' },
]
const localData = ref(normalize(props.modelValue))
function normalize(v) {
  return {
    label: v?.label || '字幕烧录',
    target_language: v?.target_language || 'en',
    video_input: v?.video_input || '{video_url}',
    subtitle_format: v?.subtitle_format || 'srt',
  }
}
watch(() => props.modelValue, (v) => { localData.value = normalize(v) }, { deep: true })
function syncEmit() { emit('update:modelValue', { ...localData.value }); emit('change', { ...localData.value }) }
</script>
