<template>
  <div
    class="property-panel"
    :class="{ visible: !!selectedNode }"
  >
    <div
      v-if="selectedNode"
      class="panel-content"
    >
      <!-- 节点基本信息 -->
      <div class="property-section">
        <h4 class="section-title">
          基本信息
        </h4>

        <div class="form-group">
          <label>节点名称</label>
          <el-input
            v-model="nodeData.name"
            placeholder="输入节点名称"
            @input="handleChange"
          />
        </div>

        <div class="form-group">
          <label>节点类型</label>
          <el-select
            v-model="nodeData.type"
            disabled
          >
            <el-option
              v-for="nt in nodeTypes"
              :key="nt.type"
              :label="nt.label"
              :value="nt.type"
            />
          </el-select>
        </div>

        <div class="form-group">
          <label>描述</label>
          <el-input
            v-model="nodeData.description"
            type="textarea"
            :rows="2"
            placeholder="节点描述（可选）"
            @input="handleChange"
          />
        </div>
      </div>

      <!-- 根据节点类型显示配置 -->
      <div class="property-section">
        <h4 class="section-title">
          {{ sectionTitle }}
        </h4>

        <!-- LLM 节点配置 -->
        <template v-if="selectedNode.type === 'llm'">
          <div class="form-group">
            <label>模型</label>
            <el-select
              v-model="nodeData.config.model"
              filterable
              :loading="modelsLoading"
              @change="handleChange"
            >
              <el-option
                v-for="opt in modelOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </div>

          <div class="form-group">
            <label>温度参数</label>
            <div class="slider-group">
              <el-slider
                v-model="nodeData.config.temperature"
                :min="0"
                :max="2"
                :step="0.1"
                :show-tooltip="true"
                @change="handleChange"
              />
              <span class="slider-value">{{ nodeData.config.temperature }}</span>
            </div>
          </div>

          <div class="form-group">
            <label>系统提示词</label>
            <el-input
              v-model="nodeData.config.systemPrompt"
              type="textarea"
              :rows="4"
              placeholder="你是一个有帮助的 AI 助手..."
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>用户消息模板</label>
            <el-input
              v-model="nodeData.config.userTemplate"
              type="textarea"
              :rows="2"
              placeholder="{input}"
              @input="handleChange"
            />
            <p class="form-hint">
              使用 {"{input}"} 作为用户输入占位符
            </p>
          </div>
        </template>

        <!-- Prompt 节点配置 -->
        <template v-else-if="selectedNode.type === 'prompt'">
          <div class="form-group">
            <label>模板内容</label>
            <el-input
              v-model="nodeData.config.template"
              type="textarea"
              :rows="6"
              placeholder="请输入提示词模板..."
              class="code-textarea"
              @input="handleChange"
            />
            <p class="form-hint">
              使用 {"{变量名}"} 定义变量
            </p>
          </div>

          <div class="form-group">
            <label>变量</label>
            <div class="dynamic-list">
              <div
                v-for="(variable, index) in nodeData.config.variables"
                :key="index"
                class="list-item"
              >
                <el-input
                  v-model="variable.name"
                  placeholder="变量名"
                  size="small"
                  @input="handleChange"
                />
                <el-input
                  v-model="variable.value"
                  placeholder="默认值"
                  size="small"
                  @input="handleChange"
                />
                <el-button
                  type="danger"
                  size="small"
                  text
                  @click="removeVariable(index)"
                >
                  <X />
                </el-button>
              </div>
              <el-button
                size="small"
                @click="addVariable"
              >
                <Plus /> 添加变量
              </el-button>
            </div>
          </div>
        </template>

        <!-- Condition 节点配置 -->
        <template v-else-if="selectedNode.type === 'condition'">
          <div class="form-group">
            <label>条件分支</label>
            <div class="dynamic-list">
              <div
                v-for="(condition, index) in nodeData.config.conditions"
                :key="index"
                class="condition-item"
              >
                <div class="condition-row">
                  <el-select
                    v-model="condition.field"
                    size="small"
                    @change="handleChange"
                  >
                    <el-option
                      label="last_output"
                      value="last_output"
                    />
                    <el-option
                      label="input"
                      value="input"
                    />
                  </el-select>
                  <el-select
                    v-model="condition.operator"
                    size="small"
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
                </div>
                <div class="condition-row">
                  <el-input
                    v-model="condition.value"
                    placeholder="比较值"
                    size="small"
                    @input="handleChange"
                  />
                  <el-input
                    v-model="condition.branch"
                    placeholder="分支名称"
                    size="small"
                    @input="handleChange"
                  />
                  <el-button
                    type="danger"
                    size="small"
                    text
                    @click="removeCondition(index)"
                  >
                    <X />
                  </el-button>
                </div>
              </div>
              <el-button
                size="small"
                @click="addCondition"
              >
                <Plus /> 添加条件
              </el-button>
            </div>
          </div>

          <div class="form-group">
            <label>默认分支</label>
            <el-input
              v-model="nodeData.config.defaultBranch"
              placeholder="default"
              @input="handleChange"
            />
          </div>
        </template>

        <!-- HTTP 节点配置 -->
        <template v-else-if="selectedNode.type === 'http'">
          <div class="form-group">
            <label>请求方法</label>
            <el-select
              v-model="nodeData.config.method"
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
          </div>

          <div class="form-group">
            <label>请求 URL</label>
            <el-input
              v-model="nodeData.config.url"
              placeholder="https://api.example.com/endpoint"
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>请求头 (JSON)</label>
            <el-input
              v-model="nodeData.config.headers"
              type="textarea"
              :rows="3"
              placeholder="{&quot;Authorization&quot;: &quot;Bearer {token}&quot;}"
              class="code-textarea"
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>请求体</label>
            <el-input
              v-model="nodeData.config.body"
              type="textarea"
              :rows="4"
              placeholder="{&quot;key&quot;: &quot;{input}&quot;}"
              class="code-textarea"
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>超时时间 (秒)</label>
            <el-input-number
              v-model="nodeData.config.timeout"
              :min="1"
              :max="300"
              @change="handleChange"
            />
          </div>
        </template>

        <!-- Tool 节点配置 -->
        <template v-else-if="selectedNode.type === 'tool'">
          <div class="form-group">
            <label>工具</label>
            <el-select
              v-model="nodeData.config.tool"
              filterable
              :loading="toolsLoading"
              @change="handleChange"
            >
              <el-option
                v-for="opt in toolOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
          </div>

          <div class="form-group">
            <label>参数 (JSON)</label>
            <el-input
              v-model="nodeData.config.parameters"
              type="textarea"
              :rows="4"
              placeholder="{&quot;query&quot;: &quot;{input}&quot;}"
              class="code-textarea"
              @input="handleChange"
            />
          </div>
        </template>

        <!-- Code 节点配置 -->
        <template v-else-if="selectedNode.type === 'code'">
          <div class="form-group">
            <label>代码</label>
            <el-input
              v-model="nodeData.config.code"
              type="textarea"
              :rows="10"
              placeholder="input = input  # 输入数据&#10;output = {'result': input}"
              class="code-textarea"
              @input="handleChange"
            />
            <p class="form-hint">
              可用变量: input (输入), json, math<br>
              必须设置 output 变量作为输出
            </p>
          </div>
        </template>

        <!-- Loop 节点配置 -->
        <template v-else-if="selectedNode.type === 'loop'">
          <div class="form-group">
            <label>循环模式</label>
            <el-select
              v-model="nodeData.config.mode"
              @change="handleChange"
            >
              <el-option
                label="For 循环"
                value="for"
              />
              <el-option
                label="While 循环"
                value="while"
              />
              <el-option
                label="ForEach 循环"
                value="foreach"
              />
            </el-select>
          </div>

          <div class="form-group">
            <label>迭代次数</label>
            <el-input-number
              v-model="nodeData.config.maxIterations"
              :min="1"
              :max="1000"
              @change="handleChange"
            />
          </div>

          <div class="form-group">
            <label>循环变量</label>
            <el-input
              v-model="nodeData.config.loopVariable"
              placeholder="item"
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>集合/数组</label>
            <el-input
              v-model="nodeData.config.collection"
              placeholder="{items}"
              class="code-textarea"
              @input="handleChange"
            />
          </div>
        </template>

        <!-- Variable 节点配置 -->
        <template v-else-if="selectedNode.type === 'variable'">
          <div class="form-group">
            <label>变量赋值</label>
            <div class="dynamic-list">
              <div
                v-for="(assignment, index) in nodeData.config.assignments"
                :key="index"
                class="assignment-item"
              >
                <el-input
                  v-model="assignment.name"
                  placeholder="变量名"
                  size="small"
                  @input="handleChange"
                />
                <span class="assign-op">=</span>
                <el-input
                  v-model="assignment.value"
                  placeholder="值"
                  size="small"
                  @input="handleChange"
                />
                <el-select
                  v-model="assignment.source"
                  size="small"
                  style="width: 100px"
                  @change="handleChange"
                >
                  <el-option
                    label="静态"
                    value="static"
                  />
                  <el-option
                    label="输入"
                    value="input"
                  />
                  <el-option
                    label="表达式"
                    value="expression"
                  />
                </el-select>
                <el-button
                  type="danger"
                  size="small"
                  text
                  @click="removeAssignment(index)"
                >
                  <X />
                </el-button>
              </div>
              <el-button
                size="small"
                @click="addAssignment"
              >
                <Plus /> 添加赋值
              </el-button>
            </div>
          </div>
        </template>

        <!-- Switch 节点配置 -->
        <template v-else-if="selectedNode.type === 'switch'">
          <SwitchConfigForm
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Transform 节点配置 -->
        <template v-else-if="selectedNode.type === 'transform'">
          <TransformConfigForm
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Email 节点配置 -->
        <template v-else-if="selectedNode.type === 'email'">
          <EmailConfigForm
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Delay 节点配置 -->
        <template v-else-if="selectedNode.type === 'delay'">
          <div class="form-group">
            <label>延时时长</label>
            <el-input-number
              v-model="nodeData.config.duration"
              :min="1"
              :max="3600"
              @change="handleChange"
            />
          </div>

          <div class="form-group">
            <label>时间单位</label>
            <el-select
              v-model="nodeData.config.unit"
              @change="handleChange"
            >
              <el-option
                label="秒"
                value="seconds"
              />
              <el-option
                label="分钟"
                value="minutes"
              />
              <el-option
                label="小时"
                value="hours"
              />
            </el-select>
          </div>
        </template>

        <!-- Input 节点配置 -->
        <template v-else-if="selectedNode.type === 'input'">
          <div class="form-group">
            <label>占位符文本</label>
            <el-input
              v-model="nodeData.config.placeholder"
              placeholder="请输入..."
              @input="handleChange"
            />
          </div>

          <div class="form-group">
            <label>输入类型</label>
            <el-select
              v-model="nodeData.config.inputType"
              @change="handleChange"
            >
              <el-option
                label="文本"
                value="text"
              />
              <el-option
                label="多行文本"
                value="textarea"
              />
              <el-option
                label="数字"
                value="number"
              />
            </el-select>
          </div>
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — Multimodal
             ===================================================== -->

        <!-- Image Generation -->
        <template v-else-if="selectedNode.type === 'image_generation'">
          <ImageGenerationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Video Generation -->
        <template v-else-if="selectedNode.type === 'video_generation'">
          <VideoGenerationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Audio Generation -->
        <template v-else-if="selectedNode.type === 'audio_generation'">
          <AudioGenerationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Subtitle Generation -->
        <template v-else-if="selectedNode.type === 'subtitle_generation'">
          <SubtitleGenerationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Image Editing -->
        <template v-else-if="selectedNode.type === 'image_editing'">
          <ImageEditingConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — Data
             ===================================================== -->

        <!-- Dataset Upload -->
        <template v-else-if="selectedNode.type === 'dataset_upload'">
          <DatasetUploadConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Data Annotation -->
        <template v-else-if="selectedNode.type === 'data_annotation'">
          <DataAnnotationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Data Augmentation -->
        <template v-else-if="selectedNode.type === 'data_augmentation'">
          <DataAugmentationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — MLOps
             ===================================================== -->

        <!-- Model Training -->
        <template v-else-if="selectedNode.type === 'model_training'">
          <ModelTrainingConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Model Evaluation -->
        <template v-else-if="selectedNode.type === 'model_evaluation'">
          <ModelEvaluationConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Model Deployment -->
        <template v-else-if="selectedNode.type === 'model_deployment'">
          <ModelDeploymentConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — RAG
             ===================================================== -->

        <!-- Document Loader -->
        <template v-else-if="selectedNode.type === 'document_loader'">
          <DocumentLoaderConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Embedding -->
        <template v-else-if="selectedNode.type === 'embedding'">
          <EmbeddingConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Vector Store -->
        <template v-else-if="selectedNode.type === 'vector_store'">
          <VectorStoreConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Retriever -->
        <template v-else-if="selectedNode.type === 'retriever'">
          <RetrieverConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Reranker -->
        <template v-else-if="selectedNode.type === 'reranker'">
          <RerankerConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — Agent
             ===================================================== -->

        <!-- Agent -->
        <template v-else-if="selectedNode.type === 'agent'">
          <AgentConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Planner -->
        <template v-else-if="selectedNode.type === 'planner'">
          <PlannerConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Executor -->
        <template v-else-if="selectedNode.type === 'executor'">
          <ExecutorConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Memory -->
        <template v-else-if="selectedNode.type === 'memory'">
          <MemoryConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- =====================================================
             DOMAIN NODE CONFIG FORMS — Utility
             ===================================================== -->

        <!-- File Reader -->
        <template v-else-if="selectedNode.type === 'file_reader'">
          <FileReaderConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- File Writer -->
        <template v-else-if="selectedNode.type === 'file_writer'">
          <FileWriterConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- Web Scraper -->
        <template v-else-if="selectedNode.type === 'web_scraper'">
          <WebScraperConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- CSV Transform -->
        <template v-else-if="selectedNode.type === 'csv_transform'">
          <CsvTransformConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>

        <!-- JSON Transform -->
        <template v-else-if="selectedNode.type === 'json_transform'">
          <JsonTransformConfig
            :model-value="nodeData.config"
            @update:model-value="handleConfigUpdate"
            @change="handleConfigChange"
          />
        </template>
      </div>

      <!-- 操作按钮 -->
      <div class="property-actions">
        <el-tooltip
          content="从画布中删除此节点"
          placement="top"
        >
          <el-button
            type="danger"
            @click="handleDelete"
          >
            <Trash2 class="btn-icon" />
            删除节点
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <!-- 空状态 -->
    <div
      v-else
      class="empty-state"
    >
      <MousePointer class="empty-icon" />
      <p>选择节点以编辑属性</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { X, Plus, Trash2, MousePointer } from 'lucide-vue-next'
