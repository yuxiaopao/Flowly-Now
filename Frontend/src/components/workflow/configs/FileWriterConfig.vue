<template>
  <div class="config-form file-writer-config-form">
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

      <!-- 文件写入配置 -->
      <div class="form-section">
        <h4 class="section-title">
          文件写入配置
        </h4>
        
        <el-form-item
          label="文件路径"
          required
        >
          <el-input
            v-model="localData.path"
            placeholder="/path/to/output.json"
            @change="handleChange"
          />
          <div class="field-hint">
            输出文件的完整路径
          </div>
        </el-form-item>

        <el-form-item label="文件格式">
          <el-select
            v-model="localData.format"
            @change="handleChange"
          >
            <el-option
              label="JSON"
              value="json"
            />
            <el-option
              label="CSV"
              value="csv"
            />
            <el-option
              label="Parquet"
              value="parquet"
            />
            <el-option
              label="Excel"
              value="excel"
            />
            <el-option
              label="纯文本 (TXT)"
              value="txt"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="覆盖已存在文件">
          <el-switch
            v-model="localData.overwrite"
            @change="handleChange"
          />
          <span class="field-hint">开启后将覆盖已存在的文件</span>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">路径:</span>
            <span class="preview-value">{{ localData.path || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">格式:</span>
            <span class="preview-value">{{ localData.format || 'json' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">覆盖:</span>
            <el-tag
              size="small"
              :type="localData.overwrite ? 'warning' : 'info'"
            >
              {{ localData.overwrite ? '是' : '否' }}
            </el-tag>
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
  path: '',
  format: 'json',
  overwrite: false
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      path: newVal.path || '',
      format: newVal.format || 'json',
      overwrite: newVal.overwrite ?? false
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
    word-break: break-all;
  }
}
</style>
