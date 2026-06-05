<template>
  <div
    class="agent-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <div
        class="node-type-badge"
        :style="{ backgroundColor: nodeColor + '22', borderColor: nodeColor }"
      >
        <Bot
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">Agent</span>
      </div>
      <button
        class="action-btn"
        @click.stop="toggleExpand"
      >
        <ChevronDown
          class="action-icon"
          :class="{ rotated: isExpanded }"
        />
      </button>
    </div>

    <div class="node-name-section">
      <input
        v-model="localName"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.agentType || localConfig.framework"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.agentType || localConfig.framework || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description || localConfig.task"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description || localConfig.task, 35) }}</span>
      </div>
      <div
        class="status-bar"
        :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
      >
        <div
          v-if="isRunning"
          class="status-running"
        >
          <Loader class="status-icon spinning" />
          <span>思考中...</span>
          <span
            v-if="currentIteration > 0"
            class="iter-badge"
          >#{{ currentIteration }}</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="totalIterations > 0"
            class="iter-badge"
          >{{ totalIterations }} 步</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>执行失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="thinking-zone"
    >
      <div class="thinking-header">
        <Brain class="thinking-icon" />
        <span class="thinking-label">思维链</span>
        <span
          v-if="totalIterations > 0"
          class="iter-count"
        >{{ totalIterations }} 步</span>
      </div>
      <div class="thought-list">
        <div
          v-for="(thought, i) in thoughts.slice(0, 3)"
          :key="i"
          class="thought-item"
          :class="{ latest: i === thoughts.length - 1 }"
        >
          <div class="thought-meta">
            <span class="thought-step">{{ getThoughtLabel(thought, i) }}</span>
            <span
              v-if="thought.timestamp || thought.time"
              class="thought-time"
            >{{ formatTime(thought.timestamp || thought.time) }}</span>
          </div>
          <div class="thought-content">
            <span class="thought-text">{{ truncate(getThoughtText(thought), 45) }}</span>
          </div>
        </div>
        <div
          v-if="thoughts.length === 0"
          class="thinking-empty"
        >
          <span>等待思考过程</span>
        </div>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">Agent 类型</label>
          <el-select
            v-model="localConfig.agentType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="react"
              label="ReAct"
            />
            <el-option
              value="plan-execute"
              label="Plan-and-Execute"
            />
            <el-option
              value="tool-calling"
              label="Tool Calling"
            />
            <el-option
              value="conversational"
              label="Conversational"
            />
            <el-option
              value="self-ask"
              label="Self-Ask"
            />
            <el-option
              value="custom"
              label="自定义"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">框架</label>
          <el-input
            v-model="localConfig.framework"
            size="small"
            placeholder="Agent 框架"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">任务描述</label>
          <el-input
            v-model="localConfig.task"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="Agent 任务描述..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">工具列表</label>
          <el-input
            v-model="localConfig.tools"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="可用工具名称 (逗号分隔)"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">最大迭代次数</label>
          <el-input-number
            v-model="localConfig.maxIterations"
            :min="1"
            :max="100"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="Agent 描述..."
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Bot, ChevronDown, Loader, Brain } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const nodeColor = '#8b5cf6'

const localName = ref(props.data.label || 'Agent')
const localConfig = ref({
  agentType: props.data.config?.agentType || 'react',
  framework: props.data.config?.framework || '',
  task: props.data.config?.task || '',
  tools: props.data.config?.tools || '',
  maxIterations: props.data.config?.maxIterations || 10,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const thoughts = computed(() => {
  if (!nodeOutput.value) return []
  if (Array.isArray(nodeOutput.value.thoughts)) return nodeOutput.value.thoughts
  if (Array.isArray(nodeOutput.value.chain)) return nodeOutput.value.chain
  if (Array.isArray(nodeOutput.value.steps)) return nodeOutput.value.steps
  if (Array.isArray(nodeOutput.value.logs)) return nodeOutput.value.logs
  if (Array.isArray(nodeOutput.value.trace)) return nodeOutput.value.trace
  if (Array.isArray(nodeOutput.value.thinking)) return nodeOutput.value.thinking
  if (Array.isArray(nodeOutput.value)) return nodeOutput.value
  return []
})

const totalIterations = computed(() => thoughts.value.length || nodeOutput.value?.iterations || nodeOutput.value?.totalSteps || nodeOutput.value?.total || 0)
const currentIteration = computed(() => nodeOutput.value?.currentIteration || nodeOutput.value?.step || 0)

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function getThoughtText(thought) {
  if (typeof thought === 'string') return thought
  return thought.text || thought.content || thought.thought || thought.action || thought.description || JSON.stringify(thought)
}

function getThoughtLabel(thought, i) {
  if (thought.type) return thought.type
  if (thought.action) return thought.action
  if (thought.role) return thought.role
  return '思考 ' + (i + 1)
}

function formatTime(ts) {
  if (!ts) return ''
  if (typeof ts === 'number') {
    if (ts > 1e12) return (ts / 1000).toFixed(1) + 's'
    return ts.toFixed(1) + 'ms'
  }
  return ''
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || 'Agent'
    localConfig.value = { agentType: d.config?.agentType || 'react', framework: d.config?.framework || '', task: d.config?.task || '', tools: d.config?.tools || '', maxIterations: d.config?.maxIterations || 10, description: d.config?.description || '', ...d.config }
  }
}, { deep: true })

