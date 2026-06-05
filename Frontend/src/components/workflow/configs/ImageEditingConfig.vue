<template>
  <div class="config-form image-editing-config-form">
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

      <!-- 模型配置 -->
      <div class="form-section">
        <h4 class="section-title">
          模型配置
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
          </el-select>
        </el-form-item>

        <el-form-item label="模型">
          <el-select
            v-model="localData.model"
            @change="handleChange"
          >
            <el-option
              label="DALL-E 2"
              value="dall-e-2"
            />
            <el-option
              label="DALL-E 3"
              value="dall-e-3"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 编辑配置 -->
      <div class="form-section">
        <h4 class="section-title">
          编辑配置
        </h4>
        
        <el-form-item
          label="原始图像"
          required
        >
          <el-input
            v-model="localData.image"
            placeholder="图像URL或base64编码"
            @change="handleChange"
          />
          <div class="field-hint">
            要编辑的原始图像
          </div>
        </el-form-item>

        <el-form-item
          label="编辑指令"
          required
        >
          <el-input
            v-model="localData.instruction"
            type="textarea"
            :rows="4"
            placeholder="描述你想要对图像进行的修改..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="蒙版 (可选)">
          <el-input
            v-model="localData.mask"
            placeholder="蒙版图像URL或base64编码"
            @change="handleChange"
          />
          <div class="field-hint">
            白色区域将被编辑，黑色区域保持不变
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
            <span class="preview-value">{{ localData.model || 'dall-e-3' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">蒙版:</span>
            <span class="preview-value">{{ localData.mask ? '已设置' : '未设置' }}</span>
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
  image: '',
  instruction: '',
  mask: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'openai',
      model: newVal.model || 'dall-e-3',
      image: newVal.image || '',
      instruction: newVal.instruction || '',
      mask: newVal.mask || ''
    })
  }
}, { immediate: true, deep: true })

const handleProviderChange = () => {
  if (localData.provider === 'openai' && !localData.model) {
    localData.model = 'dall-e-3'
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
