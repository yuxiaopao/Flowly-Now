<template>
  <div class="config-form memory-config-form">
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

      <!-- Memory 配置 -->
      <div class="form-section">
        <h4 class="section-title">
          Memory 配置
        </h4>
        
        <el-form-item label="记忆类型">
          <el-select
            v-model="localData.memoryType"
            @change="handleChange"
          >
            <el-option
              label="缓冲记忆 (Buffer)"
              value="buffer"
            />
            <el-option
              label="摘要记忆 (Summary)"
              value="summary"
            />
            <el-option
              label="实体记忆 (Entity)"
              value="entity"
            />
            <el-option
              label="对话记忆 (Conversation)"
              value="conversation"
            />
          </el-select>
          <div class="field-hint">
            <template v-if="localData.memoryType === 'buffer'">
              保留完整的对话历史
            </template>
            <template v-else-if="localData.memoryType === 'summary'">
              自动生成对话摘要
            </template>
            <template v-else-if="localData.memoryType === 'entity'">
              提取和存储关键实体
            </template>
            <template v-else>
              对话历史的简单存储
            </template>
          </div>
        </el-form-item>

        <el-form-item label="最大条目数">
          <el-input-number
            v-model="localData.maxItems"
            :min="1"
            :max="1000"
            :step="10"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            记忆存储的最大条目数量
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
            <span class="preview-label">类型:</span>
            <span class="preview-value">{{ formatMemoryType(localData.memoryType) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">最大条目:</span>
            <span class="preview-value">{{ localData.maxItems || 100 }}</span>
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
  memoryType: 'buffer',
  maxItems: 100
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      memoryType: newVal.memoryType || 'buffer',
      maxItems: newVal.maxItems ?? 100
    })
  }
}, { immediate: true, deep: true })

const formatMemoryType = (type) => {
  const types = {
    buffer: '缓冲记忆',
    summary: '摘要记忆',
    entity: '实体记忆',
    conversation: '对话记忆'
  }
  return types[type] || type || '缓冲记忆'
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
