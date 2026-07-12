<template>
  <div class="config-form planner-config-form">
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

      <!-- Planner 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Planner 配置
        </h4>
        
        <el-form-item label="模型">
          <el-input
            v-model="localData.model"
            placeholder="gpt-4, claude-3-opus"
            @change="handleChange"
          />
          <div class="field-hint">
            用于规划的语言模型
          </div>
        </el-form-item>

        <el-form-item label="分解策略">
          <el-select
            v-model="localData.decompositionStrategy"
            @change="handleChange"
          >
            <el-option
              label="顺序执行 (Sequential)"
              value="sequential"
            />
            <el-option
              label="层级分解 (Hierarchical)"
              value="hierarchical"
            />
            <el-option
              label="并行执行 (Parallel)"
              value="parallel"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="最大子任务数">
          <el-input-number
            v-model="localData.maxSubtasks"
            :min="1"
            :max="50"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            任务分解的最大子任务数量
          </div>
        </el-form-item>
      </div>

      <!-- 任务配置 -->
      <div class="form-section">
        <h4 class="section-title">
          任务配置
        </h4>
        
        <el-form-item label="任务描述">
          <el-input
            v-model="localData.task"
            type="textarea"
            :rows="4"
            placeholder="描述需要规划的任务..."
            class="task-input"
            @change="handleChange"
          />
          <div class="field-hint">
            支持使用 {变量名} 语法引用工作流变量
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
            <span class="preview-label">策略:</span>
            <span class="preview-value">{{ localData.decompositionStrategy || 'sequential' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">最大子任务:</span>
            <span class="preview-value">{{ localData.maxSubtasks || 10 }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { APP_CONFIG } from '@/config'

const DEFAULT_LLM_MODEL = APP_CONFIG.llm.defaultModel

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
  model: DEFAULT_LLM_MODEL,
  decompositionStrategy: 'sequential',
  maxSubtasks: 10,
  task: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      model: newVal.model || DEFAULT_LLM_MODEL,
      decompositionStrategy: newVal.decompositionStrategy || 'sequential',
      maxSubtasks: newVal.maxSubtasks ?? 10,
      task: newVal.task || ''
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

.task-input {
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
