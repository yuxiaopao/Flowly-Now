<template>
  <div class="execution-logs-panel">
    <div class="logs-header">
      <div class="header-left">
        <span class="header-title">执行日志</span>
        <span
          v-if="isLive"
          class="live-badge"
        >
          <span class="live-dot" />
          LIVE
        </span>
      </div>
      <div class="header-actions">
        <el-select
          v-model="selectedLevel"
          size="small"
          style="width: 100px"
          @change="$emit('filter-change', selectedLevel)"
        >
          <el-option
            label="全部"
            value="all"
          />
          <el-option
            label="DEBUG"
            value="debug"
          />
          <el-option
            label="INFO"
            value="info"
          />
          <el-option
            label="WARNING"
            value="warning"
          />
          <el-option
            label="ERROR"
            value="error"
          />
        </el-select>
        <el-button
          size="small"
          text
          @click="$emit('clear')"
        >
          <Trash2 class="btn-icon-small" />
          清空
        </el-button>
        <el-button
          size="small"
          text
          @click="$emit('download')"
        >
          <Download class="btn-icon-small" />
          下载
        </el-button>
      </div>
    </div>

    <div
      ref="logsContainerRef"
      class="logs-content"
    >
      <div
        v-if="filteredLogs.length === 0"
        class="empty-logs"
      >
        <FileText class="empty-icon" />
        <p>暂无日志</p>
      </div>

      <div
        v-for="(log, index) in filteredLogs"
        :key="index"
        class="log-entry"
        :class="[log.level, { new: isNewLog(log) }]"
      >
        <span class="log-time">{{ formatTime(log.timestamp || log.time) }}</span>
        <span
          class="log-level"
          :class="log.level"
        >{{ (log.level || 'info').toUpperCase() }}</span>
        <span
          v-if="log.node || log.nodeName"
          class="log-node"
        >[{{ log.node || log.nodeName }}]</span>
        <span class="log-message">{{ log.message || log.text }}</span>
      </div>
    </div>

    <div class="logs-footer">
      <span class="log-count">{{ filteredLogs.length }} 条日志</span>
      <el-button
        v-if="filteredLogs.length > 0"
        size="small"
        text
        @click="scrollToTop"
      >
        <ArrowUp class="btn-icon-small" />
        回到顶部
      </el-button>
      <el-button
        v-if="isLive"
        size="small"
        text
        @click="autoScroll = !autoScroll"
      >
        <span :class="{ 'text-primary': autoScroll }">自动滚动 {{ autoScroll ? 'ON' : 'OFF' }}</span>
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import {
  Trash2, Download, FileText, ArrowUp
} from 'lucide-vue-next'

const props = defineProps({
  logs: {
    type: Array,
    default: () => []
  },
  isLive: {
    type: Boolean,
    default: false
  },
  levelFilter: {
    type: String,
    default: 'all'
  }
})

const emit = defineEmits(['filter-change', 'clear', 'download'])

const logsContainerRef = ref(null)
const selectedLevel = ref(props.levelFilter)
const autoScroll = ref(true)
const seenLogCount = ref(0)

const filteredLogs = computed(() => {
  if (selectedLevel.value === 'all') {
    return props.logs
  }
  return props.logs.filter(log =>
    (log.level || 'info').toLowerCase() === selectedLevel.value.toLowerCase()
  )
})

function isNewLog(log) {
  const index = props.logs.indexOf(log)
  return index >= seenLogCount.value
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
  })
}

function scrollToTop() {
  if (logsContainerRef.value) {
    logsContainerRef.value.scrollTop = 0
  }
}

function scrollToBottom() {
  if (logsContainerRef.value) {
    logsContainerRef.value.scrollTop = logsContainerRef.value.scrollHeight
  }
}

watch(() => props.logs.length, (newLen) => {
  if (props.isLive && autoScroll.value) {
    nextTick(() => scrollToBottom())
  }
  seenLogCount.value = newLen
})

watch(() => props.levelFilter, (val) => {
  selectedLevel.value = val
})
</script>

<style lang="scss" scoped>
.execution-logs-panel {
  display: flex;
  flex-direction: column;
  height: 400px;
  background: #1e1e2e;
  border-radius: 8px;
  overflow: hidden;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #2d2d3d;
  border-bottom: 1px solid #3d3d4d;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .header-title {
    font-size: 13px;
    font-weight: 600;
    color: #e5e7eb;
  }

  .live-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    background: rgba(16, 185, 129, 0.2);
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    color: #10b981;

    .live-dot {
      width: 6px;
      height: 6px;
      background: #10b981;
      border-radius: 50%;
      animation: pulse 1.5s infinite;
    }
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.logs-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: #2d2d3d;
  }

  &::-webkit-scrollbar-thumb {
    background: #4b5563;
    border-radius: 4px;

    &:hover {
      background: #6b7280;
    }
  }
}

.empty-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;

  .empty-icon {
    width: 32px;
    height: 32px;
    margin-bottom: 8px;
  }

  p {
    margin: 0;
    font-size: 13px;
  }
}

.log-entry {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 4px 16px;
  line-height: 1.5;
  transition: background-color 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
  }

  &.new {
    animation: highlight 2s ease-out;
  }

  &.debug {
    color: #9ca3af;
  }

  &.info {
    color: #e5e7eb;
  }

  &.warning {
    color: #fbbf24;
    background: rgba(251, 191, 36, 0.05);
  }

  &.error {
    color: #f87171;
    background: rgba(248, 113, 113, 0.05);
  }
}

.log-time {
  flex-shrink: 0;
  color: #6b7280;
  font-size: 11px;
}

.log-level {
  flex-shrink: 0;
  width: 50px;
  font-weight: 600;
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  text-align: center;

  &.debug {
    background: rgba(156, 163, 175, 0.2);
    color: #9ca3af;
  }

  &.info {
    background: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
  }

  &.warning {
    background: rgba(251, 191, 36, 0.2);
    color: #fbbf24;
  }

  &.error {
    background: rgba(248, 113, 113, 0.2);
    color: #f87171;
  }
}

.log-node {
  flex-shrink: 0;
  color: #8b5cf6;
  font-size: 11px;
}

.log-message {
  flex: 1;
  word-break: break-word;
}

.logs-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #2d2d3d;
  border-top: 1px solid #3d3d4d;

  .log-count {
    font-size: 11px;
    color: #6b7280;
  }

  .text-primary {
    color: #60a5fa;
  }
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes highlight {
  0% { background: rgba(96, 165, 250, 0.2); }
  100% { background: transparent; }
}
</style>
