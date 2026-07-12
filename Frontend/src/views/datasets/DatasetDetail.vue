<template>
  <div class="dataset-detail-page">
    <!-- Back Button and Header -->
    <div class="page-header">
      <el-button
        text
        @click="goBack"
      >
        <ArrowLeft class="btn-icon" />
        返回
      </el-button>
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            {{ dataset.name || '数据集详情' }}
          </h1>
          <div class="header-meta">
            <el-tag
              size="small"
              type="info"
            >
              {{ dataset.format || 'csv' }}
            </el-tag>
            <span class="meta-item">
              <FileText class="meta-icon" />
              {{ formatFileSize(dataset.size || 0) }}
            </span>
            <span class="meta-item">
              <Database class="meta-icon" />
              {{ formatNumber(dataset.rowCount || 0) }} 行
            </span>
            <span class="meta-item">
              <Calendar class="meta-icon" />
              {{ formatDate(dataset.createdAt) }}
            </span>
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="downloadDataset">
            <Download class="btn-icon" />
            下载
          </el-button>
          <el-button
            type="danger"
            @click="deleteDataset"
          >
            <Trash2 class="btn-icon" />
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- Description -->
    <div
      v-if="dataset.description"
      class="description-section"
    >
      <p>{{ dataset.description }}</p>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">
          <Database class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ formatNumber(datasetStats.totalRows || dataset.rowCount || 0) }}
          </div>
          <div class="stat-label">
            总行数
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <Columns class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ datasetStats.columns || dataset.columns?.length || 0 }}
          </div>
          <div class="stat-label">
            列数
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <HardDrive class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ formatFileSize(datasetStats.memory || dataset.size || 0) }}
          </div>
          <div class="stat-label">
            内存占用
          </div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">
          <AlertCircle class="icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ formatNumber(datasetStats.nullCount || 0) }}
          </div>
          <div class="stat-label">
            空值数量
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs
      v-model="activeTab"
      class="detail-tabs"
    >
      <el-tab-pane
        label="数据预览"
        name="preview"
      >
        <!-- Preview Table -->
        <div class="preview-section">
          <div class="section-header">
            <h3>前 100 行数据</h3>
            <div class="preview-pagination">
              <el-pagination
                v-model:current-page="previewPage"
                :page-size="100"
                :total="datasetStats.totalRows || dataset.rowCount || 0"
                layout="total, prev, pager, next"
                small
                @current-change="loadPreview"
              />
            </div>
          </div>

          <div
            v-if="loadingPreview"
            class="loading-state"
          >
            <el-icon class="is-loading">
              <Loader />
            </el-icon>
            <span>加载中...</span>
          </div>

          <div
            v-else-if="previewData.length === 0"
            class="loading-state"
          >
            <el-empty description="暂无预览数据" />
          </div>

          <div
            v-else
            class="preview-table-wrapper"
          >
            <el-table
              :data="previewData"
              stripe
              border
              max-height="500"
              :default-sort="{ prop: 'index', order: 'ascending' }"
            >
              <el-table-column
                type="index"
                width="60"
                label="#"
                fixed
              />
              <el-table-column
                v-for="col in previewColumns"
                :key="col"
                :prop="col"
                :label="col"
                min-width="150"
                sortable
              />
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane
        label="列详情"
        name="columns"
      >
        <div class="columns-section">
          <div
            v-if="loadingStats"
            class="loading-state"
          >
            <el-icon class="is-loading">
              <Loader />
            </el-icon>
            <span>加载中...</span>
          </div>

          <div
            v-else-if="columnDetails.length === 0"
            class="loading-state"
          >
            <el-empty description="暂无列统计信息" />
          </div>

          <div
            v-else
            class="column-cards"
          >
            <div
              v-for="(col, index) in columnDetails"
              :key="col.name"
              class="column-card"
            >
              <div class="column-header">
                <div class="column-name">
                  <span class="column-index">{{ index + 1 }}</span>
                  <span class="column-title">{{ col.name }}</span>
                </div>
                <el-tag
                  size="small"
                  :type="getColumnTypeTag(col.type)"
                >
                  {{ col.type || 'string' }}
                </el-tag>
              </div>

              <div class="column-stats">
                <div class="column-stat">
                  <span class="stat-label">空值</span>
                  <span class="stat-value">{{ formatNumber(col.nullCount || 0) }}</span>
                </div>
                <div class="column-stat">
                  <span class="stat-label">唯一值</span>
                  <span class="stat-value">{{ formatNumber(col.unique || 0) }}</span>
                </div>
                <div class="column-stat">
                  <span class="stat-label">示例值</span>
                  <span class="stat-value sample">{{ col.sample || '-' }}</span>
                </div>
              </div>

              <div
                v-if="col.distribution"
                class="column-distribution"
              >
                <div class="distribution-header">
                  <span>值分布</span>
                </div>
                <div class="distribution-bars">
                  <div
                    v-for="item in col.distribution.slice(0, 5)"
                    :key="item.value"
                    class="distribution-item"
                  >
                    <span class="dist-label">{{ item.value }}</span>
                    <div class="dist-bar-wrapper">
                      <div
                        class="dist-bar"
                        :style="{ width: (item.count / col.distribution[0].count * 100) + '%' }"
                      />
                    </div>
                    <span class="dist-count">{{ formatNumber(item.count) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane
        label="使用记录"
        name="usage"
      >
        <div class="usage-section">
          <el-empty description="暂无使用记录">
            <template #image>
              <Clock class="empty-icon" />
            </template>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, Download, Trash2, FileText, Database, Calendar,
  Columns, HardDrive, AlertCircle, Loader, Clock
} from 'lucide-vue-next'
import datasetApi from '@/api/dataset'

const route = useRoute()
const router = useRouter()

const datasetId = computed(() => route.params.id)

const dataset = ref({
  name: '',
  description: '',
  format: 'csv',
  size: 0,
  rowCount: 0,
  columns: [],
  createdAt: ''
})

const datasetStats = ref({
  totalRows: 0,
  columns: 0,
  memory: 0,
  nullCount: 0
})

const previewData = ref([])
const previewColumns = ref([])
const previewPage = ref(1)
const loadingPreview = ref(false)

const columnDetails = ref([])
const loadingStats = ref(false)

const activeTab = ref('preview')

async function loadDataset() {
  try {
    const response = await datasetApi.get(datasetId.value)
    dataset.value = {
      id: response.id,
      name: response.name || response.fileName || `Dataset ${response.id}`,
      description: response.description || '',
      format: response.format || response.fileType || 'csv',
      size: response.size || response.fileSize || 0,
      rowCount: response.rowCount || response.rows || 0,
      columns: response.columns || [],
      createdAt: response.createdAt || response.created_at || new Date().toISOString()
    }
  } catch (error) {
    console.error('Failed to load dataset:', error)
    ElMessage.error('加载数据集失败')
    router.push('/datasets')
  }
}

function mapColumnStats(columnStats) {
  if (Array.isArray(columnStats)) {
    return columnStats
  }
  if (!columnStats || typeof columnStats !== 'object') {
    return []
  }
  return Object.entries(columnStats).map(([name, stats]) => ({
    name,
    type: stats.dtype || stats.type || 'string',
    nullCount: stats.null_count ?? stats.nullCount ?? 0,
    unique: stats.unique_count ?? stats.unique ?? 0,
    sample: stats.sample || '-',
    distribution: stats.distribution || [],
  }))
}

async function loadStats() {
  loadingStats.value = true
  try {
    const response = await datasetApi.stats(datasetId.value)
    const columnStats = response.column_stats || response.columnStats || {}
    const nullCount = Object.values(columnStats).reduce(
      (sum, col) => sum + (col?.null_count ?? col?.nullCount ?? 0),
      0,
    )

    datasetStats.value = {
      totalRows: response.row_count ?? response.rowCount ?? dataset.value.rowCount ?? 0,
      columns: response.column_count ?? response.columnCount ?? dataset.value.columns?.length ?? 0,
      memory: response.size ?? dataset.value.size ?? 0,
      nullCount,
    }
    columnDetails.value = mapColumnStats(columnStats)
  } catch (error) {
    console.error('Failed to load stats:', error)
    ElMessage.error('加载统计信息失败')
    datasetStats.value = {
      totalRows: dataset.value.rowCount || 0,
      columns: dataset.value.columns?.length || 0,
      memory: dataset.value.size || 0,
      nullCount: 0,
    }
    columnDetails.value = []
  } finally {
    loadingStats.value = false
  }
}

async function loadPreview() {
  loadingPreview.value = true
  try {
    const response = await datasetApi.preview(datasetId.value, previewPage.value)
    previewData.value = response.preview || response.rows || []
    previewColumns.value = response.columns || dataset.value.columns || []
    if (!previewColumns.value.length && previewData.value.length && typeof previewData.value[0] === 'object') {
      previewColumns.value = Object.keys(previewData.value[0])
    }
  } catch (error) {
    console.error('Failed to load preview:', error)
    ElMessage.error('加载数据预览失败')
    previewData.value = []
    previewColumns.value = dataset.value.columns || []
  } finally {
    loadingPreview.value = false
  }
}

async function downloadDataset() {
  try {
    const blob = await datasetApi.download(datasetId.value)
    const filename = `${dataset.value.name || 'dataset'}.${dataset.value.format || 'csv'}`
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (error) {
    console.error('Download failed:', error)
    ElMessage.error('下载失败')
  }
}

async function deleteDataset() {
  try {
    await ElMessageBox.confirm(
      '确定要删除此数据集吗？此操作不可恢复。',
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await datasetApi.delete(datasetId.value)
    ElMessage.success('删除成功')
    goBack()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Delete failed:', error)
      ElMessage.error('删除失败')
    }
  }
}

function goBack() {
  router.push('/datasets')
}

function getColumnTypeTag(type) {
  const types = {
    'int64': '',
    'float64': 'success',
    'string': 'info',
    'datetime': 'warning',
    'boolean': 'danger'
  }
  return types[type] || 'info'
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
    day: '2-digit'
  })
}

