<template>
  <div class="config-form">
    <el-form :model="localData" label-position="top" size="small">
      <el-form-item label="节点名称">
        <el-input v-model="localData.label" @change="syncEmit" />
      </el-form-item>
      <el-form-item label="输入方式">
        <el-radio-group v-model="localData.inputMode" @change="syncEmit">
          <el-radio value="upload">本地上传</el-radio>
          <el-radio value="url">公网 URL</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="localData.inputMode === 'upload'" label="视频文件">
        <el-upload :auto-upload="false" :show-file-list="false" accept="video/*" :on-change="onFile">
          <el-button type="primary" :loading="uploading">选择视频</el-button>
        </el-upload>
        <div v-if="localData.public_url" class="hint">{{ localData.public_url }}</div>
      </el-form-item>
      <el-form-item v-else label="视频 URL">
        <el-input v-model="localData.video_input" placeholder="https://..." @change="syncEmit" />
      </el-form-item>
    </el-form>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadMedia } from '@/api/workflow'

const props = defineProps({ modelValue: { type: Object, default: () => ({}) } })
const emit = defineEmits(['update:modelValue', 'change'])
const uploading = ref(false)
const localData = ref(normalize(props.modelValue))

function normalize(v) {
  return {
    label: v?.label || '上传视频',
    inputMode: v?.inputMode || 'upload',
    video_input: v?.video_input || v?.public_url || '',
    media_id: v?.media_id || '',
    public_url: v?.public_url || '',
  }
}

watch(() => props.modelValue, (v) => { localData.value = normalize(v) }, { deep: true })

function syncEmit() {
  const payload = { ...localData.value }
  if (payload.public_url) payload.video_input = payload.public_url
  emit('update:modelValue', payload)
  emit('change', payload)
}

async function onFile(f) {
  const file = f?.raw
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadMedia(file)
    const data = res?.data || res
    const meta = data?.data || data
    localData.value.media_id = meta.media_id
    localData.value.public_url = meta.public_url
    localData.value.video_input = meta.public_url
    ElMessage.success('上传成功')
    syncEmit()
  } catch (e) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>
<style scoped>.hint { font-size: 12px; color: #64748b; word-break: break-all; margin-top: 4px; }</style>
