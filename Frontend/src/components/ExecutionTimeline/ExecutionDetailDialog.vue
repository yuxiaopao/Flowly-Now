<template>
  <el-dialog
    v-model="dialogVisible"
    :title="`执行详情 #${executionId}`"
    width="900px"
    top="5vh"
    class="execution-detail-dialog"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <div
      v-if="isLoadingExecution"
      v-loading="true"
      class="execution-loading"
      element-loading-text="加载执行详情..."
    />

    <el-empty
      v-else-if="loadError"
      :description="loadError"
    >
      <el-button
        type="primary"
        @click="loadExecutionData"
      >
        重试
      </el-button>
    </el-empty>

    <el-empty
      v-else-if="!execution"
      description="暂无执行详情"
    />

    <template v-else>
      <!-- Execution Status Header -->
      <div class="execution-status-bar">
        <div class="status-info">
          <span
            class="status-badge large"
            :class="execution?.status"
          >
            <span class="status-icon">
              <Loader
                v-if="execution?.status === 'running'"
                class="spin"
              />
              <CheckCircle v-else-if="execution?.status === 'completed'" />
              <XCircle v-else-if="execution?.status === 'failed'" />
              <Pause v-else-if="execution?.status === 'paused'" />
              <Clock v-else />
            </span>
            {{ statusLabel(execution?.status) }}
          </span>
          <span class="execution-id">#{{ executionId }}</span>
          <span
            v-if="execution?.workflowName || execution?.workflow_name"
            class="workflow-name"
          >
            <Workflow class="workflow-icon" />
            {{ execution.workflowName || execution.workflow_name }}
          </span>
        </div>
        <div class="action-buttons">
          <el-button
            v-if="execution?.status === 'running'"
            type="warning"
            @click="handlePause"
          >
            <Pause class="btn-icon" />
            暂停
          </el-button>
          <el-button
            v-if="execution?.status === 'paused'"
            type="success"
            @click="handleResume"
          >
            <Play class="btn-icon" />
            继续
          </el-button>
          <el-button
            v-if="['running', 'pending'].includes(execution?.status)"
            type="danger"
            @click="handleCancel"
          >
            <Square class="btn-icon" />
            取消
          </el-button>
          <el-button
            v-if="execution?.status === 'failed'"
            type="primary"
            @click="handleRetry"
          >
            <RotateCcw class="btn-icon" />
            重试
          </el-button>
          <el-button @click="downloadLogs">
            <Download class="btn-icon" />
            下载日志
          </el-button>
        </div>
      </div>

      <!-- Progress Section -->
      <div
        v-if="execution?.status === 'running' || execution?.status === 'pending'"
        class="progress-section"
      >
        <div class="progress-header">
          <span class="progress-label">执行进度</span>
          <span class="progress-percentage">{{ progressPercentage }}%</span>
        </div>
        <el-progress
          :percentage="progressPercentage"
          :status="progressStatus"
          :stroke-width="10"
          :duration="6"
        />
        <p class="progress-message">
          <span v-if="currentNodeName">正在执行: {{ currentNodeName }}</span>
          <span v-else>等待执行...</span>
        </p>
      </div>

      <!-- Node Status Overview -->
      <div class="node-status-overview">
        <div
          class="status-card"
          :class="{ active: true }"
        >
          <span class="status-count pending">{{ nodeStatusSummary.pending }}</span>
          <span class="status-label">待处理</span>
        </div>
        <div class="status-card">
          <span class="status-count running">{{ nodeStatusSummary.running }}</span>
          <span class="status-label">执行中</span>
        </div>
        <div class="status-card">
          <span class="status-count completed">{{ nodeStatusSummary.completed }}</span>
          <span class="status-label">已完成</span>
        </div>
        <div class="status-card">
          <span class="status-count failed">{{ nodeStatusSummary.failed }}</span>
          <span class="status-label">失败</span>
        </div>
        <div class="status-card">
          <span class="status-count skipped">{{ nodeStatusSummary.skipped }}</span>
          <span class="status-label">跳过</span>
        </div>
      </div>

      <!-- Tabs -->
      <el-tabs
        v-model="activeTab"
        class="execution-tabs"
      >
        <!-- Node Timeline Tab -->
        <el-tab-pane
          label="节点时间线"
          name="timeline"
        >
          <NodeExecutionTimeline
            v-if="execution"
            :nodes="executionNodes"
            :active-node-id="selectedNodeId"
            :is-running="execution?.status === 'running'"
            @node-click="handleNodeClick"
          />
          <el-empty
            v-else
            description="暂无节点数据"
          />
        </el-tab-pane>

        <!-- Node Detail Tab -->
        <el-tab-pane
          label="节点详情"
          name="node-detail"
        >
          <NodeExecutionDetail
            v-if="selectedNode"
            :node="selectedNode"
            :is-loading="isLoadingNodeDetail"
          />
          <el-empty
            v-else
            description="请从节点时间线选择一个节点查看详情"
          />
        </el-tab-pane>

        <!-- Input Tab -->
        <el-tab-pane
          label="输入数据"
          name="input"
        >
          <div class="data-viewer">
            <div class="data-header">
              <h4>输入参数</h4>
              <el-button
                size="small"
                text
                @click="copyToClipboard(executionInput)"
              >
                <Copy class="btn-icon-small" />
                复制
              </el-button>
            </div>
            <pre class="data-content"><code>{{ formatJson(executionInput) }}</code></pre>
          </div>
        </el-tab-pane>

        <!-- Output Tab -->
        <el-tab-pane
          label="输出数据"
          name="output"
        >
          <div class="data-viewer">
            <div class="data-header">
              <h4>执行结果</h4>
              <div class="header-actions">
                <span
                  v-if="execution?.tokens"
                  class="token-count"
                >
                  {{ execution.tokens.prompt || 0 }} tokens
                </span>
                <el-button
                  size="small"
                  text
                  @click="copyToClipboard(executionOutput)"
                >
                  <Copy class="btn-icon-small" />
                  复制
                </el-button>
              </div>
            </div>
            <pre
              v-if="executionOutput"
              class="data-content"
            ><code>{{ formatJson(executionOutput) }}</code></pre>
            <el-empty
              v-else-if="execution?.status === 'running'"
              description="执行中，输出暂不可用"
            />
            <el-empty
              v-else
              description="暂无输出数据"
            />
          </div>
        </el-tab-pane>

        <!-- Streaming Output Tab -->
        <el-tab-pane
          v-if="isStreaming"
          label="实时输出"
          name="streaming"
        >
          <StreamingOutputPanel
            :content="streamingContent"
            :is-streaming="isStreaming"
            :current-node="currentStreamingNode"
            @copy="copyToClipboard(streamingContent)"
          />
        </el-tab-pane>

        <!-- Logs Tab -->
        <el-tab-pane
          label="执行日志"
          name="logs"
        >
          <ExecutionLogsPanel
            :logs="executionLogs"
            :is-live="execution?.status === 'running'"
            :level-filter="logLevelFilter"
            @filter-change="logLevelFilter = $event"
            @clear="clearLogs"
            @download="downloadLogs"
          />
        </el-tab-pane>

        <!-- Error Tab -->
        <el-tab-pane
          v-if="execution?.error"
          label="错误信息"
          name="error"
        >
          <div class="error-viewer">
            <el-alert
              :title="execution.error"
              type="error"
              :closable="false"
              show-icon
            />
            <div
              v-if="execution?.traceback"
              class="traceback-section"
            >
              <div class="section-header">
                <h4>堆栈跟踪</h4>
                <el-button
                  size="small"
                  text
                  @click="copyToClipboard(execution.traceback)"
                >
                  <Copy class="btn-icon-small" />
                  复制
                </el-button>
              </div>
              <pre class="traceback-content">{{ execution.traceback }}</pre>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <template
      v-if="execution"
      #footer
    >
      <div class="dialog-footer">
        <div class="footer-left">
          <span class="execution-meta">
            <Clock class="meta-icon" />
            开始: {{ formatDateTime(execution?.startedAt || execution?.started_at) }}
          </span>
          <span
            v-if="execution?.duration != null || execution?.durationMs != null"
            class="execution-meta"
          >
            <Timer class="meta-icon" />
            耗时: {{ formatDuration(execution.durationMs != null ? execution.durationMs / 1000 : execution.duration) }}
          </span>
        </div>
        <div class="footer-right">
          <el-button @click="dialogVisible = false">
            关闭
          </el-button>
          <el-button
            v-if="execution?.status === 'completed'"
            type="primary"
            @click="handleReexecute"
          >
            <RotateCcw class="btn-icon" />
            重新执行
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Loader, CheckCircle, XCircle, Pause, Play, Square,
  RotateCcw, Download, Copy, Clock, Timer, Workflow
} from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeExecutionTimeline from '@/components/ExecutionTimeline/NodeExecutionTimeline.vue'
import NodeExecutionDetail from '@/components/NodeExecutionStatus/NodeExecutionDetail.vue'
import StreamingOutputPanel from '@/components/ExecutionTimeline/StreamingOutputPanel.vue'
import ExecutionLogsPanel from '@/components/ExecutionTimeline/ExecutionLogsPanel.vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  executionId: {
    type: [Number, String],
    default: null
  },
  execution: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'refresh', 'reexecute'])

