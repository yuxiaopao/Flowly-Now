<template>
  <div class="execution-history">
    <div class="history-header">
      <h3 class="history-title">
        执行历史
      </h3>
      <div class="header-actions">
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          size="small"
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
          <el-option
            label="已取消"
            value="cancelled"
          />
        </el-select>
        <el-button
          size="small"
          :loading="isLoading"
          @click="handleRefresh"
        >
          <RefreshCw class="btn-icon" />
          刷新
        </el-button>
      </div>
    </div>

    <div
      v-if="isLoading && executions.length === 0"
      class="loading-state"
    >
      <el-skeleton
        :rows="5"
        animated
      />
    </div>

    <div
      v-else-if="executions.length === 0"
      class="empty-state"
    >
      <PlayCircle class="empty-icon" />
      <p>暂无执行记录</p>
    </div>

    <div
      v-else
      class="history-list"
    >
      <div
        v-for="execution in executions"
        :key="execution.id"
        :class="['execution-item', `status-${execution.status}`]"
        @click="$emit('select', execution)"
      >
        <div class="execution-main">
          <div class="execution-info">
            <span class="execution-id">#{{ execution.id }}</span>
            <el-tag
              :type="getStatusType(execution.status)"
              size="small"
            >
              {{ getStatusLabel(execution.status) }}
            </el-tag>
          </div>
          <div class="execution-meta">
            <span class="meta-item">
              <Clock class="meta-icon" />
              {{ formatDateTime(execution.started_at) }}
            </span>
            <span
              v-if="execution.duration"
              class="meta-item"
            >
              <Timer class="meta-icon" />
              {{ formatDuration(execution.duration) }}
            </span>
            <span
              v-if="execution.triggered_by_name"
              class="meta-item"
            >
              <User class="meta-icon" />
              {{ execution.triggered_by_name }}
            </span>
          </div>
        </div>

        <div class="execution-actions">
          <el-button
            text
            size="small"
            @click.stop="$emit('view', execution)"
          >
            查看
          </el-button>
          <el-dropdown
            trigger="click"
            @command="(cmd) => handleCommand(cmd, execution)"
          >
            <el-button
              text
              circle
              size="small"
              @click.stop
            >
              <MoreHorizontal />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  command="retry"
                  :disabled="execution.status === 'running'"
                >
                  重试
                </el-dropdown-item>
                <el-dropdown-item
                  command="cancel"
                  :disabled="!['pending', 'running'].includes(execution.status)"
                >
                  取消
                </el-dropdown-item>
                <el-dropdown-item
                  command="delete"
                  divided
                >
                  删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div
          v-if="execution.error_message"
          class="execution-error"
        >
          <AlertCircle class="error-icon" />
          {{ execution.error_message }}
        </div>
      </div>
    </div>

    <div
      v-if="totalPages > 1"
      class="pagination"
    >
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalCount"
        layout="prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import {
  RefreshCw, PlayCircle, Clock, Timer, User,
  MoreHorizontal, AlertCircle
} from 'lucide-vue-next'

const props = defineProps({
  workflowId: {
    type: [Number, String],
    required: true
  }
})

const emit = defineEmits(['select', 'view', 'refresh'])

const workflowStore = useWorkflowStore()
const appStore = useAppStore()

  const currentPage = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref('')
  const statusFilterLabel = ref('全部')

const isLoading = computed(() => workflowStore.isLoading)

const executions = computed(() => {
  const history = workflowStore.executionHistory
  if (!statusFilter.value) return history
  return history.filter(e => e.status === statusFilter.value)
})

const totalCount = computed(() => executions.value.length)
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

onMounted(() => {
  fetchHistory()
})

watch(() => props.workflowId, () => {
  fetchHistory()
})

async function fetchHistory() {
  try {
    await workflowStore.fetchExecutionHistory(props.workflowId)
  } catch (err) {
    appStore.error('获取执行历史失败')
  }
}

function handleRefresh() {
  currentPage.value = 1
  fetchHistory()
  emit('refresh')
}

function handleFilterChange() {
  currentPage.value = 1
  // Filter is applied via computed property `executions`
}

function handlePageChange(page) {
  currentPage.value = page
  fetchHistory()
}

async function handleCommand(command, execution) {
  switch (command) {
    case 'retry':
      await handleRetry(execution)
      break
    case 'cancel':
      await handleCancel(execution)
      break
    case 'delete':
      await handleDelete(execution)
      break
  }
}

async function handleRetry(execution) {
  try {
    await workflowStore.execute(execution.workflow_id, { retry_from: execution.id })
    appStore.success('重试已启动')
    handleRefresh()
  } catch (err) {
    appStore.error('重试失败: ' + (err.message || '未知错误'))
  }
}

async function handleCancel(execution) {
  try {
    await workflowStore.cancelExecution(execution.id)
    appStore.success('执行已取消')
    handleRefresh()
  } catch (err) {
    appStore.error('取消失败: ' + (err.message || '未知错误'))
  }
}

async function handleDelete(execution) {
  try {
    await workflowStore.deleteExecution(execution.id)
    appStore.success('记录已删除')
    handleRefresh()
  } catch (err) {
    appStore.error('删除失败: ' + (err.message || '未知错误'))
  }
}

function getStatusType(status) {
  const typeMap = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return typeMap[status] || 'info'
}

function getStatusLabel(status) {
  const labelMap = {
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labelMap[status] || status
}

function formatDateTime(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds) {
  if (!seconds) return '-'
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
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.execution-history {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-4;
}

.history-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: $spacing-2;
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.loading-state {
  padding: $spacing-4;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: $spacing-8;
  text-align: center;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--text-tertiary);
    margin-bottom: $spacing-4;
  }

  p {
    color: var(--text-secondary);
    margin: 0;
  }
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-3;
}

.execution-item {
  display: flex;
  flex-direction: column;
  padding: $spacing-4;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-lg;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    border-color: var(--border-hover);
  }

  &.status-running {
    border-left: 3px solid $color-warning;
  }

  &.status-completed {
    border-left: 3px solid $color-success;
  }

  &.status-failed {
    border-left: 3px solid $color-error;
  }
}

.execution-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.execution-info {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.execution-id {
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
}

.execution-meta {
  display: flex;
  gap: $spacing-4;
  margin-top: $spacing-2;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: $spacing-1;
  font-size: $font-size-xs;
  color: var(--text-tertiary);
}

.meta-icon {
  width: 12px;
  height: 12px;
}

.execution-actions {
  display: flex;
  gap: $spacing-2;
}

.execution-error {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  margin-top: $spacing-3;
  padding: $spacing-2 $spacing-3;
  background-color: rgba($color-error, 0.1);
  border-radius: $radius-md;
  font-size: $font-size-xs;
  color: $color-error;
}

.error-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: $spacing-4;
}
</style>
