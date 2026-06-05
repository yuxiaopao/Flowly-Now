<template>
  <div class="config-form image-generation-config-form">
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
              label="OpenAI (DALL-E)"
              value="openai"
            />
            <el-option
              label="Stability AI"
              value="stability"
            />
            <el-option
              label="Flux"
              value="flux"
            />
            <el-option
              label="Replicate"
              value="replicate"
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
            例如: dall-e-3, stable-diffusion-xl, flux-pro
          </div>
        </el-form-item>
      </div>

      <!-- 图像生成配置 -->
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
            placeholder="描述你想要生成的图像内容..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="图像尺寸">
          <el-select
            v-model="localData.size"
            @change="handleChange"
          >
            <el-option
              label="1024 x 1024 (1:1)"
              value="1024x1024"
            />
            <el-option
              label="1792 x 1024 (16:9)"
              value="1792x1024"
            />
            <el-option
              label="1024 x 1792 (9:16)"
              value="1024x1792"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="图像质量">
          <el-select
            v-model="localData.quality"
            @change="handleChange"
          >
            <el-option
              label="标准 (Standard)"
              value="standard"
            />
            <el-option
              label="高清 (HD)"
              value="hd"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="风格">
          <el-select
            v-model="localData.style"
            @change="handleChange"
          >
            <el-option
              label="生动 (Vivid)"
              value="vivid"
            />
            <el-option
              label="自然 (Natural)"
              value="natural"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="生成数量">
          <el-input-number
            v-model="localData.n"
            :min="1"
            :max="10"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
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
            <span class="preview-label">尺寸:</span>
            <span class="preview-value">{{ localData.size || '1024x1024' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">质量:</span>
            <span class="preview-value">{{ localData.quality || 'standard' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">数量:</span>
            <span class="preview-value">{{ localData.n || 1 }}</span>
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
  provider: 'openai',
  model: 'dall-e-3',
  prompt: '',
  size: '1024x1024',
  quality: 'standard',
  style: 'vivid',
  n: 1
})

const defaultModels = {
  openai: 'dall-e-3',
  stability: 'stable-diffusion-xl-1024-genai',
  flux: 'flux-pro',
  replicate: 'sdxl'
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'openai',
      model: newVal.model || defaultModels[localData.provider] || '',
      prompt: newVal.prompt || '',
      size: newVal.size || '1024x1024',
      quality: newVal.quality || 'standard',
      style: newVal.style || 'vivid',
      n: newVal.n ?? 1
    })
  }
}, { immediate: true, deep: true })

const handleProviderChange = () => {
  if (!localData.model || Object.values(defaultModels).includes(localData.model)) {
    localData.model = defaultModels[localData.provider] || ''
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
