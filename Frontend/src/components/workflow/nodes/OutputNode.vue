<template>
  <div
    ref="rootEl"
    class="output-node"
    :style="resize.sizeStyle.value"
    :class="{ selected, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <div class="node-inner">
      <div class="node-icon-wrapper">
        <LogOut class="node-icon" />
      </div>
      <div class="node-text">
        <span class="node-type-label">输出</span>
        <span class="node-label">{{ localLabel || data.label || '输出结果' }}</span>
      </div>
    </div>

    <div
      v-if="previewVideo || previewImage"
      class="preview-zone"
    >
      <video
        v-if="previewVideo"
        :key="previewVideo"
        :src="previewVideo"
        class="preview-media"
        controls
        muted
        playsinline
        preload="metadata"
        referrerpolicy="no-referrer"
      />
      <img
        v-else-if="previewImage"
        :key="previewImage"
        :src="previewImage"
        class="preview-media"
        alt="Output preview"
        referrerpolicy="no-referrer"
      >
    </div>

    <!-- Result Zone -->
    <div
      v-if="isRunning || isCompleted || isFailed"
      class="result-zone"
      :class="{ 'zone-running': isRunning, 'zone-completed': isCompleted, 'zone-failed': isFailed }"
    >
      <div
        v-if="isRunning"
        class="result-running"
      >
        <Loader class="result-icon spinning" />
        <span>执行中...</span>
      </div>
      <div
        v-else-if="isCompleted"
        class="result-summary"
      >
        <Check class="result-icon" />
        <span>{{ truncate(displaySummary, 28) }}</span>
      </div>
      <div
        v-else-if="isFailed"
        class="result-error"
      >
        <X class="result-icon" />
        <span>{{ nodeOutput?.error || '执行失败' }}</span>
      </div>
    </div>

    <div
      class="resize-handle"
      title="拖动调整节点大小"
      @pointerdown.stop="(e) => resize.startResize(e, rootEl?.offsetWidth, rootEl?.offsetHeight)"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Handle, Position } from '@vue-flow/core'
import { LogOut, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import { useNodeResize } from '@/composables/useNodeResize'
import { useUpstreamNodeOutputs } from '@/composables/useUpstreamNodeOutputs'
import { unwrapNodeExecutionOutput } from '@/utils/workflowTransform'
import { extractVideoUrl, extractImageUrl } from '@/utils/nodeMediaOutput'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const executionStore = useExecutionStore()
const { nodeOutputs, nodeStatusMap } = storeToRefs(executionStore)
const { upstreamImageUrl, upstreamVideoUrl } = useUpstreamNodeOutputs(computed(() => props.id), {
  sourceTypes: ['image_generation', 'image_editing', 'video_generation'],
})

const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 160,
  minHeight: 100,
  maxWidth: 640,
  maxHeight: 720,
})

const nodeStatus = computed(() => nodeStatusMap.value[props.id])
const nodeOutput = computed(() => unwrapNodeExecutionOutput(nodeOutputs.value[props.id]))
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const localLabel = ref(props.data?.label || '')

function resolveOwnVideoUrl(out) {
  if (!out) return null
  const fromOutput = extractVideoUrl(out)
  if (fromOutput) return fromOutput
  const result = out.result
  if (typeof result === 'string' && /\.mp4|\.webm|video/i.test(result)) return result
  const display = out._display
  if (typeof display === 'string' && /\.mp4|\.webm|video/i.test(display)) return display
  return null
}

function resolveOwnImageUrl(out) {
  if (!out) return null
  return extractImageUrl(out)
}

// 输出节点预览优先展示直连上游（图生视频/文生图）的最新结果；
// 避免 output 节点因后端配置级缓存或旧 nodeOutputs 展示上一轮视频/图片。
const previewVideo = computed(() => {
  if (isRunning.value) return upstreamVideoUrl.value || null
  if (upstreamVideoUrl.value) return upstreamVideoUrl.value
  return resolveOwnVideoUrl(nodeOutput.value)
})

const previewImage = computed(() => {
  if (previewVideo.value) return null
  if (isRunning.value) return upstreamImageUrl.value || null
  if (upstreamImageUrl.value) return upstreamImageUrl.value
  return resolveOwnImageUrl(nodeOutput.value)
})

const displaySummary = computed(() => {
  if (previewVideo.value) return '视频已输出'
  if (previewImage.value) return '图像已输出'
  const out = nodeOutput.value
  if (!out) return '完成'
  return String(out.data || out._display || out.result || '完成')
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function handleSelect() {
  emit('select')
}
</script>

<style lang="scss" scoped>
.output-node {
  position: relative;
  background: linear-gradient(145deg, #14532d 0%, #000 100%);
  border: 2px solid #84cc16;
  border-radius: 12px;
  min-width: 140px;
  box-shadow:
    0 0 0 1px rgba(132, 204, 22, 0.15),
    0 4px 16px rgba(0, 0, 0, 0.5);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  display: flex;
  flex-direction: column;

  &.selected {
    transform: scale(1.03);
    box-shadow: 0 8px 24px rgba(132, 204, 22, 0.2), 0 0 0 3px rgba(132, 204, 22, 0.2);
  }

  &:hover:not(.selected) {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(132, 204, 22, 0.15);
  }

  :deep(.vue-flow__handle) {
    width: 10px; height: 10px;
    background: #0a0a0a;
    border: 2px solid #84cc16;
    border-radius: 50%;
    &:hover { background: #84cc16; transform: scale(1.3); }
  }
}

.node-inner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
}

.preview-zone {
  flex: 1;
  min-height: 80px;
  margin: 0 10px 8px;
  border-radius: 8px;
  overflow: hidden;
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid rgba(132, 204, 22, 0.25);
}

.preview-media {
  width: 100%;
  height: 100%;
  min-height: 80px;
  max-height: 100%;
  object-fit: contain;
  display: block;
}

.node-icon-wrapper {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(132, 204, 22, 0.15);
  border: 1px solid rgba(132, 204, 22, 0.3);
  border-radius: 8px;
  flex-shrink: 0;
}

.node-icon {
  width: 16px; height: 16px;
  color: #84cc16;
}

.node-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.node-type-label {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #84cc16;
  opacity: 0.8;
}

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: #e5e5e5;
}

:global(.light) {
  .output-node {
    background: linear-gradient(145deg, #f7fee7 0%, #fff 100%);
    border-color: #84cc16;
    box-shadow: 0 2px 8px rgba(132, 204, 22, 0.15);
    .node-label { color: #111827; }
    :deep(.vue-flow__handle) { background: #fff; }
  }
}

.result-zone {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;

  &.zone-running {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #3b82f6;
  }

  &.zone-completed {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
  }

  &.zone-failed {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
  }

  .result-icon {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }

  .result-summary, .result-error {
    display: flex;
    align-items: center;
    gap: 6px;
    word-break: break-all;
    font-family: 'JetBrains Mono', monospace;
  }
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
  border-right: 2px solid rgba(132, 204, 22, 0.55);
  border-bottom: 2px solid rgba(132, 204, 22, 0.55);
  cursor: nwse-resize;
  opacity: 0.55;
  z-index: 3;

  &:hover { opacity: 1; }
}
</style>
