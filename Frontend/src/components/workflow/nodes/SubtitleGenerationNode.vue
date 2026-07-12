<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node subtitle-node"
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
        v-if="localConfig.format || localConfig.model"
        class="info-row"
      >
        <span class="info-label">格式</span>
        <span class="info-value">{{ localConfig.format?.toUpperCase() || localConfig.model || '-' }}</span>
      </div>
      <div
        v-if="localConfig.inputPath"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.inputPath, 35) }}</span>
      </div>
      <div
        v-if="localConfig.language"
        class="info-row"
      >
        <span class="info-label">语言</span>
        <span class="info-value">{{ localConfig.language }}</span>
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
      v-if="isCompleted || isRunning || isFailed"
      class="subtitle-zone"
    >
      <div
        v-if="isFailed"
        class="subtitle-error"
      >
        <AlertCircle class="error-icon" />
        <span>{{ nodeOutput?.error || '字幕生成失败' }}</span>
      </div>
      <template v-else>
        <div class="subtitle-timeline">
          <div class="timeline-bar">
            <div class="timeline-track">
              <div
                class="timeline-progress"
                :style="{ width: isRunning ? '40%' : '100%' }"
              />
            </div>
            <div class="timeline-markers">
              <span class="time-marker start">00:00</span>
              <span class="time-marker end">{{ totalDuration || '—' }}</span>
            </div>
          </div>
        </div>
        <div class="subtitle-preview">
          <div
            v-if="!showSrtFormat && subtitleLines.length > 0"
            class="subtitle-lines"
          >
            <div
              v-for="(line, i) in subtitleLines.slice(0, 3)"
              :key="i"
              class="subtitle-line"
              :class="{ active: isRunning && i === 0 }"
            >
              <span class="sub-time">{{ line.start || line.startTime || '00:00' }}</span>
              <span class="sub-text">{{ line.text || line.content || line.value || '' }}</span>
            </div>
          </div>
          <div
            v-else-if="showSrtFormat && srtContent"
            class="srt-preview"
          >
            <pre class="srt-text">{{ srtContent.length > 300 ? srtContent.slice(0, 300) + '\n...' : srtContent }}</pre>
          </div>
          <div
            v-else
            class="subtitle-empty"
          >
            <Subtitles class="empty-icon" />
            <span
              v-if="isRunning"
              class="empty-text"
            >正在识别语音...</span>
            <span
              v-else
              class="empty-text"
            >字幕预览</span>
          </div>
        </div>
        <div
          v-if="isCompleted && srtContent"
          class="subtitle-actions"
        >
          <button
            class="format-toggle"
            @click.stop="showSrtFormat = !showSrtFormat"
          >
            <FileText class="toggle-icon" />
            {{ showSrtFormat ? '时间轴视图' : 'SRT 格式' }}
          </button>
          <button
            class="copy-btn"
            :class="{ copied: copiedSrt }"
            @click.stop="copySrt"
          >
            <Check
              v-if="copiedSrt"
              class="copy-icon"
            />
            <Copy
              v-else
              class="copy-icon"
            />
            {{ copiedSrt ? '已复制' : '复制' }}
          </button>
        </div>
        <div
          v-if="subtitleCount > 0"
          class="subtitle-count"
        >
          <span class="count-badge">{{ subtitleCount }} 条字幕</span>
          <span class="count-format">{{ localConfig.format?.toUpperCase() || 'SRT' }}</span>
        </div>
      </template>
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
          <label class="config-label">输入类型</label>
          <el-select
            v-model="localConfig.inputType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="audio"
              label="音频文件"
            />
            <el-option
              value="video"
              label="视频文件"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">音频/视频路径或 URL</label>
          <el-input
            v-model="localConfig.inputPath"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="本地文件路径，或公网可访问的音频/视频 URL（DashScope 需要 URL）..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">服务商</label>
          <el-select
            v-model="localConfig.provider"
            size="small"
            placeholder="自动（URL 用 DashScope，本地路径用 OpenAI）"
            clearable
            @change="handleChange"
          >
            <el-option
              value="openai"
              label="OpenAI Whisper（本地文件）"
            />
            <el-option
              value="dashscope"
              label="阿里云百炼 Paraformer（公网 URL）"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">字幕格式</label>
          <el-select
            v-model="localConfig.format"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="srt"
              label="SRT"
            />
            <el-option
              value="vtt"
              label="VTT"
            />
            <el-option
              value="ass"
              label="ASS"
            />
            <el-option
              value="txt"
              label="TXT"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">语言</label>
          <el-input
            v-model="localConfig.language"
            size="small"
            placeholder="例如: zh-CN, en-US"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">最大字符数/行</label>
          <el-input-number
            v-model="localConfig.maxCharsPerLine"
            :min="10"
            :max="100"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
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
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Subtitles, ChevronDown, Loader, Copy, Check, AlertCircle, FileText } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'subtitle_generation'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 260,
  minHeight: 180,
  maxWidth: 720,
  maxHeight: 900,
})

