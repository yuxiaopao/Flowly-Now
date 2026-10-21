<template>
  <div
    ref="rootEl"
    class="domain-node site-factory-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    :style="{ '--node-accent': resolvedColor, ...(isExpanded ? resize.sizeStyle.value : {}) }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <NodeTypeBadge
        :node-type="nodeType"
        :label="badgeLabel || undefined"
      />
      <button
        class="action-btn"
        type="button"
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
        class="node-name-input"
        name="node-label"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div
        v-if="summaryText"
        class="info-row"
      >
        <span class="info-label">状态</span>
        <span class="info-value">{{ summaryText }}</span>
      </div>
      <div
        v-if="gateBadge"
        class="gate-badge"
        :class="gateBadge"
      >
        {{ gateLabel }}
      </div>
    </div>

    <div
      v-if="isExpanded"
      class="expanded-panel"
      @click.stop
    >
      <slot name="expanded" />
      <ul
        v-if="checks.length"
        class="check-list"
      >
        <li
          v-for="item in checks"
          :key="item.key"
          :class="{ ok: item.ok, warn: !item.ok }"
        >
          <strong>{{ item.label }}</strong> — {{ item.detail }}
        </li>
      </ul>
      <p
        v-if="summaryZh"
        class="summary-text"
      >
        {{ summaryZh }}
      </p>
      <div
        v-if="!isDesktop && showIframe && !blocked"
        class="browser-hint"
      >
        <p class="browser-hint-text">
          本地预览需在 <strong>Flowly Desktop</strong> 中运行工作流。
          浏览器模式可查看上游返回的 preview_url。
        </p>
        <button
          v-if="outputDirForCopy"
          type="button"
          class="copy-dir-btn"
          @click.stop="copyOutputDir"
        >
          复制输出目录
        </button>
      </div>
      <div
        v-if="isDesktop && outputDirForCopy"
        class="local-dir-row"
      >
        <span
          class="local-dir-path"
          :title="outputDirForCopy"
        >{{ outputDirForCopy }}</span>
        <button
          type="button"
          class="copy-dir-btn"
          @click.stop="openOutputFolder"
        >
          打开文件夹
        </button>
      </div>
      <p
        v-if="previewError"
        class="preview-error"
      >
        {{ previewError }}
      </p>
      <div
        v-if="previewLoading"
        class="env-progress"
      >
        <p class="preview-loading">
          <Loader class="env-progress-icon spinning" />
          {{ envProgressMessage || '正在准备本地环境…' }}
        </p>
        <ul
          v-if="envProgressLog.length"
          class="env-progress-log"
        >
          <li
            v-for="(entry, idx) in envProgressLog"
            :key="idx"
          >
            {{ entry }}
          </li>
        </ul>
      </div>
      <iframe
        v-if="effectivePreviewUrl && showIframe && !previewLoading"
        :src="effectivePreviewUrl"
        class="preview-frame"
        :style="resize.height.value ? { height: `${Math.max(120, resize.height.value - 160)}px` } : {}"
        title="站点预览"
      />

      <div
        class="resize-handle"
        title="拖拽调整节点大小"
        @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
      />
    </div>

    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, toRef } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, Loader } from 'lucide-vue-next'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useDesktopRuntime } from '@/composables/useDesktopRuntime'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
  /** nodeRegistry 类型键，驱动图标/颜色/标签 */
  nodeType: { type: String, required: true },
  /** 可选覆盖 registry 标签 */
  badgeLabel: { type: String, default: '' },
  /** @deprecated 使用 nodeType + registry */
  nodeColor: { type: String, default: '' },
  /** @deprecated 使用 nodeType + registry */
  icon: { type: [Object, Function], default: null },
  showIframe: { type: Boolean, default: false },
  enableDesktopPreview: { type: Boolean, default: false },
  outputDir: { type: String, default: '' },
  previewPort: { type: Number, default: null },
  siteId: { type: String, default: '' },
  blocked: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const { isDesktop, startSite, stopSite, grantPermission, onEnvProgress, openFolder } = useDesktopRuntime()
