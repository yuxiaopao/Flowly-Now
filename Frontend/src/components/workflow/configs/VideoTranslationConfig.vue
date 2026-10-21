<template>
  <div class="config-form video-translation-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <div class="form-section">
        <h4 class="section-title">
          基本信息
        </h4>
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            placeholder="视频翻译"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="localData.description"
            type="textarea"
            :rows="2"
            placeholder="多语言视频翻译、配音、口型同步与烧录字幕"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          视频输入
        </h4>
        <el-form-item label="输入方式">
          <el-radio-group
            v-model="localData.inputMode"
            @change="handleInputModeChange"
          >
            <el-radio value="upload">
              本地上传
            </el-radio>
            <el-radio value="url">
              公网 URL
            </el-radio>
            <el-radio value="upstream">
              上游绑定
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="localData.inputMode === 'upload'"
          label="上传视频"
        >
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="video/*,.mp4,.mov,.webm,.mkv"
            :on-change="handleFileChange"
          >
            <el-button
              type="primary"
              :loading="uploading"
            >
              {{ uploading ? '上传中...' : '选择视频文件' }}
            </el-button>
          </el-upload>
          <div
            v-if="localData.public_url"
            class="field-hint"
          >
            已上传：{{ localData.public_url }}
          </div>
        </el-form-item>

        <el-form-item
          v-else-if="localData.inputMode === 'url'"
          label="视频 URL"
          required
        >
          <el-input
            v-model="localData.video_input"
            placeholder="https://example.com/video.mp4"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-else
          label="上游视频变量"
        >
          <el-input
            v-model="localData.video_input"
            placeholder="{video_url}"
            @change="handleChange"
          />
          <div class="field-hint">
            绑定上游节点输出的 video_url
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          语言与配音
        </h4>
        <el-form-item label="源语言">
          <el-select
            v-model="localData.source_language"
            @change="handleChange"
          >
            <el-option
              v-for="opt in languageOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标语言（可多选）">
          <el-select
            v-model="localData.target_languages"
            multiple
            @change="handleChange"
          >
            <el-option
              v-for="opt in languageOptions"
              :key="opt.value"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="配音音色 (CosyVoice)">
          <el-select
            v-model="localData.voice"
            @change="handleChange"
          >
            <el-option
              label="longanyang（中文男声）"
              value="longanyang"
            />
            <el-option
              label="longxiaochun（女声）"
              value="longxiaochun"
            />
            <el-option
              label="longlaotie（男声）"
              value="longlaotie"
            />
          </el-select>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          输出选项
        </h4>
        <el-form-item label="字幕格式">
          <el-select
            v-model="localData.subtitle_format"
            @change="handleChange"
          >
            <el-option
              label="SRT"
              value="srt"
            />
            <el-option
              label="VTT"
              value="vtt"
            />
            <el-option
              label="SRT + VTT"
              value="both"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="口型同步 (VideoRetalk)">
          <el-switch
            v-model="localData.lip_sync"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="烧录硬字幕">
          <el-switch
            v-model="localData.burn_subtitles"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="音频更长时扩展视频">
          <el-switch
            v-model="localData.video_extension"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="人脸参考图 URL（多人脸场景）">
          <el-input
            v-model="localData.face_ref_image_url"
            placeholder="可选"
            @change="handleChange"
          />
        </el-form-item>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { uploadMedia } from '@/api/workflow'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'change'])

const languageOptions = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'ja', label: '日本語' },
  { value: 'ko', label: '한국어' },
  { value: 'es', label: 'Español' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
]

const localData = ref(normalize(props.modelValue))
const uploading = ref(false)

function normalize(val) {
  return {
    label: val?.label || '视频翻译',
    description: val?.description || '',
    inputMode: val?.inputMode || (val?.media_id ? 'upload' : val?.video_input?.includes('{') ? 'upstream' : 'url'),
    video_input: val?.video_input || val?.videoInput || '{video_url}',
    media_id: val?.media_id || val?.mediaId || '',
    public_url: val?.public_url || val?.publicUrl || '',
    source_language: val?.source_language || val?.sourceLanguage || 'zh',
    target_languages: val?.target_languages || val?.targetLanguages || ['en'],
    voice: val?.voice || 'longanyang',
    subtitle_format: val?.subtitle_format || val?.subtitleFormat || 'srt',
    lip_sync: val?.lip_sync ?? val?.lipSync ?? true,
    burn_subtitles: val?.burn_subtitles ?? val?.burnSubtitles ?? true,
    video_extension: val?.video_extension ?? val?.videoExtension ?? false,
    face_ref_image_url: val?.face_ref_image_url || val?.faceRefImageUrl || '',
    provider: val?.provider || 'dashscope',
  }
}

watch(() => props.modelValue, (val) => {
  localData.value = normalize(val)
}, { deep: true })

function syncEmit() {
  const payload = { ...localData.value }
  if (localData.value.inputMode === 'upload' && localData.value.public_url) {
    payload.video_input = localData.value.public_url
  }
  emit('update:modelValue', payload)
  emit('change', payload)
}

function handleChange() {
  syncEmit()
}

function handleInputModeChange() {
  if (localData.value.inputMode === 'upstream') {
    localData.value.video_input = '{video_url}'
  }
  handleChange()
}

async function handleFileChange(uploadFile) {
  const file = uploadFile?.raw
  if (!file) return
  uploading.value = true
  try {
    const res = await uploadMedia(file)
    const data = res?.data || res
    if (!data?.success) {
      throw new Error(data?.error || '上传失败')
    }
    const meta = data.data || {}
    localData.value.media_id = meta.media_id
    localData.value.public_url = meta.public_url
    localData.value.video_input = meta.public_url
    ElMessage.success('视频上传成功')
    handleChange()
  } catch (err) {
    ElMessage.error(err.message || '视频上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.form-section { margin-bottom: 16px; }
.section-title { margin: 0 0 8px; font-size: 13px; font-weight: 600; color: var(--el-text-color-primary); }
.field-hint { margin-top: 4px; font-size: 12px; color: var(--el-text-color-secondary); word-break: break-all; }
</style>
