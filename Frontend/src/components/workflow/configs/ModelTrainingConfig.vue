<template>
  <div class="config-form model-training-config-form">
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

      <!-- 数据集推荐 -->
      <div class="form-section">
        <h4 class="section-title">
          数据集推荐
        </h4>
        <el-tabs
          v-model="datasetTabActive"
          class="dataset-tabs"
        >
          <el-tab-pane
            label="我的数据集"
            name="mine"
          >
            <div class="my-datasets">
              <div class="dataset-toolbar">
                <el-button
                  type="primary"
                  size="small"
                  @click="showUploadDialog = true"
                >
                  <Upload class="btn-icon" />
                  上传数据集
                </el-button>
                <el-button
                  size="small"
                  @click="loadMyDatasets"
                >
                  <Refresh class="btn-icon" />
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
                v-else-if="myDatasets.length === 0"
                class="empty-state"
              >
                <el-empty
                  description="暂无数据集"
                  :image-size="60"
                >
                  <el-button
                    type="primary"
                    size="small"
                    @click="showUploadDialog = true"
                  >
                    上传第一个数据集
                  </el-button>
                </el-empty>
              </div>

              <div
                v-else
                class="dataset-list"
              >
                <div
                  v-for="dataset in myDatasets"
                  :key="dataset.id"
                  class="dataset-item"
                  :class="{ selected: localData.datasetId === dataset.id }"
                  @click="selectMyDataset(dataset)"
                >
                  <div class="dataset-icon">
                    <Database class="icon" />
                  </div>
                  <div class="dataset-info">
                    <div class="dataset-name">
                      {{ dataset.name }}
                    </div>
                    <div class="dataset-meta">
                      <el-tag
                        size="small"
                        type="info"
                      >
                        {{ dataset.format || 'csv' }}
                      </el-tag>
                      <span class="dataset-size">{{ formatFileSize(dataset.size) }}</span>
                      <span class="dataset-rows">{{ dataset.rowCount || dataset.rows || 0 }} 行</span>
                    </div>
                  </div>
                  <div
                    v-if="localData.datasetId === dataset.id"
                    class="dataset-check"
                  >
                    <el-icon><Check /></el-icon>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane
            label="推荐数据集"
            name="recommended"
          >
            <div class="recommended-datasets">
              <div class="search-bar">
                <el-input
                  v-model="datasetSearchQuery"
                  placeholder="按标签筛选数据集..."
                  clearable
                  size="small"
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                </el-input>
              </div>

              <div class="dataset-cards">
                <div
                  v-for="site in filteredRecommendedDatasets"
                  :key="site.name"
                  class="dataset-card"
                >
                  <div class="card-header">
                    <div
                      class="card-logo"
                      :style="{ backgroundColor: getSiteColor(site.name) }"
                    >
                      {{ site.name.charAt(0) }}
                    </div>
                    <div class="card-title">
                      <h4>{{ site.name }}</h4>
                      <a
                        :href="site.url"
                        target="_blank"
                        class="card-url"
                        @click.stop
                      >
                        {{ formatUrl(site.url) }}
                      </a>
                    </div>
                  </div>
                  <p class="card-description">
                    {{ site.description }}
                  </p>
                  <div class="card-tags">
                    <el-tag
                      v-for="tag in site.tags"
                      :key="tag"
                      size="small"
                      :type="datasetSearchQuery && tag.toLowerCase().includes(datasetSearchQuery.toLowerCase()) ? 'primary' : 'info'"
                    >
                      {{ tag }}
                    </el-tag>
                  </div>
                  <el-button
                    type="primary"
                    size="small"
                    plain
                    class="card-action"
                    @click="openRecommendedLink(site.url)"
                  >
                    <ExternalLink class="btn-icon" />
                    前往下载
                  </el-button>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 数据集配置 -->
      <div class="form-section">
        <h4 class="section-title">
          数据集配置
        </h4>
        
        <el-form-item label="数据来源">
          <el-select
            v-model="localData.dataSource"
            @change="handleDataSourceChange"
          >
            <el-option
              label="数据集 ID"
              value="dataset"
            />
            <el-option
              label="标注项目"
              value="annotation"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="localData.dataSource === 'dataset'"
          label="数据集 ID"
        >
          <el-input
            v-model="localData.datasetId"
            placeholder="训练数据集ID"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item
          v-if="localData.dataSource === 'annotation'"
          label="标注项目"
        >
          <div class="annotation-selector">
            <el-button
              type="primary"
              plain
              @click="showAnnotationDialog = true"
            >
              <Tag class="btn-icon" />
              选择标注项目
            </el-button>
            
            <div
              v-if="selectedAnnotation"
              class="selected-annotation"
            >
              <div class="annotation-info">
                <span class="annotation-name">{{ selectedAnnotation.name }}</span>
                <span class="annotation-meta">
                  {{ selectedAnnotation.annotationTypeDisplay }} · 
                  {{ selectedAnnotation.annotatedItems }}/{{ selectedAnnotation.totalItems }} 已标注
                </span>
              </div>
              <el-button
                type="danger"
                circle
                size="small"
                @click="clearSelectedAnnotation"
              >
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item
          v-if="localData.dataSource === 'annotation' && selectedAnnotation"
          label="使用预标注"
        >
          <el-switch
            v-model="localData.usePreLabels"
            @change="handleChange"
          />
          <span class="field-hint">同时使用 AI 预标注结果作为训练数据</span>
        </el-form-item>
      </div>

      <!-- 框架配置 -->
      <div class="form-section">
        <h4 class="section-title">
          框架配置
        </h4>
        
        <el-form-item label="深度学习框架">
          <el-select
            v-model="localData.framework"
            @change="handleChange"
          >
            <el-option
              label="PyTorch"
              value="pytorch"
            />
            <el-option
              label="Transformers (HuggingFace)"
              value="transformers"
            />
            <el-option
              label="Keras"
              value="keras"
            />
            <el-option
              label="TensorFlow"
              value="tensorflow"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="模型类型">
          <el-select
            v-model="localData.modelType"
            @change="handleChange"
          >
            <el-option
              label="分类器 (Classifier)"
              value="classifier"
            />
            <el-option
              label="回归器 (Regressor)"
              value="regressor"
            />
            <el-option
              label="生成器 (Generator)"
              value="generator"
            />
            <el-option
              label="自定义 (Custom)"
              value="custom"
            />
          </el-select>
        </el-form-item>
      </div>

      <!-- 超参数配置 -->
      <div class="form-section">
        <h4 class="section-title">
          超参数配置
        </h4>
        
        <el-form-item label="训练轮数 (Epochs)">
          <el-input-number
            v-model="localData.hyperparameters.epochs"
            :min="1"
            :max="1000"
            :step="1"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="批大小 (Batch Size)">
          <el-input-number
            v-model="localData.hyperparameters.batchSize"
            :min="1"
            :max="512"
            :step="8"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="学习率 (Learning Rate)">
          <el-input-number
            v-model="localData.hyperparameters.learningRate"
            :min="0.00001"
            :max="1"
            :step="0.0001"
            :precision="5"
            controls-position="right"
            style="width: 100%"
            @change="handleChange"
          />
        </el-form-item>
      </div>

      <!-- 训练选项 -->
      <div class="form-section">
        <h4 class="section-title">
          训练选项
        </h4>
        
        <el-form-item label="启用 GPU">
          <el-switch
            v-model="localData.gpuEnabled"
            @change="handleChange"
          />
        </el-form-item>

        <el-form-item label="GPU 检测">
          <div class="gpu-detection">
            <el-button
              type="info"
              size="small"
              :loading="gpuDetecting"
              @click="detectGPU"
            >
              <Monitor class="btn-icon" />
              检测GPU
            </el-button>
            <div
              v-if="gpuInfo"
              class="gpu-info"
            >
              <el-tag
                :type="gpuInfo.available ? 'success' : 'warning'"
                size="small"
              >
                {{ gpuInfo.available ? '可用' : '不可用' }}
              </el-tag>
              <span
                v-if="gpuInfo.name"
                class="gpu-name"
              >{{ gpuInfo.name }}</span>
              <span
                v-if="gpuInfo.memory"
                class="gpu-memory"
              >{{ gpuInfo.memory }}</span>
              <span
                v-if="gpuInfo.recommendedBatchSize"
                class="gpu-batch"
              >
                推荐Batch: {{ gpuInfo.recommendedBatchSize }}
              </span>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="输出目录">
          <el-input
            v-model="localData.outputDir"
            placeholder="模型输出目录路径"
            @change="handleChange"
          />
          <div class="field-hint">
            <el-icon><Warning /></el-icon>
            必须是空目录，训练模型将保存在此目录
          </div>
        </el-form-item>

        <el-form-item label="启用检查点">
          <el-switch
            v-model="localData.checkpointing"
            @change="handleChange"
          />
          <span class="field-hint">保存最佳模型检查点</span>
        </el-form-item>
      </div>

      <!-- 预览 -->
      <div class="form-section">
        <h4 class="section-title">
          配置预览
        </h4>
        <div class="config-preview">
          <div class="preview-row">
            <span class="preview-label">数据来源:</span>
            <span class="preview-value">{{ localData.dataSource === 'annotation' ? '标注项目' : '数据集' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">框架:</span>
            <span class="preview-value">{{ localData.framework || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">Epochs:</span>
            <span class="preview-value">{{ localData.hyperparameters?.epochs || 10 }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">Batch:</span>
            <span class="preview-value">{{ localData.hyperparameters?.batchSize || 32 }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">GPU:</span>
            <el-tag
              size="small"
              :type="localData.gpuEnabled ? 'success' : 'info'"
            >
              {{ localData.gpuEnabled ? '开启' : '关闭' }}
            </el-tag>
          </div>
        </div>
      </div>
    </el-form>

    <!-- 标注项目选择对话框 -->
    <el-dialog
      v-model="showAnnotationDialog"
      title="选择标注项目"
      width="800px"
      :close-on-click-modal="false"
    >
      <div class="annotation-dialog-content">
        <div class="dialog-toolbar">
          <el-input
            v-model="annotationSearch"
            placeholder="搜索项目名称..."
            clearable
            style="width: 300px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button @click="loadAnnotations">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <div
          v-if="loadingAnnotations"
          class="loading-state"
        >
          <el-icon class="is-loading">
            <Loader />
          </el-icon>
          <span>加载中...</span>
        </div>

        <div
          v-else-if="filteredAnnotations.length === 0"
          class="empty-state"
        >
          <el-empty description="暂无标注项目">
            <el-button
              type="primary"
              @click="goToAnnotations"
            >
              创建标注项目
            </el-button>
          </el-empty>
        </div>

        <div
          v-else
          class="annotation-list"
        >
          <div
            v-for="annotation in filteredAnnotations"
            :key="annotation.id"
            class="annotation-item"
            :class="{ selected: selectedAnnotationId === annotation.id }"
            @click="selectAnnotation(annotation)"
          >
            <div class="annotation-item-info">
              <div class="annotation-item-name">
                {{ annotation.name }}
              </div>
              <div class="annotation-item-meta">
                <el-tag
                  size="small"
                  type="info"
                >
                  {{ annotation.annotationTypeDisplay }}
                </el-tag>
                <el-tag
                  size="small"
                  :type="getStatusType(annotation.status)"
                >
                  {{ annotation.statusDisplay }}
                </el-tag>
                <span class="meta-text">{{ annotation.annotatedItems }}/{{ annotation.totalItems }} 已标注</span>
              </div>
              <div class="annotation-item-labels">
                <span
                  v-for="label in (annotation.labels || []).slice(0, 5)"
                  :key="label"
                  class="label-tag"
                >
                  {{ label }}
                </span>
                <span
                  v-if="(annotation.labels || []).length > 5"
                  class="more-labels"
                >
                  +{{ annotation.labels.length - 5 }}
                </span>
              </div>
            </div>
            <div
              v-if="selectedAnnotationId === annotation.id"
              class="annotation-item-check"
            >
              <el-icon><Check /></el-icon>
            </div>
          </div>
        </div>

        <div
          v-if="annotations.length > 0"
          class="dialog-pagination"
        >
          <el-pagination
            v-model:current-page="annotationPage"
            :page-size="pageSize"
            :total="totalAnnotations"
            layout="prev, pager, next"
            small
            @current-change="loadAnnotations"
          />
        </div>
      </div>

      <template #footer>
        <el-button @click="showAnnotationDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :disabled="!selectedAnnotation"
          @click="confirmAnnotationSelection"
        >
          确认选择
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Tag, Close, Search, RefreshCw, Loader, Check, Upload, Database, ExternalLink, Monitor, Warning } from 'lucide-vue-next'
import { annotationApi } from '@/api/annotation'
import trainingApi from '@/api/training'
import datasetApi from '@/api/dataset'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const router = useRouter()

const showAnnotationDialog = ref(false)
const loadingAnnotations = ref(false)

const annotations = ref([])
const annotationSearch = ref('')
const annotationPage = ref(1)
const pageSize = ref(10)
const totalAnnotations = ref(0)
const selectedAnnotationId = ref(null)

// Dataset tabs state
const datasetTabActive = ref('mine')
const showRecommendedDatasets = ref(false)
const datasetSearchQuery = ref('')
const myDatasets = ref([])
const loadingDatasets = ref(false)
const showUploadDialog = ref(false)

const recommendedDatasets = ref([
  {
    name: 'Kaggle',
    url: 'https://www.kaggle.com/datasets',
    description: '全球最大数据科学社区，提供丰富的标注数据集',
    tags: ['图像分类', 'NLP', '目标检测']
  },
  {
    name: 'HuggingFace',
    url: 'https://huggingface.co/datasets',
    description: '开源ML数据集库，支持NLP和CV',
    tags: ['NLP', '对话', '嵌入']
  },
  {
    name: 'UCI ML Repository',
    url: 'https://archive.ics.uci.edu/',
    description: '经典机器学习数据集集合',
    tags: ['分类', '回归']
  },
  {
    name: 'Roboflow Universe',
    url: 'https://universe.roboflow.com',
    description: '计算机视觉专用数据集平台',
    tags: ['目标检测', '图像分割', '分类']
  },
  {
    name: 'Open Images',
    url: 'https://storage.googleapis.com/openimages/web/index.html',
    description: 'Google大规模图像数据集',
    tags: ['目标检测', '图像分类']
  },
])

// GPU detection state
const gpuInfo = ref(null)
const gpuDetecting = ref(false)
const outputDir = ref('')

const localData = reactive({
  label: '',
  description: '',
  dataSource: 'dataset',
  datasetId: '',
  annotationProjectId: '',
  usePreLabels: false,
  framework: 'pytorch',
  modelType: 'classifier',
  hyperparameters: {
    epochs: 10,
    batchSize: 32,
    learningRate: 0.001
  },
  gpuEnabled: true,
  checkpointing: true,
  outputDir: ''
})

const filteredRecommendedDatasets = computed(() => {
  if (!datasetSearchQuery.value) return recommendedDatasets.value
  const query = datasetSearchQuery.value.toLowerCase()
  return recommendedDatasets.value.filter(site =>
    site.tags.some(tag => tag.toLowerCase().includes(query)) ||
    site.name.toLowerCase().includes(query) ||
    site.description.toLowerCase().includes(query)
  )
})

const selectedAnnotation = computed(() => {
  if (!selectedAnnotationId.value) return null
  return annotations.value.find(a => a.id === selectedAnnotationId.value)
})

const filteredAnnotations = computed(() => {
  if (!annotationSearch.value) return annotations.value
  const search = annotationSearch.value.toLowerCase()
  return annotations.value.filter(a => 
    a.name?.toLowerCase().includes(search)
  )
})

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      dataSource: newVal.dataSource || 'dataset',
      datasetId: newVal.datasetId || '',
      annotationProjectId: newVal.annotationProjectId || '',
      usePreLabels: newVal.usePreLabels || false,
      framework: newVal.framework || 'pytorch',
      modelType: newVal.modelType || 'classifier',
      hyperparameters: {
        epochs: newVal.hyperparameters?.epochs ?? 10,
        batchSize: newVal.hyperparameters?.batchSize ?? 32,
        learningRate: newVal.hyperparameters?.learningRate ?? 0.001
      },
      gpuEnabled: newVal.gpuEnabled ?? true,
      checkpointing: newVal.checkpointing ?? true,
      outputDir: newVal.outputDir || ''
    })
    if (newVal.annotationProjectId) {
      selectedAnnotationId.value = newVal.annotationProjectId
    }
  }
}, { immediate: true, deep: true })