const isExpanded = ref(false)

const localName = ref(props.data.label || '字幕生成')
const localConfig = ref({
  model: props.data.config?.model || '',
  provider: props.data.config?.provider || '',
  format: props.data.config?.format || 'srt',
  inputType: props.data.config?.inputType || 'audio',
  inputPath: props.data.config?.inputPath || props.data.config?.input || '',
  language: props.data.config?.language || 'zh-CN',
  maxCharsPerLine: props.data.config?.maxCharsPerLine || 42
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const showSrtFormat = ref(false)
const copiedSrt = ref(false)

function formatSeconds(sec) {
  const total = Math.max(0, Math.floor(Number(sec) || 0))
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const subtitleLines = computed(() => {
  if (!nodeOutput.value) return []
  if (Array.isArray(nodeOutput.value)) return nodeOutput.value
  const segments = nodeOutput.value.segments
  if (Array.isArray(segments) && segments.length) {
    return segments.map((seg) => ({
      start: formatSeconds(seg.start),
      end: formatSeconds(seg.end),
      text: seg.text || ''
    }))
  }
  if (Array.isArray(nodeOutput.value.lines)) return nodeOutput.value.lines
  if (nodeOutput.value.text) return [{ start: '00:00', end: '00:00', text: nodeOutput.value.text }]
  return []
})

const srtContent = computed(() => {
  if (!nodeOutput.value) return ''
  if (typeof nodeOutput.value.subtitles === 'string') return nodeOutput.value.subtitles
  if (Array.isArray(nodeOutput.value.subtitles)) {
    return nodeOutput.value.subtitles.map((line, i) => {
      const idx = i + 1
      const start = line.start || line.startTime || '00:00:00,000'
      const end = line.end || line.endTime || '00:00:00,000'
      const text = line.text || line.content || line.value || ''
      return `${idx}\n${start} --> ${end}\n${text}`
    }).join('\n\n')
  }
  return nodeOutput.value.text || ''
})

async function copySrt() {
  try {
    await navigator.clipboard.writeText(srtContent.value)
    copiedSrt.value = true
    setTimeout(() => { copiedSrt.value = false }, 2000)
  } catch (e) {
    console.error('Copy failed', e)
  }
}

const subtitleCount = computed(() => {
  if (!nodeOutput.value) return 0
  if (nodeOutput.value.count) return nodeOutput.value.count
  return subtitleLines.value.length
})

const totalDuration = computed(() => {
  if (!nodeOutput.value) return null
  if (nodeOutput.value.duration) {
    const d = nodeOutput.value.duration
    const m = Math.floor(d / 60)
    const s = Math.floor(d % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }
  const segments = nodeOutput.value.segments
  if (Array.isArray(segments) && segments.length) {
    return formatSeconds(segments[segments.length - 1].end)
  }
  return null
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '字幕生成'
    localConfig.value = {
      model: d.config?.model || '',
      provider: d.config?.provider || '',
      format: d.config?.format || 'srt',
      inputType: d.config?.inputType || 'audio',
      inputPath: d.config?.inputPath || d.config?.input || '',
      language: d.config?.language || 'zh-CN',
      maxCharsPerLine: d.config?.maxCharsPerLine || 42,
      ...d.config
    }
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
.subtitle-node {
  &.is-running { animation: sub-pulse 1.8s ease-in-out infinite; }
  &.is-completed .subtitle-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes sub-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(168, 85, 247, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(168, 85, 247, 0); }
}

.subtitle-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px dashed rgba(168, 85, 247, 0.25);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
  flex: 1 1 auto;
  min-height: 100px;
  display: flex;
  flex-direction: column;
}

.resize-handle {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 14px;
  height: 14px;
  border-right: 2px solid rgba(168, 85, 247, 0.55);
  border-bottom: 2px solid rgba(168, 85, 247, 0.55);
  cursor: nwse-resize;
  opacity: 0.55;
  z-index: 3;

  &:hover { opacity: 1; }
}

.subtitle-error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 10px;
  color: #ef4444;

  .error-icon { width: 14px; height: 14px; }
}

.subtitle-timeline {
  padding: 8px 10px 6px;
}

.timeline-bar { display: flex; flex-direction: column; gap: 4px; }

.timeline-track {
  height: 6px;
  background: rgba(168, 85, 247, 0.15);
  border-radius: 3px;
  overflow: hidden;
}

.timeline-progress {
  height: 100%;
  background: linear-gradient(90deg, rgba(168, 85, 247, 0.6), #a855f7);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.timeline-markers {
  display: flex;
  justify-content: space-between;

  .time-marker {
    font-size: 8px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(168, 85, 247, 0.5);

    &.end { color: rgba(255, 255, 255, 0.3); }
  }
}

.subtitle-preview {
  padding: 0 10px 8px;
}

.subtitle-lines { display: flex; flex-direction: column; gap: 3px; }

.subtitle-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 3px 6px;
  background: rgba(168, 85, 247, 0.06);
  border: 1px solid rgba(168, 85, 247, 0.1);
  border-radius: 4px;
  transition: all 0.2s ease;

  &.active {
    background: rgba(168, 85, 247, 0.15);
    border-color: rgba(168, 85, 247, 0.3);
  }

  .sub-time {
    font-size: 8px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(168, 85, 247, 0.6);
    flex-shrink: 0;
  }

  .sub-text {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.7);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.subtitle-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 0;

  .empty-icon { width: 20px; height: 20px; color: rgba(168, 85, 247, 0.2); }
  .empty-text { font-size: 9px; color: rgba(255, 255, 255, 0.2); }
}

.subtitle-count {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.subtitle-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px 6px;
}

.format-toggle,
.copy-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 9px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid rgba(168, 85, 247, 0.2);
  background: rgba(168, 85, 247, 0.08);
  color: rgba(168, 85, 247, 0.8);

  .toggle-icon,
  .copy-icon {
    width: 10px;
    height: 10px;
  }

  &:hover {
    background: rgba(168, 85, 247, 0.15);
    border-color: rgba(168, 85, 247, 0.4);
  }

  &.copied {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: #10b981;
  }
}

.srt-preview {
  padding: 4px 6px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  max-height: 60px;
  overflow: auto;
}

.srt-text {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(168, 85, 247, 0.7);
  white-space: pre-wrap;
  margin: 0;
  line-height: 1.4;
}

.count-badge {
  font-size: 10px;
  font-weight: 600;
  color: rgba(168, 85, 247, 0.8);
}

.count-format {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
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

  &.running { background: rgba(168, 85, 247, 0.1); color: #a855f7; border: 1px solid rgba(168, 85, 247, 0.2); }
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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #a855f7; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #a855f7; --node-text: #1e1e2e; } }
</style>