const { nodeColor: registryColor, nodeLabel } = useNodePresentation(toRef(props, 'nodeType'))

const resolvedColor = computed(() => props.nodeColor || registryColor.value)

const isExpanded = ref(false)
const localName = ref(props.data.label || props.badgeLabel || nodeLabel.value)
const livePreviewUrl = ref('')
const previewError = ref('')
const previewLoading = ref(false)
const runtimeSiteId = ref('')
const pendingSiteId = ref('')
const envProgressMessage = ref('')
const envProgressLog = ref([])
let unsubscribeEnvProgress = null
const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 240,
  minHeight: 160,
  maxWidth: 900,
  maxHeight: 800,
})

watch(() => props.data.label, (v) => { localName.value = v || props.badgeLabel || nodeLabel.value })
watch(nodeLabel, (v) => {
  if (!props.data.label && !localName.value) localName.value = v
})

const nodeOutput = computed(() => props.data.output || props.data.result || {})
const isRunning = computed(() => props.data.status === 'running')
const isCompleted = computed(() => props.data.status === 'completed')
const isFailed = computed(() => props.data.status === 'failed')

const checks = computed(() => nodeOutput.value.checks || props.data.checks || [])
const summaryZh = computed(() => nodeOutput.value.summary_zh || nodeOutput.value.summaryZh || '')
const previewUrl = computed(() => nodeOutput.value.preview_url || nodeOutput.value.previewUrl || nodeOutput.value.url || '')
const effectivePreviewUrl = computed(() => livePreviewUrl.value || previewUrl.value)
const gateBadge = computed(() => {
  const g = nodeOutput.value.gate || nodeOutput.value.qa_gate || nodeOutput.value.qaGate
    || nodeOutput.value.review_gate || nodeOutput.value.reviewGate || ''
  return g || null
})
const gateLabel = computed(() => ({ green: '通过', yellow: '警告', red: '阻塞' }[gateBadge.value] || gateBadge.value))
const summaryText = computed(() => {
  if (isRunning.value) return '运行中'
  if (nodeOutput.value.backend_ready) return '后端就绪'
  if (nodeOutput.value.frontend_ready) return '前端就绪'
  if (nodeOutput.value.ui_score != null) return `UI ${nodeOutput.value.ui_score}`
  if (nodeOutput.value.ready === true) return '就绪'
  if (nodeOutput.value.ready === false) return '未就绪'
  if (gateBadge.value) return gateLabel.value
  if (previewUrl.value) return '可预览'
  if (previewError.value) return '预览失败'
  return props.data.status || ''
})

const outputDirForCopy = computed(() => (
  props.outputDir || nodeOutput.value.output_dir || nodeOutput.value.outputDir || ''
))

async function copyOutputDir() {
  const dir = outputDirForCopy.value
  if (!dir) return
  try {
    await navigator.clipboard.writeText(dir)
    previewError.value = ''
  } catch {
    previewError.value = '无法复制到剪贴板，请手动复制'
  }
}

async function ensureDesktopPreview() {
  if (!props.enableDesktopPreview || !props.showIframe || props.blocked) return
  if (!isExpanded.value) return
  const dir = outputDirForCopy.value
  if (!dir) return
  if (livePreviewUrl.value) return

  if (!isDesktop) {
    if (!previewUrl.value) {
      previewError.value = '无 preview_url 时请使用 Flowly Desktop 运行'
    }
    return
  }

  previewLoading.value = true
  previewError.value = ''
  envProgressMessage.value = '正在申请本地运行权限…'
  envProgressLog.value = []
  const attemptId = props.siteId || crypto.randomUUID()
  pendingSiteId.value = attemptId
  try {
    const perm = await grantPermission({ outputDir: dir })
    if (!perm.success) {
      previewError.value = perm.error || '目录访问权限被拒绝'
      return
    }
    const res = await startSite({
      outputDir: dir,
      port: props.previewPort || undefined,
      siteId: attemptId,
    })
    if (res.success) {
      livePreviewUrl.value = res.previewUrl
      runtimeSiteId.value = res.siteId
      if (props.id) {
        updateNodeData(props.id, {
          output: {
            ...nodeOutput.value,
            preview_url: res.previewUrl,
            previewUrl: res.previewUrl,
            desktop_runtime: true,
          },
        })
      }
    } else {
      previewError.value = res.error || 'Desktop 预览启动失败'
    }
  } catch (err) {
    previewError.value = err?.message || 'Desktop 预览异常'
  } finally {
    previewLoading.value = false
    pendingSiteId.value = ''
  }
}

