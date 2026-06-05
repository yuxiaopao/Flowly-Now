<template>
  <div class="config-form video-generation-config-form">
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
            @change="handleChange"
          >
            <el-option
              label="Replicate"
              value="replicate"
            />
            <el-option
              label="Runway"
              value="runway"
            />
            <el-option
              label="Pika"
              value="pika"
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
            例如: models/video-generation
          </div>
        </el-form-item>
      </div>

      <!-- 视频生成配置 -->
      <div class="form-section">
        <h4 class="section-title">
          生成配置
        </h4>
        
        <el-form-item
          label="提示词"
          required
        >
          <el-input
            v-model="localData.prompt"
            type="textarea"
            :rows="4"
            placeholder="描述你想要生成的视频内容..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="时长 (秒)">
          <el-input-number
            v-model="localData.duration"
            :min="1"
            :max="60"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="帧率 (FPS)">
          <el-input-number
            v-model="localData.fps"
            :min="1"
            :max="60"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="分辨率">
          <el-select
            v-model="localData.resolution"
            @change="handleChange"
          >
            <el-option
              label="720p"
              value="720p"
            />
            <el-option
              label="1080p"
              value="1080p"
            />
            <el-option
              label="4K"
              value="4k"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="输入图像 (可选)">
          <el-input
            v-model="localData.inputImage"
            placeholder="图像URL或base64编码"
            @change="handleChange"
          />
          <div class="field-hint">
            用于图像到视频的转换
          </div>
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
            <span class="preview-label">模型:</span>
            <span class="preview-value">{{ localData.model || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">时长:</span>
            <span class="preview-value">{{ localData.duration || 4 }}秒</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">分辨率:</span>
            <span class="preview-value">{{ localData.resolution || '720p' }}</span>
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
  provider: 'replicate',
  model: '',
  prompt: '',
  duration: 4,
  fps: 24,
  resolution: '720p',
  inputImage: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'replicate',
      model: newVal.model || '',
      prompt: newVal.prompt || '',
      duration: newVal.duration ?? 4,
      fps: newVal.fps ?? 24,
      resolution: newVal.resolution || '720p',
      inputImage: newVal.inputImage || ''
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
