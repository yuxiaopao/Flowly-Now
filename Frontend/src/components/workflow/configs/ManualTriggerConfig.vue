<template>
  <div class="config-form manual-trigger-config">
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
        <el-form-item label="描述">
          <el-input
            v-model="localData.description"
            type="textarea"
            :rows="2"
            placeholder="描述此触发器的用途"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          输入参数
        </h4>
        <div class="field-hint">
          定义手动触发时可以传入的参数，工作流执行时会使用这些参数作为初始输入数据。
        </div>

        <div
          v-if="!hasSchema"
          class="schema-empty"
        >
          <p>尚未定义输入参数</p>
          <el-button
            type="primary"
            size="small"
            @click="initSchema"
          >
            定义参数
          </el-button>
        </div>

        <div
          v-else
          class="schema-editor"
        >
          <div
            v-for="(param, key) in localData.inputSchema.properties"
            :key="key"
            class="param-item"
          >
            <div class="param-header">
              <span class="param-name">{{ key }}</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ localData.inputSchema.required?.includes(key) ? '必填' : '可选' }}
              </el-tag>
              <el-button
                size="small"
                type="danger"
                @click="removeParam(key)"
              >
                <X :size="14" />
              </el-button>
            </div>
            <div class="param-body">
              <el-form-item label="类型">
                <el-select
                  v-model="param.type"
                  style="width: 100%"
                  @change="handleChange"
                >
                  <el-option
                    label="字符串"
                    value="string"
                  />
                  <el-option
                    label="数字"
                    value="number"
                  />
                  <el-option
                    label="布尔值"
                    value="boolean"
                  />
                  <el-option
                    label="对象"
                    value="object"
                  />
                  <el-option
                    label="数组"
                    value="array"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="描述">
                <el-input
                  v-model="param.description"
                  placeholder="参数描述"
                  @change="handleChange"
                />
              </el-form-item>
              <el-form-item label="默认值">
                <el-input
                  v-model="param.default"
                  placeholder="默认值（可选）"
                  @change="handleChange"
                />
              </el-form-item>
              <el-form-item label="必填">
                <el-switch
                  :model-value="localData.inputSchema.required?.includes(key)"
                  @change="(val) => toggleRequired(key, val)"
                />
              </el-form-item>
            </div>
          </div>

          <el-button
            type="primary"
            plain
            size="small"
            @click="addParam"
          >
            添加参数
          </el-button>
        </div>
      </div>

      <div class="form-section">
        <h4 class="section-title">
          预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">参数数量</span>
            <el-tag
              size="small"
              type="info"
            >
              {{ paramCount }}
            </el-tag>
          </div>
          <div class="preview-row">
            <span class="preview-label">必填参数</span>
            <el-tag
              size="small"
              type="warning"
            >
              {{ requiredParamCount }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '手动触发器',
  description: '',
  inputSchema: {}
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '手动触发器',
      description: newVal.description || '',
      inputSchema: newVal.inputSchema || {}
    })
  }
}, { immediate: true, deep: true })

const hasSchema = computed(() => {
  return localData.inputSchema && Object.keys(localData.inputSchema).length > 0 &&
         localData.inputSchema.properties && Object.keys(localData.inputSchema.properties).length > 0
})

const paramCount = computed(() => {
  if (!hasSchema.value) return 0
  return Object.keys(localData.inputSchema.properties || {}).length
})

const requiredParamCount = computed(() => {
  if (!hasSchema.value) return 0
  return (localData.inputSchema.required || []).length
})

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const initSchema = () => {
  localData.inputSchema = {
    type: 'object',
    properties: {},
    required: []
  }
  handleChange()
}

const addParam = () => {
  if (!hasSchema.value) {
    initSchema()
  }
  const paramName = `param${Object.keys(localData.inputSchema.properties).length + 1}`
  localData.inputSchema.properties[paramName] = {
    type: 'string',
    description: ''
  }
  handleChange()
}

const removeParam = (key) => {
  delete localData.inputSchema.properties[key]
  if (localData.inputSchema.required) {
    localData.inputSchema.required = localData.inputSchema.required.filter(k => k !== key)
  }
  handleChange()
}

const toggleRequired = (key, required) => {
  if (!localData.inputSchema.required) {
    localData.inputSchema.required = []
  }
  if (required) {
    if (!localData.inputSchema.required.includes(key)) {
      localData.inputSchema.required.push(key)
    }
  } else {
    localData.inputSchema.required = localData.inputSchema.required.filter(k => k !== key)
  }
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
}

.field-hint {
  margin-bottom: $spacing-3;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  line-height: 1.5;
}

.schema-empty {
  padding: $spacing-4;
  text-align: center;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px dashed var(--border-primary);

  p {
    margin: 0 0 $spacing-3;
    color: var(--text-tertiary);
    font-size: $font-size-sm;
  }
}

.schema-editor {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  padding: $spacing-3;
}

.param-item {
  margin-bottom: $spacing-4;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;

  &:last-of-type {
    margin-bottom: $spacing-3;
  }
}

.param-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);

  .param-name {
    flex: 1;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.param-body {
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
}
</style>