async function openOutputFolder() {
  const dir = outputDirForCopy.value
  if (!dir) return
  const res = await openFolder(dir)
  if (!res.success) {
    previewError.value = res.error || '无法打开文件夹'
  }
}

watch([isExpanded, () => props.outputDir, () => props.showIframe, () => props.blocked], () => {
  ensureDesktopPreview()
}, { immediate: true })

onMounted(() => {
  unsubscribeEnvProgress = onEnvProgress((payload) => {
    if (!pendingSiteId.value || payload.siteId !== pendingSiteId.value) return
    envProgressMessage.value = payload.message || envProgressMessage.value
    envProgressLog.value.push(payload.message)
    if (envProgressLog.value.length > 20) envProgressLog.value.shift()
  })
})

onUnmounted(() => {
  if (runtimeSiteId.value) {
    stopSite(runtimeSiteId.value)
  }
  unsubscribeEnvProgress?.()
})

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
}

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style scoped lang="scss">
.site-factory-node {
  min-width: 200px;
}
.gate-badge {
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  display: inline-block;
  &.green { background: rgba(16, 185, 129, 0.15); color: #10b981; }
  &.yellow { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
  &.red { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
}
.check-list {
  margin: 8px 0 0;
  padding-left: 16px;
  font-size: 11px;
  li.ok { color: #10b981; }
  li.warn { color: #f59e0b; }
}
.summary-text {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-secondary, #a1a1aa);
  line-height: 1.4;
}
.preview-frame {
  width: 100%;
  height: 180px;
  margin-top: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  background: #fff;
}
.preview-error {
  margin-top: 6px;
  font-size: 10px;
  color: #ef4444;
}
.preview-loading {
  margin-top: 6px;
  font-size: 10px;
  color: #a1a1aa;
  display: flex;
  align-items: center;
  gap: 6px;
}
.env-progress-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}
.env-progress-icon.spinning {
  animation: sfns-spin 1s linear infinite;
}
@keyframes sfns-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.env-progress-log {
  margin: 4px 0 0;
  padding-left: 16px;
  font-size: 9px;
  color: rgba(255, 255, 255, 0.4);
  max-height: 80px;
  overflow-y: auto;
}
.local-dir-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.local-dir-path {
  flex: 1;
  min-width: 0;
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.browser-hint {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.25);
}
.browser-hint-text {
  margin: 0 0 6px;
  font-size: 10px;
  line-height: 1.4;
  color: #93c5fd;
}
.copy-dir-btn {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(0, 0, 0, 0.2);
  color: inherit;
  font-size: 10px;
  cursor: pointer;
}
.expanded-panel {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  position: relative;
}
.resize-handle {
  position: absolute;
  right: -6px;
  bottom: -6px;
  width: 16px;
  height: 16px;
  cursor: nwse-resize;
  border-radius: 3px;
  background:
    linear-gradient(135deg, transparent 0 45%, var(--node-accent, #8b5cf6) 45% 55%, transparent 55% 100%),
    linear-gradient(135deg, transparent 0 65%, var(--node-accent, #8b5cf6) 65% 75%, transparent 75% 100%);
  opacity: 0.5;
  transition: opacity 0.15s ease;
  z-index: 5;
}
.resize-handle:hover {
  opacity: 1;
}
</style>
