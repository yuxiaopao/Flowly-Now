<template>
  <div class="config-form agent-config-form">
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

      <!-- Agent 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Agent 配置
        </h4>
        
        <el-form-item label="模型">
          <el-input
            v-model="localData.model"
            placeholder="gpt-4, claude-3-opus"
            @change="handleChange"
          />
          <div class="field-hint">
            用于 Agent 推理的语言模型
          </div>
        </el-form-item>

        <el-form-item label="可用工具">
          <el-input
            v-model="localData.tools"
            type="textarea"
            :rows="3"
            placeholder="search, calculator, weather"
            class="tools-input"
            @change="handleChange"
          />
          <div class="field-hint">
            Agent 可调用的工具名称，逗号分隔
          </div>
        </el-form-item>

        <el-form-item label="最大迭代次数">
          <el-input-number
            v-model="localData.maxIterations"
            :min="1"
            :max="100"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            Agent 执行的最大步数，防止无限循环
          </div>
        </el-form-item>
      </div>

      <!-- 系统提示 -->
      <div class="form-section">
        <h4 class="section-title">
          系统提示
        </h4>
        
        <el-form-item label="系统提示词">
          <el-input
            v-model="localData.systemPrompt"
            type="textarea"
            :rows="5"
            placeholder="你是一个智能助手，可以帮助用户完成各种任务..."
            class="prompt-input"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 记忆配置 -->
      <div class="form-section">
        <h4 class="section-title">
          记忆配置
        </h4>
        
        <el-form-item label="启用记忆">
          <el-switch
            v-model="localData.memoryEnabled"
            @change="handleChange"
          />
          <span class="field-hint">Agent 是否保留对话历史记忆</span>
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
            <span class="preview-label">迭代:</span>
            <span class="preview-value">{{ localData.maxIterations || 10 }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">记忆:</span>
            <el-tag
              size="small"
              :type="localData.memoryEnabled ? 'success' : 'info'"
            >
              {{ localData.memoryEnabled ? '开启' : '关闭' }}
            </el-tag>
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
  tools: '',
  maxIterations: 10,
  systemPrompt: '',
  memoryEnabled: true
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      model: newVal.model || DEFAULT_LLM_MODEL,
      tools: newVal.tools || '',
      maxIterations: newVal.maxIterations ?? 10,
      systemPrompt: newVal.systemPrompt || '',
      memoryEnabled: newVal.memoryEnabled ?? true
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

.tools-input,
.prompt-input {
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
  }
}
</style>
