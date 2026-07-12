<template>
  <div class="config-form switch-config-form">
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

      <!-- 分支配置 -->
      <div class="form-section">
        <div class="section-header">
          <h4 class="section-title">
            分支配置
          </h4>
          <el-button 
            type="primary" 
            link 
            size="small" 
            @click="addBranch"
          >
            <Plus class="icon" /> 添加分支
          </el-button>
        </div>

        <div class="branches-list">
          <el-collapse v-model="expandedBranches">
            <el-collapse-item
              v-for="(branch, index) in localData.branches"
              :key="branch.id"
              :name="branch.id"
            >
              <template #title>
                <div class="branch-header">
                  <span 
                    class="branch-color" 
                    :style="{ backgroundColor: getBranchColor(index) }"
                  />
                  <span class="branch-name">
                    {{ branch.label || `分支 ${index + 1}` }}
                  </span>
                  <el-tag
                    size="small"
                    type="info"
                  >
                    {{ getConditionTypeLabel(branch.conditionType) }}
                  </el-tag>
                  <el-button 
                    link 
                    type="danger" 
                    size="small"
                    class="remove-btn"
                    @click.stop="removeBranch(index)"
                  >
                    <Trash2 class="icon-sm" />
                  </el-button>
                </div>
              </template>

              <div class="branch-config">
                <el-form-item label="分支名称">
                  <el-input 
                    v-model="branch.label" 
                    :placeholder="`分支 ${index + 1}`"
                    @change="handleChange"
                  />
                </el-form-item>

                <el-form-item label="条件类型">
                  <el-radio-group
                    v-model="branch.conditionType"
                    size="small"
                    @change="handleChange"
                  >
                    <el-radio-button value="expression">
                      表达式
                    </el-radio-button>
                    <el-radio-button value="comparison">
                      比较
                    </el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <!-- 表达式模式 -->
                <el-form-item 
                  v-if="branch.conditionType === 'expression'" 
                  label="表达式"
                  class="expression-field"
                >
                  <el-input
                    v-model="branch.expression"
                    placeholder="例如: data.status == 'active' and data.count > 0"
                    type="textarea"
                    :rows="3"
                    class="code-input"
                    @change="handleChange"
                  />
                  <div class="field-hint">
                    支持 Python 表达式，可使用 data.field 访问输入数据
                  </div>
                </el-form-item>

                <!-- 比较模式 -->
                <template v-if="branch.conditionType === 'comparison'">
                  <el-row :gutter="8">
                    <el-col :span="10">
                      <el-form-item label="字段">
                        <el-input 
                          v-model="branch.field" 
                          placeholder="data.status"
                          @change="handleChange"
                        />
                      </el-form-item>
                    </el-col>
                    <el-col :span="7">
                      <el-form-item label="操作符">
                        <el-select
                          v-model="branch.operator"
                          @change="handleChange"
                        >
                          <el-option
                            label="等于"
                            value="equals"
                          />
                          <el-option
                            label="不等于"
                            value="not_equals"
                          />
                          <el-option
                            label="包含"
                            value="contains"
                          />
                          <el-option
                            label="大于"
                            value="greater_than"
                          />
                          <el-option
                            label="小于"
                            value="less_than"
                          />
                          <el-option
                            label="大于等于"
                            value="greater_than_or_equal"
                          />
                          <el-option
                            label="小于等于"
                            value="less_than_or_equal"
                          />
                          <el-option
                            label="正则匹配"
                            value="matches_regex"
                          />
                          <el-option
                            label="为空"
                            value="is_empty"
                          />
                          <el-option
                            label="不为空"
                            value="is_not_empty"
                          />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="7">
                      <el-form-item label="比较值">
                        <el-input 
                          v-model="branch.value" 
                          placeholder="值"
                          @change="handleChange"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                </template>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <!-- 默认分支 -->
      <div class="form-section">
        <h4 class="section-title">
          默认分支
        </h4>
        <el-form-item label="默认分支名称">
          <el-input 
            v-model="localData.defaultBranch" 
            placeholder="当所有条件都不满足时执行"
            @change="handleChange"
          />
        </el-form-item>
        <div class="field-hint">
          当没有分支条件匹配时，执行默认分支
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          分支预览
        </h4>
        <div class="branch-preview">
          <div 
            v-for="(branch, index) in localData.branches" 
            :key="branch.id"
            class="preview-branch"
            :style="{ borderColor: getBranchColor(index), backgroundColor: getBranchColor(index) + '15' }"
          >
            <span :style="{ color: getBranchColor(index) }">
              {{ branch.label || `分支 ${index + 1}` }}
            </span>
            <span class="preview-type">{{ getConditionTypeLabel(branch.conditionType) }}</span>
          </div>
          <div
            v-if="localData.defaultBranch"
            class="preview-branch default"
          >
            <span>{{ localData.defaultBranch }}</span>
            <span class="preview-type">默认</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'

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
  branches: [],
  defaultBranch: '默认'
})

