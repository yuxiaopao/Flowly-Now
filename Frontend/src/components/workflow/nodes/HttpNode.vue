<template>
  <div
    class="http-node"
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
        v-model="localName"
        name="node-label"
        class="node-name-input"
        placeholder="HTTP 请求..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div
      v-if="!isExpanded"
      class="compact-view"
    >
      <div class="url-preview">
        {{ truncateUrl(localConfig.url) }}
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
          <span>请求中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>{{ statusCode }}</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>请求失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isRunning || isCompleted || isFailed"
      class="response-zone"
    >
      <div class="response-header">
        <FileJson class="response-icon" />
        <span class="response-label">响应预览</span>
        <span
          class="response-status"
          :class="{ ok: statusCode >= 200 && statusCode < 300, err: statusCode >= 400 || isFailed }"
        >
          {{ isFailed ? 'ERR' : statusCode }}
        </span>
        <span
          v-if="responseTime"
          class="response-time"
        >{{ responseTime }}ms</span>
        <button
          v-if="jsonPreview && !isRunning"
          class="expand-btn"
          @click.stop="toggleResponseExpand"
        >
          <ChevronUp
            v-if="responseExpanded"
            class="expand-icon"
          />
          <ChevronDown
            v-else
            class="expand-icon"
          />
        </button>
        <button
          v-if="jsonPreview && !isRunning"
          class="copy-btn"
          :class="{ copied: copiedResponse }"
          @click.stop="copyResponse"
        >
          <Check
            v-if="copiedResponse"
            class="copy-icon"
          />
          <Copy
            v-else
            class="copy-icon"
          />
        </button>
      </div>
      <div
        class="response-content"
        :class="{ expanded: responseExpanded }"
      >
        <div
          v-if="jsonPreview"
          class="json-preview"
        >
          <pre class="json-text">{{ responseExpanded ? jsonPreview : truncatedPreview }}</pre>
        </div>
        <div
          v-else
          class="response-empty"
        >
          <span v-if="isRunning">等待响应...</span>
          <span v-else>无响应体</span>
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
          <label class="config-label">请求方法</label>
          <el-select
            v-model="localConfig.method"
            size="small"
            @change="handleChange"
          >
            <el-option
              label="GET"
              value="GET"
            />
            <el-option
              label="POST"
              value="POST"
            />
            <el-option
              label="PUT"
              value="PUT"
            />
            <el-option
              label="PATCH"
              value="PATCH"
            />
            <el-option
              label="DELETE"
              value="DELETE"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">URL</label>
          <el-input
            v-model="localConfig.url"
            size="small"
            placeholder="https://..."
            @input="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">请求体</label>
          <el-input
            v-model="localConfig.body"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="{&quot;key&quot;: &quot;{input}&quot;}"
            class="code-textarea"
            @input="handleChange"
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
import { ref, computed, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, FileJson, Loader, Copy, Check, ChevronUp } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'http'

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const localName = ref(props.data.label || 'HTTP 请求')
const localConfig = ref({
  method: props.data.config?.method || 'GET',
  url: props.data.config?.url || '',
  headers: props.data.config?.headers || '{}',
  body: props.data.config?.body || '',
  timeout: props.data.config?.timeout || 30,
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const responseExpanded = ref(false)
const copiedResponse = ref(false)

const statusCode = computed(() => {
  if (!nodeOutput.value) return 0
  return nodeOutput.value.status || nodeOutput.value.statusCode || nodeOutput.value.status_code || (isCompleted.value ? 200 : 0)
})

const responseTime = computed(() => {
  if (!nodeOutput.value) return null
  return nodeOutput.value.time || nodeOutput.value.duration || nodeOutput.value.responseTime || null
})

const jsonPreview = computed(() => {
  if (!nodeOutput.value) return null
  let data = null
  if (nodeOutput.value.data) data = nodeOutput.value.data
  else if (nodeOutput.value.body) data = nodeOutput.value.body
  else if (nodeOutput.value.response) data = nodeOutput.value.response
  else if (typeof nodeOutput.value === 'object' && !nodeOutput.value.status) data = nodeOutput.value

  if (!data) return null
  const str = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
  return str
})

const truncatedPreview = computed(() => {
  if (!jsonPreview.value) return null
  if (jsonPreview.value.length > 300) {
    return jsonPreview.value.slice(0, 300) + '\n...'
  }
  return jsonPreview.value
})

async function copyResponse() {
  if (!jsonPreview.value) return
  try {
    await navigator.clipboard.writeText(jsonPreview.value)
    copiedResponse.value = true
    setTimeout(() => { copiedResponse.value = false }, 2000)
  } catch (e) {
    console.error('Copy failed', e)
  }
}

function toggleResponseExpand() {
  responseExpanded.value = !responseExpanded.value
}

function truncateUrl(url) {
  if (!url) return '未设置 URL'
  return url.length > 35 ? url.slice(0, 35) + '...' : url
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || 'HTTP 请求'
    localConfig.value = { method: d.config?.method || 'GET', url: d.config?.url || '', headers: d.config?.headers || '{}', body: d.config?.body || '', timeout: d.config?.timeout || 30, ...d.config }
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
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
.http-node {
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
  &.is-running { animation: http-pulse 1.8s ease-in-out infinite; }
  &.is-completed .response-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes http-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(249, 115, 22, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(249, 115, 22, 0); }
}

.response-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(249, 115, 22, 0.2);
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.response-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(249, 115, 22, 0.15);
  background: rgba(249, 115, 22, 0.05);

  .response-icon { width: 11px; height: 11px; color: rgba(249, 115, 22, 0.6); }
  .response-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(249, 115, 22, 0.7); flex: 1; }
}

.response-status {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  padding: 1px 6px;
  border-radius: 4px;

  &.ok { background: rgba(16, 185, 129, 0.2); color: #10b981; }
  &.err { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
}

.response-time {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(249, 115, 22, 0.5);
}

.expand-btn,
.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s ease;

  .expand-icon,
  .copy-icon { width: 10px; height: 10px; }

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }
}

.copy-btn {
  &.copied {
    background: rgba(16, 185, 129, 0.15);
    border-color: rgba(16, 185, 129, 0.3);
    color: #10b981;
  }
}

.response-content {
  padding: 8px 10px;
  max-height: 80px;
  overflow: auto;
  transition: max-height 0.3s ease;

  &.expanded {
    max-height: 300px;
  }
}

.json-preview {
  .json-text {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: #a5d6ff;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
}

.response-empty { font-size: 10px; color: rgba(249, 115, 22, 0.4); font-style: italic; }

.status-bar {
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(249, 115, 22, 0.1); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.node-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: rgba(249, 115, 22, 0.08); border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; background: rgba(249, 115, 22, 0.2); border: 1px solid rgba(249, 115, 22, 0.3); border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #fb923c; .badge-icon { width: 11px; height: 11px; } }
.method-badge { font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; &.get { background: rgba(16, 185, 129, 0.2); color: #10b981; } &.post { background: rgba(59, 130, 246, 0.2); color: #3b82f6; } &.put { background: rgba(245, 158, 11, 0.2); color: #f59e0b; } &.patch { background: rgba(139, 92, 246, 0.2); color: #8b5cf6; } &.delete { background: rgba(239, 68, 68, 0.2); color: #ef4444; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s; margin-left: auto; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 8px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e2e8f0); outline: none; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: rgba(249, 115, 22, 0.5); } }
.compact-view { padding: 0 12px 10px; }
.url-preview { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: #94a3b8; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 6px 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
.code-textarea :deep(.el-textarea__inner) { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; color: var(--node-text, #e2e8f0) !important; box-shadow: none !important; }
:deep(.el-select), :deep(.el-input) { .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; } .el-input__inner { color: var(--node-text, #e2e8f0) !important; font-size: 12px !important; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: #1e1e2e; border: 2px solid #f97316; border-radius: 50%; &:hover { background: #f97316; transform: scale(1.3); } }
:global(.dark) { .http-node { --node-bg: #1e1e2e; --node-border: #f97316; --node-text: #e2e8f0; } }
:global(.light) { .http-node { --node-bg: #fff; --node-border: #f97316; --node-text: #1e293b; } }
</style>