const executionStore = useExecutionStore()

// Dialog visibility
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// State
const activeTab = ref('timeline')
const selectedNodeId = ref(null)
const isLoadingNodeDetail = ref(false)
const isLoadingExecution = ref(false)
const loadError = ref('')
const logLevelFilter = ref('all')
const streamingContent = ref('')
const isStreaming = computed(() => executionStore.isStreaming)
const currentStreamingNode = ref('')

// Polling fallback
let pollingInterval = null

// Computed
const execution = computed(() => {
  if (props.execution) return props.execution
  if (executionStore.currentExecution) return executionStore.currentExecution
  return null
})

const executionNodes = computed(() => {
  if (!execution.value) return []
  if (execution.value.nodes) return execution.value.nodes
  if (execution.value.nodeExecutions) return execution.value.nodeExecutions
  if (execution.value.node_executions) return execution.value.node_executions
  return []
})

const selectedNode = computed(() => {
  if (!selectedNodeId.value || !executionNodes.value.length) return null
  return executionNodes.value.find(n =>
    n.id === selectedNodeId.value ||
    n.nodeId === selectedNodeId.value ||
    n.node_id === selectedNodeId.value
  )
})

const executionInput = computed(() => {
  return execution.value?.input_data || execution.value?.inputData || execution.value?.input || {}
})

