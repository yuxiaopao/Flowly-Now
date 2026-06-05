<template>
  <el-dialog
    v-model="dialogVisible"
    title="执行结果"
    width="900px"
    :before-close="handleClose"
    class="execution-result-dialog"
  >
    <!-- 执行状态头部 -->
    <div class="execution-header">
      <div class="status-section">
        <el-tag
          :type="statusType"
          size="large"
          class="status-tag"
        >
          <el-icon
            v-if="isRunning"
            class="is-loading"
          >
            <Loader />
          </el-icon>
          {{ statusText }}
        </el-tag>
        <span
          v-if="execution?.duration"
          class="duration"
        >
          <el-icon><Clock /></el-icon>
          耗时: {{ formatDuration(execution.duration) }}
        </span>
      </div>
      
      <div
        v-if="isRunning"
        class="running-info"
      >
        <span
          v-if="currentNodeName"
          class="current-node"
        >
          正在执行: {{ currentNodeName }}
        </span>
      </div>
    </div>

    <!-- 执行进度 -->
    <div
      v-if="isRunning"
      class="progress-section"
    >
      <el-progress
        :percentage="progress"
        :status="progressStatus"
        :stroke-width="16"
        :duration="6"
      >
        <template #default>
          <span class="progress-text">{{ progress }}%</span>
        </template>
      </el-progress>
      <p class="progress-message">
        {{ progressMessage }}
      </p>
    </div>

    <!-- 节点状态概览 -->
    <div class="node-status-overview">
      <div class="status-card status-card--pending">
        <span class="status-count">{{ nodeStatusSummary.pending }}</span>
        <span class="status-label">等待中</span>
      </div>
      <div class="status-card status-card--running">
        <span class="status-count">{{ nodeStatusSummary.running }}</span>
        <span class="status-label">执行中</span>
      </div>
      <div class="status-card status-card--completed">
        <span class="status-count">{{ nodeStatusSummary.completed }}</span>
        <span class="status-label">已完成</span>
      </div>
      <div class="status-card status-card--failed">
        <span class="status-count">{{ nodeStatusSummary.failed }}</span>
        <span class="status-label">失败</span>
      </div>
      <div class="status-card status-card--skipped">
        <span class="status-count">{{ nodeStatusSummary.skipped }}</span>
        <span class="status-label">跳过</span>
      </div>
    </div>

    <!-- 标签页 -->
    <el-tabs
      v-model="activeTab"
      class="execution-tabs"
    >
      <!-- 执行日志 -->
      <el-tab-pane
        label="执行日志"
        name="logs"
      >
        <div
          v-if="executionLogs.length > 0"
          class="log-list"
        >
          <div
            v-for="(log, index) in executionLogs"
            :key="index"
            class="log-item"
            :class="`log-${log.status}`"
          >
            <div class="log-indicator">
              <el-icon
                v-if="log.status === 'completed'"
                class="log-icon--success"
              >
                <CheckCircle />
              </el-icon>
              <el-icon
                v-else-if="log.status === 'failed'"
                class="log-icon--error"
              >
                <CircleClose />
              </el-icon>
              <el-icon
                v-else-if="log.status === 'running'"
                class="log-icon--running is-loading"
              >
                <Loader />
              </el-icon>
              <el-icon
                v-else
                class="log-icon--pending"
              >
                <More />
              </el-icon>
            </div>
            <div class="log-content">
              <div class="log-header">
                <span class="log-node">{{ log.nodeName || log.node_id }}</span>
                <span class="log-time">{{ formatTime(log.startedAt || log.timestamp) }}</span>
              </div>
              <div
                v-if="log.duration"
                class="log-duration"
              >
                <el-icon><Clock /></el-icon>
                {{ log.duration }}ms
              </div>
              <div
                v-if="log.errorMessage"
                class="log-error"
              >
                {{ log.errorMessage }}
              </div>
            </div>
          </div>
        </div>
        <el-empty
          v-else
          description="暂无执行日志"
        />
      </el-tab-pane>

      <!-- 输入数据 -->
      <el-tab-pane
        label="输入数据"
        name="input"
      >
        <div class="json-viewer">
          <pre v-if="Object.keys(inputData).length > 0">{{ formatJSON(inputData) }}</pre>
          <el-empty
            v-else
            description="暂无输入数据"
          />
        </div>
      </el-tab-pane>

      <!-- 输出数据 -->
      <el-tab-pane
        label="输出数据"
        name="output"
      >
        <div class="json-viewer">
          <pre v-if="outputData && Object.keys(outputData).length > 0">{{ formatJSON(outputData) }}</pre>
          <el-empty
            v-else-if="isRunning"
            description="执行中，输出暂不可用"
          />
          <el-empty
            v-else
            description="暂无输出数据"
          />
        </div>
      </el-tab-pane>

      <!-- 节点详情 -->
      <el-tab-pane
        label="节点详情"
        name="nodes"
      >
        <div
          v-if="nodeResults && Object.keys(nodeResults).length > 0"
          class="node-results"
        >
          <el-collapse v-model="expandedNodes">
            <el-collapse-item
              v-for="(result, nodeId) in nodeResults"
              :key="nodeId"
              :name="String(nodeId)"
            >
              <template #title>
                <div class="node-result-header">
                  <span class="node-name">{{ getNodeName(nodeId) }}</span>
                  <el-tag 
                    size="small" 
                    :type="getResultStatusType(result.status)"
                    class="node-status-tag"
                  >
                    {{ result.status }}
                  </el-tag>
                  <span
                    v-if="result.duration"
                    class="node-duration"
                  >
                    {{ result.duration }}ms
                  </span>
                </div>
              </template>
              <div class="node-result-content">
                <div class="result-section">
                  <h4>输入</h4>
                  <pre>{{ formatJSON(result.input) }}</pre>
                </div>
                <div class="result-section">
                  <h4>输出</h4>
                  <pre>{{ formatJSON(result.output) }}</pre>
                </div>
                <div
                  v-if="result.error"
                  class="result-section result-section--error"
                >
                  <h4>错误</h4>
                  <pre>{{ result.error }}</pre>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <el-empty
          v-else
          description="暂无节点执行详情"
        />
      </el-tab-pane>

      <!-- 错误信息 -->
      <el-tab-pane
        v-if="errorMessage"
        label="错误信息"
        name="error"
      >
        <div class="error-viewer">
          <el-alert
            :title="errorMessage"
            type="error"
            :closable="false"
            show-icon
          />
          <pre
            v-if="traceback"
            class="traceback"
          >{{ traceback }}</pre>
        </div>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <div class="dialog-footer">
        <div class="footer-left">
          <el-button
            v-if="isRunning"
            type="warning"
            @click="handlePause"
          >
            <el-icon><VideoPause /></el-icon>
            暂停
          </el-button>
          <el-button
            v-if="isPaused"
            type="primary"
            @click="handleResume"
          >
            <el-icon><VideoPlay /></el-icon>
            恢复
          </el-button>
          <el-button
            v-if="isRunning || isPaused"
            type="danger"
            @click="handleCancel"
          >
            <el-icon><SwitchButton /></el-icon>
            取消
          </el-button>
        </div>
        <div class="footer-right">
          <el-button @click="handleClose">
            关闭
          </el-button>
          <el-button
            v-if="isFailed"
            type="primary"
            @click="handleRetry"
          >
            <el-icon><RefreshRight /></el-icon>
            重试
          </el-button>
          <el-button
            v-if="isCompleted"
            type="primary"
            @click="handleCopyOutput"
          >
            <el-icon><CopyDocument /></el-icon>
            复制结果
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  Loader,
  Clock,
  CheckCircle,
  CircleClose,
  More,
  VideoPause,
  VideoPlay,
  SwitchButton,
  RefreshRight,
  CopyDocument
} from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

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