const expandedBranches = ref([])

const branchColors = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#06b6d4',
  '#8b5cf6',
  '#14b8a6'
]

const getBranchColor = (index) => {
  return branchColors[index % branchColors.length]
}

const getConditionTypeLabel = (type) => {
  const labels = {
    expression: '表达式',
    comparison: '比较'
  }
  return labels[type] || '表达式'
}

const initDefaultData = () => {
  if (!localData.branches || localData.branches.length === 0) {
    localData.branches = [
      { id: 'branch_1', label: '条件 1', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' },
      { id: 'branch_2', label: '条件 2', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' }
    ]
    expandedBranches.value = ['branch_1', 'branch_2']
  }
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      branches: newVal.branches ? JSON.parse(JSON.stringify(newVal.branches)) : [],
      defaultBranch: newVal.defaultBranch || '默认'
    })
    initDefaultData()
    
    if (localData.branches.length > 0 && expandedBranches.value.length === 0) {
      expandedBranches.value = localData.branches.map(b => b.id)
    }
  }
}, { immediate: true, deep: true })

const addBranch = () => {
  const newId = `branch_${Date.now()}`
  const newIndex = localData.branches.length + 1
  localData.branches.push({
    id: newId,
    label: `条件 ${newIndex}`,
    conditionType: 'expression',
    expression: '',
    field: '',
    operator: 'equals',
    value: ''
  })
  expandedBranches.value.push(newId)
  handleChange()
}

const removeBranch = (index) => {
  if (localData.branches.length > 2) {
    const removedId = localData.branches[index].id
    localData.branches.splice(index, 1)
    expandedBranches.value = expandedBranches.value.filter(id => id !== removedId)
    handleChange()
  } else {
    console.warn('至少需要保留两个分支')
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

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-3;

  .section-title {
    margin: 0;
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

.branches-list {
  :deep(.el-collapse) {
    border: none;
  }

  :deep(.el-collapse-item__header) {
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: $radius-md;
    padding: $spacing-2 $spacing-3;
    margin-bottom: $spacing-2;
    height: auto;
    line-height: normal;
  }

  :deep(.el-collapse-item__wrap) {
    background: transparent;
    border: none;
    border-top: none;
  }

  :deep(.el-collapse-item__content) {
    padding: $spacing-3;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-top: none;
    border-radius: 0 0 $radius-md $radius-md;
    margin-top: -$spacing-1;
  }

  :deep(.el-collapse-item) {
    margin-bottom: $spacing-2;
  }
}

.branch-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  width: 100%;

  .branch-color {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    flex-shrink: 0;
  }

  .branch-name {
    font-weight: $font-weight-medium;
    color: var(--text-primary);
    flex: 1;
  }

  .remove-btn {
    padding: 4px;
    margin-left: auto;
  }
}

.branch-config {
  :deep(.el-form-item) {
    margin-bottom: $spacing-3;
  }

  :deep(.el-form-item__label) {
    font-size: $font-size-xs;
    color: var(--text-secondary);
  }
}

.expression-field {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', 'JetBrains Mono', monospace;
    font-size: $font-size-xs;
  }
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.branch-preview {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.preview-branch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-2 $spacing-3;
  border: 1px solid;
  border-radius: $radius-md;
  font-size: $font-size-sm;

  &.default {
    border-color: var(--text-tertiary);
    background: var(--bg-tertiary);
    color: var(--text-secondary);
  }
}

.preview-type {
  font-size: $font-size-xs;
  opacity: 0.7;
}

.code-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.5;
  }
}
</style>
