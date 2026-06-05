<template>
  <div class="config-form reranker-config-form">
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

      <!-- Reranker 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Reranker 配置
        </h4>
        
        <el-form-item
          label="重排序模型"
          required
        >
          <el-input
            v-model="localData.model"
            placeholder="cross-encoder/ms-marco-MiniLM-L-6-v2"
            @change="handleChange"
          />
          <div class="field-hint">
            支持 HuggingFace 上的 Cross-Encoder 模型
          </div>
        </el-form-item>

        <el-form-item label="返回数量 (Top-N)">
          <el-input-number
            v-model="localData.topN"
            :min="1"
            :max="100"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            重排序后返回的最优 N 个结果
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
            <span class="preview-value">{{ localData.model || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">Top-N:</span>
            <span class="preview-value">{{ localData.topN || 5 }}</span>
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
  model: 'cross-encoder/ms-marco-MiniLM-L-6-v2',
  topN: 5
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      model: newVal.model || 'cross-encoder/ms-marco-MiniLM-L-6-v2',
      topN: newVal.topN ?? 5
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
