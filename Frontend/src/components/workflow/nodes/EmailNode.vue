<template>
  <div
    class="email-node"
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
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div
        v-if="localConfig.to"
        class="email-preview"
      >
        <Mail class="preview-icon" />
        <span class="preview-text">{{ truncateEmail(localConfig.to) }}</span>
      </div>
      <div
        v-if="localConfig.subject"
        class="subject-preview"
      >
        <FileText class="preview-icon" />
        <span class="preview-text">{{ truncateSubject(localConfig.subject) }}</span>
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
          <span>发送中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已发送</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>发送失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="email-card"
    >
      <div class="email-header">
        <div class="email-from">
          <span class="email-label">发件人</span>
          <span class="email-value">{{ fromAddress || 'workflow@system.local' }}</span>
        </div>
        <div
          class="email-send-status"
          :class="{ ok: isCompleted }"
        >
          <Send
            v-if="isCompleted"
            class="send-icon ok"
          />
          <Loader
            v-else
            class="send-icon spinning"
          />
        </div>
      </div>
      <div
        v-if="localConfig.subject || localConfig.body"
        class="email-body-preview"
      >
        <div class="email-subject-row">
          <span class="field-label">主题</span>
          <span class="field-value">{{ localConfig.subject || '(无主题)' }}</span>
        </div>
        <div
          v-if="localConfig.body"
          class="email-snippet"
        >
          <span class="snippet-text">{{ truncate(localConfig.body, 80) }}</span>
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
          <label class="config-label">收件人</label>
          <el-input
            v-model="localConfig.to"
            size="small"
            placeholder="recipient@example.com"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">抄送</label>
          <el-input
            v-model="localConfig.cc"
            size="small"
            placeholder="cc@example.com (可选)"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">主题</label>
          <el-input
            v-model="localConfig.subject"
            size="small"
            placeholder="邮件主题"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">邮件内容</label>
          <el-input
            v-model="localConfig.body"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="邮件正文内容..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">SMTP 配置</label>
          <div
            v-if="localConfig.useGlobalSmtp !== false"
            class="smtp-global-hint"
          >
            使用全局 SMTP（可在右侧属性面板关闭并自定义）
          </div>
          <el-input
            v-else
            v-model="smtpConfigText"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="SMTP 服务器配置 (可选)"
            @change="handleSmtpTextChange"
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
import { Mail, ChevronDown, FileText, Send, Loader } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'email'

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const localName = ref(props.data.label || '发送邮件')
const localConfig = ref({
  to: props.data.config?.to || '',
  cc: props.data.config?.cc || '',
  subject: props.data.config?.subject || '',
  body: props.data.config?.body || '',
  useGlobalSmtp: props.data.config?.useGlobalSmtp !== false,
  smtpConfig: props.data.config?.smtpConfig || {}
})

const smtpConfigText = ref(JSON.stringify(props.data.config?.smtpConfig || {}, null, 2))

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const fromAddress = computed(() => {
  if (!nodeOutput.value) return null
  return nodeOutput.value.from || nodeOutput.value.sender || null
})

function truncateEmail(email) {
  if (!email) return ''
  return email.length > 25 ? email.slice(0, 25) + '...' : email
}

function truncateSubject(subject) {
  if (!subject) return ''
  return subject.length > 30 ? subject.slice(0, 30) + '...' : subject
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '发送邮件'
    localConfig.value = {
      to: d.config?.to || '',
      cc: d.config?.cc || '',
      subject: d.config?.subject || '',
      body: d.config?.body || '',
      useGlobalSmtp: d.config?.useGlobalSmtp !== false,
      smtpConfig: d.config?.smtpConfig || {},
      ...d.config,
    }
    smtpConfigText.value = JSON.stringify(d.config?.smtpConfig || {}, null, 2)
  }
}, { deep: true })

function handleSmtpTextChange() {
  try {
    localConfig.value.smtpConfig = JSON.parse(smtpConfigText.value || '{}')
  } catch {
    // keep previous config if JSON invalid
  }
  handleChange()
}

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
.email-node {
  --email-accent: #dc2626;
  --node-bg: #ffffff;
  --node-text: #111827;
  --node-text-muted: #4b5563;
  --node-text-faint: #6b7280;
  --node-border-color: #dc2626;
  --node-divider: rgba(17, 24, 39, 0.1);
  --node-surface: #f9fafb;
  --node-input-bg: #ffffff;
  --node-input-border: rgba(17, 24, 39, 0.14);
  --node-shadow: rgba(220, 38, 38, 0.18);

  background: var(--node-bg);
  border: 2px solid var(--node-border-color);
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  color: var(--node-text);
  box-shadow: 0 4px 20px var(--node-shadow);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    box-shadow: 0 8px 32px var(--node-shadow), 0 0 0 2px rgba(220, 38, 38, 0.25);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px var(--node-shadow);
    transform: translateY(-1px);
  }

  &.is-running { animation: email-pulse 1.8s ease-in-out infinite; }
  &.is-completed .email-card { border-color: rgba(16, 185, 129, 0.45); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.75) !important; }
}

