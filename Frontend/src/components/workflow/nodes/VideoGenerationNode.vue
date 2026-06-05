<template>
  <div
    class="domain-node video-gen-node"
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
        <Video
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">视频生成</span>
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
        v-if="localConfig.model || localConfig.provider"
        class="info-row"
      >
        <span class="info-label">模型</span>
        <span class="info-value">{{ localConfig.model || localConfig.provider || '-' }}</span>
      </div>
      <div
        v-if="localConfig.prompt || localConfig.text"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.prompt || localConfig.text, 35) }}</span>
      </div>
      <div
        v-if="localConfig.duration"
        class="info-row"
      >
        <span class="info-label">时长</span>
        <span class="info-value">{{ localConfig.duration }}s / {{ localConfig.resolution }}</span>
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
          <span>生成中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
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
      v-if="showPreview || isRunning || inputImage"
      class="preview-zone"
      :class="{ 'has-video': showPreview }"
    >
      <!-- 视频生成中：显示输入图片（上游图生图结果）+ 动画占位 -->
      <div
        v-if="isRunning && inputImage"
        class="input-image-wrapper"
      >
        <img
          :src="inputImage"
          class="input-image"
          alt="Input image"
        >
        <div class="input-overlay">
          <Loader class="input-spinner" />
          <span>基于输入图生成视频...</span>
        </div>
      </div>
      <!-- 纯生成中（无输入图） -->
      <div
        v-else-if="isRunning"
        class="generating-placeholder"
      >
        <div class="film-strip">
          <div
            v-for="i in 8"
            :key="i"
            class="film-frame"
          />
        </div>
        <span class="gen-hint">AI 创作中...</span>
      </div>
      <!-- 生成完成：显示视频缩略图 -->
      <div
        v-else-if="showPreview"
        class="video-thumb-wrapper"
        @click="showVideoPlayer = true"
      >
        <img
          v-if="previewThumb"
          :src="previewThumb"
          class="video-thumb"
          alt="Video thumbnail"
        >
        <div
          v-else
          class="video-placeholder"
        >
          <Video class="placeholder-icon" />
        </div>
        <div class="video-play-overlay">
          <PlayCircle class="play-icon" />
        </div>
        <div
          v-if="videoDuration"
          class="video-duration"
        >
          {{ videoDuration }}
        </div>
      </div>
      <!-- 预填充状态：显示输入图预览 -->
      <div
        v-else-if="inputImage"
        class="input-image-wrapper"
      >
        <img
          :src="inputImage"
          class="input-image"
          alt="Input image"
        >
        <div class="input-badge">
          输入图片
        </div>
      </div>
    </div>

    <!-- Video Player Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showVideoPlayer && videoUrl"
          class="video-modal"
          @click.self="showVideoPlayer = false"
        >
          <div class="video-modal-content">
            <button
              class="video-modal-close"
              @click="showVideoPlayer = false"
            >
              <X class="close-icon" />
            </button>
            <video
              ref="videoRef"
              :src="videoUrl"
              controls
              autoplay
              class="video-player"
            />
          </div>
        </div>
      </Transition>
    </Teleport>

    <div
      v-if="localConfig.resolution || localConfig.fps"
      class="meta-bar"
    >
      <span class="meta-tag">{{ localConfig.resolution || '-' }}</span>
      <span class="meta-tag">{{ localConfig.fps }}fps</span>
      <span class="meta-tag">{{ localConfig.duration }}s</span>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">模型</label>
          <el-input
            v-model="localConfig.model"
            size="small"
            placeholder="输入模型名称"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">服务商</label>
          <el-input
            v-model="localConfig.provider"
            size="small"
            placeholder="输入服务商"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">提示词</label>
          <el-input
            v-model="localConfig.prompt"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="描述想要生成的视频..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">时长 (秒)</label>
          <el-input-number
            v-model="localConfig.duration"
            :min="1"
            :max="60"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">分辨率</label>
          <el-select
            v-model="localConfig.resolution"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="720p"
              label="720p"
            />
            <el-option
              value="1080p"
              label="1080p"
            />
            <el-option
              value="4k"
              label="4K"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">帧率</label>
          <el-select
            v-model="localConfig.fps"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="24"
              label="24 fps"
            />
            <el-option
              value="30"
              label="30 fps"
            />
            <el-option
              value="60"
              label="60 fps"
            />
          </el-select>
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
import { Video, ChevronDown, PlayCircle, Loader, X } from 'lucide-vue-next'
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
const nodeColor = '#f97316'

const localName = ref(props.data.label || '视频生成')
const localConfig = ref({
  model: props.data.config?.model || '',
  provider: props.data.config?.provider || '',
  prompt: props.data.config?.prompt || '',
  text: props.data.config?.text || '',
  duration: props.data.config?.duration || 5,
  resolution: props.data.config?.resolution || '1080p',
  fps: props.data.config?.fps || '30'
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

// Input image from upstream node (e.g., ImageGeneration output)
const inputImage = computed(() => {
  if (!nodeOutput.value) return null
  // 支持 input_image / inputImage / inputUrl 等字段
  return nodeOutput.value.input_image
    || nodeOutput.value.inputImage
    || nodeOutput.value.inputUrl
    || nodeOutput.value.input_url
    || null
})

const previewThumb = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.thumbnail) return nodeOutput.value.thumbnail
  if (nodeOutput.value.thumb) return nodeOutput.value.thumb
  if (nodeOutput.value.url) return nodeOutput.value.url
  return null
})

