<template>
  <div class="config-form audio-generation-config-form">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <!-- 基本信息 -->
      <div class="form-section">
        <h4 class="section-title">
          基本信息
        </h4>
        <el-form-item label="节点名称">
          <el-input
            v-model="localData.label"
            placeholder="输入节点名称"
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="localData.description" 
            type="textarea" 
            :rows="2"
            placeholder="节点功能描述"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 服务商配置 -->
      <div class="form-section">
        <h4 class="section-title">
          服务商配置
        </h4>
        
        <el-form-item label="AI 提供商">
          <el-select
            v-model="localData.provider"
            placeholder="选择提供商"
            @change="handleProviderChange"
          >
            <el-option
              label="OpenAI (TTS)"
              value="openai"
            />
            <el-option
              label="ElevenLabs"
              value="elevenlabs"
            />
            <el-option
              label="Azure Speech"
              value="azure"
            />
            <el-option
              label="阿里云百炼 (CosyVoice)"
              value="dashscope"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型">
          <el-input
            v-model="localData.model"
            placeholder="输入模型名称"
            @change="handleChange"
          />
          <div class="field-hint">
            例如: tts-1, tts-1-hd, eleven_multilingual_v2, cosyvoice-v3-flash
          </div>
        </el-form-item>
      </div>

      <!-- 音频生成配置 -->
      <div class="form-section">
        <h4 class="section-title">
          生成配置
        </h4>
        
        <el-form-item
          label="文本内容"
          required
        >
          <el-input
            v-model="localData.text"
            type="textarea"
            :rows="4"
            placeholder="输入要转换为语音的文本内容..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="声音">
          <el-select 
            v-if="localData.provider === 'openai'" 
            v-model="localData.voice" 
            @change="handleChange"
          >
            <el-option
              label="Alloy (中性)"
              value="alloy"
            />
            <el-option
              label="Echo (男性)"
              value="echo"
            />
            <el-option
              label="Fable (英国)"
              value="fable"
            />
            <el-option
              label="Onyx (男性)"
              value="onyx"
            />
            <el-option
              label="Nova (女性)"
              value="nova"
            />
            <el-option
              label="Shimmer (女性)"
              value="shimmer"
            />
          </el-select>
          <el-select
            v-else-if="localData.provider === 'dashscope'"
            v-model="localData.voice"
            @change="handleChange"
          >
            <el-option
              label="龙安燕 (女声/晓晓风格)"
              value="longanyang"
            />
            <el-option
              label="龙小淳 (女声/温柔)"
              value="longxiaochun"
            />
            <el-option
              label="龙老铁 (男声/东北)"
              value="longlaotie"
            />
          </el-select>
          <el-input 
            v-else 
            v-model="localData.voice" 
            placeholder="输入声音ID或名称"
            @change="handleChange"
          />
          <div
            v-if="localData.provider === 'dashscope'"
            class="field-hint"
          >
            CosyVoice 音色，也可手动输入其他官方音色 ID
          </div>
        </el-form-item>

        <el-form-item label="语速">
          <el-input-number
            v-model="localData.speed"
            :min="0.25"
            :max="4.0"
            :step="0.1"
            :precision="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            1.0 为正常语速，范围 0.25 - 4.0
          </div>
        </el-form-item>

        <el-form-item label="音频格式">
          <el-select
            v-model="localData.format"
            @change="handleChange"
          >
            <el-option
              label="MP3"
              value="mp3"
            />
            <el-option
              label="Opus"
              value="opus"
            />
            <el-option
              label="AAC"
              value="aac"
            />
            <el-option
              label="FLAC"
              value="flac"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">提供商:</span>
            <span class="preview-value">{{ localData.provider || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">声音:</span>
            <span class="preview-value">{{ localData.voice || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">语速:</span>
            <span class="preview-value">{{ localData.speed || 1.0 }}x</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">格式:</span>
            <span class="preview-value">{{ localData.format || 'mp3' }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  provider: 'openai',
  model: 'tts-1',
  text: '',
  voice: 'alloy',
  speed: 1.0,
  format: 'mp3'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'openai',
      model: newVal.model || (newVal.provider === 'dashscope' ? 'cosyvoice-v3-flash' : 'tts-1'),
      text: newVal.text || '',
      voice: newVal.voice || (newVal.provider === 'dashscope' ? 'longanyang' : 'alloy'),
      speed: newVal.speed ?? 1.0,
      format: newVal.format || 'mp3'
    })
  }
}, { immediate: true, deep: true })

const defaultVoices = { openai: 'alloy', dashscope: 'longanyang' }
const defaultModels = { openai: 'tts-1', dashscope: 'cosyvoice-v3-flash' }

const handleProviderChange = () => {
  if (!localData.model || Object.values(defaultModels).includes(localData.model)) {
    localData.model = defaultModels[localData.provider] || ''
  }
  if (!localData.voice || Object.values(defaultVoices).includes(localData.voice)) {
    localData.voice = defaultVoices[localData.provider] || ''
  }
  handleChange()
}

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.config-form {
  padding: 0;
}

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
    margin-bottom: 0;
  }
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-3;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.prompt-input {
  :deep(.el-textarea__inner) {
    font-family: inherit;
    line-height: 1.6;
  }
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.config-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.preview-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
    min-width: 80px;
  }

  .preview-value {
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}
</style>
