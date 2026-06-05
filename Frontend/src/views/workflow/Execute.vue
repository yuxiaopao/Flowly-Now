<template>
  <div class="workflow-execute">
    <div class="execute-container">
      <!-- 顶部信息栏 -->
      <header class="execute-header">
        <div class="header-left">
          <el-button
            :icon="ArrowLeft"
            @click="handleBack"
          >
            返回
          </el-button>
          <div class="workflow-info">
            <h1 class="workflow-name">
              {{ workflow?.name || '执行工作流' }}
            </h1>
            <span
              v-if="executionId"
              class="execution-id"
            >执行 ID: {{ executionId }}</span>
          </div>
        </div>
        <div class="header-actions">
          <el-button
            v-if="isRunning"
            type="danger"
            @click="handleCancel"
          >
            取消执行
          </el-button>
          <el-button
            v-if="executionStatus === 'completed' || executionStatus === 'failed'"
            @click="handleRetry"
          >
            <RefreshCw class="btn-icon" />
            重试
          </el-button>
          <el-button
            :disabled="!outputData"
            @click="handleSaveOutput"
          >
            <Download class="btn-icon" />
            导出结果
          </el-button>
        </div>
      </header>

      <div class="execute-content">
        <!-- 左侧：输入参数 -->
        <aside class="input-panel">
          <h3 class="panel-title">
            输入参数
          </h3>

          <el-form
            ref="inputFormRef"
            :model="inputData"
            label-position="top"
          >
            <el-form-item
              v-for="param in inputParams"
              :key="param.name"
              :label="param.label || param.name"
            >
              <el-input
                v-if="param.type === 'string' || !param.type"
                v-model="inputData[param.name]"
                :placeholder="param.placeholder || `输入 ${param.label || param.name}`"
                :disabled="isRunning"
              />
              <el-input-number
                v-else-if="param.type === 'number'"
                v-model="inputData[param.name]"
                :disabled="isRunning"
              />
              <el-switch
                v-else-if="param.type === 'boolean'"
                v-model="inputData[param.name]"
              />
              <el-input
                v-else-if="param.type === 'textarea'"
                v-model="inputData[param.name]"
                type="textarea"
                :rows="3"
                :disabled="isRunning"
              />
            </el-form-item>
          </el-form>

          <div class="panel-actions">
            <AppButton
              variant="primary"
              :loading="isRunning"
              :disabled="!canExecute"
              @click="handleExecute"
            >
              <Play class="btn-icon" />
              {{ isRunning ? '执行中...' : '开始执行' }}
            </AppButton>
          </div>

          <!-- 执行历史 -->
          <div class="history-section">
            <h4 class="section-title">
              执行历史
            </h4>
            <div class="history-list">
              <div
                v-for="item in executionHistory"
                :key="item.id"
                :class="['history-item', `status-${item.status}`]"
                @click="loadExecution(item.id)"
              >
                <span class="history-time">{{ formatDate(item.started_at) }}</span>
                <el-tag
                  :type="getStatusType(item.status)"
                  size="small"
                >
                  {{ getStatusLabel(item.status) }}
                </el-tag>
              </div>
              <div
                v-if="executionHistory.length === 0"
                class="no-history"
              >
                暂无执行记录
              </div>
            </div>
          </div>
        </aside>

        <!-- 中间：执行状态和输出 -->
        <main class="output-panel">
          <div class="panel-header">
            <h3 class="panel-title">
              执行状态
            </h3>
            <div class="status-info">
              <el-tag
                v-if="executionStatus"
                :type="getStatusType(executionStatus)"
              >
                {{ getStatusLabel(executionStatus) }}
              </el-tag>
              <span
                v-if="executionDuration"
                class="duration"
              >
                {{ executionDuration }}
              </span>
            </div>
          </div>

          <!-- 执行进度 -->
          <div class="execution-progress">
            <el-steps
              :active="currentStep"
              finish-status="success"
              align-center
            >
              <el-step title="准备" />
              <el-step title="执行中" />
              <el-step title="完成" />
            </el-steps>
          </div>

          <!-- 节点执行状态 -->
          <div class="node-status-list">
            <div
              v-for="(status, nodeId) in nodeStatus"
              :key="nodeId"
              :class="['node-status-item', `status-${status.status}`]"
            >
              <div class="node-info">
                <component
                  :is="getNodeIcon(status.type)"
                  class="node-icon"
                />
                <span class="node-name">{{ status.name }}</span>
                <span
                  v-if="status.duration"
                  class="node-duration"
                >{{ status.duration }}s</span>
              </div>
              <div class="node-status">
                <el-tag
                  v-if="status.status === 'running'"
                  type="warning"
                  size="small"
                  :loading="true"
                >
                  运行中
                </el-tag>
                <el-tag
                  v-else-if="status.status === 'completed'"
                  type="success"
                  size="small"
                >
                  完成
                </el-tag>
                <el-tag
                  v-else-if="status.status === 'failed'"
                  type="danger"
                  size="small"
                >
                  失败
                </el-tag>
                <el-tag
                  v-else
                  type="info"
                  size="small"
                >
                  等待中
                </el-tag>
              </div>
              <div
                v-if="status.error"
                class="node-error"
              >
                {{ status.error }}
              </div>
            </div>
            <div
              v-if="Object.keys(nodeStatus).length === 0"
              class="no-nodes"
            >
              点击"开始执行"按钮开始执行工作流
            </div>
          </div>

          <!-- 输出结果 -->
          <div class="output-section">
            <div class="section-header">
              <h4>输出结果</h4>
              <div class="section-actions">
                <el-button
                  text
                  size="small"
                  :disabled="!outputData"
                  @click="copyOutput"
                >
                  <Copy class="btn-icon-sm" />
                  复制
                </el-button>
              </div>
            </div>
            <div
              ref="outputContainer"
              class="output-content"
            >
              <!-- 流式输出 -->
              <div
                v-if="streamingOutput"
                class="streaming-output"
              >
                <pre>{{ streamingOutput }}</pre>
                <span class="cursor">|</span>
              </div>
              <pre v-else-if="formattedOutput">{{ formattedOutput }}</pre>
              <p
                v-else
                class="no-output"
              >
                暂无输出
              </p>
            </div>
          </div>

          <!-- 错误信息 -->
          <div
            v-if="errorMessage"
            class="error-section"
          >
            <div class="section-header">
              <h4>错误信息</h4>
              <el-button
                text
                size="small"
                @click="showFullError = true"
              >
                详细
              </el-button>
            </div>
            <div class="error-content">
              <pre>{{ errorMessage }}</pre>
            </div>
          </div>
        </main>

        <!-- 右侧：日志 -->
        <aside class="log-panel">
          <div class="panel-header">
            <h3 class="panel-title">
              执行日志
            </h3>
            <div class="panel-actions">
              <el-button
                text
                size="small"
                @click="autoScroll = !autoScroll"
              >
                {{ autoScroll ? '自动滚动' : '固定' }}
              </el-button>
              <el-button
                text
                size="small"
                @click="clearLogs"
              >
                清除
              </el-button>
            </div>
          </div>
          <div
            ref="logContainer"
            class="log-content"
          >
            <div
              v-for="(log, index) in logs"
              :key="index"
              :class="['log-item', `log-${log.level}`]"
            >
              <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
              <span class="log-message">{{ log.message }}</span>
            </div>
            <div
              v-if="logs.length === 0"
              class="no-logs"
            >
              暂无日志
            </div>
          </div>
        </aside>
      </div>
    </div>

    <!-- 错误详情对话框 -->
    <el-dialog
      v-model="showFullError"
      title="错误详情"
      width="600px"
      :close-on-click-modal="false"
      :close-on-press-escape="true"
    >
      <pre class="error-detail">{{ errorMessage }}</pre>
      <template #footer>
        <el-button @click="showFullError = false">
          关闭
        </el-button>
        <el-button
          type="primary"
          @click="copyError"
        >
          复制错误信息
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import { workflowApi } from '@/api/workflow'
import {
  ArrowLeft, Play, RefreshCw, Copy, Download,
  PlayCircle, MessageSquare, GitBranch, Hammer,
  User, FileText, Zap, Circle
} from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const appStore = useAppStore()

