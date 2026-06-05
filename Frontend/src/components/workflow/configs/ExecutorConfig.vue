<template>
  <div class="config-form executor-config-form">
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

      <!-- Executor 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Executor 配置
        </h4>
        
        <el-form-item label="工具选择策略">
          <el-select
            v-model="localData.toolSelection"
            @change="handleChange"
          >
            <el-option
              label="自动选择 (Auto)"
              value="auto"
            />
            <el-option
              label="手动选择 (Manual)"
              value="manual"
            />
            <el-option
              label="混合模式 (Hybrid)"
              value="hybrid"
            />
          </el-select>
          <div class="field-hint">
            <template v-if="localData.toolSelection === 'auto'">
              模型自动选择最合适的工具
            </template>
            <template v-else-if="localData.toolSelection === 'manual'">
              用户手动指定要使用的工具
            </template>
            <template v-else>
              模型推荐 + 用户确认
            </template>
          </div>
        </el-form-item>

        <el-form-item label="上下文窗口 (Tokens)">
          <el-input-number
            v-model="localData.contextWindow"
            :min="1000"
            :max="200000"
            :step="1000"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            模型的最大上下文窗口大小
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
            <span class="preview-label">工具选择:</span>
            <span class="preview-value">{{ localData.toolSelection || 'auto' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">上下文:</span>
            <span class="preview-value">{{ formatContextWindow(localData.contextWindow) }}</span>
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
  toolSelection: 'auto',
  contextWindow: 128000
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      toolSelection: newVal.toolSelection || 'auto',
      contextWindow: newVal.contextWindow ?? 128000
    })
  }
}, { immediate: true, deep: true })

const formatContextWindow = (tokens) => {
  if (!tokens) return '128K'
  if (tokens >= 1000) {
    return (tokens / 1000).toFixed(0) + 'K'
  }
  return tokens.toString()
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
