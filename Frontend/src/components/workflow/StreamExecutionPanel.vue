<template>
  <div
    class="stream-execution-panel"
    :class="{ 'is-collapsed': isCollapsed }"
  >
    <!-- Header -->
    <div
      class="panel-header"
      @click="toggleCollapse"
    >
      <div class="header-left">
        <Zap class="header-icon" />
        <span class="header-title">Streaming Execution</span>
        <el-tag
          v-if="execution"
          :type="statusTagType"
          size="small"
        >
          {{ statusLabel }}
        </el-tag>
      </div>
      <div class="header-right">
        <span
          v-if="elapsedTime"
          class="elapsed-time"
        >{{ elapsedTime }}</span>
        <ChevronDown
          class="collapse-icon"
          :class="{ rotated: isCollapsed }"
        />
      </div>
    </div>

    <!-- Content -->
    <div
      v-show="!isCollapsed"
      class="panel-content"
    >
      <!-- Node Status List -->
      <div class="node-status-list">
        <div
          v-for="node in nodeStatuses"
          :key="node.id"
          class="node-status-item"
          :class="node.status"
        >
          <div class="node-status-indicator">
            <Loader
              v-if="node.status === 'running'"
              class="spinner"
            />
            <CheckCircle
              v-else-if="node.status === 'completed'"
              class="icon-success"
            />
            <XCircle
              v-else-if="node.status === 'error'"
              class="icon-error"
            />
            <Circle
              v-else
              class="icon-pending"
            />
          </div>
          <div class="node-status-info">
            <span class="node-name">{{ node.name }}</span>
            <span class="node-type">{{ node.type }}</span>
          </div>
          <span
            v-if="node.duration"
            class="node-duration"
          >{{ node.duration }}ms</span>
        </div>

        <div
          v-if="!nodeStatuses.length"
          class="empty-status"
        >
          <span>Waiting for execution to start...</span>
        </div>
      </div>

      <!-- Token Stream Output -->
      <div
        ref="outputRef"
        class="token-output"
      >
        <div class="output-header">
          <span class="output-title">Output</span>
          <span
            v-if="tokenCount"
            class="token-count"
          >{{ tokenCount }} tokens</span>
        </div>

        <div class="output-content">
          <!-- Thinking/Reasoning -->
          <div
            v-if="thinkingContent"
            class="thinking-section"
          >
            <div
              class="thinking-header"
              @click="thinkingExpanded = !thinkingExpanded"
            >
              <Brain class="thinking-icon" />
              <span>Thinking Process</span>
              <ChevronDown
                class="expand-icon"
                :class="{ rotated: thinkingExpanded }"
              />
            </div>
            <div
              v-show="thinkingExpanded"
              class="thinking-content"
            >
              {{ thinkingContent }}
            </div>
          </div>

          <!-- Stream Content -->
          <div class="stream-content">
            {{ content }}
          </div>

          <!-- Streaming Cursor -->
          <span
            v-if="isStreaming"
            class="streaming-cursor"
          >|</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="panel-actions">
        <el-button
          size="small"
          @click="scrollToTop"
        >
          Scroll to Top
        </el-button>
        <el-button
          size="small"
          @click="scrollToBottom"
        >
          Scroll to Bottom
        </el-button>
        <el-button
          size="small"
          :icon="Copy"
          @click="copyOutput"
        >
          Copy
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import Cookies from 'js-cookie'
import {
  Zap, ChevronDown, Loader, CheckCircle, XCircle, Circle,
  Brain, Copy
} from 'lucide-vue-next'

