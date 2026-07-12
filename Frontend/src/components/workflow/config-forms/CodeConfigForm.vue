<template>
  <div class="config-form code-config-form">
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

      <!-- 代码配置 -->
      <div class="form-section">
        <h4 class="section-title">
          代码配置
        </h4>
        
        <el-form-item label="代码语言">
          <el-radio-group
            v-model="localData.language"
            @change="handleChange"
          >
            <el-radio value="javascript">
              JavaScript
            </el-radio>
            <el-radio value="python">
              Python
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="输入变量">
          <el-input
            v-model="localData.inputVariable"
            placeholder="输入变量名，用于接收上游节点的数据"
            @change="handleChange"
          />
          <div class="field-hint">
            变量值将通过 <code>input</code> 参数传入代码
          </div>
        </el-form-item>

        <el-form-item
          label="代码内容"
          required
        >
          <div class="code-editor-wrapper">
            <div class="code-editor-header">
              <el-tag
                size="small"
                type="info"
              >
                {{ localData.language === 'javascript' ? 'JavaScript' : 'Python' }}
              </el-tag>
              <div class="editor-actions">
                <el-button
                  size="small"
                  text
                  @click="formatCode"
                >
                  <Wand2 class="icon-sm" /> 格式化
                </el-button>
              </div>
            </div>
            <el-input
              v-model="localData.code"
              type="textarea"
              :rows="12"
              :placeholder="codePlaceholder"
              class="code-input"
              @change="handleChange"
            />
          </div>
        </el-form-item>
      </div>

      <!-- 运行环境 -->
      <div class="form-section">
        <h4 class="section-title">
          运行环境
        </h4>
        
        <el-form-item label="超时设置">
          <el-input-number
            v-model="localData.timeout"
            :min="1"
            :max="300"
            :step="10"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            代码执行的最大超时时间（秒）
          </div>
        </el-form-item>
      </div>

      <!-- 语法参考 -->
      <div class="form-section">
        <h4 class="section-title">
          语法参考
        </h4>
        <div class="syntax-reference">
          <template v-if="localData.language === 'javascript'">
            <div class="syntax-item">
              <code>input</code>
              <span>输入数据</span>
            </div>
            <div class="syntax-item">
              <code>output = ...</code>
              <span>设置输出结果</span>
            </div>
            <div class="syntax-item">
              <code>context.variables</code>
              <span>访问工作流变量</span>
            </div>
            <div class="syntax-item">
              <code>console.log(...)</code>
              <span>调试日志输出</span>
            </div>
          </template>
          <template v-else>
            <div class="syntax-item">
              <code>input</code>
              <span>输入数据</span>
            </div>
            <div class="syntax-item">
              <code>output = ...</code>
              <span>设置输出结果</span>
            </div>
            <div class="syntax-item">
              <code>variables['name']</code>
              <span>访问工作流变量</span>
            </div>
            <div class="syntax-item">
              <code>print(...)</code>
              <span>调试日志输出</span>
            </div>
          </template>
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          代码预览
        </h4>
        <div class="code-preview">
          <pre class="preview-content">{{ localData.code || '(空代码)' }}</pre>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, computed, watch } from 'vue'
import { Wand2 } from 'lucide-vue-next'

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
  code: '',
  inputVariable: '',
  language: 'javascript',
  timeout: 30
})

const codePlaceholder = computed(() => {
  if (localData.language === 'javascript') {
    return `// 输入数据通过 input 变量接收
const { data, options } = input;

// 处理数据
const result = data.map(item => ({
  ...item,
  processed: true
}));

// 设置输出结果
output = result;`
  }
  return `# 输入数据通过 input 变量接收
data = input['data']
options = input.get('options', {})

# 处理数据
result = [item | processed: True for item in data]

# 设置输出结果
output = result`
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      code: newVal.code || '',
      inputVariable: newVal.inputVariable || '',
      language: newVal.language || 'javascript',
      timeout: newVal.timeout || 30
    })
  }
}, { immediate: true, deep: true })

const formatCode = () => {
  // Basic code formatting - could be enhanced with a proper formatter
  if (localData.language === 'javascript') {
    try {
      // Simple indentation fix
      let lines = localData.code.split('\n')
      lines = lines.map(line => line.trim())
      localData.code = lines.join('\n')
      handleChange()
    } catch (e) {
      console.warn('Code formatting failed:', e)
    }
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

.icon-sm {
  width: 12px;
  height: 12px;
  margin-right: 4px;
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

.code-editor-wrapper {
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  overflow: hidden;
}

.code-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-2 $spacing-3;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-primary);

  .editor-actions {
    display: flex;
    gap: $spacing-2;
  }
}

.code-input {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', 'JetBrains Mono', 'Monaco', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
    background: var(--bg-primary);
    min-height: 200px;
  }
}

.syntax-reference {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.syntax-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  margin-bottom: $spacing-2;
  font-size: $font-size-xs;

  &:last-child {
    margin-bottom: 0;
  }

  code {
    background: var(--bg-secondary);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'Fira Code', monospace;
    color: var(--accent-primary);
    min-width: 160px;
  }

  span {
    color: var(--text-secondary);
  }
}

.code-preview {
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
  overflow: hidden;
  max-height: 200px;
  overflow-y: auto;

  .preview-content {
    margin: 0;
    padding: $spacing-3;
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-all;
  }
}
</style>
