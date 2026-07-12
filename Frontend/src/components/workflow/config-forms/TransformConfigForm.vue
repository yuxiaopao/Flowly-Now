<template>
  <div class="config-form transform-config-form">
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

      <!-- 转换类型 -->
      <div class="form-section">
        <h4 class="section-title">
          转换类型
        </h4>
        <el-form-item label="类型">
          <el-radio-group
            v-model="localData.transformType"
            class="transform-type-group"
            @change="handleChange"
          >
            <div class="type-grid">
              <el-radio
                value="json_to_object"
                class="type-option"
              >
                <span class="type-label">JSON → 对象</span>
                <span class="type-desc">解析 JSON 字符串为对象</span>
              </el-radio>
              <el-radio
                value="object_to_json"
                class="type-option"
              >
                <span class="type-label">对象 → JSON</span>
                <span class="type-desc">将对象序列化为 JSON</span>
              </el-radio>
              <el-radio
                value="map"
                class="type-option"
              >
                <span class="type-label">映射</span>
                <span class="type-desc">字段一一对应转换</span>
              </el-radio>
              <el-radio
                value="filter"
                class="type-option"
              >
                <span class="type-label">过滤</span>
                <span class="type-desc">根据条件筛选数据</span>
              </el-radio>
              <el-radio
                value="sort"
                class="type-option"
              >
                <span class="type-label">排序</span>
                <span class="type-desc">对数组进行排序</span>
              </el-radio>
              <el-radio
                value="merge"
                class="type-option"
              >
                <span class="type-label">合并</span>
                <span class="type-desc">合并多个数据源</span>
              </el-radio>
              <el-radio
                value="split"
                class="type-option"
              >
                <span class="type-label">拆分</span>
                <span class="type-desc">将数据拆分为数组</span>
              </el-radio>
              <el-radio
                value="extract"
                class="type-option"
              >
                <span class="type-label">提取</span>
                <span class="type-desc">提取指定字段</span>
              </el-radio>
              <el-radio
                value="custom"
                class="type-option"
              >
                <span class="type-label">自定义</span>
                <span class="type-desc">编写自定义脚本</span>
              </el-radio>
            </div>
          </el-radio-group>
        </el-form-item>
      </div>

      <!-- 映射配置 -->
      <div
        v-if="localData.transformType === 'map'"
        class="form-section"
      >
        <h4 class="section-title">
          映射配置
        </h4>
        <el-form-item label="字段映射">
          <div class="mapping-list">
            <div 
              v-for="(mapping, idx) in localData.mappings" 
              :key="idx"
              class="mapping-row"
            >
              <el-input 
                v-model="mapping.source" 
                placeholder="源字段" 
                size="small" 
                class="field-input"
                @change="handleChange"
              />
              <span class="arrow">→</span>
              <el-input 
                v-model="mapping.target" 
                placeholder="目标字段" 
                size="small" 
                class="field-input"
                @change="handleChange"
              />
              <el-button 
                link 
                type="danger" 
                size="small"
                @click="removeMapping(idx)"
              >
                <Minus class="icon-sm" />
              </el-button>
            </div>
            <el-button
              size="small"
              class="add-mapping-btn"
              @click="addMapping"
            >
              <Plus class="icon" /> 添加映射
            </el-button>
          </div>
        </el-form-item>
      </div>

      <!-- 过滤配置 -->
      <div
        v-if="localData.transformType === 'filter'"
        class="form-section"
      >
        <h4 class="section-title">
          过滤配置
        </h4>
        <el-form-item label="过滤条件">
          <el-input
            v-model="localData.filterExpression"
            type="textarea"
            :rows="3"
            placeholder="例如: item['count'] > 0"
            class="code-input"
            @change="handleChange"
          />
          <div class="field-hint">
            Python 表达式，item 为当前遍历元素
          </div>
        </el-form-item>
      </div>

      <!-- 排序配置 -->
      <div
        v-if="localData.transformType === 'sort'"
        class="form-section"
      >
        <h4 class="section-title">
          排序配置
        </h4>
        <el-form-item label="排序字段">
          <el-input 
            v-model="localData.sortField" 
            placeholder="例如: data.count" 
            @change="handleChange"
          />
        </el-form-item>
        <el-form-item label="排序方式">
          <el-radio-group
            v-model="localData.sortOrder"
            @change="handleChange"
          >
            <el-radio value="asc">
              升序 (A → Z)
            </el-radio>
            <el-radio value="desc">
              降序 (Z → A)
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </div>

      <!-- 合并配置 -->
      <div
        v-if="localData.transformType === 'merge'"
        class="form-section"
      >
        <h4 class="section-title">
          合并配置
        </h4>
        <el-form-item label="合并策略">
          <el-select
            v-model="localData.mergeStrategy"
            @change="handleChange"
          >
            <el-option
              label="深度合并"
              value="deep"
            />
            <el-option
              label="覆盖合并"
              value="override"
            />
            <el-option
              label="数组拼接"
              value="concat"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据源">
          <el-input
            v-model="localData.mergeSources"
            type="textarea"
            :rows="2"
            placeholder="输入变量1&#10;输入变量2"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 拆分配置 -->
      <div
        v-if="localData.transformType === 'split'"
        class="form-section"
      >
        <h4 class="section-title">
          拆分配置
        </h4>
        <el-form-item label="分隔符">
          <el-input 
            v-model="localData.splitDelimiter" 
            placeholder="例如: , 或 |" 
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 提取配置 -->
      <div
        v-if="localData.transformType === 'extract'"
        class="form-section"
      >
        <h4 class="section-title">
          提取配置
        </h4>
        <el-form-item label="提取路径">
          <el-input 
            v-model="localData.extractPath" 
            placeholder="例如: data.items[0].name" 
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 自定义脚本 -->
      <div
        v-if="localData.transformType === 'custom'"
        class="form-section"
      >
        <h4 class="section-title">
          自定义脚本
        </h4>
        <el-form-item label="脚本内容">
          <el-input
            v-model="localData.customScript"
            type="textarea"
            :rows="8"
            placeholder="# input 是输入数据&#10;# 返回转换后的结果&#10;result = input"
            class="code-input"
            @change="handleChange"
          />
          <div class="field-hint">
            使用 Python 语法，input 变量包含输入数据
          </div>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          转换预览
        </h4>
        <div class="transform-preview">
          <el-tag
            size="small"
            type="primary"
          >
            {{ getTransformTypeLabel(localData.transformType) }}
          </el-tag>
          <div class="preview-text">
            <code>{{ getPreviewText() }}</code>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { Plus, Minus } from 'lucide-vue-next'

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
  transformType: 'map',
  mappings: [],
  filterExpression: '',
  sortField: '',
  sortOrder: 'asc',
  mergeStrategy: 'deep',
  mergeSources: '',
  splitDelimiter: ',',
  extractPath: '',
  customScript: ''
})

