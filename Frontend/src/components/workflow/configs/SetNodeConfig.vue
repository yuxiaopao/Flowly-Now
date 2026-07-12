<template>
  <div class="config-form set-node-config">
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
          变量赋值
          <el-button
            size="small"
            type="primary"
            @click="addAssignment"
          >
            添加变量
          </el-button>
        </h4>

        <el-form-item label="赋值模式">
          <el-select
            v-model="localData.mode"
            style="width: 100%"
            @change="handleChange"
          >
            <el-option
              label="替换"
              value="replace"
            >
              <div class="option-content">
                <span class="option-label">替换</span>
                <span class="option-desc">直接覆盖现有值</span>
              </div>
            </el-option>
            <el-option
              label="追加"
              value="append"
            >
              <div class="option-content">
                <span class="option-label">追加</span>
                <span class="option-desc">如果变量是数组则追加，否则替换</span>
              </div>
            </el-option>
            <el-option
              label="保留"
              value="keep"
            >
              <div class="option-content">
                <span class="option-label">保留</span>
                <span class="option-desc">如果变量已存在则保留原值</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <div
          v-if="localData.assignments.length === 0"
          class="empty-assignments"
        >
          暂无变量赋值，请点击"添加变量"按钮添加
        </div>

        <div
          v-for="(assignment, index) in localData.assignments"
          :key="index"
          class="assignment-item"
        >
          <div class="assignment-header">
            <span class="assignment-index">{{ index + 1 }}</span>
            <span class="assignment-name">{{ assignment.name || '未命名' }}</span>
            <el-button
              size="small"
              type="danger"
              @click="removeAssignment(index)"
            >
              <X :size="14" />
            </el-button>
          </div>
          <div class="assignment-body">
            <el-form-item label="变量名">
              <el-input
                v-model="assignment.name"
                placeholder="variableName"
                @change="handleChange"
              >
                <template #append>
                  <el-tooltip content="用于在后续节点中通过 $vars.variableName 引用">
                    <Info :size="14" />
                  </el-tooltip>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="值">
              <el-input
                v-model="assignment.value"
                placeholder="变量的值，支持表达式"
                @change="handleChange"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select
                v-model="assignment.type"
                style="width: 100%"
                @change="handleChange"
              >
                <el-option
                  label="字符串"
                  value="string"
                >
                  <span>string - 文本值</span>
                </el-option>
                <el-option
                  label="数字"
                  value="number"
                >
                  <span>number - 数值</span>
                </el-option>
                <el-option
                  label="布尔值"
                  value="boolean"
                >
                  <span>boolean - true/false</span>
                </el-option>
                <el-option
                  label="表达式"
                  value="expression"
                >
                  <span>expression - JavaScript 表达式</span>
                </el-option>
                <el-option
                  label="JSON"
                  value="json"
                >
                  <span>json - JSON 对象或数组</span>
                </el-option>
              </el-select>
            </el-form-item>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          使用示例
        </h4>
        <div class="example-code">
          <pre>// 设置变量
$vars.name = "Alice"
$vars.count = 42
$vars.active = true

// 引用变量
{"user": $vars.name}</pre>
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
  label: '设置变量',
  assignments: [],
  mode: 'replace'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '设置变量',
      assignments: Array.isArray(newVal.assignments) ? newVal.assignments : [],
      mode: newVal.mode || 'replace'
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const addAssignment = () => {
  localData.assignments.push({
    name: '',
    value: '',
    type: 'string'
  })
  handleChange()
}

const removeAssignment = (index) => {
  localData.assignments.splice(index, 1)
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

.option-content {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .option-label {
    font-weight: $font-weight-medium;
  }

  .option-desc {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.empty-assignments {
  padding: $spacing-4;
  text-align: center;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px dashed var(--border-primary);
}

.assignment-item {
  margin-bottom: $spacing-4;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;
}

.assignment-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);

  .assignment-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #f97316;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
  }

  .assignment-name {
    flex: 1;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.assignment-body {
  padding: $spacing-3;
}

.example-code {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  padding: $spacing-3;

  pre {
    margin: 0;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--text-secondary);
    line-height: 1.6;
    white-space: pre-wrap;
  }
}
</style>