const workflowId = computed(() => route.params.id)

const workflow = computed(() => workflowStore.currentWorkflow)
const isRunning = computed(() => executionStatus.value === 'running')
const canExecute = computed(() => workflow.value?.id)

const executionId = ref(null)
const executionStatus = ref(null)
const executionDuration = ref(null)
const nodeStatus = ref({})
const outputData = ref(null)
const streamingOutput = ref('')
const errorMessage = ref('')
const executionHistory = ref([])

const inputFormRef = ref(null)
const outputContainer = ref(null)
const logContainer = ref(null)
const showFullError = ref(false)
const autoScroll = ref(true)

// 输入参数
const inputParams = ref([
  { name: 'input', label: '输入文本', type: 'textarea', placeholder: '输入要处理的文本...' }
])

const inputData = reactive({})

// 日志
const logs = ref([])

// WebSocket 连接
let ws = null

const currentStep = computed(() => {
  if (!executionStatus.value) return 0
  if (executionStatus.value === 'pending') return 0
  if (executionStatus.value === 'running') return 1
  return 2
})

const formattedOutput = computed(() => {
  if (!outputData.value) return ''
  if (typeof outputData.value === 'string') return outputData.value

  // Extract text from node_outputs if available
  const nodeOutputs = outputData.value.nodeOutputs || outputData.value.node_outputs
  if (nodeOutputs && typeof nodeOutputs === 'object') {
    const texts = Object.values(nodeOutputs)
      .map(o => (typeof o === 'object' && o.text) ? o.text : null)
      .filter(Boolean)
    if (texts.length > 0) return texts.join('\n\n')
  }

  return JSON.stringify(outputData.value, null, 2)
})

