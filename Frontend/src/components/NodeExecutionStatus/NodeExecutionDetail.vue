<template>
  <div
    v-loading="isLoading"
    class="node-execution-detail"
  >
    <!-- Node Header -->
    <div class="detail-header">
      <div class="node-info">
        <div class="node-title">
          <span class="node-name">{{ node.name || node.label || '未知节点' }}</span>
          <span class="node-type-badge">{{ node.type }}</span>
        </div>
        <div class="node-status-row">
          <span
            class="status-badge"
            :class="node.status"
          >
            <component
              :is="statusIcon"
              class="status-icon"
            />
            {{ statusLabel }}
          </span>
          <span
            v-if="node.duration_ms || node.duration"
            class="duration"
          >
            <Clock class="duration-icon" />
            {{ formatDuration(node.duration_ms || node.duration) }}
          </span>
        </div>
      </div>
    </div>

    <!-- LLM Node Special Display -->
    <div
      v-if="node.type === 'llm'"
      class="llm-detail-section"
    >
      <h3 class="section-title">
        <Zap class="section-icon" />
        LLM 执行详情
      </h3>

      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-value">{{ node.prompt_tokens || 0 }}</span>
          <span class="metric-label">Prompt Tokens</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ node.completion_tokens || 0 }}</span>
          <span class="metric-label">Completion Tokens</span>
        </div>
        <div class="metric-card">
          <span class="metric-value">{{ (node.prompt_tokens || 0) + (node.completion_tokens || 0) }}</span>
          <span class="metric-label">Total Tokens</span>
        </div>
        <div
          v-if="node.model"
          class="metric-card"
        >
          <span class="metric-value model">{{ node.model }}</span>
          <span class="metric-label">Model</span>
        </div>
      </div>

      <div
        v-if="node.input || node.prompt"
        class="detail-block"
      >
        <div class="block-header">
          <h4>输入 Prompt</h4>
          <el-button
            size="small"
            text
            @click="copyContent(node.input || node.prompt)"
          >
            <Copy class="btn-icon-small" />
            复制
          </el-button>
        </div>
        <pre class="block-content">{{ formatContent(node.input || node.prompt) }}</pre>
      </div>

      <div
        v-if="node.output || node.content"
        class="detail-block"
      >
        <div class="block-header">
          <h4>输出内容</h4>
          <el-button
            size="small"
            text
            @click="copyContent(node.output || node.content)"
          >
            <Copy class="btn-icon-small" />
            复制
          </el-button>
        </div>
        <pre class="block-content output">{{ formatContent(node.output || node.content) }}</pre>
      </div>
    </div>

    <!-- Generic Node Display -->
    <template v-else>
      <!-- Input Section -->
      <div
        v-if="hasInput"
        class="detail-block"
      >
        <div class="block-header">
          <h4>
            <ArrowDown class="block-icon" />
            输入
          </h4>
          <el-button
            size="small"
            text
            @click="copyContent(node.input)"
          >
            <Copy class="btn-icon-small" />
            复制
          </el-button>
        </div>
        <pre class="block-content">{{ formatContent(node.input) }}</pre>
      </div>

      <!-- Output Section -->
      <div
        v-if="hasOutput"
        class="detail-block"
      >
        <div class="block-header">
          <h4>
            <ArrowUp class="block-icon" />
            输出
          </h4>
          <el-button
            size="small"
            text
            @click="copyContent(node.output)"
          >
            <Copy class="btn-icon-small" />
            复制
          </el-button>
        </div>
        <pre class="block-content output">{{ formatContent(node.output) }}</pre>
      </div>

      <!-- HTTP Node Specific -->
      <div
        v-if="node.type === 'http' && node.status_code"
        class="detail-block"
      >
        <div class="block-header">
          <h4>
            <Globe class="block-icon" />
            HTTP 响应
          </h4>
        </div>
        <div class="http-info">
          <span
            class="http-status"
            :class="getHttpStatusClass(node.status_code)"
          >
            {{ node.status_code }} {{ getHttpStatusText(node.status_code) }}
          </span>
          <span
            v-if="node.response_time"
            class="response-time"
          >
            响应时间: {{ node.response_time }}ms
          </span>
        </div>
      </div>

      <!-- Tool Node Specific -->
      <div
        v-if="node.type === 'tool' && node.tool_name"
        class="detail-block"
      >
        <div class="block-header">
          <h4>
            <Wrench class="block-icon" />
            工具调用
          </h4>
        </div>
        <div class="tool-info">
          <span class="tool-name">{{ node.tool_name }}</span>
          <span
            v-if="node.tool_call_id"
            class="tool-call-id"
          >
            ID: {{ node.tool_call_id }}
          </span>
        </div>
      </div>
    </template>

    <!-- Error Section -->
    <div
      v-if="node.error"
      class="error-block"
    >
      <div class="block-header error-header">
        <h4>
          <AlertCircle class="error-icon" />
          错误信息
        </h4>
        <el-button
          size="small"
          text
          @click="copyContent(node.error)"
        >
          <Copy class="btn-icon-small" />
          复制
        </el-button>
      </div>
      <pre class="error-content">{{ formatError(node.error) }}</pre>
    </div>

    <!-- Metadata -->
    <div
      v-if="hasMetadata"
      class="metadata-block"
    >
      <h4 class="metadata-title">
        元数据
      </h4>
      <div class="metadata-grid">
        <div
          v-if="node.id"
          class="metadata-item"
        >
          <span class="metadata-label">节点 ID</span>
          <span class="metadata-value">{{ node.id }}</span>
        </div>
        <div
          v-if="node.started_at"
          class="metadata-item"
        >
          <span class="metadata-label">开始时间</span>
          <span class="metadata-value">{{ formatDateTime(node.started_at) }}</span>
        </div>
        <div
          v-if="node.completed_at"
          class="metadata-item"
        >
          <span class="metadata-label">完成时间</span>
          <span class="metadata-value">{{ formatDateTime(node.completed_at) }}</span>
        </div>
        <div
          v-if="node.retry_count"
          class="metadata-item"
        >
          <span class="metadata-label">重试次数</span>
          <span class="metadata-value">{{ node.retry_count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Clock, Copy, Zap, ArrowDown, ArrowUp, Globe, Wrench,
  AlertCircle, CheckCircle, XCircle, Loader, Circle
} from 'lucide-vue-next'

const props = defineProps({
  node: {
    type: Object,
    default: () => ({})
  },
  isLoading: {
    type: Boolean,
    default: false
  }
})

const statusLabel = computed(() => {
  const labels = {
    pending: '待处理',
    running: '执行中',
    completed: '成功',
    failed: '失败',
    skipped: '跳过'
  }
  return labels[props.node.status] || props.node.status || '-'
})

const statusIcon = computed(() => {
  const icons = {
    pending: Circle,
    running: Loader,
    completed: CheckCircle,
    failed: XCircle,
    skipped: Circle
  }
  return icons[props.node.status] || Circle
})

const hasInput = computed(() => {
  return props.node.input && Object.keys(props.node.input).length > 0
})

const hasOutput = computed(() => {
  return props.node.output && (
    typeof props.node.output === 'string'
      ? props.node.output.length > 0
      : Object.keys(props.node.output).length > 0
  )
})

const hasMetadata = computed(() => {
  return props.node.id || props.node.started_at || props.node.completed_at || props.node.retry_count
})

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.floor(ms / 60000)}分${Math.round((ms % 60000) / 1000)}秒`
}

function formatContent(content) {
  if (!content) return ''
  if (typeof content === 'string') {
    try {
      return JSON.stringify(JSON.parse(content), null, 2)
    } catch {
      return content
    }
  }
  return JSON.stringify(content, null, 2)
}

function formatError(error) {
  if (!error) return ''
  if (typeof error === 'string') return error
  return JSON.stringify(error, null, 2)
}

function formatDateTime(date) {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

function getHttpStatusClass(code) {
  if (code >= 200 && code < 300) return 'success'
  if (code >= 300 && code < 400) return 'redirect'
  if (code >= 400 && code < 500) return 'client-error'
  if (code >= 500) return 'server-error'
  return ''
}

function getHttpStatusText(code) {
  const texts = {
    200: 'OK',
    201: 'Created',
    204: 'No Content',
    301: 'Moved Permanently',
    302: 'Found',
    304: 'Not Modified',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    429: 'Too Many Requests',
    500: 'Internal Server Error',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout'
  }
  return texts[code] || ''
}

function copyContent(content) {
  const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2)
  navigator.clipboard.writeText(text)
    .then(() => ElMessage.success('已复制到剪贴板'))
    .catch(() => ElMessage.error('复制失败'))
}
</script>

<style lang="scss" scoped>
.node-execution-detail {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  padding: 16px;
}

.detail-header {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);

  .node-info {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .node-title {
    display: flex;
    align-items: center;
    gap: 12px;

    .node-name {
      font-size: 18px;
      font-weight: 600;
      color: var(--el-text-color-primary);
    }

    .node-type-badge {
      padding: 4px 10px;
      background: var(--el-fill-color);
      border-radius: 12px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      text-transform: capitalize;
    }
  }

  .node-status-row {
    display: flex;
    align-items: center;
    gap: 16px;

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 13px;
      font-weight: 500;

      .status-icon {
        width: 14px;
        height: 14px;
      }

      &.pending {
        background: rgba(107, 114, 128, 0.1);
        color: #6b7280;
      }

      &.running {
        background: rgba(59, 130, 246, 0.1);
        color: #3b82f6;

        .status-icon {
          animation: spin 1s linear infinite;
        }
      }

      &.completed {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
      }

      &.failed {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
      }

      &.skipped {
        background: rgba(156, 163, 175, 0.1);
        color: #9ca3af;
      }
    }

    .duration {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--el-text-color-secondary);

      .duration-icon {
        width: 14px;
        height: 14px;
      }
    }
  }
}

.llm-detail-section {
  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 16px;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);

    .section-icon {
      width: 18px;
      height: 18px;
      color: #8b5cf6;
    }
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 20px;

  .metric-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 16px;
    background: var(--el-bg-color);
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;

    .metric-value {
      font-size: 24px;
      font-weight: 700;
      color: var(--el-text-color-primary);
      font-family: 'JetBrains Mono', monospace;

      &.model {
        font-size: 14px;
        font-weight: 600;
        color: #8b5cf6;
      }
    }

    .metric-label {
      margin-top: 4px;
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

.detail-block {
  margin-bottom: 16px;

  .block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;

    h4 {
      display: flex;
      align-items: center;
      gap: 6px;
      margin: 0;
      font-size: 14px;
      font-weight: 600;
      color: var(--el-text-color-primary);

      .block-icon {
        width: 16px;
        height: 16px;
        color: var(--el-text-color-secondary);
      }
    }
  }

  .block-content {
    padding: 16px;
    margin: 0;
    background: #1e1e2e;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #e5e7eb;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow: auto;

    &.output {
      border-left: 3px solid #10b981;
    }
  }
}

.http-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border-radius: 8px;

  .http-status {
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: 600;

    &.success {
      background: rgba(16, 185, 129, 0.1);
      color: #10b981;
    }

    &.redirect {
      background: rgba(59, 130, 246, 0.1);
      color: #3b82f6;
    }

    &.client-error {
      background: rgba(245, 158, 11, 0.1);
      color: #f59e0b;
    }

    &.server-error {
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }
  }

  .response-time {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

.tool-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 16px;
  background: var(--el-bg-color);
  border-radius: 8px;

  .tool-name {
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .tool-call-id {
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--el-text-color-secondary);
  }
}

.error-block {
  margin-bottom: 16px;

  .error-header {
    h4 {
      color: #ef4444;

      .error-icon {
        color: #ef4444;
      }
    }
  }

  .error-content {
    padding: 16px;
    margin: 0;
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #ef4444;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow: auto;
  }
}

.metadata-block {
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);

  .metadata-title {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 600;
    color: var(--el-text-color-primary);
  }

  .metadata-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;

    .metadata-item {
      display: flex;
      flex-direction: column;
      gap: 4px;

      .metadata-label {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }

      .metadata-value {
        font-size: 13px;
        font-family: 'JetBrains Mono', monospace;
        color: var(--el-text-color-primary);
      }
    }
  }
}

.btn-icon-small {
  width: 14px;
  height: 14px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
