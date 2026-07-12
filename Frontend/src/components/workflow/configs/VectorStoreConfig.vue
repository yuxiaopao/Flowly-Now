<template>
  <div class="config-form vector-store-config-form">
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

      <!-- 向量存储配置 -->
      <div class="form-section">
        <h4 class="section-title">
          向量存储配置
        </h4>
        
        <el-form-item label="存储提供商">
          <el-select
            v-model="localData.provider"
            placeholder="选择提供商"
            @change="handleChange"
          >
            <el-option
              label="Chroma (本地)"
              value="chroma"
            />
            <el-option
              label="Pinecone"
              value="pinecone"
            />
            <el-option
              label="Qdrant"
              value="qdrant"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="索引名称"
          required
        >
          <el-input
            v-model="localData.indexName"
            placeholder="my-index"
            @change="handleChange"
          />
          <div class="field-hint">
            向量数据库中的索引/集合名称
          </div>
        </el-form-item>

        <el-form-item label="相似度度量">
          <el-select
            v-model="localData.metric"
            @change="handleChange"
          >
            <el-option
              label="余弦相似度 (Cosine)"
              value="cosine"
            />
            <el-option
              label="欧几里得距离 (Euclidean)"
              value="euclidean"
            />
            <el-option
              label="点积 (Dot Product)"
              value="dotproduct"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="localData.provider === 'qdrant'"
          label="Qdrant URL"
        >
          <el-input
            v-model="localData.url"
            placeholder="http://localhost:6333"
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
            <span class="preview-label">索引:</span>
            <span class="preview-value">{{ localData.indexName || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">度量:</span>
            <span class="preview-value">{{ localData.metric || 'cosine' }}</span>
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
  provider: 'chroma',
  indexName: '',
  metric: 'cosine',
  url: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      provider: newVal.provider || 'chroma',
      indexName: newVal.indexName || '',
      metric: newVal.metric || 'cosine',
      url: newVal.url || ''
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