import { APP_CONFIG } from '@/config'
import { TOOL_OPTIONS, MODEL_OPTIONS } from '@/config/toolConfig'
import SwitchConfigForm from './config-forms/SwitchConfigForm.vue'
import TransformConfigForm from './config-forms/TransformConfigForm.vue'
import EmailConfigForm from './config-forms/EmailConfigForm.vue'

// Domain node config forms — Multimodal
import ImageGenerationConfig from './configs/ImageGenerationConfig.vue'
import VideoGenerationConfig from './configs/VideoGenerationConfig.vue'
import AudioGenerationConfig from './configs/AudioGenerationConfig.vue'
import SubtitleGenerationConfig from './configs/SubtitleGenerationConfig.vue'
import ImageEditingConfig from './configs/ImageEditingConfig.vue'

// Domain node config forms — Data
import DatasetUploadConfig from './configs/DatasetUploadConfig.vue'
import DataAnnotationConfig from './configs/DataAnnotationConfig.vue'
import DataAugmentationConfig from './configs/DataAugmentationConfig.vue'

// Domain node config forms — MLOps
import ModelTrainingConfig from './configs/ModelTrainingConfig.vue'
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

const workflowStore = useWorkflowStore()

const props = defineProps({
  selectedNode: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['change', 'delete'])

const nodeData = reactive({
  name: '',
  type: '',
  description: '',
  config: {}
})

// 可用的模型和工具列表（从 API 获取）
const availableModels = ref([])
const availableTools = ref([])
const modelsLoading = ref(false)
const toolsLoading = ref(false)

// 加载模型和工具列表
async function loadModelsAndTools() {
  try {
    const [modelsRes, toolsRes] = await Promise.allSettled([
      workflowStore.fetchAvailableModels({ type: 'chat' }),
      workflowStore.fetchAvailableTools()
    ])

    if (modelsRes.status === 'fulfilled' && modelsRes.value) {
      availableModels.value = modelsRes.value.map(m => ({
        value: m.model_id || m.id,
        label: `${m.name} (${m.provider?.name || m.provider_name || 'Unknown'})`
      }))
    }

    if (toolsRes.status === 'fulfilled' && toolsRes.value) {
      availableTools.value = toolsRes.value.map(t => ({
        value: t.name,
        label: t.name
      }))
    }
  } catch {
    // Error shown via appStore
  }
}

// 模型选项（优先使用 API 数据，备用常量）
const modelOptions = computed(() => {
  if (availableModels.value.length > 0) {
    return availableModels.value
  }
  return MODEL_OPTIONS
})

// 工具选项（优先使用 API 数据，备用常量）
const toolOptions = computed(() => {
  if (availableTools.value.length > 0) {
    return availableTools.value
  }
  return TOOL_OPTIONS
})

onMounted(() => {
  loadModelsAndTools()
})

const nodeTypes = [
  { type: 'start', label: '开始' },
  { type: 'end', label: '结束' },
  { type: 'llm', label: '大语言模型' },
  { type: 'prompt', label: '提示词' },
  { type: 'condition', label: '条件判断' },
  { type: 'tool', label: '工具' },
  { type: 'input', label: '输入' },
  { type: 'output', label: '输出' },
  { type: 'http', label: 'HTTP请求' },
  { type: 'code', label: '代码执行' },
  { type: 'loop', label: '循环' },
  { type: 'variable', label: '变量' },
  { type: 'switch', label: '分支' },
  { type: 'transform', label: '数据转换' },
  { type: 'email', label: '发送邮件' },
  { type: 'delay', label: '延时' },
]

const sectionTitle = computed(() => {
  const titles = {
    llm: '模型配置',
    prompt: '模板配置',
    condition: '条件配置',
    http: '请求配置',
    tool: '工具配置',
    code: '代码配置',
    input: '输入配置',
    output: '输出配置',
    variable: '变量配置',
    loop: '循环配置',
    switch: '分支配置',
    transform: '转换配置',
    email: '邮件配置',
    delay: '延时配置'
  }
  return titles[nodeData.type] || '节点配置'
})

watch(() => props.selectedNode, (newNode) => {
  if (newNode) {
    nodeData.name = newNode.data?.label || ''
    nodeData.type = newNode.type || ''
    nodeData.description = newNode.data?.description || ''
    nodeData.config = { ...(newNode.data?.config || {}) }

    // 确保必要字段存在
    if (nodeData.type === 'llm') {
      nodeData.config = {
        model: APP_CONFIG.llm.defaultModel,
        temperature: APP_CONFIG.llm.defaultTemperature,
        systemPrompt: '',
        userTemplate: '{input}',
        ...nodeData.config
      }
    } else if (nodeData.type === 'prompt') {
      nodeData.config = {
        template: '',
        variables: [],
        ...nodeData.config
      }
    } else if (nodeData.type === 'condition') {
      nodeData.config = {
        conditions: [],
        defaultBranch: 'false',
        ...nodeData.config
      }
    } else if (nodeData.type === 'http') {
      nodeData.config = {
        method: 'GET',
        url: '',
        headers: '{}',
        body: '',
        timeout: 30,
        ...nodeData.config
      }
    } else if (nodeData.type === 'tool') {
      nodeData.config = {
        tool: 'calculator',
        parameters: '{}',
        ...nodeData.config
      }
    } else if (nodeData.type === 'code') {
      nodeData.config = {
        code: 'input = input\noutput = {"result": input}',
        ...nodeData.config
      }
    } else if (nodeData.type === 'input') {
      nodeData.config = {
        placeholder: '请输入...',
        inputType: 'text',
        ...nodeData.config
      }
    } else if (nodeData.type === 'loop') {
      nodeData.config = {
        mode: 'foreach',
        maxIterations: 10,
        loopVariable: 'item',
        collection: '',
        ...nodeData.config
      }
    } else if (nodeData.type === 'variable') {
      nodeData.config = {
        assignments: [],
        ...nodeData.config
      }
    } else if (nodeData.type === 'switch') {
      nodeData.config = {
        label: '',
        description: '',
        branches: [
          { id: 'branch_1', label: '条件 1', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' },
          { id: 'branch_2', label: '条件 2', conditionType: 'expression', expression: '', field: '', operator: 'equals', value: '' }
        ],
        defaultBranch: '默认',
        ...nodeData.config
      }
    } else if (nodeData.type === 'transform') {
      nodeData.config = {
        label: '',
        description: '',
        transformType: 'map',
        mappings: [],
        filterExpression: '',
        sortField: '',
        sortOrder: 'asc',
        mergeStrategy: 'deep',
        mergeSources: '',
        splitDelimiter: ',',
        extractPath: '',
        customScript: '',
        ...nodeData.config
      }
    } else if (nodeData.type === 'email') {
      nodeData.config = {
        label: '',
        description: '',
        to: '',
        cc: '',
        bcc: '',
        fromEmail: '',
        subject: '',
        isHtml: false,
        body: '',
        smtpConfig: {
          server: '',
          port: 587,
          useTls: true,
          username: '',
          password: ''
        },
        ...nodeData.config
      }
    } else if (nodeData.type === 'delay') {
      nodeData.config = {
        duration: 1,
        unit: 'seconds',
        ...nodeData.config
      }
    }
  }
}, { immediate: true, deep: true })

function handleChange() {
  emit('change', {
    id: props.selectedNode?.id,
    data: {
      label: nodeData.name,
      type: nodeData.type,
      description: nodeData.description,
      config: { ...nodeData.config }
    }
  })
}

function handleConfigUpdate(newConfig) {
  nodeData.config = newConfig
}

function handleConfigChange(newConfig) {
  handleChange()
}

function handleDelete() {
  emit('delete', props.selectedNode?.id)
}

function addVariable() {
  if (!nodeData.config.variables) {
    nodeData.config.variables = []
  }
  nodeData.config.variables.push({ name: '', value: '' })
  handleChange()
}

function removeVariable(index) {
  nodeData.config.variables.splice(index, 1)
  handleChange()
}

function addCondition() {
  if (!nodeData.config.conditions) {
    nodeData.config.conditions = []
  }
  nodeData.config.conditions.push({
    field: 'last_output',
    operator: 'equals',
    value: '',
    branch: 'true'
  })
  handleChange()
}

function removeCondition(index) {
  nodeData.config.conditions.splice(index, 1)
  handleChange()
}

function addAssignment() {
  if (!nodeData.config.assignments) {
    nodeData.config.assignments = []
  }
  nodeData.config.assignments.push({ name: '', value: '', source: 'static' })
  handleChange()
}

function removeAssignment(index) {
  nodeData.config.assignments.splice(index, 1)
  handleChange()
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.property-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--bg-primary)-secondary;
  border-left: 1px solid var(--border-primary);
  transform: translateX(100%);
  transition: transform $transition-normal;

  &.visible {
    transform: translateX(0);
  }
}

.panel-content {
  flex: 1;
  overflow-y: auto;
}

.property-section {
  padding: $spacing-4;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }
}