const emit = defineEmits(['update:modelValue', 'retry', 'cancel', 'pause', 'resume'])

// 对话框可见性
const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// 状态
const activeTab = ref('logs')
const expandedNodes = ref([])

// 计算属性
const execution = computed(() => props.execution || {})
const status = computed(() => execution.value?.status || 'pending')

const statusType = computed(() => {
  switch (status.value) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    case 'paused': return 'info'
    case 'cancelled': return 'info'
    default: return 'info'
  }
})

const statusText = computed(() => {
  switch (status.value) {
    case 'completed': return '执行成功'
    case 'failed': return '执行失败'
    case 'running': return '执行中...'
    case 'paused': return '已暂停'
    case 'cancelled': return '已取消'
    case 'pending': return '等待中'
    default: return status.value
  }
})

const isRunning = computed(() => status.value === 'running')
const isPaused = computed(() => status.value === 'paused')
const isCompleted = computed(() => status.value === 'completed')
const isFailed = computed(() => status.value === 'failed')

const progress = computed(() => execution.value?.progress || 0)
const progressMessage = computed(() => execution.value?.message || '正在执行...')
const progressStatus = computed(() => {
  if (progress.value >= 100) return 'success'
  if (isFailed.value) return 'exception'
  return undefined
})

const currentNodeName = computed(() => execution.value?.currentNodeName || '')

const inputData = computed(() => execution.value?.input_data || execution.value?.inputData || {})
const outputData = computed(() => execution.value?.output_data || execution.value?.outputData || null)
const errorMessage = computed(() => execution.value?.error_message || execution.value?.errorMessage || '')
const traceback = computed(() => execution.value?.traceback || '')

const executionLogs = computed(() => {
  const logs = execution.value?.logs || execution.value?.executionLogs || []
  return logs.sort((a, b) => {
    const timeA = new Date(a.startedAt || a.timestamp || 0).getTime()
    const timeB = new Date(b.startedAt || b.timestamp || 0).getTime()
    return timeA - timeB
  })
})

