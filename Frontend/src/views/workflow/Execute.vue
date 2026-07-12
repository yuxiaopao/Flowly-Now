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
                :class="['history-item', `status-${item.status}`, { active: resolveExecutionId(item) === executionId }]"
                @click="loadExecution(item)"
              >
                <span class="history-time">{{ formatDate(item.startedAt || item.started_at || item.queuedAt || item.queued_at) }}</span>
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

          <!-- 执行产物 -->
          <div class="artifacts-section">
            <ExecutionArtifactsPanel
              :node-executions="nodeExecutionsList"
              :output-data="outputData"
              :node-status-map="rawNodeStatus"
              :execution="{ nodeStatus: rawNodeStatus, outputData }"
              :node-name-map="workflowNodeNameMap"
            />
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
import { ref, reactive, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWorkflowStore } from '@/stores/workflow'
import { useExecutionStore } from '@/stores/execution'
import { useAppStore } from '@/stores/app'
import { workflowApi } from '@/api/workflow'
import { nodeExecutionsFromStatus } from '@/utils/executionArtifacts'
import { getWebSocketUrl } from '@/config'
import {
  ArrowLeft, Play, RefreshCw, Copy, Download,
  PlayCircle, MessageSquare, GitBranch, Hammer,
  User, FileText, Zap, Circle
} from 'lucide-vue-next'
import AppButton from '@/components/common/AppButton.vue'
import ExecutionArtifactsPanel from '@/components/workflow/ExecutionArtifactsPanel.vue'

const route = useRoute()
const router = useRouter()
const workflowStore = useWorkflowStore()
const executionStore = useExecutionStore()
const appStore = useAppStore()

const workflowId = computed(() => route.params.id)

const workflow = computed(() => workflowStore.currentWorkflow)
const isRunning = computed(() => ['running', 'pending', 'queued'].includes(executionStatus.value))
const canExecute = computed(() => workflow.value?.id)

const executionId = ref(null)
const executionStatus = ref(null)
const executionDuration = ref(null)
const nodeStatus = ref({})
const rawNodeStatus = ref({})
const nodeExecutionsList = ref([])
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

const EXECUTION_STEP_COUNT = 3

