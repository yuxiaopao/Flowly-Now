<template>
  <div class="config-form variable-config-form">
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

      <!-- 变量操作 -->
      <div class="form-section">
        <h4 class="section-title">
          变量操作
        </h4>
        
        <el-form-item label="操作类型">
          <el-select
            v-model="localData.operation"
            @change="handleChange"
          >
            <el-option
              label="设置变量"
              value="set"
            />
            <el-option
              label="获取变量"
              value="get"
            />
            <el-option
              label="删除变量"
              value="delete"
            />
            <el-option
              label="增加数值"
              value="increment"
            />
            <el-option
              label="减少数值"
              value="decrement"
            />
            <el-option
              label="追加到数组"
              value="push"
            />
            <el-option
              label="从数组移除"
              value="pop"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="变量名称">
          <el-input
            v-model="localData.variableName"
            placeholder="变量名，例如: result"
            @change="handleChange"
          />
          <div class="field-hint">
            变量名只能包含字母、数字和下划线
          </div>
        </el-form-item>

        <el-form-item label="变量作用域">
          <el-select
            v-model="localData.scope"
            @change="handleChange"
          >
            <el-option
              label="局部变量"
              value="local"
            />
            <el-option
              label="全局变量"
              value="global"
            />
          </el-select>
          <div class="field-hint">
            局部变量仅在当前工作流执行期间有效
          </div>
        </el-form-item>
      </div>

      <!-- 赋值配置 -->
      <div
        v-if="needsValue"
        class="form-section"
      >
        <h4 class="section-title">
          赋值配置
        </h4>
        
        <el-form-item label="值类型">
          <el-radio-group
            v-model="localData.valueType"
            @change="handleChange"
          >
            <el-radio value="static">
              静态值
            </el-radio>
            <el-radio value="input">
              输入变量
            </el-radio>
            <el-radio value="expression">
              表达式
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item
          v-if="localData.valueType === 'static'"
          label="静态值"
        >
          <el-input
            v-model="localData.variableValue"
            type="textarea"
            :rows="3"
            placeholder="输入静态值"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.valueType === 'input'"
          label="输入变量"
        >
          <el-input
            v-model="localData.inputVariable"
            placeholder="上游节点的输出变量名"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.valueType === 'expression'"
          label="表达式"
        >
          <el-input
            v-model="localData.expression"
            type="textarea"
            :rows="3"
            placeholder="例如: {input} + 1 或 data.name"
            class="expression-input"
            @change="handleChange"
          />
          <div class="field-hint">
            支持 <code>{变量名}</code> 引用其他变量
          </div>
        </el-form-item>
      </div>

      <!-- 批量赋值 -->
      <div class="form-section">
        <h4 class="section-title">
          批量赋值
        </h4>
        
        <div class="assignments-list">
          <div 
            v-for="(assignment, index) in localData.assignments" 
            :key="index"
            class="assignment-item"
          >
            <el-input
              v-model="assignment.name"
              placeholder="变量名"
              size="small"
              class="assign-name"
              @change="handleChange"
            />
            <el-select
              v-model="assignment.source"
              size="small"
              @change="handleChange"
            >
              <el-option
                label="静态值"
                value="static"
              />
              <el-option
                label="输入变量"
                value="input"
              />
              <el-option
                label="表达式"
                value="expression"
              />
            </el-select>
            <el-input
              v-model="assignment.value"
              :placeholder="assignment.source === 'static' ? '静态值' : '值或变量名'"
              size="small"
              class="assign-value"
              @change="handleChange"
            />
            <el-button 
              link 
              type="danger" 
              size="small"
              @click="removeAssignment(index)"
            >
              <Minus class="icon-sm" />
            </el-button>
          </div>
        </div>
        
        <el-button
          size="small"
          class="add-btn"
          @click="addAssignment"
        >
          <Plus class="icon" /> 添加赋值
        </el-button>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          变量预览
        </h4>
        <div class="variable-preview">
          <div
            v-if="localData.variableName"
            class="preview-row"
          >
            <span class="preview-label">变量:</span>
            <code class="preview-value">{{ localData.variableName }}</code>
            <el-tag
              size="small"
              type="info"
            >
              {{ scopeLabel }}
            </el-tag>
          </div>
          <div
            v-if="localData.operation !== 'get'"
            class="preview-row"
          >
            <span class="preview-label">操作:</span>
            <span class="preview-value">{{ operationLabel }}</span>
          </div>
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
  operation: 'set',
  variableName: '',
  variableValue: '',
  inputVariable: '',
  expression: '',
  valueType: 'static',
  scope: 'local',
  assignments: []
})

const needsValue = computed(() => {
  return ['set', 'increment', 'decrement', 'push'].includes(localData.operation)
})

const operationLabel = computed(() => {
  const labels = {
    set: '设置为',
    get: '获取',
    delete: '删除',
    increment: '增加',
    decrement: '减少',
    push: '追加到',
    pop: '从数组移除'
  }
  return labels[localData.operation] || localData.operation
})

const scopeLabel = computed(() => {
  return localData.scope === 'local' ? '局部' : '全局'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      operation: newVal.operation || 'set',
      variableName: newVal.variableName || '',
      variableValue: newVal.variableValue || '',
      inputVariable: newVal.inputVariable || '',
      expression: newVal.expression || '',
      valueType: newVal.valueType || 'static',
      scope: newVal.scope || 'local',
      assignments: newVal.assignments ? JSON.parse(JSON.stringify(newVal.assignments)) : []
    })
  }
}, { immediate: true, deep: true })

const addAssignment = () => {
  localData.assignments.push({ name: '', source: 'static', value: '' })
  handleChange()
}

const removeAssignment = (index) => {
  localData.assignments.splice(index, 1)
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

.expression-input {
  :deep(.el-input__inner) {
    font-family: 'Fira Code', monospace;
  }
}

.assignments-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
}

.assignment-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .assign-name {
    width: 120px;
  }

  .assign-value {
    flex: 1;
  }
}

.add-btn {
  width: 100%;
}

.variable-preview {
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
    min-width: 60px;
  }

  .preview-value {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--text-primary);
  }

  code {
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    color: var(--accent-primary);
  }
}
</style>
