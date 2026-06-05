<template>
  <div class="augmentation-status-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          数据增强任务
        </h1>
        <p class="page-subtitle">
          查看和管理数据增强任务状态
        </p>
      </div>
      <div class="header-actions">
        <el-button
          :loading="loading"
          @click="loadJobs"
        >
          <RefreshCw :size="16" />
          刷新
        </el-button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: rgba(59, 130, 246, 0.1); color: #3b82f6;"
        >
          <Layers :size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ statistics.total_jobs || 0 }}
          </div>
          <div class="stat-label">
            总任务数
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: rgba(16, 185, 129, 0.1); color: #10b981;"
        >
          <CheckCircle :size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ statistics.completed_jobs || 0 }}
          </div>
          <div class="stat-label">
            已完成
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: rgba(245, 158, 11, 0.1); color: #f59e0b;"
        >
          <Loader :size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ statistics.running_jobs || 0 }}
          </div>
          <div class="stat-label">
            运行中
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: rgba(239, 68, 68, 0.1); color: #ef4444;"
        >
          <XCircle :size="24" />
        </div>
        <div class="stat-content">
          <div class="stat-value">
            {{ statistics.failed_jobs || 0 }}
          </div>
          <div class="stat-label">
            失败
          </div>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <el-select
          v-model="filters.status"
          placeholder="状态筛选"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="全部"
            value=""
          />
          <el-option
            label="等待中"
            value="pending"
          />
          <el-option
            label="运行中"
            value="running"
          />
          <el-option
            label="已完成"
            value="completed"
          />
          <el-option
            label="失败"
            value="failed"
          />
        </el-select>

        <el-select
          v-model="filters.strategy"
          placeholder="策略筛选"
          clearable
          @change="handleFilterChange"
        >
          <el-option
            label="全部"
            value=""
          />
          <el-option
            label="几何变换"
            value="geometric"
          />
          <el-option
            label="颜色变换"
            value="color"
          />
          <el-option
            label="噪声注入"
            value="noise"
          />
          <el-option
            label="混合增强"
            value="mixup"
          />
          <el-option
            label="全部策略"
            value="all"
          />
        </el-select>
      </div>

      <el-input
        v-model="filters.search"
        placeholder="搜索数据集名称..."
        prefix-icon="Search"
        clearable
        style="width: 250px"
        @input="handleSearchDebounced"
      />
    </div>

    <!-- Jobs Table -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="jobs"
        stripe
        style="width: 100%"
        :row-class-name="getRowClassName"
        @row-click="handleRowClick"
      >
        <el-table-column
          prop="input_dataset_name"
          label="输入数据集"
          min-width="150"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="dataset-cell">
              <Database
                :size="16"
                class="dataset-icon"
              />
              <span>{{ row.input_dataset_name || '-' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="strategy"
          label="策略"
          width="120"
        >
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="getStrategyTagType(row.strategy)"
            >
              {{ row.strategy_display || row.strategy }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column
          prop="ratio"
          label="倍数"
          width="80"
        >
          <template #default="{ row }">
            <span class="ratio-value">{{ row.ratio }}x</span>
          </template>
        </el-table-column>

        <el-table-column
          prop="original_count"
          label="原始样本"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            {{ row.original_count || 0 }}
          </template>
        </el-table-column>

        <el-table-column
          prop="augmented_count"
          label="增强样本"
          width="100"
          align="right"
        >
          <template #default="{ row }">
            <span class="augmented-value">{{ row.augmented_count || 0 }}</span>
          </template>
        </el-table-column>

        <el-table-column
          prop="status"
          label="状态"
          width="120"
        >
          <template #default="{ row }">
            <div class="status-cell">
              <el-tag 
                size="small" 
                :type="getStatusTagType(row.status)"
                :effect="row.status === 'running' ? 'light' : 'light'"
              >
                <el-icon
                  v-if="row.status === 'running'"
                  class="rotating"
                >
                  <Loader />
                </el-icon>
                {{ row.status_display || row.status }}
              </el-tag>
              <el-progress
                v-if="row.status === 'running'"
                :percentage="row.progress || 0"
                :stroke-width="3"
                :show-text="false"
                style="width: 60px; margin-left: 8px;"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column
          prop="created_at"
          label="创建时间"
          width="160"
        >
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="150"
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
                @click="viewDetails(row)"
              >
                详情
              </el-button>

              <el-button
                v-if="row.status === 'failed'"
                type="warning"
                link
                size="small"
                @click="retryJob(row)"
              >
                重试
              </el-button>

              <el-button
                v-if="['pending', 'running'].includes(row.status)"
                type="danger"
                link
                size="small"
                @click="cancelJob(row)"
              >
                取消
              </el-button>

              <el-button
                v-if="row.status === 'completed' && row.output_dataset"
                type="success"
                link
                size="small"
                @click="viewOutputDataset(row)"
              >
                查看输出
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <div class="empty-state">
            <Layers
              :size="48"
              class="empty-icon"
            />
            <p class="empty-text">
              暂无增强任务
            </p>
            <el-button
              type="primary"
              @click="goToWorkflow"
            >
              创建工作流
            </el-button>
          </div>
        </template>
      </el-table>

      <!-- Pagination -->
      <div
        v-if="totalCount > 0"
        class="pagination-wrapper"
      >
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <!-- Job Details Drawer -->
    <el-drawer
      v-model="showDetails"
      :title="`任务详情: ${selectedJob?.input_dataset_name || ''}`"
      size="500px"
      :before-close="closeDetails"
    >
      <div
        v-if="selectedJob"
        class="job-details"
      >
        <div class="detail-section">
          <h4 class="detail-title">
            基本信息
          </h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">任务ID</span>
              <span class="detail-value">{{ selectedJob.id }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">状态</span>
              <el-tag
                :type="getStatusTagType(selectedJob.status)"
                size="small"
              >
                {{ selectedJob.status_display || selectedJob.status }}
              </el-tag>
            </div>
            <div class="detail-item">
              <span class="detail-label">增强策略</span>
              <el-tag
                :type="getStrategyTagType(selectedJob.strategy)"
                size="small"
              >
                {{ selectedJob.strategy_display || selectedJob.strategy }}
              </el-tag>
            </div>
            <div class="detail-item">
              <span class="detail-label">增强倍数</span>
              <span class="detail-value">{{ selectedJob.ratio }}x</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4 class="detail-title">
            数据统计
          </h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">原始样本</span>
              <span class="detail-value">{{ selectedJob.original_count || 0 }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">增强后样本</span>
              <span class="detail-value augmented-value">{{ selectedJob.augmented_count || 0 }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="selectedJob.status === 'running'"
          class="detail-section"
        >
          <h4 class="detail-title">
            执行进度
          </h4>
          <el-progress 
            :percentage="selectedJob.progress || 0" 
            :stroke-width="8"
            :color="progressColor"
          />
        </div>

        <div
          v-if="selectedJob.error_message"
          class="detail-section"
        >
          <h4 class="detail-title">
            错误信息
          </h4>
          <div class="error-message">
            <AlertCircle :size="16" />
            {{ selectedJob.error_message }}
          </div>
        </div>

        <div class="detail-section">
          <h4 class="detail-title">
            时间信息
          </h4>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ formatDate(selectedJob.created_at) }}</span>
            </div>
            <div
              v-if="selectedJob.started_at"
              class="detail-item"
            >
              <span class="detail-label">开始时间</span>
              <span class="detail-value">{{ formatDate(selectedJob.started_at) }}</span>
            </div>
            <div
              v-if="selectedJob.completed_at"
              class="detail-item"
            >
              <span class="detail-label">完成时间</span>
              <span class="detail-value">{{ formatDate(selectedJob.completed_at) }}</span>
            </div>
            <div
              v-if="selectedJob.duration_seconds"
              class="detail-item"
            >
              <span class="detail-label">执行时长</span>
              <span class="detail-value">{{ formatDuration(selectedJob.duration_seconds) }}</span>
            </div>
          </div>
        </div>

        <div
          v-if="selectedJob.output_dataset"
          class="detail-section"
        >
          <h4 class="detail-title">
            输出数据集
          </h4>
          <div class="output-dataset-card">
            <Database :size="20" />
            <div class="output-info">
              <span class="output-name">{{ selectedJob.output_dataset_name || '输出数据集' }}</span>
              <span class="output-id">{{ selectedJob.output_dataset }}</span>
            </div>
            <el-button
              type="primary"
              size="small"
              @click="viewOutputDataset(selectedJob)"
            >
              查看
            </el-button>
          </div>
        </div>

        <div class="detail-actions">
          <el-button 
            v-if="selectedJob.status === 'failed'" 
            type="warning" 
            @click="retryJob(selectedJob); closeDetails();"
          >
            重试任务
          </el-button>
          <el-button 
            v-if="['pending', 'running'].includes(selectedJob.status)" 
            type="danger" 
            @click="cancelJob(selectedJob); closeDetails();"
          >
            取消任务
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Layers, RefreshCw, CheckCircle, Loader, XCircle,
  Database, Search, AlertCircle
} from 'lucide-vue-next'
import { augmentationApi } from '@/api/augmentation'

const router = useRouter()

// State
const loading = ref(false)
const jobs = ref([])
const statistics = ref({})
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const filters = reactive({
  status: '',
  strategy: '',
  search: '',
})

const showDetails = ref(false)
const selectedJob = ref(null)
let pollingInterval = null
let searchDebounceTimer = null

// Computed
const progressColor = computed(() => {
  if (!selectedJob.value) return '#3b82f6'
  const progress = selectedJob.value.progress || 0
  if (progress < 30) return '#ef4444'
  if (progress < 70) return '#f59e0b'
  return '#10b981'
})

// Methods
const loadJobs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (filters.status) params.status = filters.status
    if (filters.strategy) params.strategy = filters.strategy
    if (filters.search) params.search = filters.search

    const result = await augmentationApi.list(params)
    jobs.value = result.results || result || []
    totalCount.value = result.count || jobs.value.length
  } catch (error) {
    console.error('Failed to load jobs:', error)
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const loadStatistics = async () => {
  try {
    const result = await augmentationApi.getStatistics()
    statistics.value = result || {}
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

const handleFilterChange = () => {
  currentPage.value = 1
  loadJobs()
}

const handleSearchDebounced = () => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    currentPage.value = 1
    loadJobs()
  }, 300)
}

const handlePageChange = () => {
  loadJobs()
}

const handleSizeChange = () => {
  currentPage.value = 1
  loadJobs()
}

const handleRowClick = (row) => {
  viewDetails(row)
}

const getRowClassName = ({ row }) => {
  if (row.status === 'failed') return 'failed-row'
  if (row.status === 'running') return 'running-row'
  return ''
}

const viewDetails = async (job) => {
  try {
    const result = await augmentationApi.get(job.id)
    selectedJob.value = result
    showDetails.value = true
  } catch (error) {
    console.error('Failed to load job details:', error)
    ElMessage.error('加载任务详情失败')
  }
}

const closeDetails = () => {
  showDetails.value = false
  selectedJob.value = null
}

const cancelJob = async (job) => {
  try {
    await ElMessageBox.confirm(
      '确定要取消此增强任务吗？',
      '取消任务',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    await augmentationApi.cancel(job.id)
    ElMessage.success('任务已取消')
    loadJobs()
    loadStatistics()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to cancel job:', error)
      ElMessage.error('取消任务失败')
    }
  }
}

const retryJob = async (job) => {
  try {
    await augmentationApi.retry(job.id)
    ElMessage.success('任务已重新启动')
    loadJobs()
    loadStatistics()
  } catch (error) {
    console.error('Failed to retry job:', error)
    ElMessage.error('重试任务失败')
  }
}

const viewOutputDataset = (job) => {
  if (job.output_dataset) {
    router.push(`/datasets/${job.output_dataset}`)
  }
}

const goToWorkflow = () => {
  router.push('/workflows/new')
}

const getStatusTagType = (status) => {
  const types = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return types[status] || 'info'
}

const getStrategyTagType = (strategy) => {
  const types = {
    geometric: 'primary',
    color: 'success',
    noise: 'warning',
    mixup: 'danger',
    all: 'info',
  }
  return types[strategy] || 'info'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`
  return `${Math.floor(seconds / 3600)}小时${Math.floor((seconds % 3600) / 60)}分`
}

// Poll for running jobs
const startPolling = () => {
  pollingInterval = setInterval(() => {
    const hasRunningJobs = jobs.value.some(j => j.status === 'running' || j.status === 'pending')
    if (hasRunningJobs) {
      loadJobs()
      if (selectedJob.value) {
        augmentationApi.get(selectedJob.value.id).then(result => {
          if (showDetails.value) {
            selectedJob.value = result
          }
        })
      }
    }
  }, 5000)
}

const stopPolling = () => {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// Lifecycle
onMounted(() => {
  loadJobs()
  loadStatistics()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.augmentation-status-page {
  padding: $spacing-5;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: $spacing-5;

  .page-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 $spacing-1;
  }

  .page-subtitle {
    font-size: $font-size-sm;
    color: var(--text-secondary);
    margin: 0;
  }
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-4;
  margin-bottom: $spacing-5;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: $spacing-4;
  padding: $spacing-4;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    border-radius: $radius-md;
  }

  .stat-content {
    .stat-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--text-primary);
      line-height: 1.2;
    }

    .stat-label {
      font-size: $font-size-sm;
      color: var(--text-secondary);
    }
  }
}

.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: $spacing-4;
  margin-bottom: $spacing-4;
  padding: $spacing-4;
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;

  .filter-group {
    display: flex;
    gap: $spacing-3;
  }
}

.table-container {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  overflow: hidden;

  :deep(.el-table) {
    --el-table-border-color: var(--border-primary);
    --el-table-header-bg-color: var(--bg-secondary);
  }

  :deep(.failed-row) {
    background-color: rgba(239, 68, 68, 0.05);
  }

  :deep(.running-row) {
    background-color: rgba(245, 158, 11, 0.05);
  }
}

.dataset-cell {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .dataset-icon {
    color: var(--text-tertiary);
  }
}

.ratio-value {
  font-family: 'Fira Code', monospace;
  font-weight: 500;
}

.augmented-value {
  color: var(--color-primary);
  font-weight: 600;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: $spacing-2;

  .rotating {
    animation: rotate 1s linear infinite;
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.action-buttons {
  display: flex;
  gap: $spacing-2;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: $spacing-8;
  text-align: center;

  .empty-icon {
    color: var(--text-tertiary);
    margin-bottom: $spacing-4;
  }

  .empty-text {
    font-size: $font-size-base;
    color: var(--text-secondary);
    margin-bottom: $spacing-4;
  }
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: $spacing-4;
  border-top: 1px solid var(--border-primary);
}

.job-details {
  .detail-section {
    margin-bottom: $spacing-5;
    padding-bottom: $spacing-4;
    border-bottom: 1px solid var(--border-primary);

    &:last-of-type {
      border-bottom: none;
    }

    .detail-title {
      font-size: $font-size-sm;
      font-weight: 600;
      color: var(--text-primary);
      margin: 0 0 $spacing-3;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: $spacing-3;
  }

  .detail-item {
    display: flex;
    flex-direction: column;
    gap: $spacing-1;

    .detail-label {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
    }

    .detail-value {
      font-size: $font-size-sm;
      color: var(--text-primary);
      word-break: break-all;
    }
  }

  .error-message {
    display: flex;
    align-items: flex-start;
    gap: $spacing-2;
    padding: $spacing-3;
    background: rgba(239, 68, 68, 0.1);
    border-radius: $radius-md;
    color: #ef4444;
    font-size: $font-size-sm;
  }

  .output-dataset-card {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    padding: $spacing-3;
    background: var(--bg-tertiary);
    border-radius: $radius-md;

    .output-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;

      .output-name {
        font-weight: 500;
        color: var(--text-primary);
      }

      .output-id {
        font-size: $font-size-xs;
        color: var(--text-tertiary);
        font-family: 'Fira Code', monospace;
      }
    }
  }

  .detail-actions {
    display: flex;
    gap: $spacing-3;
    margin-top: $spacing-4;
  }
}
</style>