const videoDuration = computed(() => {
  if (!nodeOutput.value) return null
  const dur = nodeOutput.value.duration || nodeOutput.value.dur
  if (dur) {
    const m = Math.floor(dur / 60)
    const s = Math.floor(dur % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }
  return null
})

const videoRef = ref(null)
const showVideoPlayer = ref(false)

const videoUrl = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  return nodeOutput.value.url || nodeOutput.value.video_url || null
})

const showPreview = computed(() => isCompleted.value && (previewThumb.value || videoUrl.value))

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '视频生成'
    localConfig.value = { model: d.config?.model || '', provider: d.config?.provider || '', prompt: d.config?.prompt || '', text: d.config?.text || '', duration: d.config?.duration || 5, resolution: d.config?.resolution || '1080p', fps: d.config?.fps || '30', ...d.config }
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
.video-gen-node {
  &.is-running { animation: video-pulse 1.8s ease-in-out infinite; }
  &.is-completed .preview-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes video-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(249, 115, 22, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(249, 115, 22, 0); }
}

.preview-zone {
  position: relative;
  margin: 0 12px 8px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px dashed rgba(249, 115, 22, 0.25);
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  aspect-ratio: 16 / 9;

  &.has-video { border-style: solid; }
}

.video-thumb-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;

  &:hover .video-play-overlay { opacity: 1; }
}

.video-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(249, 115, 22, 0.1);

  .placeholder-icon { width: 32px; height: 32px; color: rgba(249, 115, 22, 0.5); }
}

.video-play-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  opacity: 0;
  transition: opacity 0.2s ease;

  .play-icon { width: 40px; height: 40px; color: white; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.5)); }
}

.video-duration {
  position: absolute;
  bottom: 6px;
  right: 6px;
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  color: white;
  background: rgba(0, 0, 0, 0.7);
  padding: 2px 6px;
  border-radius: 4px;
}

.generating-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  padding: 12px;
  gap: 12px;
}

.input-image-wrapper {
  position: relative;
  width: 100%;
  height: 100%;

  &:hover .input-overlay,
  &:hover .input-badge { opacity: 1; }
}

.input-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.input-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 4px;
  color: rgba(249, 115, 22, 0.9);
  font-size: 11px;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s ease;

  .input-spinner {
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
    color: #f97316;
  }
}

.input-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  background: rgba(249, 115, 22, 0.85);
  color: white;
  font-size: 9px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.film-strip {
  display: flex;
  gap: 3px;
  padding: 6px 8px;
  background: rgba(249, 115, 22, 0.1);
  border: 1px solid rgba(249, 115, 22, 0.2);
  border-radius: 4px;
}

.film-frame {
  width: 14px;
  height: 10px;
  background: rgba(249, 115, 22, 0.2);
  border-radius: 2px;
  animation: film-pulse 1s ease-in-out infinite;

  @for $i from 1 through 8 {
    &:nth-child(#{$i}) { animation-delay: #{($i - 1) * 0.08}s; }
  }
}

@keyframes film-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; background: rgba(249, 115, 22, 0.6); }
}

.gen-hint {
  font-size: 10px;
  color: rgba(249, 115, 22, 0.7);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.meta-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px 8px;

  .meta-tag {
    font-size: 10px;
    color: rgba(249, 115, 22, 0.7);
    background: rgba(249, 115, 22, 0.1);
    border: 1px solid rgba(249, 115, 22, 0.2);
    padding: 1px 6px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
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

  &.running { background: rgba(249, 115, 22, 0.1); color: #f97316; border: 1px solid rgba(249, 115, 22, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.domain-node {
  background: var(--node-bg, rgba(20, 20, 30, 0.95));
  border: 2px solid var(--node-border, v-bind(nodeColor));
  border-radius: 12px;
  min-width: 160px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected { box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent); transform: translateY(-1px); }
}

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; border: 1px solid; border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; .badge-icon { width: 11px; height: 11px; } }

.action-btn {
  width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;
  cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease;
  &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); }
  .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } }
}

.node-name-section { padding: 10px 12px 6px; }
.node-name-input {
  width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px;
  padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease;
  &::placeholder { color: rgba(255, 255, 255, 0.3); }
  &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); }
}
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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #f97316; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #f97316; --node-text: #1e1e2e; } }

// Video player modal
.video-modal {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
}

.video-modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

.video-modal-close {
  position: absolute;
  top: -40px;
  right: 0;
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 4px;
  opacity: 0.8;
  &:hover { opacity: 1; }
  .close-icon { width: 20px; height: 20px; }
}

.video-player {
  display: block;
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 12px;
  background: #000;
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
