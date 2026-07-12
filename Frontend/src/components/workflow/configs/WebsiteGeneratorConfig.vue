<template>
  <div class="config-form website-generator-config-form">
    <TrainingSiteWizard
      v-model="wizardData"
      :profile="upstreamProfile"
      @change="onWizardChange"
      @pick-training="selectFromTrainingNode"
      @finished="onWizardFinished"
    />

    <el-divider>高级选项</el-divider>

    <el-form
      :model="localData"
      label-position="top"
      size="small"
    >
      <!-- 模型选择 -->
      <div class="form-section">
        <h4 class="section-title">
          模型选择
        </h4>
        <el-form-item label="训练任务">
          <el-select
            v-model="localData.websiteType"
            @change="handleChange"
          >
            <el-option
              label="图像分类"
              value="classification"
            />
            <el-option
              label="回归预测"
              value="regression"
            />
            <el-option
              label="目标检测"
              value="detection"
            />
            <el-option
              label="CLIP 图文检索"
              value="clip_retrieval"
            />
            <el-option
              label="文本分类"
              value="nlp_classification"
            />
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="localData.websiteType === 'clip_retrieval'"
          label="检索索引目录"
        >
          <div class="model-path-input">
            <el-input
              v-model="localData.indexDir"
              placeholder="clip_retrieval 节点输出的 index_dir"
              @change="handleChange"
            />
            <el-button
              type="primary"
              plain
              size="small"
              @click="selectFromRetrievalNode"
            >
              <Search class="btn-icon" />
              从检索节点选择
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="模型路径">
          <div class="model-path-input">
            <el-input
              v-model="localData.modelPath"
              placeholder="训练输出的模型路径"
              @change="handleModelPathChange"
            />
            <el-button
              type="primary"
              plain
              size="small"
              @click="selectFromTrainingNode"
            >
              <Cpu class="btn-icon" />
              从训练节点选择
            </el-button>
          </div>
          <div class="field-hint">
            从模型训练节点输出获取
          </div>
        </el-form-item>
        <el-form-item label="类别标签">
          <el-input
            v-model="localData.labels"
            type="textarea"
            :rows="2"
            placeholder="cat, dog, bird"
            @change="handleChange"
          />
          <div class="field-hint">
            逗号分隔，与训练时的标签一致
          </div>
        </el-form-item>
        <el-form-item label="ML框架">
          <el-select
            v-model="localData.framework"
            @change="handleChange"
          >
            <el-option
              label="PyTorch"
              value="pytorch"
            />
            <el-option
              label="Transformers"
              value="transformers"
            />
            <el-option
              label="Keras"
              value="keras"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 输出设置 — 向导 Step4 已覆盖，此处保留 framework 选项 -->
      <div class="form-section">
        <h4 class="section-title">
          技术栈
        </h4>
        <el-form-item label="前端框架">
          <el-select
            v-model="localData.frontendFramework"
            @change="handleChange"
          >
            <el-option
              label="Vue 3"
              value="vue"
            />
            <el-option
              label="React"
              value="react"
            />
            <el-option
              label="纯HTML/JS"
              value="html"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="后端框架">
          <el-select
            v-model="localData.backendFramework"
            @change="handleChange"
          >
            <el-option
              label="Flask"
              value="flask"
            />
            <el-option
              label="FastAPI"
              value="fastapi"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="后端端口">
          <el-input-number
            v-model="localData.port"
            :min="1000"
            :max="65535"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          生成预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">任务:</span>
            <span class="preview-value">{{ localData.websiteType || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">前端:</span>
            <span class="preview-value">{{ localData.frontendFramework || 'vue' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">后端:</span>
            <span class="preview-value">{{ localData.backendFramework || 'flask' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">标签:</span>
            <span class="preview-value">{{ formatLabels(localData.labels) }}</span>
          </div>
        </div>
      </div>
    </el-form>

    <!-- Training Node Selector Dialog -->
    <el-dialog
      v-model="showNodeSelector"
      title="选择训练节点"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="node-selector-content">
        <div
          v-if="availableNodes.length === 0"
          class="empty-state"
        >
          <el-empty description="当前工作流中没有训练节点">
            <el-button
              type="primary"
              @click="showNodeSelector = false"
            >
              关闭
            </el-button>
          </el-empty>
        </div>

        <div
          v-else
          class="node-list"
        >
          <div
            v-for="node in availableNodes"
            :key="node.id"
            class="node-item"
            :class="{ selected: selectedNodeId === node.id }"
            @click="selectedNodeId = node.id"
          >
            <div class="node-icon">
              <Cpu class="icon" />
            </div>
            <div class="node-info">
              <div class="node-name">
                {{ node.label || node.data?.label || '模型训练节点' }}
              </div>
              <div class="node-meta">
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ node.data?.config?.framework || node.data?.config?.modelType || 'pytorch' }}
                </el-tag>
                <span class="node-labels">
                  {{ formatNodeLabels(node.data?.config?.labels) }}
                </span>
              </div>
              <div
                v-if="node.data?.config?.modelPath || node.data?.config?.outputDir"
                class="node-path"
              >
                {{ node.data?.config?.modelPath || node.data?.config?.outputDir }}
              </div>
            </div>
            <div
              v-if="selectedNodeId === node.id"
              class="node-check"
            >
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showNodeSelector = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!selectedNodeId"
          @click="confirmNodeSelection"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { ElMessage } from 'element-plus'
import { Cpu, Check, Search } from 'lucide-vue-next'
import TrainingSiteWizard from './TrainingSiteWizard.vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const workflowStore = useWorkflowStore()

const showNodeSelector = ref(false)
const nodeSelectorMode = ref('training')
const availableNodes = ref([])
const selectedNodeId = ref(null)

const wizardData = reactive({
  domain: '',
  scenario: '',
  uiTone: 'neutral',
  siteName: '',
  logoUrl: '',
  primaryColor: '#f59e0b',
  contactEmail: '',
  usageDescription: '',
  disclaimer: '',
  privacy: '',
  outputDir: '',
  port: 5000,
  qaProfile: 'default',
  modelPath: '',
  labels: '',
  websiteType: 'detection',
  wizardStep: 0,
  wizardCompleted: false,
})

const upstreamProfile = computed(() => {
  const profiler = workflowStore.nodes.find((n) => n.type === 'project_profiler')
  if (!profiler) return {}
  const out = profiler.data?.output || profiler.data?.result || {}
  return out.profile || profiler.data?.config?.profile || {}
})

const localData = reactive({
  label: '',
  description: '',
  websiteType: 'detection',
  modelPath: '',
  labels: '',
  framework: 'pytorch',
  outputDir: '',
  frontendFramework: 'vue',
  backendFramework: 'flask',
  port: 5000,
  trainingRunId: '',
  indexDir: '',
  wizard: {},
  profile: {},
  qaProfile: 'default',
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      websiteType: newVal.websiteType || 'detection',
      modelPath: newVal.modelPath || '',
      labels: newVal.labels || '',
      framework: newVal.framework || 'pytorch',
      outputDir: newVal.outputDir || '',
      frontendFramework: newVal.frontendFramework || 'vue',
      backendFramework: newVal.backendFramework || 'flask',
      port: newVal.port || 5000,
      trainingRunId: newVal.trainingRunId || '',
      indexDir: newVal.indexDir || '',
      qaProfile: newVal.qaProfile || 'default',
      profile: newVal.profile || upstreamProfile.value || {},
    })
    const w = newVal.wizard || {}
    Object.assign(wizardData, {
      domain: w.domain || upstreamProfile.value?.domain || '',
      scenario: w.scenario || upstreamProfile.value?.scenario || '',
      uiTone: w.uiTone || upstreamProfile.value?.ui_tone || 'neutral',
      siteName: w.siteName || newVal.siteName || '',
      logoUrl: w.logoUrl || '',
      primaryColor: w.primaryColor || '#f59e0b',
      contactEmail: w.contactEmail || '',
      usageDescription: w.usageDescription || '',
      disclaimer: w.disclaimer || '',
      privacy: w.privacy || '',
      outputDir: w.outputDir || newVal.outputDir || '',
      port: w.port || newVal.port || 5000,
      qaProfile: w.qaProfile || newVal.qaProfile || 'default',
      modelPath: w.modelPath || newVal.modelPath || '',
      labels: w.labels || newVal.labels || '',
      websiteType: w.websiteType || newVal.websiteType || 'detection',
      wizardStep: w.wizardStep ?? 0,
      wizardCompleted: w.wizardCompleted ?? false,
    })
  }
}, { immediate: true, deep: true })

watch(upstreamProfile, (p) => {
  if (p && Object.keys(p).length && !wizardData.scenario) {
    wizardData.domain = p.domain || wizardData.domain
    wizardData.scenario = p.scenario || wizardData.scenario
    wizardData.uiTone = p.ui_tone || wizardData.uiTone
    wizardData.usageDescription = wizardData.usageDescription || p.scenario || ''
    localData.profile = p
    syncEmit()
  }
}, { deep: true })

function buildPayload() {
  const wizard = { ...wizardData }
  return {
    ...localData,
    siteName: wizard.siteName,
    outputDir: wizard.outputDir || localData.outputDir,
    port: wizard.port || localData.port,
    qaProfile: wizard.qaProfile || localData.qaProfile,
    modelPath: wizard.modelPath || localData.modelPath,
    labels: wizard.labels || localData.labels,
    websiteType: wizard.websiteType || localData.websiteType,
    indexDir: localData.indexDir,
    description: wizard.usageDescription || localData.description,
    wizard,
    profile: localData.profile || upstreamProfile.value || {},
  }
}

function syncEmit() {
  const payload = buildPayload()
  emit('update:modelValue', payload)
  emit('change', payload)
}

const handleChange = () => syncEmit()

const onWizardChange = (w) => {
  Object.assign(wizardData, w)
  localData.outputDir = w.outputDir || localData.outputDir
  localData.port = w.port || localData.port
  localData.qaProfile = w.qaProfile || localData.qaProfile
  localData.modelPath = w.modelPath || localData.modelPath
  localData.labels = w.labels || localData.labels
  localData.websiteType = w.websiteType || localData.websiteType
  syncEmit()
}

const onWizardFinished = () => {
  ElMessage.success('建站向导已完成，可执行工作流')
  syncEmit()
}

const handleModelPathChange = () => {
  if (wizardData.modelPath && !wizardData.siteName) {
    const name = wizardData.modelPath.split('/').pop().replace(/\.[^.]+$/, '')
    if (name) wizardData.siteName = `${name}识别系统`
  }
  syncEmit()
}

const selectFromTrainingNode = () => {
  nodeSelectorMode.value = 'training'
  const trainingNodes = workflowStore.nodes.filter(n => {
    const type = n.type || n.data?.type
    return type === 'model_training' || type === 'yolo_training' || type === 'clip_classification' || type === 'training'
  })
  if (trainingNodes.length === 0) {
    ElMessage.warning('当前工作流中没有训练节点（模型训练 / YOLO / CLIP 分类）')
    return
  }
  availableNodes.value = trainingNodes
  selectedNodeId.value = null
  showNodeSelector.value = true
}

const selectFromRetrievalNode = () => {
  nodeSelectorMode.value = 'retrieval'
  const retrievalNodes = workflowStore.nodes.filter((n) => (n.type || n.data?.type) === 'clip_retrieval')
  if (retrievalNodes.length === 0) {
    ElMessage.warning('当前工作流中没有 CLIP 检索节点')
    return
  }
  availableNodes.value = retrievalNodes
  selectedNodeId.value = null
  showNodeSelector.value = true
}

const onNodeSelected = (node) => {
  const config = node.data?.config || {}
  const output = node.data?.output || node.data?.result || {}
  const nodeType = node.type || node.data?.type

  if (nodeType === 'clip_retrieval') {
    localData.indexDir = output.indexDir || output.index_dir || config.outputDir || ''
    localData.websiteType = 'clip_retrieval'
    wizardData.websiteType = 'clip_retrieval'
    localData.trainingRunId = output.trainingRunId || output.training_run_id || ''
    if (!wizardData.siteName) {
      wizardData.siteName = 'CLIP 图文检索'
    }
    syncEmit()
    return
  }

  const isYolo = nodeType === 'yolo_training'
  const isClipCls = nodeType === 'clip_classification'

  localData.modelPath = output.bestWeightPath || output.best_weight_path || output.modelPath || output.model_path || config.modelPath || config.outputDir || ''
  wizardData.modelPath = localData.modelPath
  const labelStr = Array.isArray(output.classNames || output.class_names)
    ? (output.classNames || output.class_names).join(', ')
    : (config.labels || config.classNames || '')
  localData.labels = labelStr
  wizardData.labels = labelStr
  localData.framework = isYolo ? 'ultralytics' : (isClipCls ? 'clip' : (config.framework || 'pytorch'))
  localData.websiteType = isYolo ? 'detection' : (isClipCls ? 'classification' : (config.websiteType || 'classification'))
  wizardData.websiteType = localData.websiteType
  localData.trainingRunId = output.trainingRunId || output.training_run_id || ''
  if (localData.modelPath && !wizardData.siteName) {
    const name = localData.modelPath.split('/').pop().replace(/\.[^.]+$/, '')
    wizardData.siteName = `${name}识别系统`
  }
  syncEmit()
}

const confirmNodeSelection = () => {
  const node = availableNodes.value.find(n => n.id === selectedNodeId.value)
  if (node) {
    onNodeSelected(node)
  }
  showNodeSelector.value = false
}

const formatNodeLabels = (labels) => {
  if (!labels) return '未设置标签'
  if (typeof labels === 'string') {
    const list = labels.split(',').map(l => l.trim()).filter(Boolean)
    return list.slice(0, 3).join(', ') + (list.length > 3 ? '...' : '') || '未设置标签'
  }
  if (Array.isArray(labels)) {
    return labels.slice(0, 3).join(', ') + (labels.length > 3 ? '...' : '') || '未设置标签'
  }
  return '未设置标签'
}

const formatLabels = (labels) => {
  if (!labels) return '(未设置)'
  const list = labels.split(',').map(l => l.trim()).filter(Boolean)
  return list.length > 0 ? list.slice(0, 3).join(', ') + (list.length > 3 ? '...' : '') : '(未设置)'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.config-form { padding: 0; }

.form-section {
  margin-bottom: $spacing-5;
  padding-bottom: $spacing-4;
  border-bottom: 1px solid var(--border-primary);
  &:last-child { border-bottom: none; margin-bottom: 0; }
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
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;

  &.hint-warning {
    color: var(--color-warning);
  }
}

.btn-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-1;
}

.model-path-input {
  display: flex;
  gap: $spacing-2;

  .el-input {
    flex: 1;
  }
}

// Node selector dialog
.node-selector-content {
  max-height: 400px;
  overflow-y: auto;
}

.empty-state {
  padding: $spacing-8;
}

.node-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.node-item {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  padding: $spacing-3;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--bg-tertiary);
    border-color: var(--color-primary);
  }

  &.selected {
    background: var(--color-primary-light-9);
    border-color: var(--color-primary);
  }
}

.node-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  color: var(--color-primary);
  flex-shrink: 0;

  .icon {
    width: 20px;
    height: 20px;
  }
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.node-meta {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-bottom: 4px;
}

.node-labels {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.node-path {
  font-size: $font-size-xs;
  color: var(--text-secondary);
  font-family: 'Fira Code', monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-check {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border-radius: 50%;
  color: white;
  flex-shrink: 0;
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
  &:last-child { margin-bottom: 0; }
  .preview-label { color: var(--text-tertiary); min-width: 80px; }
  .preview-value { color: var(--text-primary); font-family: 'Fira Code', monospace; font-size: $font-size-xs; }
}
</style>