onMounted(() => {
  loadDataset()
  loadStats()
  loadPreview()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.dataset-detail-page {
  padding: $spacing-6;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: $spacing-6;
}

.header-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-top: $spacing-3;
}

.page-title {
  font-size: $font-size-2xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0 0 $spacing-2;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.meta-icon {
  width: 14px;
  height: 14px;
}

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: $spacing-1;
}

.header-actions {
  display: flex;
  gap: $spacing-2;
}

.description-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-md;
  padding: $spacing-4;
  margin-bottom: $spacing-6;

  p {
    margin: 0;
    font-size: $font-size-sm;
    color: var(--text-secondary);
    line-height: 1.6;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-4;
  margin-bottom: $spacing-6;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary-light-9);
  border-radius: $radius-md;
  color: var(--color-primary);

  .icon {
    width: 24px;
    height: 24px;
  }
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
}

.stat-label {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.detail-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: $spacing-4;
  }
}

// Preview section
.preview-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-4;

  h3 {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: var(--text-primary);
    margin: 0;
  }
}

.preview-table-wrapper {
  overflow-x: auto;
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

// Columns section
.columns-section {
  padding: $spacing-2;
}

.column-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: $spacing-4;
}

.column-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  padding: $spacing-4;
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-3;
}

.column-name {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.column-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: $radius-sm;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  font-weight: $font-weight-medium;
}

.column-title {
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  font-family: 'Fira Code', monospace;
}

.column-stats {
  display: flex;
  gap: $spacing-4;
  margin-bottom: $spacing-3;
}

.column-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .stat-label {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }

  .stat-value {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);

    &.sample {
      font-size: $font-size-xs;
      max-width: 120px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}

.column-distribution {
  border-top: 1px solid var(--border-primary);
  padding-top: $spacing-3;
}

.distribution-header {
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  margin-bottom: $spacing-2;
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.distribution-item {
  display: flex;
  align-items: center;
  gap: $spacing-2;
}

.dist-label {
  width: 80px;
  font-size: $font-size-xs;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dist-bar-wrapper {
  flex: 1;
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.dist-bar {
  height: 100%;
  background: var(--color-primary);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.dist-count {
  width: 50px;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
  text-align: right;
}

// Usage section
.usage-section {
  padding: $spacing-8;
}

.empty-icon {
  width: 64px;
  height: 64px;
  opacity: 0.3;
}
</style>
