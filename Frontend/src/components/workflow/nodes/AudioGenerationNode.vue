<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node audio-gen-node"
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
        v-if="localConfig.model || localConfig.provider"
        class="info-row"
      >
        <span class="info-label">模型</span>
        <span class="info-value">{{ localConfig.model || localConfig.provider || '-' }}</span>
      </div>
      <div
        v-if="localConfig.voice"
        class="info-row"
      >
        <span class="info-label">音色</span>
        <span class="info-value">{{ localConfig.voice }}</span>
      </div>
      <div
        v-if="localConfig.text || localConfig.prompt"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.text || localConfig.prompt, 35) }}</span>
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
      v-if="isCompleted || isRunning"
      class="waveform-zone"
    >
      <div class="waveform-container">
        <canvas
          ref="waveCanvas"
          class="waveform-canvas"
          width="200"
          height="48"
        />
        <div
          v-if="isRunning"
          class="waveform-overlay"
        >
          <span class="waveform-label">波形生成中</span>
        </div>
      </div>
      <div
        v-if="audioDuration || localConfig.format"
        class="audio-meta"
      >
        <span
          v-if="audioDuration"
          class="audio-dur"
        >{{ audioDuration }}</span>
        <span class="audio-format">{{ localConfig.format?.toUpperCase() || 'MP3' }}</span>
      </div>
      <audio
        v-if="audioUrl && isCompleted"
        ref="audioRef"
        :src="audioUrl"
        controls
        class="audio-player"
      />
    </div>

    <div
      v-if="localConfig.format || localConfig.speed"
      class="format-bar"
    >
      <span class="format-tag">{{ localConfig.format?.toUpperCase() || 'MP3' }}</span>
      <span class="format-tag">x{{ localConfig.speed || 1 }}</span>
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
          <label class="config-label">提示词 / 文本</label>
          <el-input
            v-model="localConfig.text"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="输入要转换为语音的文本..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">语音</label>
          <el-input
            v-model="localConfig.voice"
            size="small"
            placeholder="选择语音"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">语速</label>
          <el-input-number
            v-model="localConfig.speed"
            :min="0.5"
            :max="2"
            :step="0.1"
            :precision="1"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">输出格式</label>
          <el-select
            v-model="localConfig.format"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="mp3"
              label="MP3"
            />
            <el-option
              value="wav"
              label="WAV"
            />
            <el-option
              value="ogg"
              label="OGG"
            />
          </el-select>
        </div>
      </div>
    </Transition>

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
import { ref, watch, computed, onMounted, nextTick } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Volume2, ChevronDown, Loader } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'audio_generation'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 240,
  minHeight: 160,
  maxWidth: 640,
  maxHeight: 720,
})

const isExpanded = ref(false)

const waveCanvas = ref(null)
const audioRef = ref(null)