onMounted(async () => {
  try {
    await workflowStore.fetchWorkflow(workflowId.value)
    await fetchExecutionHistory()
  } catch (err) {
    appStore.error('加载工作流失败')
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})

async function fetchExecutionHistory() {
  try {
    const response = await workflowApi.getExecutionHistory(workflowId.value)
    executionHistory.value = response.results || response || []
  } catch {
    // Error shown via appStore notification
  }
}

async function loadExecution(execId) {
  try {
    const response = await workflowApi.getExecution(execId)
    executionId.value = response.id
    executionStatus.value = response.status
    outputData.value = response.output_data
    nodeStatus.value = response.node_status || {}
    errorMessage.value = response.error_message || ''

    if (response.started_at && response.completed_at) {
      const start = new Date(response.started_at)
      const end = new Date(response.completed_at)
      executionDuration.value = ((end - start) / 1000).toFixed(2)
    }
  } catch (err) {
    appStore.error('加载执行记录失败')
  }
}

async function handleExecute() {
  clearExecutionState()
  addLog('info', '开始执行工作流...')
  addLog('info', `输入参数: ${JSON.stringify(inputData)}`)

  try {
    const response = await workflowApi.execute(workflowId.value, inputData)

    executionId.value = response.executionId || response.execution_id
    addLog('info', `执行 ID: ${executionId.value}`)

    // 获取到 executionId 后再连接 WebSocket
    if (executionId.value) {
      connectWebSocket()
    }

    // 如果是异步执行，等待结果
    if (response.taskId || response.task_id) {
      addLog('info', '工作流已加入执行队列')
      await pollExecutionStatus(executionId.value)
    } else {
      executionStatus.value = response.status
      outputData.value = response.outputData || response.output_data
      if (response.error) {
        errorMessage.value = response.error
        addLog('error', `执行失败: ${response.error}`)
      } else {
        addLog('success', '工作流执行完成')
      }
    }
  } catch (err) {
    addLog('error', `执行失败: ${err.message}`)
    appStore.error('执行失败')
    disconnectWebSocket()
  }
}

async function pollExecutionStatus(execId) {
  const maxPolls = 300 // 5 分钟超时
  let polls = 0

  const poll = async () => {
    if (polls >= maxPolls) {
      addLog('error', '执行超时')
      return
    }

    try {
      const response = await workflowApi.getExecution(execId)
      executionStatus.value = response.status
      nodeStatus.value = response.node_status || {}

      if (response.status === 'completed') {
        outputData.value = response.output_data
        addLog('success', '工作流执行完成')
        disconnectWebSocket()
      } else if (response.status === 'failed') {
        errorMessage.value = response.error_message || '未知错误'
        addLog('error', `执行失败: ${errorMessage.value}`)
        disconnectWebSocket()
      } else {
        polls++
        setTimeout(poll, 1000)
      }
    } catch (err) {
      polls++
      setTimeout(poll, 2000)
    }
  }

  await poll()
}

function connectWebSocket() {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/execution/${executionId.value || ''}/`

  try {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      addLog('info', 'WebSocket 连接已建立')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      } catch (err) {
        console.error('WebSocket 消息解析失败', err)
      }
    }

    ws.onerror = (err) => {
      addLog('error', 'WebSocket 连接错误')
    }

    ws.onclose = () => {
      addLog('info', 'WebSocket 连接已关闭')
    }
  } catch (err) {
    console.error('WebSocket 连接失败', err)
  }
}

function disconnectWebSocket() {
  if (ws) {
    ws.close()
    ws = null
  }
}

function handleWebSocketMessage(data) {
  switch (data.type) {
    case 'execution_start':
      executionStatus.value = 'running'
      addLog('info', '执行已开始')
      break

    case 'node_start':
      nodeStatus.value = {
        ...nodeStatus.value,
        [data.node_id]: {
          ...nodeStatus.value[data.node_id],
          status: 'running',
          name: data.node_name,
          type: data.node_type
        }
      }
      addLog('info', `开始执行节点: ${data.node_name}`)
      break

    case 'node_complete':
      nodeStatus.value = {
        ...nodeStatus.value,
        [data.node_id]: {
          ...nodeStatus.value[data.node_id],
          status: data.status,
          output: data.output
        }
      }
      addLog('success', `节点执行完成: ${data.node_name}`)
      break

    case 'stream_output':
      if (data.text) {
        streamingOutput.value += data.text
        scrollOutputToBottom()
      }
      break

    case 'output':
      outputData.value = data.data
      break

    case 'execution_complete':
      executionStatus.value = 'completed'
      outputData.value = data.output_data
      streamingOutput.value = ''
      if (data.duration) {
        executionDuration.value = data.duration.toFixed(2)
      }
      addLog('success', '工作流执行完成')
      break

    case 'execution_error':
      executionStatus.value = 'failed'
      errorMessage.value = data.error
      addLog('error', `执行失败: ${data.error}`)
      break

    case 'error':
      addLog('error', `错误: ${data.error}`)
      break

    case 'pong':
      // 心跳响应
      break
  }
}

function clearExecutionState() {
  executionId.value = null
  executionStatus.value = null
  executionDuration.value = null
  nodeStatus.value = {}
  outputData.value = null
  streamingOutput.value = ''
  errorMessage.value = ''
  logs.value = []
}

async function handleCancel() {
  if (!executionId.value) return

  try {
    await workflowApi.cancelExecution(executionId.value)
    executionStatus.value = 'cancelled'
    addLog('warn', '执行已取消')
    disconnectWebSocket()
    appStore.success('执行已取消')
  } catch (err) {
    appStore.error('取消失败')
  }
}

async function handleRetry() {
  await handleExecute()
}

function handleSaveOutput() {
  if (!outputData.value) return

  const dataStr = typeof outputData.value === 'string'
    ? outputData.value
    : JSON.stringify(outputData.value, null, 2)

  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `workflow-output-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  appStore.success('结果已导出')
}

function handleBack() {
  router.push(`/workflows/${workflowId.value}`)
}

function addLog(level, message) {
  logs.value.push({
    timestamp: new Date(),
    level,
    message
  })
  if (autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight
      }
    })
  }
}