const executionOutput = computed(() => {
  return execution.value?.output_data || execution.value?.outputData || execution.value?.output || null
})

const executionLogs = computed(() => {
  return executionStore.executionLogs.length > 0
    ? executionStore.executionLogs
    : (execution.value?.logs || [])
})

const nodeStatusSummary = computed(() => {
  const nodes = executionNodes.value
  const summary = {
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
    skipped: 0
  }

  nodes.forEach(node => {
    const status = node.status || 'pending'
    if (Object.hasOwn(summary, status)) {
      summary[status]++
    }
  })

  return summary
})

const progressPercentage = computed(() => {
  const total = executionNodes.value.length
  if (total === 0) return 0
  const completed = nodeStatusSummary.value.completed + nodeStatusSummary.value.skipped
  return Math.round((completed / total) * 100)
})

const progressStatus = computed(() => {
  if (progressPercentage.value >= 100) return 'success'
  if (execution.value?.status === 'failed') return 'exception'
  return undefined
})

const currentNodeName = computed(() => {
  const runningNode = executionNodes.value.find(n => n.status === 'running')
  return runningNode?.name || ''
})

// Methods
function statusLabel(status) {
  const labels = {
    pending: '待处理',
    running: '执行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
    paused: '已暂停'
  }
  return labels[status] || status || '-'
}

