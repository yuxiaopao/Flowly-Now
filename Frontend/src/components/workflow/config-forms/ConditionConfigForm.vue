<template>
  <div class="config-form condition-config-form">
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

      <!-- 条件类型 -->
      <div class="form-section">
        <h4 class="section-title">
          条件配置
        </h4>
        
        <el-form-item label="条件类型">
          <el-select
            v-model="localData.conditionType"
            @change="handleChange"
          >
            <el-option
              label="if/else（两分支）"
              value="if_else"
            />
            <el-option
              label="switch（多分支）"
              value="switch"
            />
            <el-option
              label="多条件组合"
              value="multiple"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="逻辑运算符">
          <el-radio-group
            v-model="localData.logicalOperator"
            @change="handleChange"
          >
            <el-radio value="and">
              AND（所有条件都满足）
            </el-radio>
            <el-radio value="or">
              OR（任一条件满足）
            </el-radio>
          </el-radio-group>
        </el-form-item>
      </div>

      <!-- 分支配置 -->
      <div class="form-section">
        <h4 class="section-title">
          分支配置
        </h4>
        
        <div class="branches-list">
          <div 
            v-for="(branch, index) in localData.branches" 
            :key="index"
            class="branch-card"
          >
            <div class="branch-header">
              <span class="branch-name">{{ branch.name || `分支 ${index + 1}` }}</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ branch.type === 'true' ? '条件成立' : '条件不成立' }}
              </el-tag>
              <el-button 
                v-if="localData.conditionType !== 'if_else'"
                link 
                type="danger" 
                size="small"
                @click="removeBranch(index)"
              >
                <Trash2 class="icon-sm" />
              </el-button>
            </div>

            <el-form-item label="分支名称">
              <el-input 
                v-model="branch.name" 
                :placeholder="index === 0 ? '条件成立时' : '条件不成立时'"
                size="small"
                @change="handleChange"
              />
            </el-form-item>

            <el-form-item label="条件表达式">
              <el-input
                v-model="branch.condition"
                placeholder="例如: output.length > 100"
                class="expression-input"
                @change="handleChange"
              />
              <div class="field-hint">
                支持 JavaScript 表达式，可使用 <code>{变量名}</code> 引用变量
              </div>
            </el-form-item>
          </div>
        </div>

        <el-button 
          v-if="localData.conditionType === 'multiple'"
          type="primary" 
          size="small" 
          plain
          class="add-branch-btn"
          @click="addBranch"
        >
          <Plus class="icon" /> 添加分支
        </el-button>
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
            :key="index"
            class="preview-branch"
          >
            <div
              class="branch-indicator"
              :class="branch.type"
            />
            <span class="branch-label">{{ branch.name || `分支 ${index + 1}` }}</span>
          </div>
          <div class="preview-branch default">
            <div class="branch-indicator" />
            <span class="branch-label">{{ localData.defaultBranch || '默认' }}</span>
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
  conditionType: 'if_else',
  logicalOperator: 'and',
  branches: [
    { name: '条件成立', condition: '', type: 'true' },
    { name: '条件不成立', condition: '', type: 'false' }
  ],
  defaultBranch: '默认'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      conditionType: newVal.conditionType || 'if_else',
      logicalOperator: newVal.logicalOperator || 'and',
      branches: newVal.branches ? JSON.parse(JSON.stringify(newVal.branches)) : [
        { name: '条件成立', condition: '', type: 'true' },
        { name: '条件不成立', condition: '', type: 'false' }
      ],
      defaultBranch: newVal.defaultBranch || '默认'
    })
  }
}, { immediate: true, deep: true })

const addBranch = () => {
  localData.branches.push({
    name: `条件 ${localData.branches.length + 1}`,
    condition: '',
    type: 'custom'
  })
  handleChange()
}

const removeBranch = (index) => {
  if (localData.branches.length > 2) {
    localData.branches.splice(index, 1)
    handleChange()
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

.icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.icon-sm {
  width: 12px;
  height: 12px;
}

.expression-input {
  :deep(.el-input__inner) {
    font-family: 'Fira Code', monospace;
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

.branches-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
  margin-bottom: $spacing-3;
}

.branch-card {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .branch-header {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    margin-bottom: $spacing-3;

    .branch-name {
      font-weight: $font-weight-medium;
      color: var(--text-primary);
      flex: 1;
    }
  }
}

.add-branch-btn {
  width: 100%;
}

.branch-preview {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.preview-branch {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
  font-size: $font-size-sm;

  .branch-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--accent-primary);

    &.true {
      background: $color-success;
    }

    &.false {
      background: $color-error;
    }
  }

  .branch-label {
    color: var(--text-primary);
  }

  &.default {
    opacity: 0.7;

    .branch-indicator {
      background: var(--text-tertiary);
    }
  }
}
</style>
