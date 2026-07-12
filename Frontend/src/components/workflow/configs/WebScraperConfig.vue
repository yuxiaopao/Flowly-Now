<template>
  <div class="config-form web-scraper-config-form">
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

      <!-- 网页抓取配置 -->
      <div class="form-section">
        <h4 class="section-title">
          网页抓取配置
        </h4>
        
        <el-form-item
          label="目标 URL"
          required
        >
          <el-input
            v-model="localData.url"
            placeholder="https://example.com/page"
            @change="handleChange"
          />
          <div class="field-hint">
            要抓取的网页地址
          </div>
        </el-form-item>

        <el-form-item label="选择器配置 (JSON)">
          <el-input
            v-model="localData.selectors"
            type="textarea"
            :rows="5"
            placeholder="[{&quot;name&quot;: &quot;title&quot;, &quot;selector&quot;: &quot;h1&quot;}, {&quot;name&quot;: &quot;content&quot;, &quot;selector&quot;: &quot;.article-body&quot;}]"
            class="json-input"
            @change="handleChange"
          />
          <div class="field-hint">
            CSS选择器配置，JSON数组格式
          </div>
        </el-form-item>

        <el-form-item label="等待条件 (可选)">
          <el-input
            v-model="localData.waitFor"
            placeholder=".dynamic-content-loaded"
            @change="handleChange"
          />
          <div class="field-hint">
            等待特定元素加载的选择器
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
            <span class="preview-label">URL:</span>
            <span class="preview-value">{{ truncateUrl(localData.url) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">选择器:</span>
            <span class="preview-value">{{ countSelectors(localData.selectors) }}</span>
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
  url: '',
  selectors: '[{"name": "title", "selector": "h1"}, {"name": "content", "selector": "p"}]',
  waitFor: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      url: newVal.url || '',
      selectors: newVal.selectors || '[{"name": "title", "selector": "h1"}]',
      waitFor: newVal.waitFor || ''
    })
  }
}, { immediate: true, deep: true })

const truncateUrl = (url) => {
  if (!url) return '(未设置)'
  if (url.length > 40) {
    return url.substring(0, 40) + '...'
  }
  return url
}

const countSelectors = (selectors) => {
  if (!selectors) return '0 个选择器'
  try {
    const parsed = JSON.parse(selectors)
    if (Array.isArray(parsed)) {
      return `${parsed.length} 个选择器`
    }
    return '格式错误'
  } catch {
    return '格式错误'
  }
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

.json-input {
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