function clearLogs() {
  logs.value = []
}

function scrollOutputToBottom() {
  nextTick(() => {
    if (outputContainer.value) {
      outputContainer.value.scrollTop = outputContainer.value.scrollHeight
    }
  })
}

function copyOutput() {
  if (!outputData.value) return
  const output = JSON.stringify(outputData.value, null, 2)
  navigator.clipboard.writeText(output)
  appStore.success('已复制到剪贴板')
}

function copyError() {
  if (!errorMessage.value) return
  navigator.clipboard.writeText(errorMessage.value)
  appStore.success('已复制到剪贴板')
}

function formatOutput(data) {
  if (!data) return ''
  if (typeof data === 'string') return data
  return JSON.stringify(data, null, 2)
}

function formatLogTime(date) {
  return new Date(date).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
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

function getNodeIcon(type) {
  const icons = {
    start: PlayCircle,
    end: Circle,
    input: FileText,
    llm: Zap,
    prompt: MessageSquare,
    condition: GitBranch,
    tool: Hammer,
    output: User
  }
  return icons[type] || Circle
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/variables.scss' as *;

.workflow-execute {
  min-height: calc(100vh - #{$header-height} - #{$spacing-12});
}

.execute-container {
  padding: $spacing-6;
}

.execute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-6;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-4;
}

.workflow-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-1;
}

.workflow-name {
  font-size: $font-size-xl;
  font-weight: $font-weight-bold;
  color: var(--text-primary);
  margin: 0;
}

.execution-id {
  font-size: $font-size-sm;
  color: var(--text-tertiary);
}

.header-actions {
  display: flex;
  gap: $spacing-3;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-icon-sm {
  width: 14px;
  height: 14px;
}

.execute-content {
  display: grid;
  grid-template-columns: 300px 1fr 300px;
  gap: $spacing-4;
  min-height: calc(100vh - 200px);
}

.input-panel,
.output-panel,
.log-panel {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: $radius-xl;
  padding: $spacing-4;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: $font-size-base;
  font-weight: $font-weight-semibold;
  color: var(--text-primary);
  margin: 0 0 $spacing-4;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-4;
  padding-bottom: $spacing-3;
  border-bottom: 1px solid var(--border-primary);
}

.status-info {
  display: flex;
  align-items: center;
  gap: $spacing-3;

  .duration {
    font-size: $font-size-sm;
    color: var(--text-tertiary);
  }
}

.panel-actions {
  display: flex;
  gap: $spacing-2;
}

.input-panel {
  .el-form-item {
    margin-bottom: $spacing-3;
  }
}

.panel-actions {
  margin-top: auto;
  padding-top: $spacing-4;
}

.history-section {
  margin-top: $spacing-6;
  padding-top: $spacing-4;
  border-top: 1px solid var(--border-primary);

  .section-title {
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-secondary);
    margin: 0 0 $spacing-3;
  }
}

.history-list {
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-2;
  border-radius: $radius-md;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: var(--bg-hover);
  }

  .history-time {
    font-size: $font-size-xs;
    color: var(--text-tertiary);
  }
}