const nodeResults = computed(() => execution.value?.node_results || execution.value?.nodeResults || {})

const nodeStatusSummary = computed(() => {
  const summary = execution.value?.nodeStatusSummary || execution.value?.node_status_summary || {
    pending: 0,
    running: 0,
    completed: 0,
    failed: 0,
    skipped: 0
  }
  return summary
})

// 方法
const formatDuration = (ms) => {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.floor(ms / 60000)}分${((ms % 60000) / 1000).toFixed(0)}秒`
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatJSON = (data) => {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

const getNodeName = (nodeId) => {
  const nodes = execution.value?.nodes || []
  const node = nodes.find(n => n.id === nodeId || n.id === String(nodeId))
  return node?.name || node?.label || `节点 ${nodeId}`
}

const getResultStatusType = (status) => {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'danger'
    case 'running': return 'warning'
    case 'skipped': return 'info'
    default: return 'info'
  }
}

const handleClose = () => {
  dialogVisible.value = false
  emit('close')
}

const handleRetry = () => {
  emit('retry', execution.value)
}

const handleCancel = () => {
  emit('cancel', execution.value?.id)
}

const handlePause = () => {
  emit('pause', execution.value?.id)
}

const handleResume = () => {
  emit('resume', execution.value?.id)
}

const handleCopyOutput = async () => {
  try {
    const text = outputData.value 
      ? JSON.stringify(outputData.value, null, 2)
      : ''
    await navigator.clipboard.writeText(text)
    appStore.success('已复制到剪贴板')
  } catch {
    appStore.error('复制失败')
  }
}

// 监听 visible 变化
watch(dialogVisible, (val) => {
  if (val) {
    activeTab.value = 'logs'
  }
})
</script>

<style scoped>
.execution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.status-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-tag {
  font-size: 14px;
  padding: 6px 16px;
}

.duration {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--el-text-color-secondary);
}

.running-info {
  color: var(--el-text-color-secondary);
}

.current-node {
  font-size: 13px;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-text {
  font-weight: 600;
}

.progress-message {
  text-align: center;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
  font-size: 13px;
}

.node-status-overview {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px;
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
  border-radius: 6px;
  transition: transform 0.2s;
}

.status-card:hover {
  transform: translateY(-2px);
}

.status-count {
  font-size: 24px;
  font-weight: 700;
}

.status-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.status-card--pending .status-count { color: var(--el-text-color-secondary); }
.status-card--running .status-count { color: var(--el-color-warning); }
.status-card--completed .status-count { color: var(--el-color-success); }
.status-card--failed .status-count { color: var(--el-color-danger); }
.status-card--skipped .status-count { color: var(--el-color-info); }

.execution-tabs {
  margin-top: 16px;
}

.log-list {
  max-height: 400px;
  overflow-y: auto;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  background: var(--el-fill-color-light);
  transition: background 0.2s;
}

.log-item:hover {
  background: var(--el-fill-color);
}

.log-item.log-completed {
  border-left: 3px solid var(--el-color-success);
}

.log-item.log-failed {
  border-left: 3px solid var(--el-color-danger);
  background: var(--el-color-danger-lighter);
}

.log-item.log-running {
  border-left: 3px solid var(--el-color-warning);
}

.log-indicator {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.log-icon--success { color: var(--el-color-success); }
.log-icon--error { color: var(--el-color-danger); }
.log-icon--running { color: var(--el-color-warning); }
.log-icon--pending { color: var(--el-text-color-secondary); }

.log-content {
  flex: 1;
  min-width: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.log-node {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.log-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.log-duration {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.log-error {
  margin-top: 8px;
  padding: 8px;
  background: var(--el-color-danger-lighter);
  border-radius: 4px;
  font-size: 12px;
  color: var(--el-color-danger);
  word-break: break-all;
}

.json-viewer {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding: 16px;
  max-height: 400px;
  overflow: auto;
}

.json-viewer pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}

.node-results {
  max-height: 400px;
  overflow-y: auto;
}

.node-result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.node-name {
  font-weight: 600;
}

.node-status-tag {
  font-size: 12px;
}

.node-duration {
  margin-left: auto;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.node-result-content {
  padding: 12px;
}

.result-section {
  margin-bottom: 16px;
}

.result-section:last-child {
  margin-bottom: 0;
}

.result-section h4 {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.result-section pre {
  background: var(--el-fill-color);
  padding: 12px;
  border-radius: 4px;
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.result-section--error pre {
  background: var(--el-color-danger-lighter);
  color: var(--el-color-danger);
}

.error-viewer {
  max-height: 400px;
  overflow: auto;
}

.traceback {
  margin-top: 16px;
  padding: 16px;
  background: var(--el-fill-color-dark);
  border-radius: 6px;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--el-text-color-primary);
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left,
.footer-right {
  display: flex;
  gap: 8px;
}
</style>
