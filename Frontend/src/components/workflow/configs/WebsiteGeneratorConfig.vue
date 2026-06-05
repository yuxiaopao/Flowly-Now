<template>
  <div class="config-form website-generator-config-form">
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
            placeholder="网站功能描述"
            @change="handleChange"
          />
        </el-form-item>
      </div>

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
              label="文本分类"
              value="nlp_classification"
            />
          </el-select>
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

      <!-- 输出设置 -->
      <div class="form-section">
        <h4 class="section-title">
          输出设置
        </h4>
        <el-form-item
          label="输出目录"
          required
        >
          <el-input
            v-model="localData.outputDir"
            placeholder="保存生成的网站代码"
            @change="handleOutputDirChange"
          />
          <div
            class="field-hint"
            :class="{ 'hint-warning': outputDirWarning }"
          >
            <el-icon><Warning /></el-icon>
            {{ outputDirWarning || '必须是空文件夹，请先创建目录' }}
          </div>
        </el-form-item>
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
          <el-empty description="当前工作流中没有模型训练节点">
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
import { reactive, ref, computed, watch } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { ElMessage } from 'element-plus'
import { Cpu, Check, Warning } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['update:modelValue', 'change'])

const workflowStore = useWorkflowStore()

const showNodeSelector = ref(false)
const availableNodes = ref([])
const selectedNodeId = ref(null)
const outputDirWarning = ref('')

const localData = reactive({
  label: '',
  description: '',
  websiteType: 'classification',
  modelPath: '',
  labels: '',
  framework: 'pytorch',
  outputDir: '',
  frontendFramework: 'vue',
  backendFramework: 'flask',
  port: 5000,
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      websiteType: newVal.websiteType || 'classification',
      modelPath: newVal.modelPath || '',
      labels: newVal.labels || '',
      framework: newVal.framework || 'pytorch',
      outputDir: newVal.outputDir || '',
      frontendFramework: newVal.frontendFramework || 'vue',
      backendFramework: newVal.backendFramework || 'flask',
      port: newVal.port || 5000,
    })
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  emit('update:modelValue', { ...localData })
  emit('change', { ...localData })
}

const handleModelPathChange = () => {
  if (localData.modelPath && !localData.label) {
    const name = localData.modelPath.split('/').pop().replace(/\.[^.]+$/, '')
    if (name) {
      localData.label = `${name}预测网站`
    }
  }
  handleChange()
}

const handleOutputDirChange = () => {
  outputDirWarning.value = ''
  if (localData.outputDir) {
    outputDirWarning.value = '输出目录必须是空文件夹，请先创建目录'
  }
  handleChange()
}

const selectFromTrainingNode = () => {
  const trainingNodes = workflowStore.nodes.filter(n => {
    const type = n.type || n.data?.type
    return type === 'model_training' || type === 'training'
  })
  if (trainingNodes.length === 0) {
    ElMessage.warning('当前工作流中没有模型训练节点')
    return
  }
  availableNodes.value = trainingNodes
  selectedNodeId.value = null
  showNodeSelector.value = true
}

const onNodeSelected = (node) => {
  const config = node.data?.config || {}
  localData.modelPath = config.modelPath || config.outputDir || ''
  localData.labels = config.labels || ''
  localData.framework = config.framework || 'pytorch'
  if (localData.modelPath) {
    const name = localData.modelPath.split('/').pop().replace(/\.[^.]+$/, '')
    localData.label = `${name}预测网站`
  }
  handleChange()
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