function toggleExpand() { isExpanded.value = !isExpanded.value }

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.agent-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent);
    transform: translateY(-1px);
  }

  &.is-running { animation: agent-pulse 1.8s ease-in-out infinite; }
  &.is-completed .thinking-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes agent-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(139, 92, 246, 0); }
}

.thinking-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(139, 92, 246, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.15);
  background: rgba(139, 92, 246, 0.05);

  .thinking-icon { width: 11px; height: 11px; color: rgba(139, 92, 246, 0.6); }
  .thinking-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(139, 92, 246, 0.7); flex: 1; }
  .iter-count { font-size: 9px; font-weight: 600; background: rgba(139, 92, 246, 0.15); color: #a78bfa; padding: 1px 6px; border-radius: 10px; border: 1px solid rgba(139, 92, 246, 0.3); }
}

.thought-list { padding: 6px 8px; display: flex; flex-direction: column; gap: 3px; }

.thought-item {
  padding: 4px 6px;
  border-radius: 4px;
  background: rgba(139, 92, 246, 0.03);
  border: 1px solid transparent;
  transition: all 0.2s ease;

  &.latest {
    background: rgba(139, 92, 246, 0.08);
    border-color: rgba(139, 92, 246, 0.2);
    animation: thought-flash 2s ease-in-out;
    line-clamp: 1;
  }
}

@keyframes thought-flash {
  0% { background: rgba(139, 92, 246, 0.2); }
  100% { background: rgba(139, 92, 246, 0.08); }
}

.thought-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}

.thought-step { font-size: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #a78bfa; }
.thought-time { font-size: 8px; font-family: 'JetBrains Mono', monospace; color: rgba(139, 92, 246, 0.4); }

  .thought-content { .thought-text { font-size: 9px; color: rgba(255, 255, 255, 0.6); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; } }

.thinking-empty { text-align: center; padding: 12px 0; font-size: 10px; color: rgba(139, 92, 246, 0.3); font-style: italic; }

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.iter-badge { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(139, 92, 246, 0.6); margin-left: auto; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; border: 1px solid; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; .badge-icon { width: 11px; height: 11px; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 10px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); } }
.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 4px; }
.info-row { display: flex; align-items: center; gap: 6px; .info-label { font-size: 10px; color: rgba(255, 255, 255, 0.4); } .info-value { font-size: 11px; color: rgba(255, 255, 255, 0.7); font-family: 'JetBrains Mono', monospace; } }
.preview-row .preview-text { font-size: 10px; color: rgba(255, 255, 255, 0.6); line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
:deep(.el-select), :deep(.el-input), :deep(.el-input-number) { width: 100%; .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; border-radius: 6px; } .el-input__inner { color: var(--node-text, #e5e5e5) !important; font-size: 12px !important; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: rgba(10, 10, 18, 0.95); border: 2px solid v-bind(nodeColor); border-radius: 50%; &:hover { background: v-bind(nodeColor); transform: scale(1.3); } }
:global(.dark) { .agent-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #8b5cf6; --node-text: #e5e5e5; } }
:global(.light) { .agent-node { --node-bg: #fff; --node-border: #8b5cf6; --node-text: #1e1e2e; } }
</style>