const props = defineProps({
  executionId: {
    type: String,
    default: null
  },
  wsUrl: {
    type: String,
    default: null
  },
  sseUrl: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['complete', 'error', 'node-click'])

// State
const isCollapsed = ref(false)
const execution = ref(null)
const nodeStatuses = ref([])
const content = ref('')
const thinkingContent = ref('')
const thinkingExpanded = ref(false)
const isStreaming = ref(false)
const startTime = ref(null)
const elapsedTime = ref('')
const outputRef = ref(null)
let ws = null
let eventSource = null
let timerInterval = null

// Computed
const statusLabel = computed(() => {
  if (!execution.value) return ''
  const statusMap = {
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled'
  }
  return statusMap[execution.value.status] || execution.value.status
})

const statusTagType = computed(() => {
  if (!execution.value) return ''
  const typeMap = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return typeMap[execution.value.status] || ''
})

const tokenCount = computed(() => {
  return content.value.split(/\s+/).filter(Boolean).length
})

// Methods
function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function updateNodeStatus(nodeId, status, data = {}) {
  const node = nodeStatuses.value.find(n => n.id === nodeId)
  if (node) {
    node.status = status
    if (data.duration) node.duration = data.duration
    if (data.error) node.error = data.error
  }
}

function addNodeStatus(node) {
  if (!nodeStatuses.value.find(n => n.id === node.id)) {
    nodeStatuses.value.push({
      id: node.id,
      name: node.name || node.id,
      type: node.type,
      status: 'pending',
      duration: null
    })
  }
}

function appendContent(text) {
  content.value += text
  if (isStreaming.value) {
    nextTick(() => scrollToBottom())
  }
}

function setThinking(text) {
  thinkingContent.value = text
}

function scrollToTop() {
  if (outputRef.value) {
    outputRef.value.scrollTop = 0
  }
}

function scrollToBottom() {
  if (outputRef.value) {
    outputRef.value.scrollTop = outputRef.value.scrollHeight
  }
}

function copyOutput() {
  navigator.clipboard.writeText(content.value)
}

function updateElapsedTime() {
  if (!startTime.value) return
  const elapsed = Date.now() - startTime.value
  const seconds = Math.floor(elapsed / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    elapsedTime.value = `${hours}h ${minutes % 60}m ${seconds % 60}s`
  } else if (minutes > 0) {
    elapsedTime.value = `${minutes}m ${seconds % 60}s`
  } else {
    elapsedTime.value = `${seconds}s`
  }
}

function handleEvent(event) {
  const { type, data } = event

  switch (type) {
    case 'execution_start':
      execution.value = { status: 'running', id: data.execution_id }
      startTime.value = Date.now()
      timerInterval = setInterval(updateElapsedTime, 1000)
      if (data.nodes) {
        data.nodes.forEach(addNodeStatus)
      }
      break

    case 'node_start':
      updateNodeStatus(data.node_id, 'running')
      if (data.node) addNodeStatus(data.node)
      break

    case 'node_complete':
      updateNodeStatus(data.node_id, 'completed', { duration: data.duration })
      break

    case 'node_error':
      updateNodeStatus(data.node_id, 'error', { error: data.error })
      break

    case 'thinking_start':
      thinkingContent.value = ''
      break

    case 'thinking_stream':
      thinkingContent.value += data.content
      break

    case 'token_stream':
      appendContent(data.content)
      isStreaming.value = true
      break

    case 'execution_complete':
      isStreaming.value = false
      execution.value = { status: 'completed', ...data }
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
      updateNodeStatusesToComplete()
      emit('complete', data)
      break

    case 'execution_error':
      isStreaming.value = false
      execution.value = { status: 'failed', error: data.error }
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
      emit('error', data.error)
      break

    case 'progress_update':
      // Handle progress updates
      break
  }
}

function updateNodeStatusesToComplete() {
  nodeStatuses.value.forEach(node => {
    if (node.status === 'running') {
      node.status = 'completed'
    }
  })
}

function connect() {
  if (!props.wsUrl) return

  try {
    ws = new WebSocket(props.wsUrl)

    ws.onopen = () => {
      if (props.executionId) {
        ws.send(JSON.stringify({
          type: 'subscribe',
          execution_id: props.executionId
        }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleEvent(data)
      } catch (e) {
        // Silently ignore malformed messages
      }
    }

    ws.onerror = () => {
      // Error handled by parent component
    }

    ws.onclose = () => {
      // Cleanup handled in disconnect()
    }
  } catch (error) {
    // Connection failure handled by parent component
  }
}

function disconnect() {
  if (ws) {
    ws.close()
    ws = null
  }
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function connectSSE() {
  if (!props.sseUrl) return

  try {
    const token = localStorage.getItem('access_token') || Cookies.get('access_token')
    const url = new URL(props.sseUrl, window.location.origin)
    if (token) {
      url.searchParams.set('token', token)
    }
    if (props.executionId) {
      url.searchParams.set('execution_id', props.executionId)
    }

    eventSource = new EventSource(url.toString())

    eventSource.onopen = () => {
      // Connected successfully
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleEvent(data)
      } catch (e) {
        // Silently ignore malformed SSE data
      }
    }

    // Register named event listeners for structured events
    const eventNames = [
      'execution_start', 'node_start', 'node_complete', 'node_error',
      'token_stream', 'thinking_stream', 'execution_complete', 'execution_error'
    ]
    eventNames.forEach(eventName => {
      eventSource.addEventListener(eventName, (event) => {
        try {
          const data = JSON.parse(event.data)
          handleEvent({ type: eventName, data })
        } catch (e) {
          // Silently ignore malformed SSE event data
        }
      })
    })

    eventSource.onerror = () => {
      // SSE error handled by parent component
    }
  } catch (error) {
    // Connection failure handled by parent component
  }
}

// Lifecycle
onMounted(() => {
  if (props.wsUrl) {
    connect()
  } else if (props.sseUrl) {
    connectSSE()
  }
})

onUnmounted(() => {
  disconnect()
})

// Watchers
watch(() => props.wsUrl, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl) {
    disconnect()
    if (newUrl) {
      connect()
    }
  }
})

watch(() => props.sseUrl, (newUrl, oldUrl) => {
  if (newUrl !== oldUrl) {
    disconnect()
    if (newUrl) {
      connectSSE()
    }
  }
})

// Expose methods
defineExpose({
  handleEvent,
  addNodeStatus,
  updateNodeStatus,
  appendContent,
  setThinking,
  reset: () => {
    content.value = ''
    thinkingContent.value = ''
    nodeStatuses.value = []
    execution.value = null
    startTime.value = null
    elapsedTime.value = ''
    isStreaming.value = false
  }
})
</script>

<style scoped>
.stream-execution-panel {
  background: var(--card-bg);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stream-execution-panel.is-collapsed {
  max-height: 56px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s ease;
}

.panel-header:hover {
  background: var(--bg-hover);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  width: 18px;
  height: 18px;
  color: var(--color-primary);
}

.header-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.elapsed-time {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
}

.collapse-icon {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
  transition: transform 0.2s;
}

.collapse-icon.rotated {
  transform: rotate(-90deg);
}

.panel-content {
  padding: 16px;
}

.node-status-list {
  margin-bottom: 16px;
  max-height: 200px;
  overflow-y: auto;
}

.node-status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 4px;
  background: var(--bg-secondary);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.node-status-item:hover {
  background: var(--bg-hover);
}

.node-status-item.running {
  background: var(--info-bg);
}

.node-status-item.completed {
  background: var(--success-bg);
}

.node-status-item.error {
  background: var(--error-bg);
}

.node-status-indicator {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.node-status-indicator .spinner {
  width: 16px;
  height: 16px;
  color: var(--color-primary);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.icon-success {
  width: 16px;
  height: 16px;
  color: var(--success);
}

.icon-error {
  width: 16px;
  height: 16px;
  color: var(--error);
}

.icon-pending {
  width: 16px;
  height: 16px;
  color: var(--text-tertiary);
}

.node-status-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.node-type {
  font-size: 11px;
  color: var(--text-secondary);
}

.node-duration {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: monospace;
}

.empty-status {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 13px;
}

.token-output {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 8px;
  overflow: hidden;
}

.output-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: var(--code-surface);
  border-bottom: 1px solid var(--code-border);
}

.output-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--code-text);
}

.token-count {
  font-size: 12px;
  color: var(--code-muted);
}

.output-content {
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
  color: var(--code-text);
}

.thinking-section {
  margin-bottom: 12px;
  padding: 10px;
  background: var(--surface-muted);
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: var(--info);
}

.thinking-icon {
  width: 14px;
  height: 14px;
}

.expand-icon {
  width: 14px;
  height: 14px;
  margin-left: auto;
  transition: transform 0.2s;
}

.expand-icon.rotated {
  transform: rotate(-90deg);
}

.thinking-content {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

.stream-content {
  word-wrap: break-word;
  white-space: pre-wrap;
}

.streaming-cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: var(--color-primary);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.panel-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
