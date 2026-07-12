<template>
  <div class="node-config-form">
    <!-- LLM 节点 -->
    <LLMConfigForm
      v-if="nodeType === 'llm'"
      v-model="localConfig"
      :available-models="availableModels"
      @change="handleConfigChange"
    />

    <!-- Prompt 节点 -->
    <PromptConfigForm
      v-else-if="nodeType === 'prompt'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Condition 节点 -->
    <ConditionConfigForm
      v-else-if="nodeType === 'condition'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Code 节点 -->
    <CodeConfigForm
      v-else-if="nodeType === 'code'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- HTTP 节点 -->
    <HTTPConfigForm
      v-else-if="nodeType === 'http'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Loop 节点 -->
    <LoopConfigForm
      v-else-if="nodeType === 'loop'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Tool 节点 -->
    <ToolConfigForm
      v-else-if="nodeType === 'tool'"
      v-model="localConfig"
      :available-tools="availableTools"
      @change="handleConfigChange"
    />

    <!-- Variable 节点 -->
    <VariableConfigForm
      v-else-if="nodeType === 'variable'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Input 节点 -->
    <InputOutputConfigForm
      v-else-if="nodeType === 'input'"
      v-model="localConfig"
      node-mode="input"
      @change="handleConfigChange"
    />

    <!-- Output 节点 -->
    <InputOutputConfigForm
      v-else-if="nodeType === 'output'"
      v-model="localConfig"
      node-mode="output"
      @change="handleConfigChange"
    />

    <!-- Switch 节点 -->
    <SwitchConfigForm
      v-else-if="nodeType === 'switch'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Transform 节点 -->
    <TransformConfigForm
      v-else-if="nodeType === 'transform'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Email 节点 -->
    <EmailConfigForm
      v-else-if="nodeType === 'email'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- Delay 节点 -->
    <DelayConfigForm
      v-else-if="nodeType === 'delay'"
      v-model="localConfig"
      @change="handleConfigChange"
    />

    <!-- 默认基础配置（Start/End/通用） -->
    <!-- Multimodal: Image Generation -->
    <ImageGenerationConfig
      v-else-if="nodeType === 'image_generation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Multimodal: Video Generation -->
    <VideoGenerationConfig
      v-else-if="nodeType === 'video_generation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Multimodal: Audio Generation -->
    <AudioGenerationConfig
      v-else-if="nodeType === 'audio_generation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Multimodal: Subtitle Generation -->
    <SubtitleGenerationConfig
      v-else-if="nodeType === 'subtitle_generation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Multimodal: Image Editing -->
    <ImageEditingConfig
      v-else-if="nodeType === 'image_editing'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Data: Dataset Upload -->
    <DatasetUploadConfig
      v-else-if="nodeType === 'dataset_upload'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Data: Data Annotation -->
    <DataAnnotationConfig
      v-else-if="nodeType === 'data_annotation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Data: Data Augmentation -->
    <DataAugmentationConfig
      v-else-if="nodeType === 'data_augmentation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- MLOps: Model Training -->
    <ModelTrainingConfig
      v-else-if="nodeType === 'model_training'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- MLOps: Model Evaluation -->
    <ModelEvaluationConfig
      v-else-if="nodeType === 'model_evaluation'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- MLOps: Model Deployment -->
    <ModelDeploymentConfig
      v-else-if="nodeType === 'model_deployment'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- RAG: Document Loader -->
    <DocumentLoaderConfig
      v-else-if="nodeType === 'document_loader'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- RAG: Embedding -->
    <EmbeddingConfig
      v-else-if="nodeType === 'embedding'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- RAG: Vector Store -->
    <VectorStoreConfig
      v-else-if="nodeType === 'vector_store'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- RAG: Retriever -->
    <RetrieverConfig
      v-else-if="nodeType === 'retriever'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- RAG: Reranker -->
    <RerankerConfig
      v-else-if="nodeType === 'reranker'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Agent: Agent -->
    <AgentConfig
      v-else-if="nodeType === 'agent'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Agent: Planner -->
    <PlannerConfig
      v-else-if="nodeType === 'planner'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Agent: Executor -->
    <ExecutorConfig
      v-else-if="nodeType === 'executor'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Agent: Memory -->
    <MemoryConfig
      v-else-if="nodeType === 'memory'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Utility: File Reader -->
    <FileReaderConfig
      v-else-if="nodeType === 'file_reader'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Utility: File Writer -->
    <FileWriterConfig
      v-else-if="nodeType === 'file_writer'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Utility: Web Scraper -->
    <WebScraperConfig
      v-else-if="nodeType === 'web_scraper'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Utility: CSV Transform -->
    <CsvTransformConfig
      v-else-if="nodeType === 'csv_transform'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <!-- Utility: JSON Transform -->
    <JsonTransformConfig
      v-else-if="nodeType === 'json_transform'"
      v-model="localConfig"
      @change="handleConfigChange"
    />
    <div
      v-else
      class="base-config"
    >
      <el-form
        label-width="100px"
        size="small"
      >
        <div class="form-section">
          <h4 class="section-title">
            基本配置
          </h4>
          <el-form-item label="节点名称">
            <el-input 
              v-model="localConfig.label" 
              placeholder="输入节点名称"
              @change="handleConfigChange"
            />
          </el-form-item>

          <el-form-item label="描述">
            <el-input 
              v-model="localConfig.description" 
              type="textarea"
              :rows="2"
              placeholder="节点描述（可选）"
              @change="handleConfigChange"
            />
          </el-form-item>
        </div>

        <!-- 错误处理配置 -->
        <div class="form-section">
          <h4 class="section-title">
            错误处理
          </h4>
          
          <el-form-item label="错误策略">
            <el-select
              v-model="localConfig.errorHandling"
              @change="handleConfigChange"
            >
              <el-option
                label="停止执行"
                value="stop"
              />
              <el-option
                label="跳过节点"
                value="skip"
              />
              <el-option
                label="重试"
                value="retry"
              />
              <el-option
                label="使用默认值"
                value="fallback"
              />
            </el-select>
          </el-form-item>

          <el-form-item
            v-if="localConfig.errorHandling === 'retry'"
            label="最大重试次数"
          >
            <el-input-number
              v-model="localConfig.maxRetries"
              :min="1"
              :max="10"
              @change="handleConfigChange"
            />
          </el-form-item>

          <el-form-item
            v-if="localConfig.errorHandling === 'retry'"
            label="重试延迟"
          >
            <el-input-number
              v-model="localConfig.retryDelay"
              :min="0"
              :max="60"
              @change="handleConfigChange"
            />
            <span class="timeout-unit">秒</span>
          </el-form-item>

          <el-form-item
            v-if="localConfig.errorHandling === 'fallback'"
            label="默认值"
          >
            <el-input 
              v-model="localConfig.fallbackValue" 
              placeholder="出错时使用的默认值"
              @change="handleConfigChange"
            />
          </el-form-item>
        </div>

        <el-divider />

        <div class="form-actions">
          <el-tooltip
            content="从画布中删除此节点"
            placement="top"
          >
            <el-button
              type="danger"
              @click="handleDelete"
            >
              删除节点
            </el-button>
          </el-tooltip>
          <el-tooltip
            content="复制当前节点配置"
            placement="top"
          >
            <el-button @click="handleDuplicate">
              复制节点
            </el-button>
          </el-tooltip>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch, computed } from 'vue'