const currentStep = computed(() => {
  const status = executionStatus.value
  if (!status) return 0
  if (['pending', 'queued'].includes(status)) return 0
  if (['running', 'paused'].includes(status)) return 1
  // active 等于步骤总数时，全部步骤显示为已完成（含「完成」）
  if (['completed', 'failed', 'cancelled'].includes(status)) return EXECUTION_STEP_COUNT
  return 1
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

const workflowNodeNameMap = computed(() => buildWorkflowNodeLookup().nameById)

onMounted(async () => {
  try {
    await workflowStore.fetchWorkflow(workflowId.value)
    executionStore.registerEditorSnapshotListener(workflowId.value, handleStoreExecutionSnapshot)
    await fetchExecutionHistory()
    await resumeExecutePageState()
  } catch {
    appStore.error('加载工作流失败')
  }
})

onUnmounted(() => {
  executionStore.unregisterEditorSnapshotListener(workflowId.value)
  disconnectWebSocket()
})

function resolveExecutionId(source) {
  if (!source) return null
  if (typeof source === 'string' || typeof source === 'number') return String(source)
  return source.id || source.executionId || source.execution_id || null
}

function buildWorkflowNodeLookup() {
  const nodes = workflowStore.nodes || workflow.value?.nodes || []
  const nameById = {}
  const typeById = {}
  nodes.forEach((node) => {
    const id = node.id || node.node_id
    if (!id) return
    nameById[id] = node.data?.label || node.label || node.name || node.config?.label || id
    typeById[id] = node.data?.type || node.type || node.node_type || node.nodeType || 'default'
  })
  return { nameById, typeById }
}

function buildNodeStatusView(execution, nodeExecutions = []) {
  const { nameById, typeById } = buildWorkflowNodeLookup()
  const map = {}

  if (Array.isArray(nodeExecutions) && nodeExecutions.length > 0) {
    nodeExecutions.forEach((nodeExecution) => {
      const nodeId = nodeExecution.nodeId || nodeExecution.node_id || nodeExecution.node
      if (!nodeId) return
      map[nodeId] = {
        status: nodeExecution.status || 'pending',
        name: nodeExecution.nodeName || nodeExecution.node_name || nameById[nodeId] || nodeId,
        type: nodeExecution.nodeType || nodeExecution.node_type || typeById[nodeId] || 'default',
        error: nodeExecution.errorMessage || nodeExecution.error_message || null,
        duration: nodeExecution.durationMs != null
          ? (Number(nodeExecution.durationMs) / 1000).toFixed(1)
          : nodeExecution.durationSeconds != null
            ? Number(nodeExecution.durationSeconds).toFixed(1)
            : null,
        output: nodeExecution.outputData ?? nodeExecution.output_data ?? null,
      }
    })
    return map
  }

  const raw = execution?.nodeStatus || execution?.node_status || {}
  Object.entries(raw).forEach(([nodeId, value]) => {
    const status = typeof value === 'string' ? value : value?.status || 'pending'
    const snapshotName = typeof value === 'object'
      ? (value.node_name || value.nodeName || value.node_type_display || value.nodeTypeDisplay)
      : null
    const snapshotType = typeof value === 'object'
      ? (value.node_type || value.nodeType)
      : null
    map[nodeId] = {
      status,
      name: nameById[nodeId] || snapshotName || nodeId,
      type: typeById[nodeId] || snapshotType || 'default',
      error: typeof value === 'object' ? (value.error || value.error_message || value.errorMessage) : null,
      output: typeof value === 'object' ? (value.output ?? value.output_data ?? value.outputData) : null,
    }
  })
  return map
}

function normalizeTimelineLogs(rawLogs = []) {
  return rawLogs.map((log) => ({
    level: (log.level || log.type || 'info').toLowerCase(),
    timestamp: log.timestamp || log.time || log.created_at || log.createdAt || null,
    message: log.message || log.text || '',
  }))
}

function applyExecutionDetail(execution, timeline = null, execId = null) {
  const resolvedId = execId || resolveExecutionId(execution)
  if (!resolvedId || !execution) return false

  executionId.value = resolvedId
  executionStatus.value = execution.status || null
  outputData.value = execution.outputData ?? execution.output_data ?? null
  rawNodeStatus.value = execution.nodeStatus ?? execution.node_status ?? {}
  errorMessage.value = execution.errorMessage ?? execution.error_message ?? ''
  nodeStatus.value = buildNodeStatusView(
    execution,
    timeline?.nodeExecutions ?? timeline?.node_executions ?? []
  )
  nodeExecutionsList.value = timeline?.nodeExecutions
    ?? timeline?.node_executions
    ?? nodeExecutionsFromStatus(execution)

  const durationMs = execution.durationMs ?? execution.duration_ms
  if (durationMs != null) {
    executionDuration.value = (Number(durationMs) / 1000).toFixed(2)
  } else if (execution.duration != null) {
    executionDuration.value = Number(execution.duration).toFixed(2)
  } else {
    const startedAt = execution.startedAt ?? execution.started_at
    const completedAt = execution.completedAt ?? execution.completed_at
    if (startedAt && completedAt) {
      executionDuration.value = ((new Date(completedAt) - new Date(startedAt)) / 1000).toFixed(2)
    }
  }

  const rawLogs = timeline?.logs || execution.executionLogs || execution.logs || []
  if (rawLogs.length > 0) {
    logs.value = normalizeTimelineLogs(rawLogs)
  }

  return true
}

function handleStoreExecutionSnapshot(execution, nodeStateMap) {
  if (!execution) return
  const nodeExecutions = Object.entries(nodeStateMap || {}).map(([nodeId, state]) => ({
    nodeId,
    node_id: nodeId,
    status: state?.status,
    output_data: state?.output,
    error_message: state?.error,
  }))
  applyExecutionDetail(execution, { nodeExecutions })
  if (['completed', 'failed', 'cancelled'].includes(execution.status)) {
    disconnectWebSocket()
    fetchExecutionHistory()
  }
}

async function fetchExecutionHistory() {
  try {
    const response = await workflowApi.getExecutionHistory(workflowId.value, { page_size: 20 })
    const items = (response.results || response || [])
      .filter((item) => resolveExecutionId(item))
      .sort((a, b) => {
        const ta = new Date(a.startedAt || a.started_at || a.queuedAt || a.queued_at || 0).getTime()
        const tb = new Date(b.startedAt || b.started_at || b.queuedAt || b.queued_at || 0).getTime()
        return tb - ta
      })
    executionHistory.value = items
  } catch {
    executionHistory.value = []
  }
}

async function resumeExecutePageState() {
  const replayId = route.query.replay
  if (replayId) {
    await loadExecution(String(replayId))
    return
  }

  try {
    const resumed = await executionStore.resumeEditorExecution(workflowId.value)
    if (resumed?.execution) {
      applyExecutionDetail(resumed.execution, null, resumed.executionId)
      logs.value.unshift({
        level: 'info',
        timestamp: new Date(),
        message: `已恢复执行监控，ID: ${resumed.executionId}`,
      })
      if (isRunning.value) {
        connectWebSocket()
      }
      return
    }
  } catch {
    // ignore resume errors
  }

  const active = executionHistory.value.find((item) => ['running', 'pending', 'queued', 'paused'].includes(item.status))
  if (active) {
    await loadExecution(active)
  }
}

async function loadExecution(execIdOrItem) {
  const execId = resolveExecutionId(execIdOrItem)
  if (!execId) {
    appStore.warning('无效的执行记录')
    return
  }

  disconnectWebSocket()
  try {
    const timeline = await workflowApi.getExecutionTimeline(execId, { skipErrorToast: true })
    const execution = timeline?.execution || timeline
    if (!applyExecutionDetail(execution, timeline, execId)) {
      throw new Error('empty execution payload')
    }

    logs.value.unshift({
      level: 'info',
      timestamp: new Date(),
      message: `已加载执行记录: ${execId}`,
    })

    if (isRunning.value) {
      connectWebSocket()
      await executionStore.startEditorPolling(workflowId.value, execId)
    }
  } catch {
    appStore.error('加载执行记录失败')
  }
}

async function handleExecute() {
  clearExecutionState()
  addLog('info', '开始执行工作流...')
  addLog('info', `输入参数: ${JSON.stringify(inputData)}`)

  try {
    const response = await workflowApi.executeAsync(workflowId.value, inputData)

    executionId.value = response.executionId || response.execution_id || response.id
    addLog('info', `执行 ID: ${executionId.value}`)

    if (executionId.value) {
      connectWebSocket()
      executionStatus.value = response.status || 'running'
      await executionStore.startEditorPolling(workflowId.value, executionId.value)
      await fetchExecutionHistory()
    } else {
      executionStatus.value = response.status
      outputData.value = response.outputData || response.output_data
      if (response.error) {
        errorMessage.value = response.error
        addLog('error', `执行失败: ${response.error}`)
      } else {
        addLog('success', '工作流执行完成')
      }
      await fetchExecutionHistory()
    }
  } catch (err) {
    addLog('error', `执行失败: ${err.message}`)
    appStore.error('执行失败')
    disconnectWebSocket()
  }
}

function connectWebSocket() {
  if (!executionId.value) return

  const wsUrl = getWebSocketUrl(`/ws/execution/${executionId.value}/`)

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

    ws.onerror = (_err) => {
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
      outputData.value = data.outputData ?? data.output_data ?? data.data
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
  rawNodeStatus.value = {}
  nodeExecutionsList.value = []
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
    executionStore.stopEditorPolling({ resetSession: true, clearActive: true })
    addLog('warn', '执行已取消')
    disconnectWebSocket()
    appStore.success('执行已取消')
    await fetchExecutionHistory()
  } catch {
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

function formatLogTime(date) {
  if (!date) return '--:--:--'
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return '--:--:--'
  return parsed.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
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

  &.active {
    background-color: color-mix(in srgb, var(--color-primary, #3b82f6) 12%, transparent);
    outline: 1px solid color-mix(in srgb, var(--color-primary, #3b82f6) 35%, transparent);
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

.artifacts-section,
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
