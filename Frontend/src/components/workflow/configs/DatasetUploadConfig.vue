<template>
  <div class="config-form dataset-upload-config-form">
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

      <!-- 数据源配置 -->
      <div class="form-section">
        <h4 class="section-title">
          数据源配置
        </h4>
        
        <el-form-item label="数据来源">
          <el-select
            v-model="localData.source"
            @change="handleSourceChange"
          >
            <el-option
              label="本地上传"
              value="upload"
            />
            <el-option
              label="URL 下载"
              value="url"
            />
            <el-option
              label="S3 存储"
              value="s3"
            />
          </el-select>
        </el-form-item>

        <!-- 上传模式 -->
        <template v-if="localData.source === 'upload'">
          <el-form-item label="上传数据集">
            <div class="upload-area">
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :limit="1"
                :file-list="fileList"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                accept=".csv,.txt,.json,.jsonl,.parquet"
                drag
              >
                <div class="upload-content">
                  <el-icon class="upload-icon">
                    <Upload />
                  </el-icon>
                  <div class="upload-text">
                    <span class="upload-main">拖拽文件到此处或<em>点击上传</em></span>
                    <span class="upload-sub">支持 CSV、TXT、JSON、Parquet 格式</span>
                  </div>
                </div>
              </el-upload>
              <div
                v-if="uploadProgress > 0 && uploadProgress < 100"
                class="upload-progress"
              >
                <el-progress
                  :percentage="uploadProgress"
                  :stroke-width="6"
                />
              </div>
            </div>
          </el-form-item>

          <el-form-item label="已有数据集">
            <el-button
              type="primary"
              plain
              @click="showDatasetDialog = true"
            >
              <el-icon><FolderOpened /></el-icon>
              浏览数据集
            </el-button>
          </el-form-item>

          <el-form-item
            v-if="selectedDataset"
            label="已选择数据集"
          >
            <div class="selected-dataset">
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
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </el-form-item>

          <el-form-item v-if="selectedDataset">
            <div class="annotation-actions">
              <el-button
                type="primary"
                @click="openAnnotationWorkspace"
              >
                <Tag class="btn-icon" />
                打开标注工作台
              </el-button>
              <span class="annotation-hint">创建标注项目开始数据标注</span>
            </div>
          </el-form-item>
        </template>

        <!-- URL 模式 -->
        <template v-else-if="localData.source === 'url'">
          <el-form-item
            label="数据 URL"
            required
          >
            <el-input 
              v-model="localData.path" 
              placeholder="https://example.com/data.csv"
              @change="handleChange"
            />
            <div class="field-hint">
              数据文件的 HTTP/HTTPS URL
            </div>
          </el-form-item>
          <el-form-item label="URL 名称">
            <el-input 
              v-model="localData.datasetName" 
              placeholder="数据集名称（可选）"
              @change="handleChange"
            />
          </el-form-item>
        </template>

        <!-- S3 模式 -->
        <template v-else-if="localData.source === 's3'">
          <el-form-item
            label="S3 路径"
            required
          >
            <el-input 
              v-model="localData.path" 
              placeholder="s3://bucket/path/to/data.csv"
              @change="handleChange"
            />
            <div class="field-hint">
              S3 存储路径，格式: s3://bucket/key
            </div>
          </el-form-item>
          <el-form-item label="S3 名称">
            <el-input 
              v-model="localData.datasetName" 
              placeholder="数据集名称（可选）"
              @change="handleChange"
            />
          </el-form-item>
        </template>

        <el-form-item label="数据格式">
          <el-select
            v-model="localData.format"
            @change="handleChange"
          >
            <el-option
              label="文本 (TXT)"
              value="text"
            />
            <el-option
              label="CSV"
              value="csv"
            />
            <el-option
              label="JSON"
              value="json"
            />
            <el-option
              label="Parquet"
              value="parquet"
            />
          </el-select>
          <div class="field-hint">
            自动从文件扩展名检测，如需覆盖可手动选择
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
            <span class="preview-label">来源:</span>
            <span class="preview-value">{{ getSourceLabel(localData.source) }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">格式:</span>
            <span class="preview-value">{{ localData.format || '(未选择)' }}</span>
          </div>
          <div class="preview-row">
            <span class="preview-label">数据集:</span>
            <span class="preview-value">{{ selectedDataset?.name || localData.datasetName || localData.path || '(未设置)' }}</span>
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
          <el-empty description="暂无数据集" />
          <el-button
            type="primary"
            @click="showUploadTip"
          >
            上传数据集
          </el-button>
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
          @click="confirmDatasetSelection"
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
import { Upload, FolderOpened, Close, Search, RefreshCw, Loader, Check, Tag, ExternalLink } from 'lucide-vue-next'
import { datasetApi, createDatasetFormData, formatFileSize, detectFormatFromFilename } from '@/api/dataset'
import { annotationApi } from '@/api/annotation'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const router = useRouter()

const uploadRef = ref(null)
const fileList = ref([])
const uploadProgress = ref(0)
const showDatasetDialog = ref(false)
const loadingDatasets = ref(false)
const datasets = ref([])
const datasetSearch = ref('')
const datasetPage = ref(1)
const pageSize = ref(10)
const totalDatasets = ref(0)
const selectedDatasetId = ref(null)

const localData = reactive({
  label: '',
  description: '',
  source: 'upload',
  path: '',
  datasetName: '',
  format: 'csv',
  datasetId: ''
})

const selectedDataset = computed(() => {
  if (!selectedDatasetId.value) return null
  return datasets.value.find(d => d.id === selectedDatasetId.value)
})

const filteredDatasets = computed(() => {
  if (!datasetSearch.value) return datasets.value
  const search = datasetSearch.value.toLowerCase()
  return datasets.value.filter(d => 
    d.name?.toLowerCase().includes(search) || 
    d.description?.toLowerCase().includes(search)
  )
})

async function openAnnotationWorkspace() {
  if (!selectedDataset.value) {
    ElMessage.warning('请先选择数据集')
    return
  }

  try {
    const labels = ['positive', 'negative']
    const projectName = `${selectedDataset.value.name}_标注`

    const response = await annotationApi.create({
      name: projectName,
      annotation_type: 'classification',
      labels: labels,
      dataset: selectedDatasetId.value,
      model_assisted: true,
      model_id: 'gpt-4o-mini'
    })

    ElMessage.success('标注项目创建成功，正在跳转到标注工作台...')
    await router.push(`/annotations/${response.id}`)
  } catch (error) {
    console.error('Failed to create annotation project:', error)
    ElMessage.error('创建标注项目失败: ' + (error.message || '未知错误'))
  }
}

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(localData, {
      label: newVal.label || '',
      description: newVal.description || '',
      source: newVal.source || 'upload',
      path: newVal.path || '',
      datasetName: newVal.datasetName || '',
      format: newVal.format || 'csv',
      datasetId: newVal.datasetId || ''
    })
    if (newVal.datasetId) {
      selectedDatasetId.value = newVal.datasetId
    }
  }
}, { immediate: true, deep: true })