watch(showAnnotationDialog, (newVal) => {
  if (newVal) {
    loadAnnotations()
  }
})

const handleChange = () => {
  const output = {
    ...localData,
    annotationProjectId: selectedAnnotationId.value || localData.annotationProjectId
  }
  emit('update:modelValue', output)
  emit('change', output)
}

function handleDataSourceChange() {
  if (localData.dataSource === 'dataset') {
    selectedAnnotationId.value = null
    localData.annotationProjectId = ''
    localData.usePreLabels = false
  }
  handleChange()
}

function getStatusType(status) {
  const types = {
    draft: 'info',
    in_progress: 'warning',
    completed: 'success'
  }
  return types[status] || 'info'
}

function clearSelectedAnnotation() {
  selectedAnnotationId.value = null
  localData.annotationProjectId = ''
  handleChange()
}

async function loadAnnotations() {
  loadingAnnotations.value = true
  try {
    const response = await annotationApi.list({
      page: annotationPage.value,
      pageSize: pageSize.value,
      status: 'completed'
    })
    
    annotations.value = (response.results || response).map(a => ({
      id: a.id,
      name: a.name,
      annotationType: a.annotationType,
      annotationTypeDisplay: a.annotationTypeDisplay || a.annotationType,
      status: a.status,
      statusDisplay: a.statusDisplay || a.status,
      labels: a.labels || [],
      totalItems: a.totalItems || 0,
      annotatedItems: a.annotatedItems || 0,
      datasetName: a.datasetName || '',
      progressPercentage: a.progressPercentage || 0
    }))
    
    totalAnnotations.value = response.count || annotations.value.length
  } catch (error) {
    console.error('Failed to load annotations:', error)
    ElMessage.error('加载标注项目失败')
  } finally {
    loadingAnnotations.value = false
  }
}

