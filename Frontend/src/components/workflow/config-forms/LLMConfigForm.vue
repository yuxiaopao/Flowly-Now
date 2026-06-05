<template>
  <div class="config-form llm-config-form">
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

      <!-- 模型配置 -->
      <div class="form-section">
        <h4 class="section-title">
          模型配置
        </h4>
        
        <el-form-item label="AI 提供商">
          <el-select
            v-model="localData.provider"
            placeholder="选择提供商"
            @change="handleChange"
          >
            <el-option
              label="OpenAI"
              value="openai"
            />
            <el-option
              label="Anthropic"
              value="anthropic"
            />
            <el-option
              label="Ollama"
              value="ollama"
            />
            <el-option
              label="Azure OpenAI"
              value="azure"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="选择模型"
          required
        >
          <el-select 
            v-model="localData.model" 
            placeholder="选择模型"
            filterable
            :loading="loading"
            @change="handleChange"
          >
            <template v-if="modelOptions">
              <el-option-group
                v-for="(models, provider) in modelOptions"
                :key="provider"
                :label="provider"
              >
                <el-option
                  v-for="opt in models"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                >
                  <div class="model-option">
                    <span>{{ opt.label }}</span>
                    <span class="model-badges">
                      <el-tag
                        v-if="opt.supportsVision"
                        size="small"
                        type="success"
                      >视觉</el-tag>
                      <el-tag
                        v-if="opt.supportsFunctionCalling"
                        size="small"
                        type="warning"
                      >函数</el-tag>
                      <el-tag
                        v-if="opt.supportsStreaming"
                        size="small"
                        type="info"
                      >流式</el-tag>
                    </span>
                  </div>
                </el-option>
              </el-option-group>
            </template>
            <template v-else>
              <el-option
                value=""
                label="加载模型中..."
                disabled
              />
            </template>
          </el-select>
        </el-form-item>

        <el-form-item label="流式输出">
          <el-switch
            v-model="localData.streaming"
            @change="handleChange"
          />
          <span class="field-hint">开启后将在执行时实时显示输出内容</span>
        </el-form-item>
      </div>

      <!-- 提示词配置 -->
      <div class="form-section">
        <h4 class="section-title">
          提示词配置
        </h4>
        
        <el-form-item label="系统提示词">
          <el-input
            v-model="localData.systemPrompt"
            type="textarea"
            :rows="5"
            placeholder="设定 AI 角色和背景，例如：&#10;你是一个专业的技术文档助手..."
            class="prompt-input"
            @change="handleChange"
          />
          <div class="field-hint">
            定义 AI 的角色定位、行为规则和约束条件
          </div>
        </el-form-item>

        <el-form-item label="用户模板">
          <el-input
            v-model="localData.userTemplate"
            type="textarea"
            :rows="4"
            placeholder="用户输入模板，使用 {变量名} 占位，例如：&#10;请帮我处理以下数据：&#10;{input_data}&#10;额外参数：{options}"
            class="prompt-input"
            @change="handleChange"
          />
          <div class="field-hint">
            支持使用 {变量名} 语法引用工作流中的变量
          </div>
        </el-form-item>

        <el-form-item label="输入变量">
          <el-input
            v-model="localData.inputVariable"
            placeholder="输入变量名，用于传递上游节点的数据"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 生成参数 -->
      <div class="form-section">
        <h4 class="section-title">
          生成参数
        </h4>
        
        <el-form-item label="温度参数">
          <div class="slider-wrapper">
            <el-slider
              v-model="localData.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              :marks="temperatureMarks"
              @change="handleChange"
            />
          </div>
          <div class="field-hint">
            控制输出的随机性：0 精确稳定，1 平衡，2 创意随机
          </div>
        </el-form-item>

        <el-form-item label="最大 Token 数">
          <el-input-number
            v-model="localData.maxTokens"
            :min="1"
            :max="32000"
            :step="100"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
          <div class="field-hint">
            限制单次生成的最大 token 数量
          </div>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">模型:</span>
            <span class="preview-value">{{ localData.model || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">温度:</span>
            <span class="preview-value">{{ localData.temperature }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">最大 Tokens:</span>
            <span class="preview-value">{{ localData.maxTokens || '无限制' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">流式输出:</span>
            <el-tag
              size="small"
              :type="localData.streaming ? 'success' : 'info'"
            >
              {{ localData.streaming ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  },
  availableModels: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localData = reactive({
  label: '',
  description: '',
  model: '',
  systemPrompt: '',
  userTemplate: '',
  temperature: 0.7,
  maxTokens: 2000,
  provider: 'openai',
  streaming: false,
  inputVariable: ''
})

const loading = ref(false)

const temperatureMarks = {
  0: '0',
  0.5: '0.5',
  1: '1',
  1.5: '1.5',
  2: '2'
}

const modelOptions = computed(() => {
  if (props.availableModels.length > 0) {
    const grouped = {}
    props.availableModels.forEach(m => {
      const provider = m.provider || 'Unknown'
      if (!grouped[provider]) grouped[provider] = []
      grouped[provider].push({
        value: m.modelId || m.model_id || m.id,
        label: m.name,
        supportsVision: m.supportsVision || m.supports_vision,
        supportsFunctionCalling: m.supportsFunctionCalling || m.supports_function_calling,
        supportsStreaming: m.supportsStreaming || m.supports_streaming
      })
    })
    return grouped
  }
  return null
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      model: newVal.model || '',
      systemPrompt: newVal.systemPrompt || '',
      userTemplate: newVal.userTemplate || '',
      temperature: newVal.temperature ?? 0.7,
      maxTokens: newVal.maxTokens || 2000,
      provider: newVal.provider || 'openai',
      streaming: newVal.streaming || false,
      inputVariable: newVal.inputVariable || ''
    })
  }
}, { immediate: true, deep: true })

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

.model-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;

  .model-badges {
    display: flex;
    gap: 4px;
  }
}

.prompt-input {
  :deep(.el-textarea__inner) {
    font-family: inherit;
    line-height: 1.6;
  }
}

.slider-wrapper {
  padding: 0 $spacing-2;
}

.field-hint {
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
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
    min-width: 80px;
  }

  .preview-value {
    color: var(--text-primary);
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
  }
}
</style>
