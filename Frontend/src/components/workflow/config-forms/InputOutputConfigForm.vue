<template>
  <div class="config-form input-output-config-form">
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

      <!-- 输入节点配置 -->
      <template v-if="nodeMode === 'input'">
        <div class="form-section">
          <h4 class="section-title">
            输入配置
          </h4>
          
          <el-form-item
            label="变量名"
            required
          >
            <el-input
              v-model="localData.variableName"
              placeholder="定义此输入的参数名"
              @change="handleChange"
            />
            <div class="field-hint">
              工作流外部可通过此变量名传入数据
            </div>
          </el-form-item>

          <el-form-item label="提示文本">
            <el-input
              v-model="localData.prompt"
              type="textarea"
              :rows="3"
              placeholder="给用户/调用者的提示信息"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="输入类型">
            <el-select
              v-model="localData.inputType"
              @change="handleChange"
            >
              <el-option
                label="文本"
                value="text"
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
                label="JSON 对象"
                value="json"
              />
              <el-option
                label="文件"
                value="file"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="是否必填">
            <el-switch
              v-model="localData.required"
              @change="handleChange"
            />
          </el-form-item>

          <el-form-item label="默认值">
            <el-input
              v-model="localData.default"
              type="textarea"
              :rows="2"
              placeholder="默认值（可选）"
              @change="handleChange"
            />
            <div class="field-hint">
              当未提供输入时使用此默认值
            </div>
          </el-form-item>
        </div>
      </template>

      <!-- 输出节点配置 -->
      <template v-else>
        <div class="form-section">
          <h4 class="section-title">
            输出配置
          </h4>
          
          <el-form-item label="输出模板">
            <el-input
              v-model="localData.template"
              type="textarea"
              :rows="6"
              placeholder="输出模板，支持 {变量名} 占位符&#10;&#10;示例：&#10;处理结果：{result}&#10;状态：{status}"
              class="template-input"
              @change="handleChange"
            />
            <div class="field-hint">
              支持使用 <code>{变量名}</code> 语法引用工作流中的变量
            </div>
          </el-form-item>

          <el-form-item label="输出变量">
            <el-input
              v-model="localData.outputVariable"
              placeholder="输出变量名"
              @change="handleChange"
            />
            <div class="field-hint">
              指定此输出的变量名，供外部调用者获取结果
            </div>
          </el-form-item>

          <el-form-item label="输出格式">
            <el-select
              v-model="localData.format"
              @change="handleChange"
            >
              <el-option
                label="纯文本"
                value="text"
              />
              <el-option
                label="JSON"
                value="json"
              />
              <el-option
                label="Markdown"
                value="markdown"
              />
              <el-option
                label="XML"
                value="xml"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="响应头">
            <div class="key-value-list">
              <div 
                v-for="(header, index) in responseHeaders" 
                :key="index"
                class="key-value-row"
              >
                <el-input
                  v-model="header.key"
                  placeholder="Header-Name"
                  size="small"
                  class="key-input"
                  @change="updateResponseHeaders"
                />
                <el-input
                  v-model="header.value"
                  placeholder="Header Value"
                  size="small"
                  class="value-input"
                  @change="updateResponseHeaders"
                />
                <el-button 
                  link 
                  type="danger" 
                  size="small"
                  @click="removeResponseHeader(index)"
                >
                  <Minus class="icon-sm" />
                </el-button>
              </div>
              <el-button
                size="small"
                @click="addResponseHeader"
              >
                <Plus class="icon" /> 添加响应头
              </el-button>
            </div>
          </el-form-item>
        </div>
      </template>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <template v-if="nodeMode === 'input'">
            <div class="preview-row">
              <span class="preview-label">变量名:</span>
              <code class="preview-value">{{ localData.variableName || '(未设置)' }}</code>
            </div>
            <div class="preview-row">
              <span class="preview-label">类型:</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ inputTypeLabel }}
              </el-tag>
            </div>
            <div class="preview-row">
              <span class="preview-label">必填:</span>
              <el-tag
                size="small"
                :type="localData.required ? 'danger' : 'info'"
              >
                {{ localData.required ? '是' : '否' }}
              </el-tag>
            </div>
          </template>
          <template v-else>
            <div class="preview-row">
              <span class="preview-label">输出变量:</span>
              <code class="preview-value">{{ localData.outputVariable || '(未设置)' }}</code>
            </div>
            <div class="preview-row">
              <span class="preview-label">格式:</span>
              <el-tag
                size="small"
                type="info"
              >
                {{ formatLabel }}
              </el-tag>
            </div>
          </template>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Plus, Minus } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  nodeMode: {
    type: String,
    default: 'input',
    validator: (val) => ['input', 'output'].includes(val)
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  // Input
  variableName: '',
  prompt: '',
  required: false,
  default: null,
  inputType: 'text',
  // Output
  template: '',
  outputVariable: '',
  format: 'text',
  responseHeaders: []
})

const responseHeaders = ref([])

const inputTypeLabel = computed(() => {
  const labels = {
    text: '文本',
    number: '数字',
    boolean: '布尔值',
    json: 'JSON',
    file: '文件'
  }
  return labels[localData.inputType] || '文本'
})

const formatLabel = computed(() => {
  const labels = {
    text: '纯文本',
    json: 'JSON',
    markdown: 'Markdown',
    xml: 'XML'
  }
  return labels[localData.format] || '纯文本'
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    if (props.nodeMode === 'input') {
      Object.assign(localData, {
        label: newVal.label || '',
        description: newVal.description || '',
        variableName: newVal.variableName || '',
        prompt: newVal.prompt || '',
        required: newVal.required || false,
        default: newVal.default || null,
        inputType: newVal.inputType || 'text'
      })
    } else {
      // Parse response headers
      let headers = []
      if (newVal.responseHeaders) {
        if (typeof newVal.responseHeaders === 'string') {
          try {
            headers = Object.entries(JSON.parse(newVal.responseHeaders))
          } catch {
            headers = []
          }
        } else if (typeof newVal.responseHeaders === 'object') {
          headers = Object.entries(newVal.responseHeaders)
        }
      }
      
      Object.assign(localData, {
        label: newVal.label || '',
        description: newVal.description || '',
        template: newVal.template || '',
        outputVariable: newVal.outputVariable || '',
        format: newVal.format || 'text'
      })
      
      responseHeaders.value = headers
    }
  }
}, { immediate: true, deep: true })

const addResponseHeader = () => {
  responseHeaders.value.push({ key: '', value: '' })
}

const removeResponseHeader = (index) => {
  responseHeaders.value.splice(index, 1)
  updateResponseHeaders()
}

const updateResponseHeaders = () => {
  const headersObj = {}
  responseHeaders.value.forEach(h => {
    if (h.key) {
      headersObj[h.key] = h.value
    }
  })
  localData.responseHeaders = headersObj
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

.template-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
  }
}

.key-value-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.key-value-row {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .key-input {
    width: 150px;
  }

  .value-input {
    flex: 1;
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
    min-width: 60px;
  }

  .preview-value {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--text-primary);
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 3px;
  }

  code {
    color: var(--accent-primary);
  }
}
</style>