function selectAnnotation(annotation) {
  selectedAnnotationId.value = annotation.id
}

function confirmAnnotationSelection() {
  if (selectedAnnotation.value) {
    localData.annotationProjectId = selectedAnnotation.value.id
    handleChange()
  }
  showAnnotationDialog.value = false
}

function goToAnnotations() {
  router.push('/dataset-recommend')
  showAnnotationDialog.value = false
}

// Dataset methods
async function loadMyDatasets() {
  loadingDatasets.value = true
  try {
    const response = await datasetApi.list()
    myDatasets.value = (response.results || response).map(d => ({
      id: d.id,
      name: d.name || d.fileName || `Dataset ${d.id}`,
      format: d.format || d.fileType || 'csv',
      size: d.size || d.fileSize || 0,
      rowCount: d.rowCount || d.rows || 0,
      columns: d.columns || [],
      createdAt: d.createdAt || d.created_at || new Date().toISOString()
    }))
  } catch (error) {
    console.error('Failed to load datasets:', error)
    ElMessage.error('加载数据集失败')
  } finally {
    loadingDatasets.value = false
  }
}

function selectMyDataset(dataset) {
  localData.datasetId = dataset.id
  handleChange()
}

function openRecommendedLink(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatUrl(url) {
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '')
}

function getSiteColor(name) {
  const colors = {
    'Kaggle': '#20BEFF',
    'HuggingFace': '#FFD21E',
    'UCI': '#4CAF50',
    'Roboflow': '#4A90D9',
    'Open Images': '#F4B400'
  }
  return colors[name] || '#6366F1'
}