:global(.dark) .email-node {
  --node-bg: #18181b;
  --node-text: #f4f4f5;
  --node-text-muted: #d4d4d8;
  --node-text-faint: #a1a1aa;
  --node-divider: rgba(255, 255, 255, 0.1);
  --node-surface: #27272a;
  --node-input-bg: #27272a;
  --node-input-border: rgba(255, 255, 255, 0.14);
  --node-shadow: rgba(0, 0, 0, 0.35);
}

@keyframes email-pulse {
  0%, 100% { box-shadow: 0 4px 20px var(--node-shadow), 0 0 0 0 rgba(220, 38, 38, 0.25); }
  50% { box-shadow: 0 4px 20px var(--node-shadow), 0 0 0 6px rgba(220, 38, 38, 0); }
}

.email-card {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 1px solid var(--node-divider);
  background: var(--node-surface);
  overflow: hidden;
  transition: all 0.3s ease;
}

.email-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--node-divider);
}

.email-from {
  display: flex;
  flex-direction: column;
  gap: 2px;

  .email-label {
    font-size: 8px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--node-text-faint);
  }

  .email-value {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--node-text);
  }
}

.email-send-status {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;

  .send-icon { width: 16px; height: 16px; }
  .ok { color: #16a34a; }
  .spinning { animation: spin 1s linear infinite; color: var(--node-text-muted); }
}

@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.email-body-preview { padding: 8px 10px; }

.email-subject-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;

  .field-label {
    font-size: 8px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--node-text-faint);
    flex-shrink: 0;
  }

  .field-value {
    font-size: 11px;
    font-weight: 600;
    color: var(--node-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.email-snippet {
  .snippet-text {
    font-size: 10px;
    color: var(--node-text-muted);
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.status-bar {
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running {
    background: rgba(220, 38, 38, 0.08);
    color: var(--email-accent);
    border: 1px solid rgba(220, 38, 38, 0.2);
  }

  &.completed {
    background: rgba(16, 185, 129, 0.12);
    color: #15803d;
    border: 1px solid rgba(16, 185, 129, 0.28);
  }

  &.failed {
    background: rgba(239, 68, 68, 0.12);
    color: #b91c1c;
    border: 1px solid rgba(239, 68, 68, 0.28);
  }
}

:global(.dark) .status-bar {
  &.completed { color: #4ade80; }
  &.failed { color: #fca5a5; }
}

.status-running,
.status-done,
.status-error {
  display: flex;
  align-items: center;
  gap: 5px;
}

.status-icon {
  width: 12px;
  height: 12px;

  &.spinning { animation: spin 1s linear infinite; }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--node-divider);
  background: var(--node-surface);
}

.action-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--node-input-bg);
  border: 1px solid var(--node-input-border);
  border-radius: 6px;
  cursor: pointer;
  color: var(--node-text-muted);
  transition: all 0.15s ease;

  &:hover {
    background: var(--node-surface);
    color: var(--node-text);
    border-color: var(--email-accent);
  }

  .action-icon {
    width: 14px;
    height: 14px;
    transition: transform 0.2s ease;

    &.rotated { transform: rotate(180deg); }
  }
}

.node-name-section { padding: 10px 12px 6px; }

.node-name-input {
  width: 100%;
  background: var(--node-input-bg);
  border: 1px solid var(--node-input-border);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text);
  outline: none;
  transition: all 0.15s ease;

  &::placeholder { color: var(--node-text-faint); }

  &:focus {
    border-color: var(--email-accent);
    box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.12);
  }
}

.compact-view {
  padding: 0 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.email-preview,
.subject-preview {
  display: flex;
  align-items: center;
  gap: 6px;

  .preview-icon {
    width: 12px;
    height: 12px;
    color: var(--email-accent);
    flex-shrink: 0;
  }

  .preview-text {
    font-size: 11px;
    color: var(--node-text);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.expanded-config {
  border-top: 1px solid var(--node-divider);
  padding: 8px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--node-surface);
}

.config-section {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.config-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--node-text-muted);
}

.smtp-global-hint {
  padding: 8px 10px;
  border-radius: 6px;
  border: 1px solid var(--node-input-border);
  background: var(--node-input-bg);
  font-size: 11px;
  line-height: 1.5;
  color: var(--node-text-muted);
}

:deep(.el-select),
:deep(.el-input),
:deep(.el-input-number) {
  width: 100%;

  .el-input__wrapper {
    background: var(--node-input-bg) !important;
    border: 1px solid var(--node-input-border) !important;
    box-shadow: none !important;
    border-radius: 6px;
  }

  .el-input__inner,
  .el-textarea__inner {
    color: var(--node-text) !important;
    font-size: 12px !important;
    background: transparent !important;

    &::placeholder {
      color: var(--node-text-faint) !important;
    }
  }
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 400px;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: var(--email-accent);
  border: 2px solid var(--node-bg);
  border-radius: 50%;

  &:hover {
    background: var(--node-text);
    transform: scale(1.3);
  }
}
</style>
