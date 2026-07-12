<template>
  <div
    ref="rootEl"
    class="domain-node input-node"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    :class="{
      selected,
      'is-running': isRunning,
      'is-completed': isCompleted,
      'is-failed': isFailed,
      'needs-input': needsInputHighlight,
      'is-focused': isFocused,
    }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <Handle
      type="source"
      :position="Position.Right"
    />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
      <div class="header-actions">
        <button
          v-if="localInput.trim()"
          type="button"
          class="icon-btn"
          title="全选（Ctrl+A）"
          @click.stop="selectAllText"
        >
          <TextSelect class="icon-sm" />
        </button>
        <button
          v-if="localInput.trim()"
          type="button"
          class="icon-btn icon-btn-danger"
          title="清空内容"
          @click.stop="clearInput"
        >
          <X class="icon-sm" />
        </button>
      </div>
    </div>

    <div
      v-if="localLabel"
      class="node-name-section"
    >
      <span class="node-label">{{ localLabel }}</span>
    </div>

    <div
      class="input-body nodrag nopan nowheel"
      @mousedown.stop
      @pointerdown.stop
    >
      <textarea
        :id="id ? `user-input-${id}` : undefined"
        ref="textareaRef"
        v-model="localInput"
        class="prompt-textarea nodrag nopan nowheel"
        :placeholder="placeholderText"
        rows="3"
        spellcheck="false"
        @focus="onFocus"
        @blur="onBlur"
        @input="onInput"
        @mousedown.stop
        @pointerdown.stop
        @click.stop="onTextareaClick"
        @keydown.ctrl.a.stop
        @keydown.meta.a.stop
      />
      <div class="input-meta">
        <span class="var-chip">{{ variableLabel }}</span>
        <span class="char-count">{{ charCount }}</span>
      </div>
    </div>

    <div
      v-if="isRunning || isCompleted || isFailed"
      class="status-bar"
      :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
    >
      <div
        v-if="isRunning"
        class="status-running"
      >
        <Loader class="status-icon spinning" />
        <span>提交中...</span>
      </div>
      <div
        v-else-if="isCompleted"
        class="status-done"
      >
        <span class="status-dot" />
        <span>已提交 · 将传递给下游节点</span>
      </div>
      <div
        v-else-if="isFailed"
        class="status-error"
      >
        <span class="status-dot" />
        <span>{{ nodeOutput?.error || '执行失败' }}</span>
      </div>
    </div>

    <div
      v-if="isCompleted && displayPrompt"
      class="result-preview"
    >
      <div class="result-preview-label">
        已输出
      </div>
      <p class="result-preview-text">
        {{ displayPrompt }}
      </p>
    </div>

    <div class="input-hint">
      可拖选文本 · Ctrl+A 全选 · 自动保存
    </div>

    <div
      class="resize-handle"
      title="拖动调整节点大小"
      @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed, nextTick, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Loader, X, TextSelect } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import { useNodeResize } from '@/composables/useNodeResize'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { unwrapNodeExecutionOutput } from '@/utils/workflowTransform'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'

const NODE_TYPE = 'input'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const { nodeColor } = useNodePresentation(NODE_TYPE)

const executionStore = useExecutionStore()
const { nodeOutputs, nodeStatusMap } = storeToRefs(executionStore)

const rootEl = ref(null)
const textareaRef = ref(null)
const isFocused = ref(false)
let saveTimer = null

const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 220,
  minHeight: 140,
  maxWidth: 520,
  maxHeight: 420,
})

const nodeStatus = computed(() => nodeStatusMap.value[props.id])
const nodeOutput = computed(() => unwrapNodeExecutionOutput(nodeOutputs.value[props.id]))
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const needsInputHighlight = computed(() => Boolean(props.data?._needsInput))

const localLabel = computed(() => props.data?.label || '')

const localConfig = ref({
  placeholder: props.data.config?.placeholder || '描述你想生成的画面…',
  inputType: props.data.config?.inputType || props.data.config?.input_type || 'text',
  input_name: props.data.config?.input_name || props.data.config?.variableName || 'prompt',
})

const placeholderText = computed(() => localConfig.value.placeholder || '描述你想生成的画面…')

const variableLabel = computed(() => {
  const name = localConfig.value.input_name || 'prompt'
  return `{${name}}`
})

function readStoredInput(config = {}) {
  const raw = config.userInput ?? config.user_input ?? config.default ?? config.value
  return raw != null ? String(raw) : ''
}

const localInput = ref(readStoredInput(props.data?.config || {}))

const charCount = computed(() => {
  const len = localInput.value.length
  return len ? `${len} 字` : '未填写'
})

const displayPrompt = computed(() => {
  const out = nodeOutput.value
  if (typeof out === 'string' && out.trim()) return out.trim()
  if (out && typeof out === 'object') {
    const value = out.prompt || out.user_input || out.userInput || out.text || out.input
    if (value) return String(value).trim()
  }
  return localInput.value.trim()
})

function autoResizeTextarea() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  const max = Math.max(120, (rootEl.value?.clientHeight || 280) - 120)
  el.style.height = `${Math.min(el.scrollHeight, max)}px`
}

function persistInput() {
  if (!props.id) return
  updateNodeData(props.id, {
    config: {
      ...(props.data?.config || {}),
      ...localConfig.value,
      userInput: localInput.value,
      user_input: localInput.value,
      default: localInput.value,
      value: localInput.value,
    },
  })
}