async function detectGPU() {
  gpuDetecting.value = true
  gpuInfo.value = null
  try {
    const response = await trainingApi.getGpuInfo()
    gpuInfo.value = {
      available: response.available ?? true,
      name: response.name || response.gpuName || 'GPU',
      memory: response.memory || response.gpuMemory || '',
      recommendedBatchSize: response.recommendedBatchSize || response.recommended_batch_size || 32
    }
    ElMessage.success('GPU检测成功')
  } catch (error) {
    console.error('GPU detection failed:', error)
    // Mock GPU info for demo
    gpuInfo.value = {
      available: true,
      name: 'NVIDIA GeForce RTX 3080',
      memory: '10GB',
      recommendedBatchSize: 64
    }
    ElMessage.info('使用模拟GPU信息')
  } finally {
    gpuDetecting.value = false
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
  display: flex;
  align-items: center;
  gap: 4px;
}

.btn-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-1;
}

// Dataset tabs
.dataset-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: $spacing-3;
  }
}

.my-datasets {
  .dataset-toolbar {
    display: flex;
    gap: $spacing-2;
    margin-bottom: $spacing-3;
  }
}

.dataset-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.dataset-item {
  display: flex;
  align-items: center;
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

.dataset-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-light-9);
  border-radius: $radius-md;
  color: var(--color-primary);
}

