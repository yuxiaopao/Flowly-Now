<template>
  <PageShell
    width="wide"
    class="dataset-list-page"
  >
    <!-- Header -->
    <PageHeader
      title="数据集管理"
      subtitle="管理和查看您上传的训练数据集"
    >
      <template #actions>
        <el-button
          type="primary"
          @click="showUploadDialog = true"
        >
          <Upload class="btn-icon" />
          上传数据集
        </el-button>
      </template>
    </PageHeader>

    <!-- Search and Filter -->
    <PageToolbar>
      <el-input
        v-model="searchQuery"
        placeholder="搜索数据集名称..."
        clearable
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select
        v-model="formatFilter"
        placeholder="格式"
        clearable
        class="format-filter"
      >
        <el-option
          label="全部"
          value=""
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
          label="ZIP"
          value="zip"
        />
        <el-option
          label="其他"
          value="other"
        />
      </el-select>
      <el-button @click="loadDatasets">
        <RefreshCw class="btn-icon" />
        刷新
      </el-button>
    </PageToolbar>

    <!-- Dataset Table -->
    <div class="dataset-table-container">
      <div
        v-if="loading"
        class="loading-state"
      >
        <el-icon class="is-loading">
          <Loader />
        </el-icon>
        <span>加载中...</span>
      </div>

      <el-empty
        v-else-if="filteredDatasets.length === 0 && !loading"
        description="还没有数据集"
      >
        <el-button
          type="primary"
          @click="showUploadDialog = true"
        >
          上传第一个数据集
        </el-button>
      </el-empty>

      <el-table
        v-else
        :data="filteredDatasets"
        stripe
        class="dataset-table"
        @row-click="goToDetail"
      >
        <el-table-column
          label="名称"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="dataset-name-cell">
              <Database class="dataset-icon" />
              <div class="dataset-info">
                <span class="dataset-name">{{ row.name }}</span>
                <span
                  v-if="row.description"
                  class="dataset-desc"
                >{{ row.description }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="格式"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              type="info"
            >
              {{ row.format || 'csv' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          label="大小"
          width="120"
        >
          <template #default="{ row }">
            {{ formatFileSize(row.size || row.fileSize || 0) }}
          </template>
        </el-table-column>

        <el-table-column
          label="行数"
          width="100"
        >
          <template #default="{ row }">
            {{ formatNumber(row.rowCount || row.rows || 0) }}
          </template>
        </el-table-column>

        <el-table-column
          label="创建时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatDate(row.createdAt || row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <div
              class="action-buttons"
              @click.stop
            >
              <el-button
                type="primary"
                link
                size="small"
                :disabled="!supportsDatasetPreview(row)"
                @click="previewDataset(row)"
              >
                预览
              </el-button>
              <el-button
                type="info"
                link
                size="small"
                @click="showStats(row)"
              >
                统计
              </el-button>
              <el-button
                type="danger"
                link
                size="small"
                @click="deleteDataset(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div
        v-if="totalDatasets > 0"
        class="pagination-container"
      >
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalDatasets"
          layout="total, prev, pager, next"
          @current-change="loadDatasets"
        />
      </div>
    </div>

    <!-- Upload Dialog -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传数据集"
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="upload-dialog-content">
        <el-upload
          ref="uploadRef"
          class="upload-zone"
          drag
          :auto-upload="false"
          :limit="1"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          accept=".csv,.json,.zip,.txt"
        >
          <div class="upload-content">
            <Upload class="upload-icon" />
            <span class="upload-text">将文件拖到此处，或<em>点击上传</em></span>
            <span class="upload-hint">支持 CSV, JSON, ZIP 格式</span>
          </div>
        </el-upload>

        <div
          v-if="selectedFile"
          class="file-info"
        >
          <div class="file-detail">
            <FileText class="file-icon" />
            <div class="file-meta">
              <span class="file-name">{{ selectedFile.name }}</span>
              <span class="file-size">{{ formatFileSize(selectedFile.size) }}</span>
            </div>
            <el-tag
              size="small"
              type="success"
            >
              {{ detectedFormat }}
            </el-tag>
          </div>
        </div>

        <el-form
          :model="uploadForm"
          label-position="top"
          class="upload-form"
        >
          <el-form-item
            label="数据集名称"
            required
          >
            <el-input
              v-model="uploadForm.name"
              placeholder="给数据集起个名字"
            />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="uploadForm.description"
              type="textarea"
              :rows="3"
              placeholder="描述数据集的用途或内容"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showUploadDialog = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="uploading"
          @click="submitUpload"
        >
          开始上传
        </el-button>
      </template>
    </el-dialog>

    <!-- Preview Dialog -->
    <el-dialog
      v-model="showPreviewDialog"
      title="数据预览"
      width="900px"
      :close-on-click-modal="false"
    >
      <div
        v-if="previewData"
        class="preview-content"
      >
        <el-table
          :data="previewData.rows"
          max-height="400"
          stripe
        >
          <el-table-column
            v-for="col in previewData.columns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="120"
          />
        </el-table>
        <div class="preview-footer">
          <span>显示前 100 行</span>
          <el-pagination
            v-model:current-page="previewPage"
            :page-size="100"
            :total="previewData.total"
            layout="prev, pager, next"
            small
            @current-change="loadPreview"
          />
        </div>
      </div>
    </el-dialog>

    <!-- Stats Dialog -->
    <el-dialog
      v-model="showStatsDialog"
      title="数据集统计"
      width="500px"
    >
      <div
        v-if="statsData"
        class="stats-content"
      >
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">
              {{ formatNumber(statsData.totalRows || statsData.total || 0) }}
            </div>
            <div class="stat-label">
              总行数
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-value">
              {{ statsData.columns || statsData.columnCount || 0 }}
            </div>
            <div class="stat-label">
              列数
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-value">
              {{ formatFileSize(statsData.memory || statsData.size || 0) }}
            </div>
            <div class="stat-label">
              内存占用
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-value">
              {{ statsData.nullCount || statsData.nullValues || 0 }}
            </div>
            <div class="stat-label">
              空值数量
            </div>
          </div>
        </div>

        <div
          v-if="statsData.columnStats.length"
          class="column-stats"
        >
          <h4>列统计</h4>
          <el-table
            :data="statsData.columnStats"
            size="small"
          >
            <el-table-column
              prop="name"
              label="列名"
            />
            <el-table-column
              prop="type"
              label="类型"
            />
            <el-table-column
              prop="nullCount"
              label="空值"
            />
            <el-table-column
              prop="unique"
              label="唯一值"
            />
          </el-table>
        </div>
      </div>
    </el-dialog>
  </PageShell>
</template>

<script setup>
import PageToolbar from '@/components/layout/PageToolbar.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, RefreshCw, Loader, Upload, Database, FileText } from 'lucide-vue-next'
import datasetApi from '@/api/dataset'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const appStore = useAppStore()

// State
const datasets = ref([])
const loading = ref(false)
const searchQuery = ref('')
const formatFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalDatasets = ref(0)

// Upload state
const showUploadDialog = ref(false)
const uploadRef = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const uploadForm = reactive({
  name: '',
  description: ''
})

// Preview state
const showPreviewDialog = ref(false)
const previewData = ref(null)
const previewDatasetId = ref(null)
const previewPage = ref(1)

// Stats state
const showStatsDialog = ref(false)
const statsData = ref(null)
const statsDatasetId = ref(null)

const filteredDatasets = computed(() => {
  let result = datasets.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(d =>
      (d.name || '').toLowerCase().includes(query) ||
      (d.description || '').toLowerCase().includes(query)
    )
  }

  if (formatFilter.value) {
    if (formatFilter.value === 'other') {
      result = result.filter(d => {
        const fmt = (d.format || d.fileType || '').toLowerCase()
        return !['csv', 'json', 'zip'].includes(fmt)
      })
    } else {
      result = result.filter(d =>
        (d.format || d.fileType || '').toLowerCase() === formatFilter.value
      )
    }
  }

  return result
})

const detectedFormat = computed(() => {
  if (!selectedFile.value) return ''
  const name = selectedFile.value.name || ''
  const ext = name.split('.').pop()?.toLowerCase()
  const formatMap = {
    'csv': 'CSV',
    'json': 'JSON',
    'zip': 'ZIP',
    'txt': 'TXT',
    'tsv': 'TSV'
  }
  return formatMap[ext] || ext?.toUpperCase() || 'Unknown'
})

const PREVIEWABLE_DATASET_FORMATS = new Set(['csv', 'json', 'jsonl', 'txt', 'text', 'tsv'])

function getDatasetFormat(row = {}) {
  return String(row.format || row.fileType || '').toLowerCase()
}

function supportsDatasetPreview(row = {}) {
  return PREVIEWABLE_DATASET_FORMATS.has(getDatasetFormat(row))
}

function normalizeDatasetListResponse(response) {
  const results = Array.isArray(response?.results)
    ? response.results
    : Array.isArray(response)
      ? response
      : []
  return {
    results,
    total: Number(response?.count ?? response?.total ?? results.length),
  }
}

function normalizePreviewResponse(response = {}) {
  const rows = Array.isArray(response.rows)
    ? response.rows
    : Array.isArray(response.preview)
      ? response.preview
      : []
  const columns = Array.isArray(response.columns)
    ? response.columns
    : rows.length && typeof rows[0] === 'object'
      ? Object.keys(rows[0])
      : []
  return {
    rows,
    columns,
    total: Number(response.total ?? response.totalRows ?? response.total_rows ?? rows.length),
  }
}

function normalizeColumnStats(columnStats) {
  if (Array.isArray(columnStats)) {
    return columnStats.map((item) => ({
      name: item.name,
      type: item.type || item.dtype || 'string',
      nullCount: item.nullCount ?? item.null_count ?? 0,
      unique: item.unique ?? item.uniqueCount ?? item.unique_count ?? 0,
    }))
  }

  if (!columnStats || typeof columnStats !== 'object') {
    return []
  }

  return Object.entries(columnStats).map(([name, item]) => ({
    name,
    type: item?.type || item?.dtype || 'string',
    nullCount: item?.nullCount ?? item?.null_count ?? 0,
    unique: item?.unique ?? item?.uniqueCount ?? item?.unique_count ?? 0,
  }))
}

function normalizeStatsResponse(response = {}, row = {}) {
  const columnStats = normalizeColumnStats(response.columnStats || response.column_stats)
  const nullCount = columnStats.reduce((sum, item) => sum + Number(item.nullCount || 0), 0)
  return {
    totalRows: response.totalRows ?? response.total_rows ?? response.rowCount ?? response.row_count ?? row.rowCount ?? 0,
    columns: response.columnCount ?? response.column_count ?? (Array.isArray(response.columns) ? response.columns.length : response.columns) ?? row.columns?.length ?? 0,
    memory: response.memory ?? response.size ?? row.size ?? 0,
    nullCount: response.nullCount ?? response.null_count ?? nullCount,
    columnStats,
  }
}

// Methods
async function loadDatasets() {
  loading.value = true
  try {
    const response = await datasetApi.list({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const normalized = normalizeDatasetListResponse(response)

    datasets.value = normalized.results.map(d => ({
      id: d.id,
      name: d.name || d.fileName || `Dataset ${d.id}`,
      description: d.description || '',
      format: d.format || d.fileType || 'csv',
      size: d.size || d.fileSize || 0,
      rowCount: d.rowCount || d.rows || 0,
      columns: d.columns || [],
      createdAt: d.createdAt || d.created_at || new Date().toISOString()
    }))

    totalDatasets.value = normalized.total
  } catch {
    ElMessage.error('加载数据集失败')
  } finally {
    loading.value = false
  }
}

function handleFileChange(file) {
  selectedFile.value = file.raw
  if (!uploadForm.name) {
    const name = file.name.replace(/\.[^.]+$/, '')
    uploadForm.name = name
  }
}

function handleFileRemove() {
  selectedFile.value = null
}

async function submitUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  if (!uploadForm.name) {
    ElMessage.warning('请输入数据集名称')
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('name', uploadForm.name)
    if (uploadForm.description) {
      formData.append('description', uploadForm.description)
    }

    await datasetApi.upload(formData)

    ElMessage.success('上传成功')
    showUploadDialog.value = false
    uploadForm.name = ''
    uploadForm.description = ''
    selectedFile.value = null
    loadDatasets()
  } catch (error) {
    console.error('Upload failed:', error)
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

async function previewDataset(row) {
  if (!supportsDatasetPreview(row)) {
    appStore.warning('该数据集格式暂不支持预览')
    return
  }
  previewDatasetId.value = row.id
  previewPage.value = 1
  const loaded = await loadPreview()
  if (loaded) {
    showPreviewDialog.value = true
  }
}

async function loadPreview() {
  if (!previewDatasetId.value) return false
  try {
    const response = await datasetApi.preview(previewDatasetId.value, previewPage.value)
    previewData.value = normalizePreviewResponse(response)
    return true
  } catch (error) {
    previewData.value = null
    const message = error?.response?.data?.message || error?.message || '预览失败'
    appStore.error(message)
    return false
  }
}

async function showStats(row) {
  statsDatasetId.value = row.id
  try {
    const response = await datasetApi.stats(row.id)
    statsData.value = normalizeStatsResponse(response, row)
  } catch (error) {
    statsData.value = normalizeStatsResponse({}, row)
    const message = error?.response?.data?.message || error?.message || '统计信息加载失败'
    appStore.error(message)
  }
  showStatsDialog.value = true
}

async function deleteDataset(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据集 "${row.name}" 吗？此操作不可恢复。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await datasetApi.delete(row.id)
    ElMessage.success('删除成功')
    loadDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
      ElMessage.error('删除失败')
    }
  }
}

function goToDetail(row) {
  router.push(`/datasets/${row.id}`)
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatNumber(num) {
  if (!num) return '0'
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  loadDatasets()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: $spacing-1;
}





.dataset-table-container {
  background: var(--bg-secondary);
  border-radius: $radius-lg;
  border: 1px solid var(--border-primary);
  overflow: hidden;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-10;
  gap: $spacing-3;
  color: var(--text-tertiary);
}

.dataset-table {
  :deep(.el-table__row) {
    cursor: pointer;
  }
}

.dataset-name-cell {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.dataset-icon {
  width: 32px;
  height: 32px;
  color: var(--color-primary);
}

.dataset-info {
  display: flex;
  flex-direction: column;
}

.dataset-name {
  font-weight: 500;
  color: var(--text-primary);
}

.dataset-desc {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.action-buttons {
  display: flex;
  gap: $spacing-2;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);
}

// Upload dialog
.upload-dialog-content {
  .upload-zone {
    margin-bottom: $spacing-4;
  }
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $spacing-8;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: var(--color-primary);
  margin-bottom: $spacing-3;
}

.upload-text {
  font-size: $font-size-base;
  color: var(--text-primary);
  margin-bottom: $spacing-1;

  em {
    color: var(--color-primary);
    font-style: normal;
  }
}

.upload-hint {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.file-info {
  padding: $spacing-3;
  background: var(--bg-tertiary);
  border-radius: $radius-md;
  margin-bottom: $spacing-4;
}

.file-detail {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.file-icon {
  width: 24px;
  height: 24px;
  color: var(--color-primary);
}

.file-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.file-name {
  font-weight: 500;
  color: var(--text-primary);
}

.file-size {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.upload-form {
  :deep(.el-form-item__label) {
    font-weight: 500;
  }
}

// Preview dialog
.preview-content {
  .preview-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: $spacing-3;
    padding-top: $spacing-3;
    border-top: 1px solid var(--border-primary);
    font-size: $font-size-sm;
    color: var(--text-tertiary);
  }
}

// Stats dialog
.stats-content {
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: $spacing-4;
    margin-bottom: $spacing-4;
  }

  .stat-card {
    background: var(--bg-tertiary);
    border-radius: $radius-md;
    padding: $spacing-4;
    text-align: center;
  }

  .stat-value {
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
    color: var(--color-primary);
  }

  .stat-label {
    font-size: $font-size-sm;
    color: var(--text-tertiary);
    margin-top: $spacing-1;
  }

  .column-stats {
    h4 {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: var(--text-primary);
      margin: 0 0 $spacing-3;
    }
  }
}
</style>