.section-title {
  margin: 0 0 $spacing-4;
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-group {
  margin-bottom: $spacing-4;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    margin-bottom: $spacing-2;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary)-secondary;
  }

  :deep(.el-input__wrapper),
  :deep(.el-textarea__inner) {
    background-color: var(--bg-primary)-tertiary;
    border: 1px solid var(--border-primary);
    box-shadow: none;

    &:hover {
      border-color: var(--border-primary)-hover;
    }

    &:focus {
      border-color: $color-primary;
    }
  }

  :deep(.el-select) {
    width: 100%;
  }
}

.form-hint {
  margin: $spacing-2 0 0;
  font-size: $font-size-xs;
  color: var(--text-primary)-tertiary;
}

.slider-group {
  display: flex;
  align-items: center;
  gap: $spacing-3;

  :deep(.el-slider) {
    flex: 1;
  }

  .slider-value {
    min-width: 40px;
    font-size: $font-size-sm;
    color: var(--text-primary)-secondary;
    text-align: right;
  }
}

.code-textarea {
  :deep(.el-textarea__inner) {
    font-family: 'Fira Code', monospace;
    font-size: $font-size-xs;
    line-height: 1.6;
  }
}

.dynamic-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.list-item {
  display: flex;
  gap: $spacing-2;
  align-items: center;

  .el-input {
    flex: 1;
  }
}

.condition-item {
  padding: $spacing-3;
  background-color: var(--bg-primary)-tertiary;
  border-radius: $radius-md;
  margin-bottom: $spacing-2;

  .condition-row {
    display: flex;
    gap: $spacing-2;
    margin-bottom: $spacing-2;

    &:last-child {
      margin-bottom: 0;
    }

    .el-select {
      width: 100px;
    }

    .el-input {
      flex: 1;
    }
  }
}

.assignment-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2;
  background-color: var(--bg-primary)-tertiary;
  border-radius: $radius-md;
  margin-bottom: $spacing-2;

  .el-input {
    flex: 1;
  }

  .assign-op {
    color: $color-primary;
    font-weight: $font-weight-bold;
  }
}

.branch-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2;
  background-color: var(--bg-primary)-tertiary;
  border-radius: $radius-md;
  margin-bottom: $spacing-2;

  .el-input {
    flex: 1;
  }
}

.property-actions {
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);

  .el-button {
    width: 100%;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: $spacing-8;
  text-align: center;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--text-primary)-tertiary;
    margin-bottom: $spacing-4;
  }

  p {
    color: var(--text-primary)-tertiary;
    margin: 0;
  }
}
</style>



