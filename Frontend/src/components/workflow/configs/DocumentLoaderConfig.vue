<template>
  <div class="config-form document-loader-config-form">
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

      <!-- 源配置 -->
      <div class="form-section">
        <h4 class="section-title">
          源配置
        </h4>
        
        <el-form-item label="来源类型">
          <el-select
            v-model="localData.sourceType"
            @change="handleChange"
          >
            <el-option
              label="本地文件"
              value="file"
            />
            <el-option
              label="URL"
              value="url"
            />
            <el-option
              label="网页"
              value="web"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="文件路径/URL"
          required
        >
          <el-input
            v-model="localData.path"
            placeholder="/path/to/document"
            @change="handleChange"
          />
          <div class="field-hint">
            本地文件路径或远程URL
          </div>
        </el-form-item>

        <el-form-item label="解析器">
          <el-select
            v-model="localData.parser"
            @change="handleChange"
          >
            <el-option
              label="纯文本 (TXT)"
              value="txt"
            />
            <el-option
              label="Markdown"
              value="markdown"
            />
            <el-option
              label="HTML"
              value="html"
            />
            <el-option
              label="PDF"
              value="pdf"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 分块配置 -->
      <div class="form-section">
        <h4 class="section-title">
          分块配置
        </h4>
        
        <el-form-item label="块大小 (字符数)">
          <el-input-number
            v-model="localData.chunkSize"
            :min="100"
            :max="10000"
            :step="100"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            每个文本块的目标字符数
          </div>
        </el-form-item>

        <el-form-item label="块重叠 (字符数)">
          <el-input-number
            v-model="localData.chunkOverlap"
            :min="0"
            :max="1000"
            :step="10"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            相邻块之间的重叠字符数
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
            <span class="preview-label">来源:</span>
            <span class="preview-value">{{ localData.sourceType || 'file' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">解析器:</span>
            <span class="preview-value">{{ localData.parser || 'txt' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">块大小:</span>
            <span class="preview-value">{{ localData.chunkSize || 500 }} chars</span>
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
  sourceType: 'file',
  path: '',
  parser: 'txt',
  chunkSize: 500,
  chunkOverlap: 50
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      sourceType: newVal.sourceType || 'file',
      path: newVal.path || '',
      parser: newVal.parser || 'txt',
      chunkSize: newVal.chunkSize ?? 500,
      chunkOverlap: newVal.chunkOverlap ?? 50
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
