<template>
  <div class="execution-list-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1>执行记录</h1>
        <p class="subtitle">
          查看和管理工作流执行历史
        </p>
      </div>
      <div class="header-actions">
        <el-button
          type="primary"
          :loading="isLoading"
          @click="refreshData"
        >
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon pending">
          <Clock class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.pending }}</span>
          <span class="stat-label">待处理</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon running">
          <Loader class="icon spin" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.running }}</span>
          <span class="stat-label">运行中</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon success">
          <CheckCircle class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.completed }}</span>
          <span class="stat-label">已完成</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon error">
          <XCircle class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.failed }}</span>
          <span class="stat-label">失败</span>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <el-select
          v-model="statusFilter"
          placeholder="状态筛选"
          clearable
          size="default"
        >
          <el-option
            label="全部状态"
            value=""
          />
          <el-option
            label="待处理"
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
          <el-option
            label="已取消"
            value="cancelled"
          />
          <el-option
            label="已暂停"
            value="paused"
          />
        </el-select>
      </div>
      <div class="filter-group">
        <el-input
          v-model="workflowFilter"
          placeholder="工作流名称..."
          clearable
          size="default"
          :prefix-icon="Search"
        />
      </div>
      <div class="filter-group date-range">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="default"
          value-format="YYYY-MM-DD"
        />
      </div>
    </div>

    <!-- Execution Table -->
    <div class="execution-table-container">
      <el-table
        v-loading="isLoading"
        :data="paginatedExecutions"
        stripe
        highlight-current-row
        class="execution-table"
        @row-click="handleRowClick"
      >
        <el-table-column
          label="ID"
          width="120"
          prop="id"
        >
          <template #default="{ row }">
            <span class="execution-id">#{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="工作流"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="workflow-cell">
              <Workflow class="workflow-icon" />
              <span class="workflow-name">{{ row.workflow_name || row.workflowName || '-' }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          label="状态"
          width="120"
        >
          <template #default="{ row }">
            <span
              class="status-badge"
              :class="row.status"
            >
              <span class="status-dot" />
              {{ statusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="开始时间"
          width="180"
        >
          <template #default="{ row }">
            <span class="time-cell">
              <Clock class="time-icon" />
              {{ formatDate(row.started_at || row.startedAt) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="耗时"
          width="120"
        >
          <template #default="{ row }">
            <span
              class="duration-cell"
              :class="{ running: row.status === 'running' }"
            >
              <Timer class="duration-icon" />
              {{ formatDuration(row.duration || row.duration_ms || row.durationMs) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column
          label="节点进度"
          width="180"
        >
          <template #default="{ row }">
            <div
              v-if="row.nodes_total || row.nodesTotal"
              class="node-progress"
            >
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: getProgressWidth(row) + '%' }"
                  :class="getProgressClass(row)"
                />
              </div>
              <span class="progress-text">
                {{ row.nodes_success || row.nodesSuccess || 0 }}/{{ row.nodes_total || row.nodesTotal || 0 }}
              </span>
            </div>
            <span
              v-else
              class="no-progress"
            >-</span>
          </template>
        </el-table-column>

        <el-table-column
          label="触发方式"
          width="100"
        >
          <template #default="{ row }">
            <span class="trigger-badge">{{ triggerLabel(row.trigger_type || row.triggerType) }}</span>
          </template>
        </el-table-column>

        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button
                size="small"
                text
                type="primary"
                @click.stop="viewDetail(row)"
              >
                详情
              </el-button>
              <el-button
                v-if="row.status === 'running'"
                size="small"
                text
                type="warning"
                @click.stop="pauseExecution(row)"
              >
                暂停
              </el-button>
              <el-button
                v-if="row.status === 'paused'"
                size="small"
                text
                type="success"
                @click.stop="resumeExecution(row)"
              >
                继续
              </el-button>
              <el-button
                v-if="['running', 'pending'].includes(row.status)"
                size="small"
                text
                type="danger"
                @click.stop="cancelExecution(row)"
              >
                取消
              </el-button>
              <el-button
                v-if="row.status === 'failed'"
                size="small"
                text
                type="warning"
                @click.stop="retryExecution(row)"
              >
                重试
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Pagination -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="filteredExecutions.length"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- Execution Detail Dialog -->
    <ExecutionDetailDialog
      v-model="showDetailDialog"
      :execution-id="selectedExecutionId"
      :execution="selectedExecutionData"
      @refresh="refreshData"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import {
  RefreshCw, Clock, Loader, CheckCircle, XCircle, Workflow,
  Timer, Search, Play, Pause, Square, RotateCcw
} from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import { useAppStore } from '@/stores/app'
import ExecutionDetailDialog from '@/components/ExecutionTimeline/ExecutionDetailDialog.vue'

const router = useRouter()
const executionStore = useExecutionStore()
const appStore = useAppStore()

// Filters
const statusFilter = ref('')
const workflowFilter = ref('')
const dateRange = ref([])

// Pagination
const page = ref(1)
const pageSize = ref(20)

// Detail Dialog
const showDetailDialog = ref(false)
const selectedExecutionId = ref(null)
const selectedExecutionData = ref(null)

// Statistics
const stats = ref({
  pending: 0,
  running: 0,
  completed: 0,
  failed: 0,
  cancelled: 0,
  paused: 0
})

// Computed
const isLoading = computed(() => executionStore.historyLoading)

const executions = computed(() => {
  return executionStore.executionHistory.length > 0
    ? executionStore.executionHistory
    : getMockExecutions()
})

const filteredExecutions = computed(() => {
  let result = executions.value

  // Status filter
  if (statusFilter.value) {
    result = result.filter(e => e.status === statusFilter.value)
  }

  // Workflow name filter
  if (workflowFilter.value) {
    const filter = workflowFilter.value.toLowerCase()
    result = result.filter(e =>
      (e.workflow_name || e.workflowName || '').toLowerCase().includes(filter)
    )
  }

  // Date range filter
  if (dateRange.value && dateRange.value.length === 2) {
    const [startDate, endDate] = dateRange.value
    result = result.filter(e => {
      const execDate = (e.started_at || e.startedAt || '').split('T')[0]
      return execDate >= startDate && execDate <= endDate
    })
  }

  return result
})

const paginatedExecutions = computed(() => {
  const start = (page.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredExecutions.value.slice(start, end)
})

// Methods
function getMockExecutions() {
  return [
    {
      id: 'exec_1001',
      workflow_name: '数据处理流水线',
      workflowName: '数据处理流水线',
      status: 'completed',
      duration: 4521,
      duration_ms: 4521,
      started_at: '2024-01-15T14:30:00Z',
      trigger_type: 'manual',
      nodes_total: 5,
      nodes_success: 5,
      nodes_failed: 0
    },
    {
      id: 'exec_1002',
      workflow_name: 'API数据同步',
      workflowName: 'API数据同步',
      status: 'running',
      duration: 1234,
      duration_ms: 1234,
      started_at: '2024-01-15T14:35:00Z',
      trigger_type: 'schedule',
      nodes_total: 8,
      nodes_success: 3,
      nodes_failed: 0
    },
    {
      id: 'exec_1003',
      workflow_name: 'LLM内容生成',
      workflowName: 'LLM内容生成',
      status: 'failed',
      duration: 8900,
      duration_ms: 8900,
      started_at: '2024-01-15T14:20:00Z',
      trigger_type: 'webhook',
      nodes_total: 4,
      nodes_success: 2,
      nodes_failed: 1
    },
    {
      id: 'exec_1004',
      workflow_name: '用户行为分析',
      workflowName: '用户行为分析',
      status: 'pending',
      duration: null,
      started_at: '2024-01-15T14:40:00Z',
      trigger_type: 'manual',
      nodes_total: 6,
      nodes_success: 0,
      nodes_failed: 0
    },
    {
      id: 'exec_1005',
      workflow_name: '定时报表生成',
      workflowName: '定时报表生成',
      status: 'paused',
      duration: 2500,
      duration_ms: 2500,
      started_at: '2024-01-15T14:15:00Z',
      trigger_type: 'schedule',
      nodes_total: 10,
      nodes_success: 7,
      nodes_failed: 0
    }
  ]
}

async function refreshData() {
  try {
    await executionStore.fetchHistory()
    updateStats()
    ElMessage.success('数据已刷新')
  } catch (error) {
    ElMessage.error('刷新失败: ' + (error.message || '未知错误'))
  }
}

function updateStats() {
  const all = executions.value
  stats.value = {
    pending: all.filter(e => e.status === 'pending').length,
    running: all.filter(e => e.status === 'running').length,
    completed: all.filter(e => e.status === 'completed').length,
    failed: all.filter(e => e.status === 'failed').length,
    cancelled: all.filter(e => e.status === 'cancelled').length,
    paused: all.filter(e => e.status === 'paused').length
  }
}

function statusLabel(status) {
  const labels = {
    pending: '待处理',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    paused: '已暂停'
  }
  return labels[status] || status || '-'
}

function triggerLabel(trigger) {
  const labels = {
    manual: '手动',
    schedule: '定时',
    webhook: 'Webhook',
    api: 'API'
  }
  return labels[trigger] || trigger || '-'
}

function formatDate(date) {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(0)
    return `${mins}m ${secs}s`
  }
  const hours = Math.floor(seconds / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}

function getProgressWidth(row) {
  const total = row.nodes_total || row.nodesTotal || 0
  const success = row.nodes_success || row.nodesSuccess || 0
  if (total === 0) return 0
  return Math.round((success / total) * 100)
}

function getProgressClass(row) {
  if (row.nodes_failed > 0) return 'warning'
  if (getProgressWidth(row) === 100) return 'success'
  return ''
}

function handleRowClick(row) {
  viewDetail(row)
}

function viewDetail(row) {
  selectedExecutionId.value = row.id
  selectedExecutionData.value = row
  showDetailDialog.value = true
}

async function pauseExecution(row) {
  try {
    await ElMessageBox.confirm(`确定要暂停执行 #${row.id} 吗？`, '暂停执行', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await executionStore.pauseExecution(row.id)
    ElMessage.success('执行已暂停')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('暂停失败: ' + (error.message || '未知错误'))
    }
  }
}

async function resumeExecution(row) {
  try {
    await executionStore.resumeExecution(row.id)
    ElMessage.success('执行已恢复')
    refreshData()
  } catch (error) {
    ElMessage.error('恢复失败: ' + (error.message || '未知错误'))
  }
}

async function cancelExecution(row) {
  try {
    await ElMessageBox.confirm(`确定要取消执行 #${row.id} 吗？`, '取消执行', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await executionStore.cancelExecution(row.id)
    ElMessage.warning('执行已取消')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败: ' + (error.message || '未知错误'))
    }
  }
}

async function retryExecution(row) {
  try {
    await ElMessageBox.confirm(`确定要重试执行 #${row.id} 吗？`, '重试执行', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'info'
    })
    await executionStore.retryExecution(row.id)
    ElMessage.success('重试已启动')
    refreshData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('重试失败: ' + (error.message || '未知错误'))
    }
  }
}

function handleSizeChange(val) {
  pageSize.value = val
  page.value = 1
}

function handlePageChange(val) {
  page.value = val
}

// Polling for running executions
let pollingInterval = null

function startPolling() {
  pollingInterval = setInterval(() => {
    const hasRunning = executions.value.some(e => e.status === 'running' || e.status === 'pending')
    if (hasRunning) {
      refreshData()
    }
  }, 5000) // Poll every 5 seconds
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

// Lifecycle
onMounted(() => {
  refreshData()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.execution-list-page {
  padding: 24px;
  background: var(--bg-page);
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .subtitle {
    margin: 8px 0 0;
    font-size: 14px;
    color: var(--text-secondary);
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
  margin-right: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;

  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;

    &.pending {
      background: rgba(107, 114, 128, 0.1);
      .icon { color: #6b7280; }
    }

    &.running {
      background: rgba(59, 130, 246, 0.1);
      .icon { color: #3b82f6; }
    }

    &.success {
      background: rgba(16, 185, 129, 0.1);
      .icon { color: #10b981; }
    }

    &.error {
      background: rgba(239, 68, 68, 0.1);
      .icon { color: #ef4444; }
    }

    .icon {
      width: 24px;
      height: 24px;
    }

    .spin {
      animation: spin 1s linear infinite;
    }
  }

  .stat-info {
    display: flex;
    flex-direction: column;

    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 14px;
      color: var(--text-secondary);
      margin-top: 4px;
    }
  }
}

.filters-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;

  .filter-group {
    min-width: 180px;

    &.date-range {
      min-width: 280px;
    }
  }
}

.execution-table-container {
  background: var(--bg-card);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
}

.execution-table {
  :deep(.el-table__row) {
    cursor: pointer;
    transition: background-color 0.2s;

    &:hover > td {
      background-color: var(--bg-hover) !important;
    }
  }
}

.execution-id {
  font-family: 'JetBrains Mono', 'Monaco', monospace;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.workflow-cell {
  display: flex;
  align-items: center;
  gap: 8px;

  .workflow-icon {
    width: 16px;
    height: 16px;
    color: var(--text-secondary);
  }

  .workflow-name {
    font-weight: 500;
    color: var(--text-primary);
  }
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;

  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
  }

  &.pending {
    background: rgba(107, 114, 128, 0.1);
    color: #6b7280;
    .status-dot { background: #6b7280; }
  }

  &.running {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
    .status-dot {
      background: #3b82f6;
      animation: pulse 1.5s infinite;
    }
  }

  &.completed {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    .status-dot { background: #10b981; }
  }

  &.failed {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    .status-dot { background: #ef4444; }
  }

  &.cancelled {
    background: rgba(107, 114, 128, 0.1);
    color: #6b7280;
    .status-dot { background: #6b7280; }
  }

  &.paused {
    background: rgba(245, 158, 11, 0.1);
    color: #f59e0b;
    .status-dot { background: #f59e0b; }
  }
}

.time-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);

  .time-icon {
    width: 14px;
    height: 14px;
  }
}

.duration-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
  color: var(--text-secondary);

  .duration-icon {
    width: 14px;
    height: 14px;
  }

  &.running {
    color: #3b82f6;
  }
}

.node-progress {
  display: flex;
  align-items: center;
  gap: 8px;

  .progress-bar {
    flex: 1;
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
    background: #10b981;

    &.warning { background: #f59e0b; }
    &.success { background: #10b981; }
  }

  .progress-text {
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    min-width: 40px;
  }
}

.no-progress {
  color: var(--text-tertiary);
}

.trigger-badge {
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