const handleChange = () => {
  const output = {
    ...localData,
    datasetId: selectedDatasetId.value || localData.datasetId
  }
  emit('update:modelValue', output)
  emit('change', output)
}

const handleSourceChange = () => {
  fileList.value = []
  selectedDatasetId.value = null
  localData.path = ''
  localData.datasetId = ''
  handleChange()
}

const handleFileChange = async (file, files) => {
  fileList.value = files
  
  if (file.size > 100 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 100MB')
    fileList.value = []
    return
  }

  const detectedFormat = detectFormatFromFilename(file.name)
  if (!localData.format || localData.format === 'csv') {
    localData.format = detectedFormat
  }

  const formData = createDatasetFormData(file.raw, {
    name: file.name.replace(/\.[^/.]+$/, ''),
    format: localData.format
  })

  uploadProgress.value = 0

  try {
    const response = await datasetApi.upload(formData, (progressEvent) => {
      if (progressEvent.total) {
        uploadProgress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
      }
    })

    selectedDatasetId.value = response.id
    localData.datasetId = response.id
    localData.path = response.filePath || file.name
    
    ElMessage.success('数据集上传成功')
    uploadProgress.value = 100
    
    handleChange()
  } catch (error) {
    ElMessage.error('上传失败: ' + (error.message || '未知错误'))
    fileList.value = []
    uploadProgress.value = 0
  }
}

const handleFileRemove = () => {
  fileList.value = []
  selectedDatasetId.value = null
  localData.path = ''
  localData.datasetId = ''
  uploadProgress.value = 0
  handleChange()
}

const clearSelectedDataset = () => {
  selectedDatasetId.value = null
  localData.datasetId = ''
  localData.path = ''
  handleChange()
}

const loadDatasets = async () => {
  loadingDatasets.value = true
  try {
    const response = await datasetApi.list({
      page: datasetPage.value,
      pageSize: pageSize.value,
      status: 'ready',
      source: localData.source === 'upload' ? undefined : localData.source
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

const selectDataset = (dataset) => {
  selectedDatasetId.value = dataset.id
}

const confirmDatasetSelection = () => {
  if (selectedDataset.value) {
    localData.datasetId = selectedDataset.value.id
    localData.path = selectedDataset.value.name
    localData.format = selectedDataset.value.format
    handleChange()
  }
  showDatasetDialog.value = false
}

const showUploadTip = () => {
  ElMessage.info('请在节点配置中使用上传功能上传数据集')
}

const getSourceLabel = (source) => {
  const labels = {
    upload: '本地上传',
    url: 'URL 下载',
    s3: 'S3 存储'
  }
  return labels[source] || source
}

watch(showDatasetDialog, (newVal) => {
  if (newVal) {
    loadDatasets()
  }
})
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

.upload-area {
  width: 100%;
}

.upload-content {
  padding: 20px 0;
}

.upload-icon {
  font-size: 32px;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.upload-main {
  color: var(--text-primary);
  
  em {
    color: var(--color-primary);
    font-style: normal;
  }
}

.upload-sub {
  font-size: 12px;
  color: var(--text-tertiary);
}

.upload-progress {
  margin-top: 12px;
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

.annotation-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-icon {
  width: 14px;
  height: 14px;
  margin-right: $spacing-1;
}

.annotation-hint {
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
    word-break: break-all;
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
</style>
