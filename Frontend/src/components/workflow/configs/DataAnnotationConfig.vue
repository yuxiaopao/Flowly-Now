<template>
  <div class="config-form data-annotation-config-form">
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

      <!-- 数据集选择 -->
      <div class="form-section">
        <h4 class="section-title">
          选择数据集
        </h4>
        
        <el-form-item label="数据集">
          <div class="dataset-selector">
            <el-button
              type="primary"
              plain
              @click="showDatasetDialog = true"
            >
              <FolderOpen class="btn-icon" />
              选择数据集
            </el-button>
            
            <div
              v-if="selectedDataset"
              class="selected-dataset"
            >
              <div class="dataset-info">
                <span class="dataset-name">{{ selectedDataset.name }}</span>
                <span class="dataset-meta">
                  {{ selectedDataset.rowCount }} 行 · {{ selectedDataset.columnCount }} 列 · {{ selectedDataset.sizeDisplay }}
                </span>
              </div>
              <el-button
                type="danger"
                circle
                size="small"
                @click="clearSelectedDataset"
              >
                <el-icon><X /></el-icon>
              </el-button>
            </div>
          </div>
        </el-form-item>
      </div>

      <!-- 标注配置 -->
      <div class="form-section">
        <h4 class="section-title">
          标注任务设置
        </h4>
        
        <el-form-item label="标注类型">
          <el-select
            v-model="localData.annotationType"
            @change="handleChange"
          >
            <el-option
              label="分类 (Classification)"
              value="classification"
            />
            <el-option
              label="命名实体识别 (NER)"
              value="ner"
            />
            <el-option
              label="情感分析 (Sentiment)"
              value="sentiment"
            />
            <el-option
              label="目标检测 (Detection)"
              value="detection"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="标签"
          required
        >
          <el-input
            v-model="localData.labels"
            type="textarea"
            :rows="3"
            placeholder="标签1, 标签2, 标签3"
            @change="handleChange"
          />
          <div class="field-hint">
            多个标签用逗号分隔
          </div>
        </el-form-item>

        <el-form-item label="AI 辅助标注">
          <el-switch
            v-model="localData.modelAssisted"
            @change="handleChange"
          />
          <span class="field-hint">使用 AI 模型预标注，人工审核修正</span>
        </el-form-item>

        <el-form-item
          v-if="localData.modelAssisted"
          label="AI 模型"
        >
          <el-select
            v-model="localData.modelId"
            placeholder="选择 AI 模型"
            @change="handleChange"
          >
            <el-option
              label="GPT-4o-mini"
              value="gpt-4o-mini"
            />
            <el-option
              label="GPT-4o"
              value="gpt-4o"
            />
            <el-option
              label="Claude 3 Haiku"
              value="claude-3-haiku"
            />
            <el-option
              label="Claude 3.5 Sonnet"
              value="claude-3-5-sonnet"
            />
            <el-option
              label="自定义模型"
              value="custom"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 标注工作台 -->
      <div class="form-section">
        <h4 class="section-title">
          标注工作台
        </h4>
        
        <div class="workspace-actions">
          <el-button
            type="primary"
            :disabled="!selectedDataset || !localData.labels"
            @click="createAndOpenAnnotation"
          >
            <Tag class="btn-icon" />
            创建并打开标注工作台
          </el-button>
          
          <el-button
            v-if="projectId"
            type="default"
            @click="openExistingAnnotation"
          >
            <ExternalLink class="btn-icon" />
            打开已有标注
          </el-button>
        </div>

        <div
          v-if="projectId"
          class="existing-project"
        >
          <el-tag type="success">
            已关联项目: {{ projectId }}
          </el-tag>
        </div>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">类型:</span>
            <span class="preview-value">{{ getAnnotationTypeLabel(localData.annotationType) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">数据集:</span>
            <span class="preview-value">{{ selectedDataset?.name || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">标签:</span>
            <span class="preview-value">{{ parsedLabels.join(', ') || '(未设置)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">AI辅助:</span>
            <el-tag
              size="small"
              :type="localData.modelAssisted ? 'success' : 'info'"
            >
              {{ localData.modelAssisted ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>

    <!-- 数据集选择对话框 -->
    <el-dialog
      v-model="showDatasetDialog"
      title="选择数据集"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="dataset-dialog-content">
        <div class="dialog-toolbar">
          <el-input
            v-model="datasetSearch"
            placeholder="搜索数据集..."
            clearable
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button @click="loadDatasets">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div
          v-if="loadingDatasets"
          class="loading-state"
        >
          <el-icon class="is-loading">
            <Loader />
          </el-icon>
          <span>加载中...</span>
        </div>

        <div
          v-else-if="datasets.length === 0"
          class="empty-state"
        >
          <el-empty description="暂无数据集">
            <el-button
              type="primary"
              @click="goToUpload"
            >
              上传数据集
            </el-button>
          </el-empty>
        </div>

        <div
          v-else
          class="dataset-list"
        >
          <div
            v-for="dataset in filteredDatasets"
            :key="dataset.id"
            class="dataset-item"
            :class="{ selected: selectedDatasetId === dataset.id }"
            @click="selectDataset(dataset)"
          >
            <div class="dataset-item-info">
              <div class="dataset-item-name">
                {{ dataset.name }}
              </div>
              <div class="dataset-item-meta">
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ dataset.sourceDisplay }}
                </el-tag>
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ dataset.formatDisplay }}
                </el-tag>
                <span class="meta-text">{{ dataset.rowCount }} 行</span>
                <span class="meta-text">{{ dataset.sizeDisplay }}</span>
              </div>
              <div
                v-if="dataset.description"
                class="dataset-item-desc"
              >
                {{ dataset.description }}
              </div>
            </div>
            <div
              v-if="selectedDatasetId === dataset.id"
              class="dataset-item-check"
            >
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>

        <div
          v-if="datasets.length > 0"
          class="dialog-pagination"
        >
          <el-pagination
            v-model:current-page="datasetPage"
            :page-size="pageSize"
            :total="totalDatasets"
            layout="prev, pager, next"
            small
            @current-change="loadDatasets"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="showDatasetDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!selectedDataset"
          @click="confirmDatasetSelection"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>

    <!-- 标注项目创建对话框 -->
    <el-dialog
      v-model="showProjectDialog"
      title="创建标注项目"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="项目名称">
          <el-input
            v-model="projectName"
            placeholder="输入项目名称"
          />
        </el-form-item>
        <el-form-item label="项目配置">
          <div class="project-config-preview">
            <div class="config-item">
              <span class="config-label">数据集:</span>
              <span class="config-value">{{ selectedDataset?.name }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">标注类型:</span>
              <span class="config-value">{{ getAnnotationTypeLabel(localData.annotationType) }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">标签:</span>
              <span class="config-value">{{ parsedLabels.join(', ') }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">AI辅助:</span>
              <el-tag
                size="small"
                :type="localData.modelAssisted ? 'success' : 'info'"
              >
                {{ localData.modelAssisted ? '开启' : '关闭' }}
              </el-tag>
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showProjectDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="creatingProject"
          @click="handleCreateProject"
        >
          创建并打开
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { FolderOpen, X, Search, Loader, Check, Tag, ExternalLink } from 'lucide-vue-next'
import { datasetApi, formatFileSize } from '@/api/dataset'
import { annotationApi } from '@/api/annotation'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const router = useRouter()

const showDatasetDialog = ref(false)
const showProjectDialog = ref(false)
const loadingDatasets = ref(false)
const creatingProject = ref(false)

const datasets = ref([])
const datasetSearch = ref('')
const datasetPage = ref(1)
const pageSize = ref(10)
const totalDatasets = ref(0)
const selectedDatasetId = ref(null)
const projectName = ref('')
const projectId = ref('')

const localData = reactive({
  label: '',
  description: '',
  annotationType: 'classification',
  labels: '',
  datasetId: '',
  modelAssisted: false,
  modelId: ''
})

const selectedDataset = computed(() => {
  if (!selectedDatasetId.value) return null
  return datasets.value.find(d => d.id === selectedDatasetId.value)
})

const parsedLabels = computed(() => {
  if (!localData.labels) return []
  return localData.labels.split(',').map(l => l.trim()).filter(l => l)
})

const filteredDatasets = computed(() => {
  if (!datasetSearch.value) return datasets.value
  const search = datasetSearch.value.toLowerCase()
  return datasets.value.filter(d => 
    d.name?.toLowerCase().includes(search) || 
    d.description?.toLowerCase().includes(search)
  )
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      annotationType: newVal.annotationType || 'classification',
      labels: newVal.labels || '',
      datasetId: newVal.datasetId || '',
      modelAssisted: newVal.modelAssisted || false,
      modelId: newVal.modelId || ''
    })
    if (newVal.datasetId) {
      selectedDatasetId.value = newVal.datasetId
    }
    if (newVal.projectId) {
      projectId.value = newVal.projectId
    }
  }
}, { immediate: true, deep: true })

watch(showDatasetDialog, (newVal) => {
  if (newVal) {
    loadDatasets()
  }
})

const handleChange = () => {
  const output = {
    ...localData,
    datasetId: selectedDatasetId.value || localData.datasetId,
    projectId: projectId.value
  }
  emit('update:modelValue', output)
  emit('change', output)
}

function getAnnotationTypeLabel(type) {
  const labels = {
    classification: '分类',
    ner: '命名实体识别',
    sentiment: '情感分析',
    detection: '目标检测'
  }
  return labels[type] || type
}

function clearSelectedDataset() {
  selectedDatasetId.value = null
  localData.datasetId = ''
  projectId.value = ''
  handleChange()
}

async function loadDatasets() {
  loadingDatasets.value = true
  try {
    const response = await datasetApi.list({
      page: datasetPage.value,
      pageSize: pageSize.value,
      status: 'ready'
    })
    
    datasets.value = (response.results || response).map(d => ({
      id: d.id,
      name: d.name,
      description: d.description,
      source: d.source,
      sourceDisplay: d.sourceDisplay || d.source,
      format: d.format,
      formatDisplay: d.formatDisplay || d.format,
      rowCount: d.rowCount || 0,
      columnCount: d.columnCount || 0,
      sizeBytes: d.sizeBytes || 0,
      sizeDisplay: d.sizeDisplay || formatFileSize(d.sizeBytes || 0),
      status: d.status,
      columns: d.columns || []
    }))
    
    totalDatasets.value = response.count || datasets.value.length
  } catch (error) {
    console.error('Failed to load datasets:', error)
    ElMessage.error('加载数据集失败')
  } finally {
    loadingDatasets.value = false
  }
}

function selectDataset(dataset) {
  selectedDatasetId.value = dataset.id
}

function confirmDatasetSelection() {
  if (selectedDataset.value) {
    localData.datasetId = selectedDataset.value.id
    handleChange()
  }
  showDatasetDialog.value = false
}

function goToUpload() {
  ElMessage.info('请先上传数据集')
  showDatasetDialog.value = false
}

function createAndOpenAnnotation() {
  if (!selectedDataset.value) {
    ElMessage.warning('请先选择数据集')
    return
  }
  
  if (!parsedLabels.value.length) {
    ElMessage.warning('请设置标签')
    return
  }

  projectName.value = `${selectedDataset.value.name}_标注`
  showProjectDialog.value = true
}

async function handleCreateProject() {
  if (!projectName.value.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }

  creatingProject.value = true
  try {
    const response = await annotationApi.create({
      name: projectName.value,
      annotation_type: localData.annotationType,
      labels: parsedLabels.value,
      dataset: selectedDatasetId.value,
      model_assisted: localData.modelAssisted,
      model_id: localData.modelAssisted ? localData.modelId : ''
    })

    projectId.value = response.id
    handleChange()

    showProjectDialog.value = false
    ElMessage.success('标注项目创建成功')

    await router.push(`/annotations/${response.id}`)
  } catch (error) {
    console.error('Failed to create project:', error)
    ElMessage.error('创建标注项目失败')
  } finally {
    creatingProject.value = false
  }
}

function openExistingAnnotation() {
  if (projectId.value) {
    router.push(`/annotations/${projectId.value}`)
  }
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
  margin-top: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.btn-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-1;
}

.dataset-selector {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.selected-dataset {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
}

.dataset-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dataset-name {
  font-weight: 500;
  color: var(--text-primary);
}

.dataset-meta {
  font-size: 12px;
  color: var(--text-tertiary);
}

.workspace-actions {
  display: flex;
  gap: $spacing-3;
  flex-wrap: wrap;
}

.existing-project {
  margin-top: $spacing-3;
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

// Dataset dialog styles
.dataset-dialog-content {
  max-height: 60vh;
  overflow-y: auto;
}

.dialog-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 0;
  gap: 12px;
  color: var(--text-tertiary);
}

.dataset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dataset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
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

.dataset-item-info {
  flex: 1;
  min-width: 0;
}

.dataset-item-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dataset-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-text {
  font-size: 12px;
  color: var(--text-tertiary);
}

.dataset-item-desc {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dataset-item-check {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border-radius: 50%;
  color: white;
}

.dialog-pagination {
  display: flex;
  justify-content: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.project-config-preview {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  border: 1px solid var(--border-primary);
}

.config-item {
  display: flex;
  gap: $spacing-2;
  margin-bottom: $spacing-2;
  font-size: $font-size-sm;

  &:last-child {
    margin-bottom: 0;
  }

  .config-label {
    color: var(--text-tertiary);
    min-width: 80px;
  }

  .config-value {
    color: var(--text-primary);
    font-weight: $font-weight-medium;
  }
}
</style>
