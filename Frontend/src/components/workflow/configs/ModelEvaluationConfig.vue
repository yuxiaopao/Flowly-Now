<template>
  <div class="config-form model-evaluation-config-form">
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

      <!-- 评估配置 -->
      <div class="form-section">
        <h4 class="section-title">
          评估配置
        </h4>
        
        <el-form-item
          label="模型路径"
          required
        >
          <el-input
            v-model="localData.modelPath"
            placeholder="/path/to/model"
            @change="handleChange"
          />
          <div class="field-hint">
            训练好的模型文件路径或模型ID
          </div>
        </el-form-item>

        <el-form-item
          label="测试数据集"
          required
        >
          <el-input
            v-model="localData.testDataset"
            placeholder="测试数据集ID或路径"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="评估指标">
          <el-input
            v-model="localData.metrics"
            type="textarea"
            :rows="3"
            placeholder="accuracy, precision, recall, f1, auc"
            class="metrics-input"
            @change="handleChange"
          />
          <div class="field-hint">
            多个指标用逗号分隔
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
            <span class="preview-label">模型:</span>
            <span class="preview-value">{{ localData.modelPath || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">指标:</span>
            <span class="preview-value">{{ formatMetrics(localData.metrics) }}</span>
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
  modelPath: '',
  testDataset: '',
  metrics: 'accuracy, precision, recall, f1'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      modelPath: newVal.modelPath || '',
      testDataset: newVal.testDataset || '',
      metrics: newVal.metrics || 'accuracy, precision, recall, f1'
    })
  }
}, { immediate: true, deep: true })

const formatMetrics = (metrics) => {
  if (!metrics) return '(未设置)'
  const list = metrics.split(',').map(m => m.trim()).filter(Boolean)
  return list.length > 0 ? list.join(', ') : '(未设置)'
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

.metrics-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
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
    word-break: break-all;
  }
}
</style>
