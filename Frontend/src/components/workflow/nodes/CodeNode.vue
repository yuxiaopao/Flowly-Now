<template>
  <div
    class="code-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
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
        :id="id ? `node-label-${id}` : undefined"
        name="node-label"
        v-model="localName"
        class="node-name-input"
        placeholder="代码节点..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div
      v-if="!isExpanded"
      class="compact-view"
    >
      <div class="code-preview">
        <pre class="preview-code">{{ codePreview }}</pre>
      </div>
    </div>

    <div
      v-if="isRunning || isCompleted || isFailed"
      class="execution-zone"
    >
      <div class="exec-header">
        <Terminal class="exec-icon" />
        <span class="exec-label">执行结果</span>
        <span
          class="exec-status"
          :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
        >
          <span v-if="isRunning">
            <Loader class="status-icon spinning" /> 运行中
          </span>
          <span v-else-if="isCompleted">
            <CheckCircle class="status-icon ok" /> 成功
          </span>
          <span v-else-if="isFailed">
            <XCircle class="status-icon err" /> 失败
          </span>
        </span>
        <button
          v-if="execResult && !isRunning"
          class="copy-btn"
          :class="{ copied }"
          @click.stop="copyOutput"
        >
          <Check
            v-if="copied"
            class="copy-icon"
          />
          <Copy
            v-else
            class="copy-icon"
          />
        </button>
      </div>
      <div class="exec-output">
        <div
          v-if="execResult !== null"
          class="output-block"
        >
          <pre
            class="output-text"
            :class="{ 'error-output': isFailed }"
          >{{ truncateOutput(execResult) }}</pre>
        </div>
        <div
          v-else
          class="output-empty"
        >
          <span v-if="isRunning">执行中...</span>
          <span v-else>等待执行</span>
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
          <label class="config-label">JavaScript 代码</label>
          <el-input
            v-model="localConfig.code"
            type="textarea"
            :rows="6"
            size="small"
            placeholder="input = input&#10;output = {'result': input}"
            class="code-editor"
            @input="handleChange"
          />
        </div>
        <div class="config-hint">
          <span class="hint-icon">💡</span>
          <span>可用变量: <code>input</code> (输入), <code>output</code> (必须设置)</span>
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
import { ref, computed, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Code, ChevronDown, Terminal, CheckCircle, XCircle, Loader, Copy, Check } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'code'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const localName = ref(props.data.label || '代码执行')
const localConfig = ref({
  code: props.data.config?.code || 'input = input\noutput = {"result": input}',
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const copied = ref(false)

async function copyOutput() {
  if (!execResult.value) return
  try {
    await navigator.clipboard.writeText(execResult.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (e) {
    console.error('Copy failed', e)
  }
}

const execResult = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.result !== undefined) return JSON.stringify(nodeOutput.value.result)
  if (nodeOutput.value.output !== undefined) return typeof nodeOutput.value.output === 'object' ? JSON.stringify(nodeOutput.value.output) : nodeOutput.value.output
  if (nodeOutput.value.data !== undefined) return typeof nodeOutput.value.data === 'object' ? JSON.stringify(nodeOutput.value.data) : nodeOutput.value.data
  return null
})

const codePreview = computed(() => {
  const code = localConfig.value.code || ''
  const lines = code.split('\n').slice(0, 2)
  return lines.join('\n') + (code.split('\n').length > 2 ? '\n...' : '')
})

function truncateOutput(str) {
  if (!str) return ''
  return str.length > 200 ? str.slice(0, 200) + '\n...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '代码执行'
    localConfig.value = { code: d.config?.code || 'input = input\noutput = {"result": input}' }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
  isExpanded.value = !isExpanded.value
}

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.code-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid var(--node-border, #f97316);
  border-radius: 12px;
  min-width: 200px;
  max-width: 300px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.selected { box-shadow: 0 8px 32px rgba(249, 115, 22, 0.2), 0 0 0 2px rgba(249, 115, 22, 0.3); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px rgba(249, 115, 22, 0.12); transform: translateY(-1px); }
  &.is-running { animation: code-pulse 1.8s ease-in-out infinite; }
  &.is-completed .execution-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes code-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(249, 115, 22, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(249, 115, 22, 0); }
}

.execution-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(249, 115, 22, 0.2);
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.exec-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(249, 115, 22, 0.15);
  background: rgba(249, 115, 22, 0.05);

  .exec-icon { width: 11px; height: 11px; color: rgba(249, 115, 22, 0.6); }
  .exec-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(249, 115, 22, 0.7); flex: 1; }
}

.exec-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  font-weight: 600;

  .status-icon { width: 10px; height: 10px; }
  .spinning { animation: spin 1s linear infinite; }
  .ok { color: #10b981; }
  .err { color: #ef4444; }

  &.running { color: #f97316; }
  &.completed { color: #10b981; }
  &.failed { color: #ef4444; }
}

.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s ease;
  margin-left: auto;

  .copy-icon { width: 11px; height: 11px; }

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }

  &.copied {
    background: rgba(16, 185, 129, 0.15);
    border-color: rgba(16, 185, 129, 0.3);
    color: #10b981;
  }
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.exec-output {
  padding: 8px 10px;
  max-height: 80px;
  overflow: auto;
}

.output-block {
  .output-text {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: #a5d6ff;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
    background: rgba(0, 0, 0, 0.2);
    padding: 6px 8px;
    border-radius: 4px;

    &.error-output {
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.2);
    }
  }
}

.output-empty {
  font-size: 10px;
  color: rgba(249, 115, 22, 0.4);
  font-style: italic;
}

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: rgba(249, 115, 22, 0.08); border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; background: rgba(249, 115, 22, 0.2); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #fb923c; .badge-icon { width: 11px; height: 11px; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 8px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e2e8f0); outline: none; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: rgba(249, 115, 22, 0.5); background: rgba(249, 115, 22, 0.05); } }
.compact-view { padding: 0 12px 10px; }
.code-preview { font-size: 10px; font-family: 'JetBrains Mono', monospace; color: #94a3b8; background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 6px 8px; overflow: hidden; max-height: 40px; line-height: 1.4; .preview-code { margin: 0; white-space: pre; } }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 8px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
.code-editor :deep(.el-textarea__inner) { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; line-height: 1.5 !important; background: #0d1117 !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; color: #a5d6ff !important; box-shadow: none !important; border-radius: 8px !important; }
.config-hint { display: flex; align-items: flex-start; gap: 6px; padding: 6px 8px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.15); border-radius: 6px; font-size: 10px; color: rgba(255, 255, 255, 0.4); line-height: 1.4; .hint-icon { font-size: 12px; } code { background: rgba(245, 158, 11, 0.15); color: #fbbf24; padding: 1px 4px; border-radius: 3px; font-family: 'JetBrains Mono', monospace; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: #1e1e2e; border: 2px solid #f97316; border-radius: 50%; &:hover { background: #f97316; transform: scale(1.3); } }
:global(.dark) { .code-node { --node-bg: #1e1e2e; --node-border: #f97316; --node-text: #e2e8f0; } }
:global(.light) { .code-node { --node-bg: #fff; --node-border: #f97316; --node-text: #1e293b; } }
</style>
