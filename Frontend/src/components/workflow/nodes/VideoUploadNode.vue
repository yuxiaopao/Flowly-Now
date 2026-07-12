<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node video-upload-node"
    :class="{ selected, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    @click.stop="handleSelect"
  >
    <Handle type="target" :position="Position.Left" />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" />
    </div>

    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        class="node-name-input"
        placeholder="上传视频"
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop
      >
    </div>

    <div class="upload-body nodrag nopan nowheel" @mousedown.stop @pointerdown.stop>
      <div v-if="previewUrl" class="player-wrap">
        <video
          :key="previewUrl"
          class="video-player"
          :src="previewUrl"
          controls
          playsinline
          preload="metadata"
          @click.stop
        />
      </div>
      <div v-else class="upload-placeholder">
        <Upload class="upload-icon" />
        <span>选择或拖拽视频</span>
      </div>

      <div class="upload-actions">
        <label class="upload-btn">
          <input type="file" accept="video/*,.mp4,.mov,.webm,.mkv" hidden @change="onFilePick">
          <span>{{ uploading ? '上传中...' : '本地上传' }}</span>
        </label>
        <button type="button" class="link-btn" @click.stop="toggleUrlInput">
          {{ showUrlInput ? '隐藏 URL' : '公网 URL' }}
        </button>
      </div>

      <input
        v-if="showUrlInput"
        v-model="localConfig.video_input"
        class="url-input nodrag"
        placeholder="https://example.com/video.mp4"
        @blur="handleChange"
        @click.stop
      >

      <div v-if="localConfig.public_url || localConfig.video_input" class="meta-row">
        <span class="meta-label">源</span>
        <span class="meta-value">{{ shortUrl(localConfig.public_url || localConfig.video_input) }}</span>
      </div>
    </div>

    <div v-if="isRunning" class="status-row running">
      <Loader class="spin" /> 解析视频中...
    </div>
    <div v-else-if="isCompleted" class="status-row done">已就绪</div>
    <div v-else-if="isFailed" class="status-row fail">{{ outputError || '失败' }}</div>

    <Handle type="source" :position="Position.Right" />

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
import { Loader, Upload } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'
import { useExecutionStore } from '@/stores/execution'
import { uploadMedia } from '@/api/workflow'

const NODE_TYPE = 'video_upload'

const props = defineProps({
  id: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const { nodeColor } = useNodePresentation(NODE_TYPE)
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const rootEl = ref(null)
const uploading = ref(false)
const showUrlInput = ref(false)
const localBlobUrl = ref('')

const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 280,
  minHeight: 220,
  maxWidth: 560,
  maxHeight: 480,
})

const localName = ref(props.data.label || '上传视频')
const localConfig = ref(normalizeConfig(props.data.config))

function normalizeConfig(cfg = {}) {
  return {
    inputMode: cfg.inputMode || (cfg.media_id ? 'upload' : 'url'),
    video_input: cfg.video_input || cfg.videoUrl || cfg.public_url || '',
    media_id: cfg.media_id || cfg.mediaId || '',
    public_url: cfg.public_url || cfg.publicUrl || cfg.video_input || '',
  }
}

watch(() => props.data, (data) => {
  if (!data) return
  localName.value = data.label || '上传视频'
  localConfig.value = normalizeConfig(data.config)
}, { deep: true })

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const outputError = computed(() => executionStore.nodeStatusDetails?.[props.id]?.error || '')

const previewUrl = computed(() => {
  return nodeOutput.value?.video_url
    || localConfig.value.public_url
    || localConfig.value.video_input
    || localBlobUrl.value
    || ''
})

function shortUrl(url) {
  if (!url) return ''
  return url.length > 48 ? `${url.slice(0, 24)}…${url.slice(-16)}` : url
}

function handleChange() {
  if (!props.id) return
  updateNodeData(props.id, {
    label: localName.value,
    config: { ...localConfig.value },
  })
}

function handleSelect() {
  emit('select')
}

function toggleUrlInput() {
  showUrlInput.value = !showUrlInput.value
}

async function onFilePick(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  if (localBlobUrl.value) {
    URL.revokeObjectURL(localBlobUrl.value)
  }
  localBlobUrl.value = URL.createObjectURL(file)
  localConfig.value.inputMode = 'upload'

  uploading.value = true
  try {
    const res = await uploadMedia(file)
    const data = res?.data || res
    if (data?.success === false) throw new Error(data?.error || '上传失败')
    const meta = data?.data || data
    localConfig.value.media_id = meta.media_id
    localConfig.value.public_url = meta.public_url
    localConfig.value.video_input = meta.public_url
    ElMessage.success('视频上传成功')
    handleChange()
  } catch (err) {
    ElMessage.error(err.message || '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.video-upload-node {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, var(--node-accent));
  border-radius: 12px;
  min-width: 280px;
  max-width: 420px;
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

.upload-body {
  padding: 0 12px 10px;
}

.player-wrap {
  border-radius: 8px;
  overflow: hidden;
  background: #0f172a;
}

.video-player {
  width: 100%;
  max-height: 200px;
  display: block;
  background: #000;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 24px 12px;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
}

.upload-icon {
  width: 24px;
  height: 24px;
  opacity: 0.6;
}

.upload-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.upload-btn span,
.link-btn {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.75);
}

.link-btn {
  background: transparent;
}

.url-input {
  width: 100%;
  margin-top: 8px;
  font-size: 12px;
  padding: 6px 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--node-text, #e5e5e5);
}

.meta-row {
  display: flex;
  gap: 6px;
  margin-top: 6px;
  font-size: 11px;
}

.meta-label {
  color: rgba(255, 255, 255, 0.4);
}

.meta-value {
  color: rgba(255, 255, 255, 0.7);
  word-break: break-all;
}

.status-row {
  margin: 0 12px 10px;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 6px;
}

.status-row.running {
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
  border: 1px solid rgba(96, 165, 250, 0.2);
}

.status-row.done {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-row.fail {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.spin {
  width: 14px;
  height: 14px;
  animation: spin 1s linear infinite;
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

:global(.light) .video-upload-node {
  --node-bg: #fff;
  --node-text: #1e1e2e;

  .node-header {
    border-bottom-color: rgba(0, 0, 0, 0.06);
    background: rgba(0, 0, 0, 0.02);
  }

  .node-name-input,
  .url-input {
    background: rgba(0, 0, 0, 0.03);
    border-color: rgba(0, 0, 0, 0.08);
    color: var(--node-text);

    &::placeholder {
      color: rgba(0, 0, 0, 0.35);
    }
  }

  .upload-placeholder {
    border-color: rgba(0, 0, 0, 0.12);
    color: rgba(0, 0, 0, 0.45);
  }

  .upload-btn span,
  .link-btn {
    border-color: rgba(0, 0, 0, 0.1);
    background: rgba(0, 0, 0, 0.03);
    color: rgba(0, 0, 0, 0.7);
  }

  .meta-label {
    color: rgba(0, 0, 0, 0.45);
  }

  .meta-value {
    color: rgba(0, 0, 0, 0.75);
  }
}
</style>