// Import dedicated config forms
import LLMConfigForm from './config-forms/LLMConfigForm.vue'
import PromptConfigForm from './config-forms/PromptConfigForm.vue'
import ConditionConfigForm from './config-forms/ConditionConfigForm.vue'
import CodeConfigForm from './config-forms/CodeConfigForm.vue'
import HTTPConfigForm from './config-forms/HTTPConfigForm.vue'
import LoopConfigForm from './config-forms/LoopConfigForm.vue'
import ToolConfigForm from './config-forms/ToolConfigForm.vue'
import VariableConfigForm from './config-forms/VariableConfigForm.vue'
import InputOutputConfigForm from './config-forms/InputOutputConfigForm.vue'
import SwitchConfigForm from './config-forms/SwitchConfigForm.vue'
import TransformConfigForm from './config-forms/TransformConfigForm.vue'
import EmailConfigForm from './config-forms/EmailConfigForm.vue'
import DelayConfigForm from './config-forms/DelayConfigForm.vue'

// Domain node config forms — Multimodal
import ImageGenerationConfig from './configs/ImageGenerationConfig.vue'
import VideoGenerationConfig from './configs/VideoGenerationConfig.vue'
import AudioGenerationConfig from './configs/AudioGenerationConfig.vue'
import SubtitleGenerationConfig from './configs/SubtitleGenerationConfig.vue'
import ImageEditingConfig from './configs/ImageEditingConfig.vue'

// Domain node config forms — Data / MLOps（异步加载，避免 HMR 循环依赖）
import {
  DatasetUploadConfig,
  DataAnnotationConfig,
  DataAugmentationConfig,
  ModelTrainingConfig,
} from './configs/asyncConfigComponents'
import ModelEvaluationConfig from './configs/ModelEvaluationConfig.vue'
import ModelDeploymentConfig from './configs/ModelDeploymentConfig.vue'