function handleChange() {
  persistInput()
}

function scheduleSave() {
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => {
    persistInput()
    saveTimer = null
  }, 350)
}

function onInput() {
  autoResizeTextarea()
  scheduleSave()
}

function onBlur() {
  isFocused.value = false
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  handleChange()
}

function onFocus() {
  isFocused.value = true
  emit('select')
}

function onTextareaClick() {
  emit('select')
}

function selectAllText() {
  const el = textareaRef.value
  if (!el) return
  el.focus()
  el.select()
}

function clearInput() {
  localInput.value = ''
  handleChange()
  nextTick(() => {
    autoResizeTextarea()
    textareaRef.value?.focus()
  })
}

function handleSelect() {
  emit('select')
}

watch(() => props.data, (d) => {
  if (!d) return
  localConfig.value = {
    placeholder: d.config?.placeholder || '描述你想生成的画面…',
    inputType: d.config?.inputType || d.config?.input_type || 'text',
    input_name: d.config?.input_name || d.config?.variableName || 'prompt',
  }
  const stored = readStoredInput(d.config || {})
  if (stored !== localInput.value && !isFocused.value) {
    localInput.value = stored
    nextTick(autoResizeTextarea)
  }
}, { deep: true })

watch(isCompleted, (done) => {
  if (done) nextTick(autoResizeTextarea)
})

onMounted(() => {
  nextTick(autoResizeTextarea)
})
</script>

<style lang="scss" scoped>
.domain-node {
  --node-bg: rgba(20, 20, 30, 0.95);
  --node-text: #e5e5e5;
  position: relative;
  background: var(--node-bg);
  border: 2px solid var(--node-accent, #06b6d4);
  border-radius: 12px;
  min-width: 220px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  cursor: default;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  &.selected {
    box-shadow: 0 8px 32px color-mix(in srgb, var(--node-accent) 30%, transparent),
      0 0 0 2px color-mix(in srgb, var(--node-accent) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, var(--node-accent) 20%, transparent);
    transform: translateY(-1px);
  }

  &.needs-input {
    border-color: #f59e0b;
    box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.35);
  }

  &.is-focused {
    border-color: color-mix(in srgb, var(--node-accent) 80%, white);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.icon-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }

  &.icon-btn-danger:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: rgba(239, 68, 68, 0.35);
    color: #fca5a5;
  }

  .icon-sm {
    width: 12px;
    height: 12px;
  }
}

.node-name-section {
  padding: 8px 12px 0;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text);
  opacity: 0.9;
}

.input-body {
  padding: 10px 12px 6px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  cursor: text;
}

.prompt-textarea {
  width: 100%;
  min-height: 72px;
  max-height: 240px;
  resize: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--node-text);
  font-size: 13px;
  line-height: 1.55;
  padding: 10px 12px;
  outline: none;
  font-family: inherit;
  cursor: text;
  user-select: text;
  -webkit-user-select: text;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;

  &::placeholder {
    color: rgba(255, 255, 255, 0.35);
  }

  &:focus {
    border-color: color-mix(in srgb, var(--node-accent) 70%, white);
    background: color-mix(in srgb, var(--node-accent) 8%, transparent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--node-accent) 18%, transparent);
  }
}

.input-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.var-chip {
  font-size: 10px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  color: color-mix(in srgb, var(--node-accent) 85%, white);
  background: color-mix(in srgb, var(--node-accent) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--node-accent) 35%, transparent);
  border-radius: 4px;
  padding: 2px 6px;
}

.char-count {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
}

.status-bar {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;

  &.running {
    background: rgba(59, 130, 246, 0.1);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.25);
  }

  &.completed {
    background: rgba(16, 185, 129, 0.1);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
  }

  &.failed {
    background: rgba(239, 68, 68, 0.1);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
  }
}

.status-running,
.status-done,
.status-error {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;

  &.spinning {
    animation: spin 1s linear infinite;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.result-preview {
  margin: 0 12px 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(16, 185, 129, 0.06);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.result-preview-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(52, 211, 153, 0.85);
  margin-bottom: 4px;
}

.result-preview-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.85);
  word-break: break-word;
  max-height: 120px;
  overflow-y: auto;
}

.input-hint {
  padding: 0 12px 10px;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.28);
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.resize-handle {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 12px;
  height: 12px;
  border-right: 2px solid color-mix(in srgb, var(--node-accent) 55%, transparent);
  border-bottom: 2px solid color-mix(in srgb, var(--node-accent) 55%, transparent);
  cursor: nwse-resize;
  opacity: 0.55;
  z-index: 3;

  &:hover {
    opacity: 1;
  }
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: rgba(10, 10, 18, 0.95);
  border: 2px solid var(--node-accent, #06b6d4);
  border-radius: 50%;

  &:hover {
    background: var(--node-accent, #06b6d4);
    transform: scale(1.3);
  }
}

:global(.light) {
  .domain-node.input-node {
    --node-bg: #fff;
    --node-text: #1e293b;

    .prompt-textarea {
      background: rgba(6, 182, 212, 0.04);
      border-color: rgba(6, 182, 212, 0.2);
      color: #1e293b;

      &::placeholder {
        color: rgba(15, 23, 42, 0.35);
      }
    }

    .char-count,
    .input-hint {
      color: rgba(15, 23, 42, 0.45);
    }

    .result-preview-text {
      color: #334155;
    }
  }
}
</style>
