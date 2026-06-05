<template>
  <div class="config-form subtitle-generation-config-form">
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

      <!-- 输入配置 -->
      <div class="form-section">
        <h4 class="section-title">
          输入配置
        </h4>
        
        <el-form-item label="输入类型">
          <el-select
            v-model="localData.inputType"
            @change="handleChange"
          >
            <el-option
              label="音频文件"
              value="audio"
            />
            <el-option
              label="视频文件"
              value="video"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="输入路径"
          required
        >
          <el-input
            v-model="localData.inputPath"
            placeholder="音频或视频文件路径"
            @change="handleChange"
          />
          <div class="field-hint">
            支持本地路径或URL
          </div>
        </el-form-item>
      </div>

      <!-- 字幕配置 -->
      <div class="form-section">
        <h4 class="section-title">
          字幕配置
        </h4>
        
        <el-form-item label="语言">
          <el-input
            v-model="localData.language"
            placeholder="en"
            @change="handleChange"
          />
          <div class="field-hint">
            语言代码，如: en, zh, ja, ko
          </div>
        </el-form-item>

        <el-form-item label="字幕格式">
          <el-select
            v-model="localData.format"
            @change="handleChange"
          >
            <el-option
              label="SRT (SubRip)"
              value="srt"
            />
            <el-option
              label="VTT (WebVTT)"
              value="vtt"
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
            <span class="preview-label">输入类型:</span>
            <span class="preview-value">{{ localData.inputType || 'audio' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">语言:</span>
            <span class="preview-value">{{ localData.language || 'en' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">格式:</span>
            <span class="preview-value">{{ localData.format || 'srt' }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

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
  inputType: 'audio',
  inputPath: '',
  language: 'en',
  format: 'srt'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      inputType: newVal.inputType || 'audio',
      inputPath: newVal.inputPath || '',
      language: newVal.language || 'en',
      format: newVal.format || 'srt'
    })
  }
}, { immediate: true, deep: true })

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