.no-history {
  text-align: center;
  font-size: $font-size-sm;
  color: var(--text-tertiary);
  padding: $spacing-4;
}

.execution-progress {
  margin-bottom: $spacing-6;
  padding: $spacing-4 0;
}

.node-status-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-2;
  margin-bottom: $spacing-6;
  max-height: 300px;
  overflow-y: auto;
}

.node-status-item {
  display: flex;
  flex-direction: column;
  padding: $spacing-3;
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;
  border-left: 3px solid transparent;

  &.status-pending {
    border-left-color: var(--border-primary);
  }

  &.status-running {
    border-left-color: $color-warning;
    background-color: rgba($color-warning, 0.1);
  }

  &.status-completed {
    border-left-color: $color-success;
  }

  &.status-failed {
    border-left-color: $color-error;
    background-color: rgba($color-error, 0.1);
  }

  .node-info {
    display: flex;
    align-items: center;
    gap: $spacing-2;

    .node-icon {
      width: 18px;
      height: 18px;
      color: $color-primary;
    }

    .node-name {
      flex: 1;
      font-size: $font-size-sm;
      color: var(--text-primary);
    }

    .node-duration {
      font-size: $font-size-xs;
      color: var(--text-tertiary);
    }
  }

  .node-error {
    margin-top: $spacing-2;
    font-size: $font-size-xs;
    color: $color-error;
  }
}

