<template>
  <div class="config-form filter-config">
    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
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
      </div>

      <div class="form-section">
        <h4 class="section-title">
          筛选条件
          <el-button
            size="small"
            type="primary"
            @click="addCondition"
          >
            添加条件
          </el-button>
        </h4>

        <el-form-item label="条件组合方式">
          <el-radio-group
            v-model="localData.combinator"
            @change="handleChange"
          >
            <el-radio label="and">
              满足所有条件 (AND)
            </el-radio>
            <el-radio label="or">
              满足任一条件 (OR)
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="结果数量限制">
          <el-input-number
            v-model="localData.limit"
            :min="0"
            :max="10000"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            0 表示不限制
          </div>
        </el-form-item>

        <div
          v-if="localData.conditions.length === 0"
          class="empty-conditions"
        >
          暂无筛选条件，请点击"添加条件"按钮添加
        </div>

        <div
          v-for="(condition, index) in localData.conditions"
          :key="index"
          class="condition-item"
        >
          <div class="condition-header">
            <span class="condition-index">{{ index + 1 }}</span>
            <span
              v-if="index > 0"
              class="condition-logic"
            >{{ localData.combinator === 'and' ? '且' : '或' }}</span>
            <el-button
              size="small"
              type="danger"
              @click="removeCondition(index)"
            >
              <X :size="14" />
            </el-button>
          </div>
          <div class="condition-body">
            <el-form-item label="字段">
              <el-input
                v-model="condition.field"
                placeholder="data.fieldName"
                @change="handleChange"
              >
                <template #append>
                  <el-tooltip content="要检查的字段路径，支持嵌套如 user.name">
                    <Info :size="14" />
                  </el-tooltip>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="运算符">
              <el-select
                v-model="condition.operator"
                style="width: 100%"
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
                  label="不包含"
                  value="not_contains"
                />
                <el-option
                  label="开头是"
                  value="starts_with"
                />
                <el-option
                  label="结尾是"
                  value="ends_with"
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
                  label="为空"
                  value="is_empty"
                />
                <el-option
                  label="不为空"
                  value="is_not_empty"
                />
              </el-select>
            </el-form-item>
            <el-form-item
              v-if="!['is_empty', 'is_not_empty'].includes(condition.operator)"
              label="比较值"
            >
              <el-input
                v-model="condition.value"
                placeholder="比较的值"
                @change="handleChange"
              />
            </el-form-item>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          输出说明
        </h4>
        <div class="output-info">
          <div class="output-item matched">
            <div class="output-icon">
              1
            </div>
            <div class="output-desc">
              <strong>匹配</strong>
              <span>满足条件的输出到右侧连接</span>
            </div>
          </div>
          <div class="output-item not-matched">
            <div class="output-icon">
              2
            </div>
            <div class="output-desc">
              <strong>不匹配</strong>
              <span>不满足条件的输出到底部连接</span>
            </div>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { X, Info } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '数据筛选',
  conditions: [],
  combinator: 'and',
  limit: 0
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '数据筛选',
      conditions: Array.isArray(newVal.conditions) ? newVal.conditions : [],
      combinator: newVal.combinator || 'and',
      limit: newVal.limit ?? 0
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const addCondition = () => {
  localData.conditions.push({
    field: '',
    operator: 'equals',
    value: '',
    logic: 'and'
  })
  handleChange()
}

const removeCondition = (index) => {
  localData.conditions.splice(index, 1)
  handleChange()
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
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.empty-conditions {
  padding: $spacing-4;
  text-align: center;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px dashed var(--border-primary);
}

.condition-item {
  margin-bottom: $spacing-4;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;
}

.condition-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);

  .condition-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #ec4899;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
  }

  .condition-logic {
    flex: 1;
    font-size: $font-size-xs;
    color: var(--text-tertiary);
    text-align: center;
  }
}

.condition-body {
  padding: $spacing-3;
}

.output-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.output-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-secondary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .output-icon {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
    color: white;
    flex-shrink: 0;
  }

  &.matched .output-icon {
    background: #10b981;
  }

  &.not-matched .output-icon {
    background: #ef4444;
  }

  .output-desc {
    display: flex;
    flex-direction: column;
    gap: 2px;

    strong {
      font-size: $font-size-sm;
      color: var(--text-primary);
    }

    span {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
    }
  }
}
</style>
