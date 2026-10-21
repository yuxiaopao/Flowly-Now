<template>
  <PageShell
    width="wide"
    class="execution-history-page"
  >
    <PageHeader
      title="执行历史"
      subtitle="查看和回放工作流执行记录"
    >
      <template #actions>
        <el-button @click="refreshData">
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </template>
    </PageHeader>

    <PageToolbar>
      <el-select
        v-model="statusFilter"
        placeholder="状态"
        clearable
        class="filter-control"
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
        class="date-control"
      />
    </PageToolbar>

    <!-- Statistics Cards -->
    <StatGrid>
      <StatCard
        label="总执行次数"
        :value="stats.total"
        :icon="Play"
        tone="primary"
        :loading="loading"
      />
      <StatCard
        label="成功"
        :value="stats.success"
        :icon="CheckCircle"
        tone="success"
        :loading="loading"
      />
      <StatCard
        label="失败"
        :value="stats.failed"
        :icon="XCircle"
        tone="danger"
        :loading="loading"
      />
      <StatCard
        label="平均耗时"
        :value="formatDuration(stats.avgDuration)"
        :icon="Clock"
        tone="warning"
        :loading="loading"
      />
    </StatGrid>

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
              <el-tag
                v-if="getMediaExecutionLabel(row)"
                type="info"
                size="small"
              >
                {{ getMediaExecutionLabel(row) }}
              </el-tag>
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
  </PageShell>
</template>

<script setup>
import StatCard from '@/components/layout/StatCard.vue'
import StatGrid from '@/components/layout/StatGrid.vue'
import PageToolbar from '@/components/layout/PageToolbar.vue'
import PageHeader from '@/components/layout/PageHeader.vue'
import PageShell from '@/components/layout/PageShell.vue'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  Play, CheckCircle, XCircle, Clock, RefreshCw,
  Workflow, MoreHorizontal, RotateCcw
} from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { workflowApi } from '@/api/workflow'
import { getMediaExecutionLabel } from '@/config/executionMedia'
import {
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

function extractWorkflowId(execution) {
  const nested = execution?.workflow
  if (typeof nested === 'string' || typeof nested === 'number') return String(nested)
  if (nested && typeof nested === 'object') {
    const nestedId = nested.id || nested.pk
    if (nestedId) return String(nestedId)
  }
  const direct = execution?.workflowId || execution?.workflow_id
  if (direct && typeof direct !== 'object') return String(direct)
  return ''
}

const viewDetails = (execution) => {
  router.push(`/executions/${execution.id}`)
}

const replayExecution = (execution) => {
  const workflowId = extractWorkflowId(execution)
  if (!workflowId) {
    appStore.error('无法定位该执行对应的工作流')
    return
  }
  router.push({
    path: `/workflows/${workflowId}/edit`,
    query: { execution: execution.id },
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

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-icon-small {
  width: 14px;
  height: 14px;
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

</style>
