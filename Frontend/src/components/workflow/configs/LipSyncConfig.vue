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
      <el-form-item label="源视频绑定">
        <el-input
          v-model="localData.video_input"
          placeholder="{source_video_url}"
          @change="syncEmit"
        />
      </el-form-item>
      <el-form-item label="配音音频绑定">
        <el-input
          v-model="localData.audio_input"
          placeholder="{dubbed_audio_url}"
          @change="syncEmit"
        />
      </el-form-item>
      <el-form-item label="启用 VideoRetalk">
        <el-switch
          v-model="localData.lip_sync"
          @change="syncEmit"
        />
      </el-form-item>
      <el-form-item label="人脸参考图 URL">
        <el-input
          v-model="localData.face_ref_image_url"
          placeholder="可选"
          @change="syncEmit"
        />
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
    label: v?.label || '口型同步',
    target_language: v?.target_language || 'en',
    video_input: v?.video_input || '{source_video_url}',
    audio_input: v?.audio_input || '{dubbed_audio_url}',
    lip_sync: v?.lip_sync ?? true,
    face_ref_image_url: v?.face_ref_image_url || '',
  }
}
watch(() => props.modelValue, (v) => { localData.value = normalize(v) }, { deep: true })
function syncEmit() { emit('update:modelValue', { ...localData.value }); emit('change', { ...localData.value }) }
</script>