.dataset-info {
  flex: 1;
  min-width: 0;
}

.dataset-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dataset-meta {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.dataset-check {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
  border-radius: 50%;
  color: white;
}

// Recommended datasets
.recommended-datasets {
  .search-bar {
    margin-bottom: $spacing-4;
  }
}

.dataset-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: $spacing-4;
}

.dataset-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;
  transition: all 0.2s;

  &:hover {
    border-color: var(--color-primary);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: $spacing-3;
  margin-bottom: $spacing-3;
}

.card-logo {
  width: 40px;
  height: 40px;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.card-title {
  flex: 1;
  min-width: 0;

  h4 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
    margin: 0 0 4px;
  }
}

.card-url {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;

  &:hover {
    color: var(--color-primary);
  }
}

.card-description {
  font-size: $font-size-sm;
  color: var(--text-secondary);
  margin: 0 0 $spacing-3;
  line-height: 1.5;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-1;
  margin-bottom: $spacing-3;
}

.card-action {
  width: 100%;
}

// GPU detection
.gpu-detection {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
}

.gpu-info {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-2;
  padding: $spacing-2;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  font-size: $font-size-sm;
}

.gpu-name {
  color: var(--text-primary);
  font-weight: 500;
}

.gpu-memory,
.gpu-batch {
  color: var(--text-secondary);
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

.annotation-selector {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.selected-annotation {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
}

.annotation-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.annotation-name {
  font-weight: 500;
  color: var(--text-primary);
}

.annotation-meta {
  font-size: 12px;
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

// Annotation dialog styles
.annotation-dialog-content {
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

.annotation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.annotation-item {
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

.annotation-item-info {
  flex: 1;
  min-width: 0;
}

.annotation-item-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.annotation-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.meta-text {
  font-size: 12px;
  color: var(--text-tertiary);
}

.annotation-item-labels {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.label-tag {
  font-size: 10px;
  padding: 2px 6px;
  background: var(--bg-tertiary);
  border-radius: $radius-sm;
  color: var(--text-secondary);
}

.more-labels {
  font-size: 10px;
  color: var(--text-tertiary);
}

.annotation-item-check {
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
</style>