function formatDateTime(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
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

function formatJson(data) {
  if (!data) return 'null'
  if (typeof data === 'string') {
    try {
      return JSON.stringify(JSON.parse(data), null, 2)
    } catch {
      return data
    }
  }
  return JSON.stringify(data, null, 2)
}

function copyToClipboard(text) {
  const content = typeof text === 'string' ? text : JSON.stringify(text, null, 2)
  navigator.clipboard.writeText(content)
    .then(() => ElMessage.success('已复制到剪贴板'))
    .catch(() => ElMessage.error('复制失败'))
}

function handleNodeClick(nodeId) {
  selectedNodeId.value = nodeId
  activeTab.value = 'node-detail'
}

async function handlePause() {
  try {
    await executionStore.pauseExecution(props.executionId)
    ElMessage.success('执行已暂停')
    emit('refresh')
  } catch (error) {
    ElMessage.error('暂停失败: ' + (error.message || '未知错误'))
  }
}

async function handleResume() {
  try {
    await executionStore.resumeExecution(props.executionId)
    ElMessage.success('执行已恢复')
    emit('refresh')
  } catch (error) {
    ElMessage.error('恢复失败: ' + (error.message || '未知错误'))
  }
}

async function handleCancel() {
  try {
    await executionStore.cancelExecution(props.executionId)
    ElMessage.warning('执行已取消')
    emit('refresh')
  } catch (error) {
    ElMessage.error('取消失败: ' + (error.message || '未知错误'))
  }
}

async function handleRetry() {
  try {
    await executionStore.retryExecution(props.executionId)
    ElMessage.success('重试已启动')
    emit('refresh')
  } catch (error) {
    ElMessage.error('重试失败: ' + (error.message || '未知错误'))
  }
}

function handleReexecute() {
  emit('reexecute', execution.value)
  dialogVisible.value = false
}

function clearLogs() {
  executionStore.executionLogs = []
}

function downloadLogs() {
  const logs = executionLogs.value
  const content = logs.map(log =>
    `[${log.timestamp || log.time}] [${log.level?.toUpperCase()}] [${log.node || log.nodeName}] ${log.message || log.text}`
  ).join('\n')

  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `execution_${props.executionId}_logs_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// WebSocket connection for real-time updates
function connectWebSocket() {
  if (!props.executionId) return

  disconnectWebSocket()

  try {
    executionStore.connectWebSocket(props.executionId)
  } catch (error) {
    // Fallback to polling on WebSocket failure
    startPolling()
  }
}

function disconnectWebSocket() {
  executionStore.disconnectWebSocket()
  stopPolling()
}

function startPolling() {
  if (pollingInterval) return
  pollingInterval = setInterval(async () => {
    if (props.executionId) {
      await executionStore.fetchExecutionDetails(props.executionId)
    }
  }, 3000)
}

function stopPolling() {
  if (pollingInterval) {
    clearInterval(pollingInterval)
    pollingInterval = null
  }
}

async function loadExecutionData() {
  if (!props.executionId) {
    loadError.value = '缺少执行 ID'
    return
  }

  isLoadingExecution.value = true
  loadError.value = ''

  try {
    await executionStore.fetchExecutionDetails(props.executionId)
    await executionStore.fetchExecutionLogs(props.executionId)
  } catch (error) {
    loadError.value = error?.message || '加载执行详情失败'
  } finally {
    isLoadingExecution.value = false
  }
}

// Watchers
watch(dialogVisible, async (val) => {
  if (val) {
    activeTab.value = 'timeline'
    selectedNodeId.value = null
    loadError.value = ''
    await loadExecutionData()
    if (props.executionId && !loadError.value) {
      connectWebSocket()
    }
  } else {
    disconnectWebSocket()
  }
})

watch(() => props.executionId, (val) => {
  if (val && dialogVisible.value) {
    connectWebSocket()
  }
})

// Lifecycle
onMounted(() => {
  if (props.executionId && dialogVisible.value) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style lang="scss" scoped>
.execution-loading {
  min-height: 240px;
}

.execution-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.status-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;

  .status-icon {
    display: flex;
    align-items: center;

    svg {
      width: 16px;
      height: 16px;
    }
  }

  &.pending {
    background: var(--surface-muted);
    color: var(--text-tertiary);
  }

  &.running {
    background: var(--info-bg);
    color: var(--info);
  }

  &.completed {
    background: var(--success-bg);
    color: var(--success);
  }

  &.failed {
    background: var(--error-bg);
    color: var(--error);
  }

  &.paused {
    background: var(--warning-bg);
    color: var(--warning);
  }

  &.large {
    padding: 8px 18px;
    font-size: 14px;
  }
}

.execution-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.workflow-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: var(--el-text-color-secondary);

  .workflow-icon {
    width: 16px;
    height: 16px;
  }
}

.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 14px;
  height: 14px;
  margin-right: 4px;
}

.progress-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;

  .progress-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;

    .progress-label {
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }

    .progress-percentage {
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }
  }

  .progress-message {
    margin: 8px 0 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    text-align: center;
  }
}

.node-status-overview {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.status-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px;
  background: var(--el-bg-color);
  border-radius: 8px;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
  }

  .status-count {
    font-size: 24px;
    font-weight: 700;

    &.pending { color: var(--text-tertiary); }
    &.running { color: var(--info); }
    &.completed { color: var(--success); }
    &.failed { color: var(--error); }
    &.skipped { color: var(--text-tertiary); }
  }

  .status-label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }
}

.execution-tabs {
  margin-top: 16px;
}

.data-viewer {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  overflow: hidden;

  .data-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: var(--el-fill-color);

    h4 {
      margin: 0;
      font-size: 14px;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;

      .token-count {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .data-content {
    padding: 16px;
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    max-height: 400px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

.error-viewer {
  .traceback-section {
    margin-top: 16px;

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      h4 {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
      }
    }

    .traceback-content {
      padding: 16px;
      background: var(--el-fill-color-dark);
      border-radius: 8px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 300px;
      overflow: auto;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .footer-left {
    display: flex;
    gap: 16px;
  }

  .footer-right {
    display: flex;
    gap: 8px;
  }

  .execution-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--el-text-color-secondary);

    .meta-icon {
      width: 14px;
      height: 14px;
    }
  }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