// Domain node config forms — RAG
import DocumentLoaderConfig from './configs/DocumentLoaderConfig.vue'
import EmbeddingConfig from './configs/EmbeddingConfig.vue'
import VectorStoreConfig from './configs/VectorStoreConfig.vue'
import RetrieverConfig from './configs/RetrieverConfig.vue'
import RerankerConfig from './configs/RerankerConfig.vue'

// Domain node config forms — Agent
import AgentConfig from './configs/AgentConfig.vue'
import PlannerConfig from './configs/PlannerConfig.vue'
import ExecutorConfig from './configs/ExecutorConfig.vue'
import MemoryConfig from './configs/MemoryConfig.vue'

// Domain node config forms — Utility
import FileReaderConfig from './configs/FileReaderConfig.vue'
import FileWriterConfig from './configs/FileWriterConfig.vue'
import WebScraperConfig from './configs/WebScraperConfig.vue'
import CsvTransformConfig from './configs/CsvTransformConfig.vue'
import JsonTransformConfig from './configs/JsonTransformConfig.vue'

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  availableModels: {
    type: Array,
    default: () => []
  },
  availableTools: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update', 'delete', 'duplicate'])

// 节点类型
const nodeType = computed(() => props.node?.type || '')

// 本地配置
const localConfig = reactive({
  label: '',
  description: '',
  errorHandling: 'stop',
  maxRetries: 3,
  retryDelay: 1,
  fallbackValue: null
})

// 监听 props.node 变化，初始化配置
watch(
  () => props.node,
  (newNode) => {
    if (newNode?.data?.config) {
      Object.assign(localConfig, newNode.data.config)
    }
    if (newNode?.data?.label) {
      localConfig.label = newNode.data.label
    }
    if (newNode?.data?.description) {
      localConfig.description = newNode.data.description
    }
  },
  { immediate: true, deep: true }
)

// 处理配置变化
const handleConfigChange = (config) => {
  emit('update', props.node.id, {
    label: config.label || localConfig.label,
    description: config.description || localConfig.description,
    config: { ...config }
  })
}

// 删除节点
const handleDelete = () => {
  emit('delete', props.node.id)
}

// 复制节点
const handleDuplicate = () => {
  emit('duplicate', props.node.id)
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.node-config-form {
  padding: 0;
}

.base-config {
  :deep(.el-form-item__label) {
    font-size: $font-size-sm;
  }
}

.form-section {
  margin-bottom: $spacing-4;
}

.section-title {
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin-bottom: $spacing-3;
  padding-bottom: $spacing-2;
  border-bottom: 1px solid var(--border-secondary);
}

.timeout-unit {
  margin-left: $spacing-2;
  color: var(--text-secondary);
  font-size: $font-size-xs;
}

// ============================================
// 表单控件主题覆盖（el-input / el-select / el-textarea / el-input-number）
// ============================================
:deep(.el-input__wrapper),
:deep(.el-textarea__inner),
:deep(.el-select__wrapper),
:deep(.el-input-number) {
  background-color: var(--bg-secondary) !important;
  box-shadow: 0 0 0 1px var(--border-primary) inset !important;
  border-radius: $radius-md;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner),
:deep(.el-select__wrapper .el-select__selected-item) {
  color: var(--text-primary) !important;
}

:deep(.el-input__wrapper:hover),
:deep(.el-textarea__inner:hover),
:deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-hover) inset !important;
}

:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus),
:deep(.el-select__wrapper.is-focused) {
  box-shadow: 0 0 0 1px var(--color-primary) inset !important;
}

:deep(.el-input.is-disabled .el-input__wrapper),
:deep(.el-textarea.is-disabled .el-textarea__inner),
:deep(.el-select .el-select__wrapper.is-disabled),
:deep(.el-input-number.is-disabled) {
  background-color: var(--bg-tertiary) !important;
  opacity: 0.6;
}

:deep(.el-input__prefix),
:deep(.el-input__suffix),
:deep(.el-select__caret),
:deep(.el-input-number__increase),
:deep(.el-input-number__decrease) {
  color: var(--text-tertiary);
}

:deep(.el-input__inner::placeholder),
:deep(.el-textarea__inner::placeholder) {
  color: var(--text-tertiary);
}

:deep(.el-input-group__append .el-button),
:deep(.el-input-group__prepend .el-button) {
  background-color: var(--bg-tertiary);
  border-color: var(--border-primary);
  color: var(--text-secondary);
}

.form-actions {
  display: flex;
  justify-content: space-between;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-secondary);

  :deep(.el-button) {
    flex: 1;
    margin: 0 $spacing-2;

    &:first-child {
      margin-left: 0;
    }

    &:last-child {
      margin-right: 0;
    }
  }
}
</style>