const getTransformTypeLabel = (type) => {
  const labels = {
    json_to_object: 'JSON → 对象',
    object_to_json: '对象 → JSON',
    map: '映射',
    filter: '过滤',
    sort: '排序',
    merge: '合并',
    split: '拆分',
    extract: '提取',
    custom: '自定义'
  }
  return labels[type] || type || '数据转换'
}

const getPreviewText = () => {
  switch (localData.transformType) {
    case 'map':
      return localData.mappings.length > 0 
        ? localData.mappings.map(m => `${m.source} → ${m.target}`).join(', ')
        : '暂无映射规则'
    case 'filter':
      return localData.filterExpression || '请输入过滤条件'
    case 'sort':
      return `${localData.sortField || '字段'} (${localData.sortOrder === 'asc' ? '升序' : '降序'})`
    case 'merge':
      return `合并策略: ${localData.mergeStrategy}`
    case 'split':
      return `分隔符: "${localData.splitDelimiter || ','}"`
    case 'extract':
      return `路径: ${localData.extractPath || '未设置'}`
    case 'custom':
      return localData.customScript ? '自定义脚本已配置' : '请输入脚本'
    case 'json_to_object':
      return 'JSON 字符串 → 对象'
    case 'object_to_json':
      return '对象 → JSON 字符串'
    default:
      return '未知类型'
  }
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      transformType: newVal.transformType || 'map',
      mappings: newVal.mappings ? JSON.parse(JSON.stringify(newVal.mappings)) : [],
      filterExpression: newVal.filterExpression || '',
      sortField: newVal.sortField || '',
      sortOrder: newVal.sortOrder || 'asc',
      mergeStrategy: newVal.mergeStrategy || 'deep',
      mergeSources: newVal.mergeSources || '',
      splitDelimiter: newVal.splitDelimiter || ',',
      extractPath: newVal.extractPath || '',
      customScript: newVal.customScript || ''
    })
  }
}, { immediate: true, deep: true })

const addMapping = () => {
  localData.mappings.push({ source: '', target: '' })
  handleChange()
}

const removeMapping = (index) => {
  localData.mappings.splice(index, 1)
  handleChange()
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

.icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.icon-sm {
  width: 14px;
  height: 14px;
}

.transform-type-group {
  width: 100%;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-2;
}

.type-option {
  display: flex;
  flex-direction: column;
  padding: $spacing-2;
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  margin-right: 0;
  margin-bottom: $spacing-1;
  transition: all $transition-fast;
  width: 100%;

  &:hover {
    border-color: var(--accent-primary);
    background: var(--bg-hover);
  }

  &.is-checked {
    border-color: var(--accent-primary);
    background: rgba(59, 130, 246, 0.08);
  }

  .type-label {
    font-weight: $font-weight-medium;
    color: var(--text-primary);
    font-size: $font-size-sm;
  }

  .type-desc {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    margin-top: 2px;
  }
}

.mapping-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .field-input {
    flex: 1;
  }

  .arrow {
    color: var(--accent-primary);
    font-weight: $font-weight-bold;
    flex-shrink: 0;
  }
}

.add-mapping-btn {
  margin-top: $spacing-2;
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.code-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', 'JetBrains Mono', monospace;
    font-size: $font-size-xs;
    line-height: 1.5;
  }
}

.transform-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .el-tag {
    margin-bottom: $spacing-2;
  }
}

.preview-text {
  margin-top: $spacing-2;

  code {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--text-secondary);
    word-break: break-all;
  }
}
</style>
