<template>
  <div class="execution-history-page">
    <div class="page-header">
      <div class="header-left">
        <h1>执行历史</h1>
        <p class="subtitle">
          查看和回放工作流执行记录
        </p>
      </div>
      <div class="header-actions">
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 120px"
        >
          <el-option
            label="全部"
            value=""
          />
          <el-option
            label="成功"
            value="completed"
          />
          <el-option
            label="失败"
            value="failed"
          />
          <el-option
            label="运行中"
            value="running"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-button @click="refreshData">
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div class="stats-grid">
      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: var(--info);"
        >
          <Play class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.total }}</span>
          <span class="stat-label">总执行次数</span>
        </div>
      </div>
      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: var(--success);"
        >
          <CheckCircle class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.success }}</span>
          <span class="stat-label">成功</span>
        </div>
      </div>
      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: var(--error);"
        >
          <XCircle class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stats.failed }}</span>
          <span class="stat-label">失败</span>
        </div>
      </div>
      <div class="stat-card">
        <div
          class="stat-icon"
          style="background: var(--warning);"
        >
          <Clock class="icon" />
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ formatDuration(stats.avgDuration) }}</span>
          <span class="stat-label">平均耗时</span>
        </div>
      </div>
    </div>

    <!-- Execution List -->
    <el-card
      shadow="never"
      class="execution-list"
    >
      <el-table
        v-loading="loading"
        :data="filteredExecutions"
        stripe
      >
        <el-table-column
          label="执行ID"
          width="140"
        >
          <template #default="{ row }">
            <div class="execution-id">
              <code>{{ row.id }}</code>
              <el-tag
                v-if="row.isReplayed"
                type="info"
                size="small"
              >
                重放
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="工作流"
          min-width="200"
        >
          <template #default="{ row }">
            <div class="workflow-cell">
              <Workflow class="workflow-icon" />
              <span class="workflow-name">{{ row.workflowName || row.workflow?.name || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          label="产物"
          width="200"
        >
          <template #default="{ row }">
            <div
              v-if="getRowArtifactSummary(row).hasArtifacts"
              class="artifact-summary-cell"
            >
              <img
                v-if="getRowArtifactSummary(row).thumbnailUrl"
                :src="getRowArtifactSummary(row).thumbnailUrl"
                class="artifact-thumb"
                alt=""
                loading="lazy"
              >
              <div class="artifact-badges">
                <span
                  v-for="badge in getRowArtifactBadges(row)"
                  :key="badge.id"
                  class="artifact-badge"
                  :class="`badge-${badge.id}`"
                >
                  {{ badge.label }} {{ badge.count }}
                </span>
              </div>
            </div>
            <span
              v-else
              class="artifact-empty-hint"
            >—</span>
          </template>
        </el-table-column>
        <el-table-column
          label="状态"
          width="100"
        >
          <template #default="{ row }">
            <el-tag
              :type="getStatusType(row.status)"
              size="small"
            >
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          label="耗时"
          width="100"
        >
          <template #default="{ row }">
            <span class="duration">{{ formatDuration(getDurationMs(row)) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="触发"
          width="100"
        >
          <template #default="{ row }">
            <span class="trigger">{{ getTriggerLabel(row.triggerType) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="时间"
          width="160"
        >
          <template #default="{ row }">
            <span class="time">{{ formatDateTime(row.startedAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="200"
          fixed="right"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              text
              @click="viewDetails(row)"
            >
              详情
            </el-button>
            <el-button
              size="small"
              text
              :disabled="!['completed', 'success'].includes(row.status)"
              @click="replayExecution(row)"
            >
              <RotateCcw class="btn-icon-small" />
              重放
            </el-button>
            <el-dropdown trigger="click">
              <el-button
                size="small"
                text
              >
                <MoreHorizontal />
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="copyInput(row)">
                    复制输入
                  </el-dropdown-item>
                  <el-dropdown-item @click="copyOutput(row)">
                    复制输出
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    @click="deleteExecution(row)"
                  >
                    删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="totalCount"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- Detail Drawer -->
    <el-drawer
      v-model="showDetailDrawer"
      title="执行详情"
      size="60%"
    >
      <div
        v-if="selectedExecution"
        class="execution-detail"
      >
        <!-- Header Info -->
        <div class="detail-header">
          <div class="detail-info">
            <h3>{{ selectedExecution.workflowName || selectedExecution.workflow?.name || '工作流' }}</h3>
            <div class="meta-info">
              <el-tag
                :type="getStatusType(selectedExecution.status)"
                size="small"
              >
                {{ getStatusLabel(selectedExecution.status) }}
              </el-tag>
              <span class="meta-item">
                <Clock class="meta-icon" />
                {{ formatDuration(getDurationMs(selectedExecution)) }}
              </span>
              <span class="meta-item">
                <Calendar class="meta-icon" />
                {{ formatDateTime(selectedExecution.startedAt) }}
              </span>
            </div>
          </div>
          <div class="detail-actions">
            <el-button @click="replayExecution(selectedExecution)">
              <RotateCcw class="btn-icon" />
              重放此执行
            </el-button>
          </div>
        </div>

        <!-- Tabs -->
        <el-tabs v-model="detailTab">
          <!-- Artifacts Tab -->
          <el-tab-pane
            label="产物"
            name="artifacts"
          >
            <ExecutionArtifactsPanel
              :node-executions="getNodeExecutions(selectedExecution)"
              :output-data="getExecutionOutput(selectedExecution)"
              :node-status-map="selectedExecution.nodeStatus || selectedExecution.node_status"
              :execution="selectedExecution"
              :node-name-map="detailNodeNameMap"
              :show-header="false"
            />
          </el-tab-pane>

          <!-- Input Tab -->
          <el-tab-pane
            label="输入"
            name="input"
          >
            <div class="data-section">
              <div class="section-header">
                <h4>输入参数</h4>
                <el-button
                  size="small"
                  text
                  @click="copyToClipboard(getExecutionInput(selectedExecution))"
                >
                  <Copy class="btn-icon-small" />
                  复制
                </el-button>
              </div>
              <pre class="data-content"><code>{{ formatJson(getExecutionInput(selectedExecution)) }}</code></pre>
            </div>
          </el-tab-pane>

          <!-- Output Tab -->
          <el-tab-pane
            label="输出"
            name="output"
          >
            <div class="data-section">
              <div class="section-header">
                <h4>执行结果</h4>
                <el-button
                  size="small"
                  text
                  @click="copyToClipboard(getExecutionOutput(selectedExecution))"
                >
                  <Copy class="btn-icon-small" />
                  复制
                </el-button>
              </div>
              <pre class="data-content"><code>{{ formatJson(getExecutionOutput(selectedExecution)) }}</code></pre>
            </div>
          </el-tab-pane>

          <!-- Node Executions Tab -->
          <el-tab-pane
            label="节点执行"
            name="nodes"
          >
            <div class="node-timeline">
              <div
                v-for="(node, index) in getNodeExecutions(selectedExecution)"
                :key="node.id || node.nodeId || index"
                class="node-item"
                :class="{ failed: node.status === 'failed', running: node.status === 'running' }"
              >
                <div class="node-timeline-marker">
                  <div
                    class="marker-dot"
                    :class="node.status"
                  />
                  <div
                    v-if="index < getNodeExecutions(selectedExecution).length - 1"
                    class="marker-line"
                  />
                </div>
                <div class="node-content">
                  <div class="node-header">
                    <span class="node-name">{{ node.nodeName || node.name || '节点' }}</span>
                    <el-tag
                      :type="getStatusType(node.status)"
                      size="small"
                    >
                      {{ getStatusLabel(node.status) }}
                    </el-tag>
                    <span class="node-duration">{{ formatDuration(getDurationMs(node)) }}</span>
                  </div>
                  <div class="node-details">
                    <div
                      v-if="node.inputData || node.input"
                      class="node-data"
                    >
                      <span class="data-label">输入:</span>
                      <code>{{ truncate(node.inputData || node.input) }}</code>
                    </div>
                    <div
                      v-if="node.outputData || node.output"
                      class="node-data"
                    >
                      <span class="data-label">输出:</span>
                      <ExecutionArtifactsPanel
                        :node-executions="[node]"
                        :node-name-map="detailNodeNameMap"
                        compact
                        :show-header="false"
                        empty-text="该节点无产物"
                      />
                    </div>
                    <div
                      v-if="node.errorMessage || node.error"
                      class="node-error"
                    >
                      <span class="data-label">错误:</span>
                      <code>{{ node.errorMessage || node.error }}</code>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <!-- Logs Tab -->
          <el-tab-pane
            label="日志"
            name="logs"
          >
            <div class="logs-container">
              <div
                v-for="(log, index) in selectedExecution.logs"
                :key="index"
                class="log-entry"
                :class="log.level"
              >
                <span class="log-time">{{ log.timestamp }}</span>
                <span class="log-level">{{ log.level.toUpperCase() }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Play, CheckCircle, XCircle, Clock, RefreshCw,
  Workflow, MoreHorizontal, RotateCcw, Copy, Calendar
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { workflowApi } from '@/api/workflow'
import ExecutionArtifactsPanel from '@/components/workflow/ExecutionArtifactsPanel.vue'
import {
  buildNodeNameMap,
  getExecutionArtifactSummary,
} from '@/utils/executionArtifacts'

const router = useRouter()
const appStore = useAppStore()

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const totalCount = ref(0)
const statusFilter = ref('')
const dateRange = ref([])
const showDetailDrawer = ref(false)
const selectedExecution = ref(null)
const detailTab = ref('artifacts')
const detailNodeNameMap = ref({})
const workflowNodeNameCache = ref({})

const ARTIFACT_BADGE_LABELS = {
  prompt: '词',
  image: '图',
  video: '视',
  audio: '音',
  website: '站',
  file: '文件',
  subtitle: '资料',
}

const stats = ref({
  total: 0,
  success: 0,
  failed: 0,
  avgDuration: 0
})

const executions = ref([])

const filteredExecutions = computed(() => {
  let result = executions.value

  if (statusFilter.value) {
    result = result.filter(e => e.status === statusFilter.value)
  }

  return result
})

const getStatusType = (status) => {
  const types = {
    completed: 'success',
    success: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info',
    cancelled: 'info',
    paused: 'warning'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    completed: '已完成',
    success: '成功',
    failed: '失败',
    running: '运行中',
    pending: '等待中',
    cancelled: '已取消',
    paused: '已暂停'
  }
  return labels[status] || status
}

function getDurationMs(row) {
  if (!row) return null
  if (row.durationMs != null) return row.durationMs
  if (row.durationSeconds != null) return Math.round(Number(row.durationSeconds) * 1000)
  if (row.duration != null) return Math.round(Number(row.duration) * 1000)
  return null
}

function getExecutionInput(execution) {
  return execution?.inputData ?? execution?.input ?? null
}

function getExecutionOutput(execution) {
  return execution?.outputData ?? execution?.output ?? null
}

function getRowArtifactSummary(row) {
  return getExecutionArtifactSummary(row)
}

function getRowArtifactBadges(row) {
  const { counts } = getRowArtifactSummary(row)
  return Object.entries(counts).map(([id, count]) => ({
    id,
    count,
    label: ARTIFACT_BADGE_LABELS[id] || id,
  }))
}

async function loadNodeNameMap(workflowId) {
  if (!workflowId) return {}
  if (workflowNodeNameCache.value[workflowId]) {
    return workflowNodeNameCache.value[workflowId]
  }
  try {
    const nodes = await workflowApi.getWorkflowNodes(workflowId)
    const list = Array.isArray(nodes) ? nodes : (nodes?.results || [])
    const map = buildNodeNameMap(list)
    workflowNodeNameCache.value[workflowId] = map
    return map
  } catch {
    return {}
  }
}

function getNodeExecutions(execution) {
  return execution?.nodeExecutions ?? execution?.node_executions ?? []
}

const getTriggerLabel = (type) => {
  const labels = { manual: '手动', schedule: '定时', webhook: 'Webhook', api: 'API' }
  return labels[type] || type
}

const formatDuration = (ms) => {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`
}

const formatDateTime = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const formatJson = (obj) => {
  if (!obj) return 'null'
  return JSON.stringify(obj, null, 2)
}

const truncate = (str) => {
  if (!str) return '-'
  const s = typeof str === 'string' ? str : JSON.stringify(str)
  return s.length > 100 ? s.slice(0, 100) + '...' : s
}

const viewDetails = async (execution) => {
  selectedExecution.value = execution
  detailTab.value = 'artifacts'
  showDetailDrawer.value = true
  const workflowId = execution.workflowId || execution.workflow || execution.workflow_id
  detailNodeNameMap.value = await loadNodeNameMap(workflowId)
  try {
    const timeline = await workflowApi.getExecutionTimeline(execution.id, { skipErrorToast: true })
    const detail = timeline?.execution
      ? null
      : await workflowApi.getExecution(execution.id, { skipErrorToast: true }).catch(() => null)
    selectedExecution.value = {
      ...execution,
      ...(detail || {}),
      ...(timeline?.execution || {}),
      nodeExecutions: timeline?.nodeExecutions ?? timeline?.node_executions ?? [],
      logs: timeline?.logs ?? [],
      nodeStatus: timeline?.execution?.node_status || timeline?.execution?.nodeStatus || execution.nodeStatus,
      outputData: timeline?.execution?.output_data || timeline?.execution?.outputData || execution.outputData,
    }
  } catch {
    appStore.error('加载执行详情失败')
  }
}

const replayExecution = (execution) => {
  ElMessageBox.confirm(
    `确定要重新执行此工作流吗？这将使用相同的输入参数重新运行「${execution.workflowName || execution.workflow?.name || '工作流'}」。`,
    '重放执行',
    { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
  ).then(() => {
    router.push({ path: `/workflows/${execution.workflowId || execution.workflow}/execute`, query: { replay: execution.id } })
  })
}

const copyInput = (execution) => {
  navigator.clipboard.writeText(JSON.stringify(getExecutionInput(execution), null, 2))
  appStore.success('输入已复制')
}

const copyOutput = (execution) => {
  navigator.clipboard.writeText(JSON.stringify(getExecutionOutput(execution), null, 2))
  appStore.success('输出已复制')
}

const copyToClipboard = (data) => {
  navigator.clipboard.writeText(typeof data === 'string' ? data : JSON.stringify(data, null, 2))
  appStore.success('已复制到剪贴板')
}

// ==================== API Integration ====================

async function fetchExecutions() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const response = await workflowApi.getAllExecutions(params)
    executions.value = response.results || response || []
    totalCount.value = response.count || executions.value.length

    const durations = executions.value.map(getDurationMs).filter(v => v != null)
    if (durations.length > 0) {
      stats.value.avgDuration = durations.reduce((sum, ms) => sum + ms, 0) / durations.length
    }
  } catch {
    // Error shown via API interceptor
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const response = await workflowApi.getExecutionStatistics()
    const byStatus = response.byStatus || []
    const statusMap = Object.fromEntries(byStatus.map(s => [s.status, s.count]))
    stats.value = {
      total: response.totalExecutions || 0,
      success: response.completedCount ?? statusMap.completed ?? 0,
      failed: statusMap.failed ?? 0,
      avgDuration: stats.value.avgDuration || 0
    }
  } catch {
    // Error shown via API interceptor
  }
}

async function deleteExecutionById(execId) {
  ElMessageBox.confirm('确定要删除此执行记录吗？', '删除', { type: 'warning' })
    .then(async () => {
      try {
        await workflowApi.deleteExecution(execId)
        executions.value = executions.value.filter(e => e.id !== execId)
        appStore.success('删除成功')
      } catch {
        // Error shown via API interceptor
      }
    })
}

function refreshData() {
  fetchExecutions()
  fetchStats()
}

// Initial data fetch
fetchExecutions()
fetchStats()

const deleteExecution = (execution) => {
  deleteExecutionById(execution.id)
}

const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  fetchExecutions()
}

const handlePageChange = (val) => {
  currentPage.value = val
  fetchExecutions()
}
</script>

<style lang="scss" scoped>
.execution-history-page {
  padding: 24px;
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
  }

  .subtitle {
    margin: 8px 0 0;
    color: var(--el-text-color-secondary);
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 12px;

  .stat-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;

    .icon {
      width: 24px;
      height: 24px;
      color: white;
    }
  }

  .stat-info {
    display: flex;
    flex-direction: column;

    .stat-value {
      font-size: 24px;
      font-weight: 700;
    }

    .stat-label {
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.execution-list {
  .execution-id {
    display: flex;
    align-items: center;
    gap: 8px;

    code {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
    }
  }

  .workflow-cell {
    display: flex;
    align-items: center;
    gap: 8px;

    .workflow-icon {
      width: 16px;
      height: 16px;
      color: var(--el-text-color-secondary);
    }

    .workflow-name {
      font-weight: 500;
    }
  }

  .artifact-summary-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 36px;
  }

  .artifact-thumb {
    width: 36px;
    height: 36px;
    border-radius: 6px;
    object-fit: cover;
    background: rgba(0, 0, 0, 0.2);
    flex-shrink: 0;
  }

  .artifact-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }

  .artifact-badge {
    font-size: 11px;
    line-height: 1;
    padding: 3px 6px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    color: var(--el-text-color-secondary);
    white-space: nowrap;

    &.badge-image { color: #67e8f9; }
    &.badge-video { color: #c4b5fd; }
    &.badge-prompt { color: #fcd34d; }
    &.badge-audio { color: #86efac; }
    &.badge-file { color: #fdba74; }
  }

  .artifact-empty-hint {
    color: var(--el-text-color-placeholder);
    font-size: 13px;
  }

  .duration, .trigger, .time {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.execution-detail {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--el-border-color);

    h3 {
      margin: 0 0 8px;
      font-size: 18px;
    }

    .meta-info {
      display: flex;
      align-items: center;
      gap: 12px;

      .meta-item {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
        color: var(--el-text-color-secondary);

        .meta-icon {
          width: 14px;
          height: 14px;
        }
      }
    }
  }
}

.data-section {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;

    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }
  }

  .data-content {
    padding: 16px;
    background: var(--code-bg);
    border: 1px solid var(--code-border);
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--code-text);
    overflow-x: auto;
    max-height: 400px;
    overflow-y: auto;
  }
}

.node-timeline {
  .node-item {
    display: flex;
    gap: 16px;
    padding-bottom: 24px;

    &.failed .marker-dot {
      background: var(--el-color-danger);
    }

    &.running .marker-dot {
      background: var(--el-color-warning);
      animation: pulse 1.5s infinite;
    }

    .node-timeline-marker {
      display: flex;
      flex-direction: column;
      align-items: center;

      .marker-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--el-color-success);
        flex-shrink: 0;
      }

      .marker-line {
        width: 2px;
        flex: 1;
        background: var(--el-border-color);
        margin-top: 4px;
      }
    }

    .node-content {
      flex: 1;
      padding-bottom: 8px;

      .node-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;

        .node-name {
          font-weight: 600;
        }

        .node-duration {
          margin-left: auto;
          font-size: 13px;
          color: var(--el-text-color-secondary);
        }
      }

      .node-details {
        .node-data {
          font-size: 13px;
          color: var(--el-text-color-secondary);
          margin-bottom: 4px;

          .data-label {
            font-weight: 500;
            margin-right: 4px;
          }

          code {
            font-family: 'JetBrains Mono', monospace;
            background: var(--el-fill-color-light);
            padding: 2px 6px;
            border-radius: 4px;
          }
        }

        .node-error {
          font-size: 13px;
          color: var(--error);

          code {
            font-family: 'JetBrains Mono', monospace;
            background: var(--error-bg);
            padding: 2px 6px;
            border-radius: 4px;
          }
        }
      }
    }
  }
}

.logs-container {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  padding: 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;

  .log-entry {
    display: flex;
    gap: 12px;
    padding: 4px 0;
    color: var(--code-text);
    transition: background-color 0.2s ease;

    &:hover {
      background: var(--surface-muted);
    }

    &.error {
      color: var(--error);
    }

    &.warning {
      color: var(--warning);
    }

    .log-time {
      color: var(--code-muted);
      flex-shrink: 0;
    }

    .log-level {
      width: 50px;
      flex-shrink: 0;
      font-weight: 600;
    }

    .log-message {
      flex: 1;
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