.no-nodes {
  text-align: center;
  color: var(--text-tertiary);
  padding: $spacing-6;
}

.output-section,
.error-section {
  margin-top: $spacing-4;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: $spacing-3;

  h4 {
    margin: 0;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    color: var(--text-primary);
  }
}

.section-actions {
  display: flex;
  gap: $spacing-2;
}

.output-content {
  background-color: var(--bg-tertiary);
  border-radius: $radius-md;
  padding: $spacing-4;
  max-height: 300px;
  overflow: auto;

  pre {
    margin: 0;
    font-size: $font-size-sm;
    font-family: 'Fira Code', monospace;
    color: var(--text-primary);
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.no-output {
  color: var(--text-tertiary);
  font-size: $font-size-sm;
  text-align: center;
  padding: $spacing-4;
  margin: 0;
}

.streaming-output {
  display: flex;
  align-items: center;

  pre {
    margin: 0;
  }

  .cursor {
    animation: blink 1s infinite;
    color: $color-primary;
  }
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.error-content {
  background-color: rgba($color-error, 0.1);
  border-radius: $radius-md;
  padding: $spacing-4;
  max-height: 200px;
  overflow: auto;

  pre {
    margin: 0;
    font-size: $font-size-sm;
    font-family: 'Fira Code', monospace;
    color: $color-error;
    white-space: pre-wrap;
    word-break: break-all;
  }
}

.log-content {
  flex: 1;
  overflow-y: auto;
}

.log-item {
  display: flex;
  gap: $spacing-2;
  padding: $spacing-2 0;
  font-size: $font-size-xs;
  border-bottom: 1px solid var(--border-primary);

  &:last-child {
    border-bottom: none;
  }

  &.log-info .log-message {
    color: var(--text-secondary);
  }

  &.log-success .log-message {
    color: $color-success;
  }

  &.log-warn .log-message {
    color: $color-warning;
  }

  &.log-error .log-message {
    color: $color-error;
  }
}

.log-time {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.log-message {
  word-break: break-all;
}

.no-logs {
  text-align: center;
  color: var(--text-tertiary);
  padding: $spacing-4;
  font-size: $font-size-sm;
}

.error-detail {
  max-height: 400px;
  overflow: auto;
  font-family: 'Fira Code', monospace;
  font-size: $font-size-sm;
  color: $color-error;
  white-space: pre-wrap;
  background-color: rgba($color-error, 0.1);
  padding: $spacing-4;
  border-radius: $radius-md;
}

@media (max-width: 1200px) {
  .execute-content {
    grid-template-columns: 1fr;
  }

  .log-panel {
    max-height: 300px;
  }
}
</style>
