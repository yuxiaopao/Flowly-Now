<template>
  <div class="config-form prompt-config-form">
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

      <!-- 模板配置 -->
      <div class="form-section">
        <h4 class="section-title">
          模板配置
        </h4>
        
        <el-form-item label="模板名称">
          <el-input 
            v-model="localData.name" 
            placeholder="给模板起一个描述性的名称"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="模板内容">
          <el-input
            v-model="localData.template"
            type="textarea"
            :rows="8"
            placeholder="输入提示词模板，使用 {变量名} 占位变量&#10;&#10;示例：&#10;请分析以下 {content_type}：&#10;&#10;{content}&#10;&#10;请按照 {format} 格式输出结果。"
            class="template-input"
            @change="handleChange"
          />
          <div class="field-hint">
            使用 <code>{变量名}</code> 语法定义输入变量
          </div>
        </el-form-item>
      </div>

      <!-- 变量管理 -->
      <div class="form-section">
        <h4 class="section-title">
          变量管理
        </h4>
        
        <el-form-item label="已定义的变量">
          <div
            v-if="localData.variables && localData.variables.length > 0"
            class="variable-list"
          >
            <div 
              v-for="(variable, index) in localData.variables" 
              :key="index"
              class="variable-item"
            >
              <el-input
                v-model="variable.name"
                placeholder="变量名"
                size="small"
                class="var-name-input"
                @change="handleChange"
              />
              <el-input
                v-model="variable.value"
                placeholder="默认值（可选）"
                size="small"
                class="var-value-input"
                @change="handleChange"
              />
              <el-button 
                link 
                type="danger" 
                size="small"
                @click="removeVariable(index)"
              >
                <Minus class="icon-sm" />
              </el-button>
            </div>
          </div>
          <div
            v-else
            class="empty-variables"
          >
            <span class="empty-text">暂无定义变量</span>
          </div>
        </el-form-item>

        <el-form-item label="添加变量">
          <div class="add-variable-row">
            <el-input
              v-model="newVariable.name"
              placeholder="变量名"
              size="small"
              class="var-name-input"
              @keyup.enter="addVariable"
            />
            <el-input
              v-model="newVariable.value"
              placeholder="默认值（可选）"
              size="small"
              class="var-value-input"
              @keyup.enter="addVariable"
            />
            <el-button 
              type="primary" 
              size="small"
              :disabled="!newVariable.name.trim()"
              @click="addVariable"
            >
              <Plus class="icon" /> 添加
            </el-button>
          </div>
        </el-form-item>
      </div>

      <!-- 语法帮助 -->
      <div class="form-section">
        <h4 class="section-title">
          语法帮助
        </h4>
        <div class="syntax-help">
          <div class="syntax-item">
            <code>{variable}</code>
            <span>变量占位符，运行时会替换为实际值</span>
          </div>
          <div class="syntax-item">
            <code>{variable:default}</code>
            <span>带默认值的变量</span>
          </div>
          <div class="syntax-item">
            <code>[[if condition]]...[[/if]]</code>
            <span>条件块语法</span>
          </div>
          <div class="syntax-item">
            <code>[[for item in list]]...[[/for]]</code>
            <span>循环块语法</span>
          </div>
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="template-preview">
          <div class="preview-header">
            <span>模板预览</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ variableCount }} 个变量
            </el-tag>
          </div>
          <pre class="preview-content">{{ localData.template || '(空模板)' }}</pre>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
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
  name: '',
  template: '',
  variables: []
})

const newVariable = reactive({
  name: '',
  value: ''
})

const variableCount = computed(() => {
  const template = localData.template || ''
  const matches = template.match(/\{([^}:]+)/g) || []
  return matches.length
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      name: newVal.name || '',
      template: newVal.template || '',
      variables: newVal.variables ? JSON.parse(JSON.stringify(newVal.variables)) : []
    })
  }
}, { immediate: true, deep: true })

const addVariable = () => {
  if (!newVariable.name.trim()) return
  
  const exists = localData.variables.some(v => v.name === newVariable.name.trim())
  if (exists) {
    return
  }
  
  localData.variables.push({
    name: newVariable.name.trim(),
    value: newVariable.value || ''
  })
  
  newVariable.name = ''
  newVariable.value = ''
  handleChange()
}

const removeVariable = (index) => {
  localData.variables.splice(index, 1)
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
  width: 12px;
  height: 12px;
}

.template-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', 'JetBrains Mono', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
  }
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);

  code {
    background: var(--bg-tertiary);
    padding: 1px 4px;
    border-radius: 3px;
    font-family: 'Fira Code', monospace;
    color: var(--accent-primary);
  }
}

.variable-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .var-name-input {
    width: 120px;
  }

  .var-value-input {
    flex: 1;
  }
}

.empty-variables {
  padding: $spacing-4;
  text-align: center;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px dashed var(--border-primary);

  .empty-text {
    color: var(--text-tertiary);
    font-size: $font-size-sm;
  }
}

.add-variable-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .var-name-input {
    width: 120px;
  }

  .var-value-input {
    flex: 1;
  }
}

.syntax-help {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.syntax-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  margin-bottom: $spacing-2;
  font-size: $font-size-xs;

  &:last-child {
    margin-bottom: 0;
  }

  code {
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Fira Code', monospace;
    color: var(--accent-primary);
    min-width: 180px;
  }

  span {
    color: var(--text-secondary);
  }
}

.template-preview {
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
  overflow: hidden;

  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $spacing-2 $spacing-3;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-primary);
    font-size: $font-size-xs;
    color: var(--text-secondary);
  }

  .preview-content {
    margin: 0;
    padding: $spacing-3;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
  }
}
</style>
