<template>
  <div class="config-form form-trigger-config">
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
          表单配置
        </h4>
        
        <el-form-item label="表单标题">
          <el-input
            v-model="localData.formTitle"
            placeholder="输入表单标题"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="提交按钮文字">
          <el-input
            v-model="localData.submitButtonText"
            placeholder="提交"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="提交后重定向URL（可选）">
          <el-input
            v-model="localData.redirectUrl"
            placeholder="https://example.com/thank-you"
            @change="handleChange"
          />
          <div class="field-hint">
            用户提交表单后跳转到的页面，留空则停留在当前页面
          </div>
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          表单字段
          <el-button
            size="small"
            type="primary"
            @click="addField"
          >
            添加字段
          </el-button>
        </h4>

        <div
          v-if="localData.formFields.length === 0"
          class="empty-fields"
        >
          暂无字段，请点击"添加字段"按钮添加
        </div>

        <div
          v-for="(field, index) in localData.formFields"
          :key="index"
          class="field-item"
        >
          <div class="field-header">
            <span class="field-index">{{ index + 1 }}</span>
            <span class="field-name">{{ field.label || '未命名字段' }}</span>
            <el-button
              size="small"
              type="danger"
              @click="removeField(index)"
            >
              <X :size="14" />
            </el-button>
          </div>
          <div class="field-body">
            <el-form-item label="字段名称">
              <el-input
                v-model="field.name"
                placeholder="fieldName"
                @change="handleChange"
              >
                <template #append>
                  <el-tooltip content="用于在数据中引用此字段">
                    <Info :size="14" />
                  </el-tooltip>
                </template>
              </el-input>
            </el-form-item>
            <el-form-item label="显示标签">
              <el-input
                v-model="field.label"
                placeholder="显示给用户的标签"
                @change="handleChange"
              />
            </el-form-item>
            <el-form-item label="字段类型">
              <el-select
                v-model="field.type"
                style="width: 100%"
                @change="handleChange"
              >
                <el-option
                  label="文本输入"
                  value="text"
                />
                <el-option
                  label="文本域"
                  value="textarea"
                />
                <el-option
                  label="数字"
                  value="number"
                />
                <el-option
                  label="邮箱"
                  value="email"
                />
                <el-option
                  label="密码"
                  value="password"
                />
                <el-option
                  label="日期"
                  value="date"
                />
                <el-option
                  label="日期时间"
                  value="datetime"
                />
                <el-option
                  label="下拉选择"
                  value="select"
                />
                <el-option
                  label="多选"
                  value="checkbox"
                />
                <el-option
                  label="单选"
                  value="radio"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="必填">
              <el-switch
                v-model="field.required"
                @change="handleChange"
              />
            </el-form-item>
            <el-form-item
              v-if="['select', 'checkbox', 'radio'].includes(field.type)"
              label="选项（逗号分隔）"
            >
              <el-input
                v-model="field.options"
                placeholder="选项1, 选项2, 选项3"
                @change="handleChange"
              />
            </el-form-item>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">标题</span>
            <span class="preview-value">{{ localData.formTitle || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">字段数</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ localData.formFields.length }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">必填字段</span>
            <el-tag
              size="small"
              type="warning"
            >
              {{ requiredFieldsCount }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { X, Info } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '表单触发器',
  formTitle: '表单',
  formFields: [],
  submitButtonText: '提交',
  redirectUrl: ''
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '表单触发器',
      formTitle: newVal.formTitle || '表单',
      formFields: Array.isArray(newVal.formFields) ? newVal.formFields : [],
      submitButtonText: newVal.submitButtonText || '提交',
      redirectUrl: newVal.redirectUrl || ''
    })
  }
}, { immediate: true, deep: true })

const requiredFieldsCount = computed(() => {
  return localData.formFields.filter(f => f.required).length
})

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const addField = () => {
  localData.formFields.push({
    name: `field${localData.formFields.length + 1}`,
    label: `字段 ${localData.formFields.length + 1}`,
    type: 'text',
    required: false,
    options: ''
  })
  handleChange()
}

const removeField = (index) => {
  localData.formFields.splice(index, 1)
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

.empty-fields {
  padding: $spacing-4;
  text-align: center;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px dashed var(--border-primary);
}

.field-item {
  margin-bottom: $spacing-4;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;
}

.field-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);

  .field-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--color-primary);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
  }

  .field-name {
    flex: 1;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.field-body {
  padding: $spacing-3;
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
  justify-content: space-between;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .preview-label {
    color: var(--text-tertiary);
  }

  .preview-value {
    color: var(--text-primary);
    font-size: $font-size-xs;
  }
}
</style>