const localName = ref(props.data.label || '音频生成')
const localConfig = ref({
  model: props.data.config?.model || '',
  provider: props.data.config?.provider || '',
  prompt: props.data.config?.prompt || '',
  text: props.data.config?.text || '',
  voice: props.data.config?.voice || '',
  speed: props.data.config?.speed || 1,
  format: props.data.config?.format || 'mp3'
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const audioDuration = computed(() => {
  if (!nodeOutput.value) return null
  const dur = nodeOutput.value.duration || nodeOutput.value.dur
  if (dur) {
    const m = Math.floor(dur / 60)
    const s = Math.floor(dur % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }
  return null
})

const showPreview = computed(() => isCompleted.value && nodeOutput.value)

const audioUrl = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.audio_base64) {
    const fmt = nodeOutput.value.format || 'mp3'
    return `data:audio/${fmt};base64,${nodeOutput.value.audio_base64}`
  }
  return nodeOutput.value.url || nodeOutput.value.audio_url || null
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function drawWaveform() {
  nextTick(() => {
    const canvas = waveCanvas.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const w = canvas.width
    const h = canvas.height
    ctx.clearRect(0, 0, w, h)

    const gradient = ctx.createLinearGradient(0, 0, w, 0)
    gradient.addColorStop(0, 'rgba(217, 70, 239, 0.6)')
    gradient.addColorStop(0.5, 'rgba(217, 70, 239, 1)')
    gradient.addColorStop(1, 'rgba(217, 70, 239, 0.6)')

    const bars = 40
    const barW = w / bars

    for (let i = 0; i < bars; i++) {
      const x = i * barW + barW * 0.1
      const bw = barW * 0.8
      const phase = i / bars * Math.PI * 2
      const amp = isRunning.value
        ? (Math.sin(phase + Date.now() * 0.003) * 0.3 + 0.5) * h * 0.8
        : (Math.sin(phase * 1.7 + 0.3) * 0.2 + Math.sin(phase * 0.5 + 1.2) * 0.15 + 0.25) * h
      const y = (h - amp) / 2
      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.roundRect(x, y, bw, Math.max(amp, 3), 2)
      ctx.fill()
    }
  })
}

let waveInterval = null

watch([isRunning, isCompleted], ([running, completed]) => {
  if (running || completed) {
    drawWaveform()
    if (running) {
      waveInterval = setInterval(drawWaveform, 100)
    }
  } else {
    if (waveInterval) { clearInterval(waveInterval); waveInterval = null }
  }
}, { immediate: true })

onMounted(() => {
  if (isRunning.value || isCompleted.value) {
    drawWaveform()
    if (isRunning.value) waveInterval = setInterval(drawWaveform, 100)
  }
})

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '音频生成'
    localConfig.value = { model: d.config?.model || '', provider: d.config?.provider || '', prompt: d.config?.prompt || '', text: d.config?.text || '', voice: d.config?.voice || '', speed: d.config?.speed || 1, format: d.config?.format || 'mp3', ...d.config }
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
.audio-gen-node {
  &.is-running { animation: audio-pulse 1.8s ease-in-out infinite; }
  &.is-completed .waveform-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes audio-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(217, 70, 239, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(217, 70, 239, 0); }
}

.waveform-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px dashed rgba(217, 70, 239, 0.25);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
  flex: 1 1 auto;
  min-height: 72px;

  &.has-wave { border-style: solid; }
}

.resize-handle {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 14px;
  height: 14px;
  border-right: 2px solid rgba(217, 70, 239, 0.55);
  border-bottom: 2px solid rgba(217, 70, 239, 0.55);
  cursor: nwse-resize;
  opacity: 0.55;
  z-index: 3;

  &:hover { opacity: 1; }
}

.waveform-container {
  position: relative;
  width: 100%;
}

.waveform-canvas {
  width: 100%;
  height: 48px;
  display: block;
}

.waveform-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);

  .waveform-label {
    font-size: 10px;
    font-weight: 600;
    color: rgba(217, 70, 239, 0.8);
    letter-spacing: 0.05em;
  }
}

.audio-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px 6px;

  .audio-dur {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(217, 70, 239, 0.8);
    font-weight: 600;
  }

  .audio-format {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 1px 6px;
    border-radius: 4px;
  }
}

.format-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px 8px;

  .format-tag {
    font-size: 10px;
    color: rgba(217, 70, 239, 0.7);
    background: rgba(217, 70, 239, 0.1);
    border: 1px solid rgba(217, 70, 239, 0.2);
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

  &.running { background: rgba(217, 70, 239, 0.1); color: #d946ef; border: 1px solid rgba(217, 70, 239, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.domain-node {
  position: relative;
  display: flex;
  flex-direction: column;
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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #d946ef; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #d946ef; --node-text: #1e1e2e; } }

.audio-player {
  width: 100%;
  height: 32px;
  margin-top: 4px;
  border-radius: 6px;
  cursor: pointer;

  &::-webkit-media-controls-panel {
    background: rgba(217, 70, 239, 0.1);
  }
}
</style>
