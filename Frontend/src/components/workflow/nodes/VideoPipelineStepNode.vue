<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node pipeline-step-node"
    :class="{ selected, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <NodeTypeBadge :node-type="nodeType" />
    </div>

    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        class="node-name-input"
        :placeholder="defaultLabel"
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop
      >
    </div>

    <div class="compact-view">
      <div
        v-if="targetLang"
        class="info-row"
      >
        <span class="info-label">语言</span>
        <span class="info-value">{{ targetLang }}</span>
      </div>
      <div
        v-if="detailText && !isRunning && !isCompleted && !isFailed"
        class="info-row"
      >
        <span class="info-label">说明</span>
        <span class="info-value">{{ detailText }}</span>
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
          <span>{{ detailText || '处理中...' }}</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>{{ detailText || '已完成' }}</span>
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
      v-if="videoUrl && showVideoPreview"
      class="preview-zone"
    >
      <NodeMediaPreview
        kind="video"
        :src="videoUrl"
      />
    </div>

    <Handle
      type="source"
      :position="Position.Right"
    />

    <div
      class="resize-handle"
      title="拖动调整节点大小"
      @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Loader } from 'lucide-vue-next'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import NodeMediaPreview from '@/components/workflow/nodes/NodeMediaPreview.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'
import { useExecutionStore } from '@/stores/execution'
import { extractVideoUrl } from '@/utils/nodeMediaOutput'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
  nodeType: { type: String, required: true },
  defaultLabel: { type: String, default: '处理节点' },
  showVideoPreview: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const { nodeColor } = useNodePresentation(props.nodeType)
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()
const rootEl = ref(null)

const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 200,
  minHeight: 120,
  maxWidth: 480,
  maxHeight: 360,
})

const localName = ref(props.data.label || props.defaultLabel)
const localConfig = ref({ ...(props.data.config || {}) })

watch(() => props.data, (data) => {
  if (!data) return
  localName.value = data.label || props.defaultLabel
  localConfig.value = { ...(data.config || {}) }
}, { deep: true })

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const targetLang = computed(() => {
  return localConfig.value.target_language
    || localConfig.value.targetLanguage
    || nodeOutput.value?.target_language
    || ''
})

const videoUrl = computed(() => extractVideoUrl(nodeOutput.value))

const detailText = computed(() => {
  if (isRunning.value) return '处理中...'
  if (isFailed.value) return '失败'
  if (!isCompleted.value) return ''
  if (props.nodeType === 'subtitle_translate') {
    const n = (nodeOutput.value?.segments || []).length
    return n ? `${n} 段字幕` : '已翻译'
  }
  if (props.nodeType === 'segment_dubbing') return nodeOutput.value?.dubbed_audio_url ? '配音完成' : '完成'
  if (props.nodeType === 'lip_sync') {
    return nodeOutput.value?.lip_sync_applied ? '口型已同步' : '已合成（无口型）'
  }
  if (props.nodeType === 'subtitle_burn') {
    return nodeOutput.value?.burn_subtitles_applied ? '字幕已烧录' : '完成'
  }
  return '完成'
})

function handleChange() {
  if (!props.id) return
  updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
}
</script>

<style scoped>
.pipeline-step-node {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, var(--node-accent));
  border-radius: 12px;
  min-width: 200px;
  max-width: 320px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    box-shadow:
      0 8px 32px color-mix(in srgb, var(--node-accent) 30%, transparent),
      0 0 0 2px color-mix(in srgb, var(--node-accent) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, var(--node-accent) 20%, transparent);
    transform: translateY(-1px);
  }

  &.is-running {
    animation: wf-node-pulse 1.8s ease-in-out infinite;
  }

  &.is-failed {
    border-color: rgba(239, 68, 68, 0.6) !important;
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

.node-name-section {
  padding: 10px 12px 6px;
}

.node-name-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text, #e5e5e5);
  outline: none;
  transition: all 0.15s ease;

  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }

  &:focus {
    border-color: var(--node-accent);
    background: color-mix(in srgb, var(--node-accent) 10%, transparent);
  }
}

.compact-view {
  padding: 0 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;

  .info-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
  }

  .info-value {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
  }
}

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running {
    background: color-mix(in srgb, var(--node-accent) 10%, transparent);
    color: var(--node-accent);
    border: 1px solid color-mix(in srgb, var(--node-accent) 20%, transparent);
  }

  &.completed {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.2);
  }

  &.failed {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.2);
  }
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

.preview-zone {
  margin: 0 12px 10px;
  border-radius: 8px;
  overflow: hidden;
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

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes wf-node-pulse {
  0%,
  100% {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 color-mix(in srgb, var(--node-accent) 30%, transparent);
  }

  50% {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px transparent;
  }
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: rgba(10, 10, 18, 0.95);
  border: 2px solid var(--node-accent);
  border-radius: 50%;

  &:hover {
    background: var(--node-accent);
    transform: scale(1.3);
  }
}

:global(.light) .pipeline-step-node {
  --node-bg: #fff;
  --node-text: #1e1e2e;

  .node-header {
    border-bottom-color: rgba(0, 0, 0, 0.06);
    background: rgba(0, 0, 0, 0.02);
  }

  .node-name-input {
    background: rgba(0, 0, 0, 0.03);
    border-color: rgba(0, 0, 0, 0.08);
    color: var(--node-text);

    &::placeholder {
      color: rgba(0, 0, 0, 0.35);
    }
  }

  .info-row .info-label {
    color: rgba(0, 0, 0, 0.45);
  }

  .info-row .info-value {
    color: rgba(0, 0, 0, 0.75);
  }
}
</style>
