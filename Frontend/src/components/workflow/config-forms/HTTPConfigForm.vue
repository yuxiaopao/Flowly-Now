<template>
  <div class="config-form http-config-form">
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

      <!-- 请求配置 -->
      <div class="form-section">
        <h4 class="section-title">
          请求配置
        </h4>
        
        <el-form-item label="请求方法">
          <el-select
            v-model="localData.method"
            @change="handleChange"
          >
            <el-option
              label="GET"
              value="GET"
            />
            <el-option
              label="POST"
              value="POST"
            />
            <el-option
              label="PUT"
              value="PUT"
            />
            <el-option
              label="PATCH"
              value="PATCH"
            />
            <el-option
              label="DELETE"
              value="DELETE"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="请求地址"
          required
        >
          <el-input
            v-model="localData.url"
            placeholder="https://api.example.com/endpoint"
            class="url-input"
            @change="handleChange"
          />
          <div class="field-hint">
            支持 <code>{变量名}</code> 语法进行变量插值
          </div>
        </el-form-item>

        <el-form-item label="URL 参数">
          <div class="key-value-list">
            <div 
              v-for="(param, index) in urlParams" 
              :key="index"
              class="key-value-row"
            >
              <el-input
                v-model="param.key"
                placeholder="参数名"
                size="small"
                class="key-input"
                @change="updateUrlParams"
              />
              <el-input
                v-model="param.value"
                placeholder="参数值"
                size="small"
                class="value-input"
                @change="updateUrlParams"
              />
              <el-button 
                link 
                type="danger" 
                size="small"
                @click="removeUrlParam(index)"
              >
                <Minus class="icon-sm" />
              </el-button>
            </div>
            <el-button
              size="small"
              @click="addUrlParam"
            >
              <Plus class="icon" /> 添加参数
            </el-button>
          </div>
        </el-form-item>
      </div>

      <!-- 请求头 -->
      <div class="form-section">
        <h4 class="section-title">
          请求头
        </h4>
        
        <el-form-item label="请求头配置">
          <div class="key-value-list">
            <div 
              v-for="(header, index) in headers" 
              :key="index"
              class="key-value-row"
            >
              <el-input
                v-model="header.key"
                placeholder="Header-Name"
                size="small"
                class="key-input"
                @change="updateHeaders"
              />
              <el-input
                v-model="header.value"
                placeholder="Header Value"
                size="small"
                class="value-input"
                @change="updateHeaders"
              />
              <el-button 
                link 
                type="danger" 
                size="small"
                @click="removeHeader(index)"
              >
                <Minus class="icon-sm" />
              </el-button>
            </div>
            <el-button
              size="small"
              @click="addHeader"
            >
              <Plus class="icon" /> 添加请求头
            </el-button>
          </div>
        </el-form-item>
      </div>

      <!-- 请求体 -->
      <div class="form-section">
        <h4 class="section-title">
          请求体
        </h4>
        
        <el-form-item label="请求体类型">
          <el-select
            v-model="localData.bodyType"
            @change="handleChange"
          >
            <el-option
              label="JSON"
              value="json"
            />
            <el-option
              label="表单数据"
              value="form"
            />
            <el-option
              label="原始数据"
              value="raw"
            />
            <el-option
              label="无请求体"
              value="none"
            />
          </el-select>
        </el-form-item>

        <el-form-item 
          v-if="localData.bodyType !== 'none'" 
          label="请求体内容"
        >
          <el-input
            v-model="localData.body"
            type="textarea"
            :rows="6"
            :placeholder="bodyPlaceholder"
            class="body-input"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 高级设置 -->
      <div class="form-section">
        <h4 class="section-title">
          高级设置
        </h4>
        
        <el-form-item label="超时时间">
          <el-input-number
            v-model="localData.timeout"
            :min="1"
            :max="300"
            :step="10"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="跟随重定向">
          <el-switch
            v-model="localData.followRedirects"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="验证 SSL">
          <el-switch
            v-model="localData.sslVerify"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          请求预览
        </h4>
        <div class="request-preview">
          <div
            class="preview-method"
            :class="localData.method.toLowerCase()"
          >
            {{ localData.method }}
          </div>
          <div class="preview-url">
            {{ localData.url || '(未设置 URL)' }}
          </div>
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
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  method: 'GET',
  url: '',
  headers: {},
  body: '',
  bodyType: 'none',
  timeout: 30,
  followRedirects: true,
  sslVerify: true
})

const urlParams = ref([])
const headers = ref([])

const bodyPlaceholder = computed(() => {
  switch (localData.bodyType) {
    case 'json':
      return `{
  "key": "value",
  "name": "{input_name}"
}`
    case 'form':
      return `key1=value1
key2=value2`
    case 'raw':
      return '原始文本内容...'
    default:
      return ''
  }
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    // Parse headers object to array for UI
    let headersArray = []
    if (newVal.headers) {
      if (typeof newVal.headers === 'string') {
        try {
          headersArray = Object.entries(JSON.parse(newVal.headers))
        } catch {
          headersArray = []
        }
      } else if (typeof newVal.headers === 'object') {
        headersArray = Object.entries(newVal.headers)
      }
    }
    
    // Parse URL params from URL string
    let paramsArray = []
    if (newVal.url && newVal.url.includes('?')) {
      const queryString = newVal.url.split('?')[1]
      paramsArray = queryString.split('&')
        .filter(p => p)
        .map(p => {
          const [key, value] = p.split('=')
          return { key: decodeURIComponent(key), value: decodeURIComponent(value || '') }
        })
    }
    
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      method: newVal.method || 'GET',
      url: newVal.url || '',
      body: newVal.body || '',
      bodyType: newVal.bodyType || 'none',
      timeout: newVal.timeout || 30,
      followRedirects: newVal.followRedirects !== false,
      sslVerify: newVal.sslVerify !== false
    })
    
    headers.value = headersArray
    urlParams.value = paramsArray
  }
}, { immediate: true, deep: true })

const addUrlParam = () => {
  urlParams.value.push({ key: '', value: '' })
}

const removeUrlParam = (index) => {
  urlParams.value.splice(index, 1)
  updateUrlParams()
}

const updateUrlParams = () => {
  // This could build the URL with params
  handleChange()
}

const addHeader = () => {
  headers.value.push({ key: '', value: '' })
}

const removeHeader = (index) => {
  headers.value.splice(index, 1)
  updateHeaders()
}

const updateHeaders = () => {
  // Convert array back to object
  const headersObj = {}
  headers.value.forEach(h => {
    if (h.key) {
      headersObj[h.key] = h.value
    }
  })
  localData.headers = headersObj
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

.url-input {
  :deep(.el-input__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
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

.body-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}

.request-preview {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .preview-method {
    padding: $spacing-1 $spacing-2;
    border-radius: $radius-sm;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
    text-transform: uppercase;

    &.get {
      background: rgba(59, 130, 246, 0.15);
      color: #3b82f6;
    }

    &.post {
      background: rgba(16, 185, 129, 0.15);
      color: #10b981;
    }

    &.put {
      background: rgba(245, 158, 11, 0.15);
      color: #f59e0b;
    }

    &.patch {
      background: rgba(139, 92, 246, 0.15);
      color: #8b5cf6;
    }

    &.delete {
      background: rgba(239, 68, 68, 0.15);
      color: #ef4444;
    }
  }

  .preview-url {
    flex: 1;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    color: var(--text-primary);
    word-break: break-all;
  }
}
</style>
