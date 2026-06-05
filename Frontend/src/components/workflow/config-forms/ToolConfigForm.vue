<template>
  <div class="config-form tool-config-form">
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

      <!-- 工具选择 -->
      <div class="form-section">
        <h4 class="section-title">
          工具配置
        </h4>
        
        <el-form-item
          label="选择工具"
          required
        >
          <el-select
            v-model="localData.tool"
            placeholder="搜索或选择工具"
            filterable
            :loading="loading"
            @change="onToolChange"
          >
            <el-option
              v-for="tool in availableTools"
              :key="tool.name || tool.id"
              :label="tool.name"
              :value="tool.name || tool.id"
            >
              <div class="tool-option">
                <span class="tool-name">{{ tool.name }}</span>
                <span class="tool-desc">{{ tool.description }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="凭证">
          <el-select
            v-model="localData.credential"
            placeholder="选择凭证（可选）"
            clearable
            @change="handleChange"
          >
            <el-option
              v-for="cred in availableCredentials"
              :key="cred.id"
              :label="cred.name"
              :value="cred.id"
            >
              <span>{{ cred.name }}</span>
              <span class="cred-type">{{ cred.type }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </div>

      <!-- 工具参数 -->
      <div
        v-if="selectedTool"
        class="form-section"
      >
        <h4 class="section-title">
          工具参数
        </h4>
        
        <div class="tool-info">
          <div class="tool-header">
            <el-tag
              size="small"
              type="info"
            >
              {{ selectedTool.name }}
            </el-tag>
          </div>
          <p
            v-if="selectedTool.description"
            class="tool-description"
          >
            {{ selectedTool.description }}
          </p>
        </div>

        <div class="parameters-list">
          <div 
            v-for="param in selectedToolParameters" 
            :key="param.name"
            class="param-item"
          >
            <div class="param-header">
              <span class="param-name">{{ param.name }}</span>
              <el-tag
                v-if="param.required"
                size="small"
                type="danger"
              >
                必填
              </el-tag>
              <el-tag
                v-if="param.type"
                size="small"
                type="info"
              >
                {{ param.type }}
              </el-tag>
            </div>
            
            <div class="param-config">
              <el-form-item label="值类型">
                <el-select
                  v-model="paramValueTypes[param.name]"
                  size="small"
                  @change="handleChange"
                >
                  <el-option
                    label="静态值"
                    value="static"
                  />
                  <el-option
                    label="输入变量"
                    value="variable"
                  />
                  <el-option
                    label="表达式"
                    value="expression"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="参数值">
                <el-input
                  v-if="paramValueTypes[param.name] === 'static'"
                  v-model="localData.parametersArray[idxByName(param.name)].value"
                  :placeholder="param.description || `输入 ${param.name}`"
                  size="small"
                  @change="handleChange"
                />
                <el-input
                  v-else-if="paramValueTypes[param.name] === 'variable'"
                  v-model="localData.parametersArray[idxByName(param.name)].value"
                  placeholder="变量名"
                  size="small"
                  @change="handleChange"
                />
                <el-input
                  v-else
                  v-model="localData.parametersArray[idxByName(param.name)].value"
                  :placeholder="`表达式，例如: variables.name`"
                  size="small"
                  class="expression-input"
                  @change="handleChange"
                />
              </el-form-item>
            </div>
            
            <p
              v-if="param.description"
              class="param-desc"
            >
              {{ param.description }}
            </p>
          </div>

          <div
            v-if="!selectedToolParameters || selectedToolParameters.length === 0"
            class="no-params"
          >
            <span>此工具不需要参数</span>
          </div>
        </div>
      </div>

      <!-- 预览 -->
      <div
        v-if="selectedTool"
        class="form-section"
      >
        <h4 class="section-title">
          工具预览
        </h4>
        <div class="tool-preview">
          <div class="preview-row">
            <span class="preview-label">工具:</span>
            <span class="preview-value">{{ selectedTool.name }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">参数:</span>
            <span class="preview-value">{{ filledParamsCount }} / {{ selectedToolParameters.length }}</span>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  availableTools: {
    type: Array,
    default: () => []
  },
  availableCredentials: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  tool: '',
  toolName: '',
  parameters: {},
  parametersArray: [],
  credential: ''
})

const loading = ref(false)
const paramValueTypes = reactive({})

const selectedTool = computed(() => {
  return props.availableTools.find(t => (t.name || t.id) === localData.tool)
})

const selectedToolParameters = computed(() => {
  if (!selectedTool.value) return []
  return selectedTool.value.parameters || []
})

const filledParamsCount = computed(() => {
  return localData.parametersArray.filter(p => p.value).length
})

const idxByName = (name) => {
  return localData.parametersArray.findIndex(p => p.name === name)
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    const toolName = newVal.tool || newVal.toolName || ''
    
    // Initialize parameters array
    let paramsArray = []
    if (newVal.parametersArray) {
      paramsArray = JSON.parse(JSON.stringify(newVal.parametersArray))
    } else if (newVal.parameters && typeof newVal.parameters === 'object') {
      paramsArray = Object.entries(newVal.parameters).map(([name, value]) => ({
        name,
        value: String(value),
        type: 'static'
      }))
    }
    
    // Set default value types
    paramsArray.forEach(p => {
      if (!paramValueTypes[p.name]) {
        paramValueTypes[p.name] = 'static'
      }
    })
    
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      tool: toolName,
      toolName: toolName,
      parameters: newVal.parameters || {},
      parametersArray: paramsArray,
      credential: newVal.credential || ''
    })
  }
}, { immediate: true, deep: true })

const onToolChange = (toolName) => {
  const tool = props.availableTools.find(t => (t.name || t.id) === toolName)
  if (tool) {
    localData.toolName = tool.name || tool.id
    
    // Initialize parameters from tool definition
    if (tool.parameters && tool.parameters.length > 0) {
      localData.parametersArray = tool.parameters.map(p => ({
        name: p.name,
        value: p.default || '',
        type: 'static'
      }))
      
      // Set default value types
      tool.parameters.forEach(p => {
        paramValueTypes[p.name] = 'static'
      })
    } else {
      localData.parametersArray = []
    }
  }
  handleChange()
}

const handleChange = () => {
  // Convert parametersArray back to parameters object
  const params = {}
  localData.parametersArray.forEach(p => {
    params[p.name] = p.value
  })
  localData.parameters = params
  
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

.tool-option {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .tool-name {
    font-weight: $font-weight-medium;
  }

  .tool-desc {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.cred-type {
  margin-left: 8px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.tool-info {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
  margin-bottom: $spacing-4;

  .tool-header {
    margin-bottom: $spacing-2;
  }

  .tool-description {
    margin: 0;
    font-size: $font-size-sm;
    color: var(--text-secondary);
  }
}

.parameters-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.param-item {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);

  .param-header {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    margin-bottom: $spacing-2;

    .param-name {
      font-weight: $font-weight-medium;
      color: var(--text-primary);
      font-family: 'Fira Code', monospace;
      font-size: $font-size-sm;
    }
  }

  .param-config {
    display: flex;
    gap: $spacing-2;
    align-items: flex-start;

    .el-form-item {
      flex: 1;
      margin-bottom: 0;
    }
  }

  .param-desc {
    margin: $spacing-2 0 0;
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.expression-input {
  :deep(.el-input__inner) {
    font-family: 'Fira Code', monospace;
  }
}

.no-params {
  padding: $spacing-4;
  text-align: center;
  color: var(--text-tertiary);
  font-size: $font-size-sm;
}

.tool-preview {
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
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}
</style>
