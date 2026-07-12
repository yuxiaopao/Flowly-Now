<template>
  <div class="config-form csv-transform-config-form">
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

      <!-- CSV 转换配置 -->
      <div class="form-section">
        <h4 class="section-title">
          转换配置
        </h4>
        
        <el-form-item label="操作类型">
          <el-select
            v-model="localData.operation"
            @change="handleChange"
          >
            <el-option
              label="过滤 (Filter)"
              value="filter"
            />
            <el-option
              label="聚合 (Aggregate)"
              value="aggregate"
            />
            <el-option
              label="连接 (Join)"
              value="join"
            />
            <el-option
              label="透视表 (Pivot)"
              value="pivot"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="操作参数 (JSON)">
          <el-input
            v-model="localData.params"
            type="textarea"
            :rows="5"
            placeholder="{&quot;column&quot;: &quot;age&quot;, &quot;operator&quot;: &quot;>&quot;, &quot;value&quot;: 25}"
            class="json-input"
            @change="handleChange"
          />
          <div class="field-hint">
            根据操作类型配置相应参数
          </div>
        </el-form-item>

        <el-form-item label="测试数据 (JSON数组)">
          <el-input
            v-model="localData.data"
            type="textarea"
            :rows="5"
            placeholder="[{&quot;name&quot;: &quot;Alice&quot;, &quot;age&quot;: 30}, {&quot;name&quot;: &quot;Bob&quot;, &quot;age&quot;: 25}]"
            class="json-input"
            @change="handleChange"
          />
          <div class="field-hint">
            用于测试的CSV数据(JSON数组格式)
          </div>
        </el-form-item>
      </div>

      <!-- 操作说明 -->
      <div class="form-section">
        <h4 class="section-title">
          操作说明
        </h4>
        <div class="operation-guide">
          <div class="guide-item">
            <strong>过滤 (Filter):</strong>
            <code>{"column": "col", "operator": "eq", "value": "x"}</code>
          </div>
          <div class="guide-item">
            <strong>聚合 (Aggregate):</strong>
            <code>{"groupBy": "col", "agg": "sum", "target": "value"}</code>
          </div>
          <div class="guide-item">
            <strong>连接 (Join):</strong>
            <code>{"left": "id", "right": "id", "type": "inner"}</code>
          </div>
          <div class="guide-item">
            <strong>透视表 (Pivot):</strong>
            <code>{"index": "date", "columns": "category", "values": "amount"}</code>
          </div>
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">操作:</span>
            <span class="preview-value">{{ localData.operation || '(未选择)' }}</span>
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
  operation: 'filter',
  params: '{"column": "", "operator": "eq", "value": ""}',
  data: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      operation: newVal.operation || 'filter',
      params: newVal.params || '{"column": "", "operator": "eq", "value": ""}',
      data: newVal.data || ''
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

.operation-guide {
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  padding: $spacing-3;
  font-size: $font-size-xs;

  .guide-item {
    margin-bottom: $spacing-2;
    line-height: 1.6;

    &:last-child {
      margin-bottom: 0;
    }

    strong {
      color: var(--text-primary);
    }

    code {
      display: block;
      margin-top: 2px;
      padding: 4px 8px;
      background: var(--bg-primary);
      border-radius: $radius-sm;
      font-family: 'Fira Code', monospace;
      color: var(--accent-primary);
      word-break: break-all;
    }
  }
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
