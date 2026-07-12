<template>
  <div class="node-execution-timeline">
    <div class="timeline-header">
      <span class="header-label">执行时间线</span>
      <span
        v-if="isRunning"
        class="live-indicator"
      >
        <span class="live-dot" />
        实时更新中
      </span>
    </div>

    <div class="timeline-nodes">
      <div
        v-for="(node, index) in nodes"
        :key="node.id || node.node_id"
        class="timeline-node"
        :class="[
          node.status,
          { active: (node.id || node.node_id) === activeNodeId }
        ]"
        @click="handleNodeClick(node)"
      >
        <!-- Connector Line -->
        <div
          v-if="index > 0"
          class="connector-line"
          :class="nodes[index - 1].status"
        />

        <!-- Node Indicator -->
        <div class="node-indicator">
          <div class="indicator-icon">
            <Loader
              v-if="node.status === 'running'"
              class="icon-spin"
            />
            <CheckCircle
              v-else-if="node.status === 'completed'"
              class="icon-success"
            />
            <XCircle
              v-else-if="node.status === 'failed'"
              class="icon-error"
            />
            <Minus
              v-else-if="node.status === 'skipped'"
              class="icon-skipped"
            />
            <Circle
              v-else
              class="icon-pending"
            />
          </div>
          <div class="node-line" />
        </div>

        <!-- Node Content -->
        <div class="node-content">
          <div class="node-header">
            <span class="node-name">{{ node.name || node.label || `节点 ${node.id || node.node_id}` }}</span>
            <span
              class="node-status-badge"
              :class="node.status"
            >
              {{ statusLabel(node.status) }}
            </span>
          </div>

          <div class="node-meta">
            <span class="node-type-badge">
              <component
                :is="getNodeTypeIcon(node.type)"
                class="type-icon"
              />
              {{ node.type }}
            </span>
            <span
              v-if="nodeDurationMs(node)"
              class="node-duration"
            >
              <Clock class="duration-icon" />
              {{ formatDuration(nodeDurationMs(node)) }}
            </span>
          </div>

          <!-- LLM Node Metrics -->
          <div
            v-if="node.type === 'llm' && ((node.promptTokens ?? node.prompt_tokens) || (node.completionTokens ?? node.completion_tokens))"
            class="llm-metrics"
          >
            <span class="metric">
              <span class="metric-label">Prompt:</span>
              <span class="metric-value">{{ node.promptTokens ?? node.prompt_tokens ?? 0 }}</span>
            </span>
            <span class="metric">
              <span class="metric-label">Completion:</span>
              <span class="metric-value">{{ node.completionTokens ?? node.completion_tokens ?? 0 }}</span>
            </span>
            <span
              v-if="node.model"
              class="metric"
            >
              <span class="metric-label">Model:</span>
              <span class="metric-value">{{ node.model }}</span>
            </span>
          </div>

          <!-- Error Message -->
          <div
            v-if="node.error"
            class="node-error"
          >
            <AlertCircle class="error-icon" />
            {{ truncateError(node.error) }}
          </div>

          <!-- Output Preview -->
          <div
            v-if="node.output && node.status === 'completed'"
            class="node-output-preview"
          >
            <ChevronDown class="preview-icon" />
            {{ truncateOutput(node.output) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!nodes || nodes.length === 0"
      class="empty-state"
    >
      <Activity class="empty-icon" />
      <p>暂无节点执行数据</p>
    </div>
  </div>
</template>

<script setup>
import {
  Loader, CheckCircle, XCircle, Circle, Minus,
  Clock, AlertCircle, ChevronDown, Activity,
  Play, FileText, Code, Zap, Globe, Database, Branches, ArrowRight
} from 'lucide-vue-next'

defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  activeNodeId: {
    type: [String, Number],
    default: null
  },
  isRunning: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['node-click'])

function handleNodeClick(node) {
  emit('node-click', node.id || node.node_id)
}

function statusLabel(status) {
  const labels = {
    pending: '待处理',
    running: '执行中',
    completed: '成功',
    failed: '失败',
    skipped: '跳过'
  }
  return labels[status] || status || '-'
}

function nodeDurationMs(node) {
  if (!node) return null
  if (node.durationMs != null) return node.durationMs
  if (node.duration_ms != null) return node.duration_ms
  if (node.duration != null) return Math.round(Number(node.duration) * 1000)
  return null
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.floor(ms / 60000)}分${Math.round((ms % 60000) / 1000)}秒`
}

function truncateError(error) {
  if (!error) return ''
  const str = typeof error === 'string' ? error : JSON.stringify(error)
  return str.length > 80 ? str.substring(0, 80) + '...' : str
}

function truncateOutput(output) {
  if (!output) return ''
  const str = typeof output === 'string' ? output : JSON.stringify(output)
  return str.length > 100 ? str.substring(0, 100) + '...' : str
}

function getNodeTypeIcon(type) {
  const iconMap = {
    start: Play,
    end: ArrowRight,
    llm: Zap,
    prompt: FileText,
    http: Globe,
    tool: Branches,
    code: Code,
    condition: Branches,
    loop: Database,
    input: FileText,
    output: FileText,
    variable: Database,
    delay: Clock
  }
  return iconMap[type] || Circle
}
</script>

<style lang="scss" scoped>
.node-execution-timeline {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 16px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-primary);

  .header-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .live-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--success);

    .live-dot {
      width: 8px;
      height: 8px;
      background: var(--success);
      border-radius: 50%;
      animation: pulse 1.5s infinite;
    }
  }
}

.timeline-nodes {
  position: relative;
}

.timeline-node {
  position: relative;
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease;

  &:hover {
    background: var(--bg-hover);

    .node-content {
      .node-name {
        color: var(--color-primary);
      }
    }
  }

  &.active {
    background: var(--color-primary-10);

    .node-indicator .indicator-icon {
      transform: scale(1.1);
    }
  }

  &.running {
    .node-indicator .indicator-icon {
      background: var(--info-bg);
    }
  }

  &.completed {
    .node-indicator .indicator-icon {
      background: var(--success-bg);
    }
  }

  &.failed {
    .node-indicator .indicator-icon {
      background: var(--error-bg);
    }
  }
}

.connector-line {
  position: absolute;
  left: 31px;
  top: -12px;
  width: 2px;
  height: 12px;
  background: var(--border-primary);

  &.completed {
    background: var(--success);
  }

  &.failed {
    background: var(--error);
  }

  &.running {
    background: var(--info);
  }
}

.node-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;

  .indicator-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--bg-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s ease, transform 0.2s ease;

    svg {
      width: 18px;
      height: 18px;
    }

    .icon-spin {
      color: var(--info);
      animation: spin 1s linear infinite;
    }

    .icon-success {
      color: var(--success);
    }

    .icon-error {
      color: var(--error);
    }

    .icon-skipped {
      color: var(--text-tertiary);
    }

    .icon-pending {
      color: var(--text-disabled);
    }
  }

  .node-line {
    flex: 1;
    width: 2px;
    background: var(--border-primary);
    margin-top: 4px;

    .timeline-node:last-child & {
      display: none;
    }
  }
}

.node-content {
  flex: 1;
  min-width: 0;

  .node-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    .node-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      transition: color 0.2s;
    }

    .node-status-badge {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 500;
      transition: background-color 0.2s ease, color 0.2s ease;

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

      &.skipped {
        background: var(--surface-muted);
        color: var(--text-tertiary);
      }
    }
  }
}

.node-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;

  .node-type-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: capitalize;

    .type-icon {
      width: 12px;
      height: 12px;
    }
  }

  .node-duration {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-tertiary);

    .duration-icon {
      width: 12px;
      height: 12px;
    }
  }
}

.llm-metrics {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--surface-muted);
  border-radius: 6px;

  .metric {
    display: flex;
    gap: 4px;
    font-size: 12px;

    .metric-label {
      color: var(--text-tertiary);
    }

    .metric-value {
      font-family: 'JetBrains Mono', monospace;
      color: var(--accent-violet);
    }
  }
}

.node-error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--error-bg);
  border-radius: 6px;
  font-size: 12px;
  color: var(--error);

  .error-icon {
    width: 14px;
    height: 14px;
    flex-shrink: 0;
    margin-top: 1px;
  }
}

.node-output-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background: var(--bg-hover);
  }

  .preview-icon {
    width: 12px;
    height: 12px;
    transition: transform 0.2s;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px;
  text-align: center;

  .empty-icon {
    width: 48px;
    height: 48px;
    color: var(--text-disabled);
    margin-bottom: 12px;
  }

  p {
    margin: 0;
    font-size: 14px;
    color: var(--text-secondary);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
