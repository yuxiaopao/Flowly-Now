<template>
  <div class="config-form embedding-config-form">
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

      <!-- Embedding 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Embedding 配置
        </h4>
        
        <el-form-item label="AI 提供商">
          <el-select
            v-model="localData.provider"
            placeholder="选择提供商"
            @change="handleProviderChange"
          >
            <el-option
              label="OpenAI"
              value="openai"
            />
            <el-option
              label="HuggingFace"
              value="huggingface"
            />
            <el-option
              label="Cohere"
              value="cohere"
            />
            <el-option
              label="Ollama (本地)"
              value="ollama"
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
            {{ getModelHint() }}
          </div>
        </el-form-item>

        <el-form-item label="批处理大小">
          <el-input-number
            v-model="localData.batchSize"
            :min="1"
            :max="1000"
            :step="10"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            每批处理的文本数量
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
            <span class="preview-label">批大小:</span>
            <span class="preview-value">{{ localData.batchSize || 100 }}</span>
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
  model: 'text-embedding-3-small',
  batchSize: 100
})

const defaultModels = {
  openai: 'text-embedding-3-small',
  huggingface: 'sentence-transformers/all-MiniLM-L6-v2',
  cohere: 'embed-english-v3.0',
  ollama: 'nomic-embed-text'
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'openai',
      model: newVal.model || defaultModels[localData.provider] || '',
      batchSize: newVal.batchSize ?? 100
    })
  }
}, { immediate: true, deep: true })

const getModelHint = () => {
  const hints = {
    openai: '例如: text-embedding-3-small, text-embedding-3-large',
    huggingface: '例如: sentence-transformers/all-MiniLM-L6-v2',
    cohere: '例如: embed-english-v3.0',
    ollama: '例如: nomic-embed-text'
  }
  return hints[localData.provider] || ''
}

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
