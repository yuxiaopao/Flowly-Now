<template>
  <div
    class="domain-node image-gen-node"
    :class="{ selected, expanded: isExpanded, 'is-running': showRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
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
        <Sparkles
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">图像生成</span>
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
        class="status-bar"
        :class="{ running: showRunning, completed: isCompleted, failed: isFailed }"
      >
        <div
          v-if="showRunning"
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
      v-if="showPreview || showRunning"
      class="preview-zone"
      :class="{ 'has-image': showPreview }"
      :style="previewAspectRatio ? { aspectRatio: previewAspectRatio } : {}"
    >
      <div
        v-if="showRunning"
        class="generating-placeholder"
      >
        <div class="gen-grid">
          <div
            v-for="i in 9"
            :key="i"
            class="gen-cell"
          />
        </div>
        <span class="gen-hint">AI 创作中...</span>
      </div>
      <img
        v-else-if="showPreview"
        :src="previewImage"
        class="preview-img"
        :style="previewAspectRatio ? { height: 'auto', aspectRatio: previewAspectRatio } : {}"
        alt="Generated image"
        @click="handleImageClick"
      >
      <div
        v-if="showPreview"
        class="preview-overlay"
      >
        <button
          class="preview-btn"
          title="放大查看"
          @click.stop="handleImageClick"
        >
          <ZoomIn class="btn-icon" />
        </button>
        <button
          class="preview-btn"
          title="下载图片"
          @click.stop="handleDownload"
        >
          <Download class="btn-icon" />
        </button>
      </div>
    </div>

    <div
      v-if="localConfig.size"
      class="size-bar"
    >
      <span class="size-label">{{ localConfig.size }}</span>
      <span class="quality-label">{{ localConfig.quality === 'hd' ? '高清' : '标准' }}</span>
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
            placeholder="描述想要生成的图像..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">尺寸</label>
          <el-select
            v-model="localConfig.size"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="1024x1024"
              label="1024x1024"
            />
            <el-option
              value="1024x1792"
              label="1024x1792 (竖版)"
            />
            <el-option
              value="1792x1024"
              label="1792x1024 (横版)"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">质量</label>
          <el-select
            v-model="localConfig.quality"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="standard"
              label="标准"
            />
            <el-option
              value="hd"
              label="高清"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">风格</label>
          <el-select
            v-model="localConfig.style"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="vivid"
              label="生动"
            />
            <el-option
              value="natural"
              label="自然"
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
import { Sparkles, ChevronDown, Download, ZoomIn, Loader } from 'lucide-vue-next'
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
const nodeColor = '#ec4899'

const localName = ref(props.data.label || '图像生成')
const localConfig = ref({
  model: props.data.config?.model || '',
  provider: props.data.config?.provider || '',
  prompt: props.data.config?.prompt || '',
  text: props.data.config?.text || '',
  size: props.data.config?.size || '1024x1024',
  quality: props.data.config?.quality || 'standard',
  style: props.data.config?.style || 'vivid'
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const previewImage = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.url) return nodeOutput.value.url
  if (nodeOutput.value.image) return nodeOutput.value.image
  if (nodeOutput.value.data) return nodeOutput.value.data
  return null
})

const previewAspectRatio = computed(() => {
  if (!nodeOutput.value) return null
  const w = nodeOutput.value.width || nodeOutput.value.w
  const h = nodeOutput.value.height || nodeOutput.value.h
  if (w && h) return w / h
  // 尝试从 size 配置推导比例
  const size = localConfig.value.size || '1024x1024'
  const [sw, sh] = size.split('x').map(Number)
  if (sw && sh) return sw / sh
  return null
})

const showPreview = computed(() => isCompleted.value && previewImage.value)
const showRunning = computed(() => isRunning.value)

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function handleImageClick() {
  if (previewImage.value) window.open(previewImage.value, '_blank')
}

function handleDownload() {
  if (!previewImage.value) return
  const a = document.createElement('a')
  a.href = previewImage.value
  a.download = `generated-${props.id}.png`
  a.click()
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '图像生成'
    localConfig.value = {
      model: d.config?.model || '',
      provider: d.config?.provider || '',
      prompt: d.config?.prompt || '',
      text: d.config?.text || '',
      size: d.config?.size || '1024x1024',
      quality: d.config?.quality || 'standard',
      style: d.config?.style || 'vivid',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() { isExpanded.value = !isExpanded.value }

function handleChange() {
  if (props.id) {
    updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
  }
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}
</script>

<style lang="scss" scoped>
.image-gen-node {
  &.is-running {
    animation: gen-pulse 1.8s ease-in-out infinite;
  }

  &.is-completed .preview-zone {
    border-color: rgba(16, 185, 129, 0.4);
  }

  &.is-failed {
    border-color: rgba(239, 68, 68, 0.6) !important;
  }
}

@keyframes gen-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(236, 72, 153, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(236, 72, 153, 0); }
}

.preview-zone {
  position: relative;
  margin: 0 12px 8px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px dashed rgba(236, 72, 153, 0.25);
  background: rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;

  &.has-image {
    border-style: solid;
  }
}

.preview-img {
  width: 100%;
  height: auto;
  max-height: 200px;
  object-fit: cover;
  display: block;
  cursor: pointer;
  transition: transform 0.2s ease;

  &:hover { transform: scale(1.02); }
}

.preview-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.5);
  opacity: 0;
  transition: opacity 0.2s ease;

  .preview-zone:hover & { opacity: 1; }
}

.preview-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  cursor: pointer;
  color: white;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.25);
    transform: scale(1.1);
  }

  .btn-icon { width: 16px; height: 16px; }
}

.generating-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100px;
  padding: 12px;
  gap: 8px;
}

.gen-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  width: 48px;
  height: 48px;
}

.gen-cell {
  background: rgba(236, 72, 153, 0.2);
  border-radius: 2px;
  animation: cell-pulse 1.2s ease-in-out infinite;

  @for $i from 1 through 9 {
    &:nth-child(#{$i}) { animation-delay: #{($i - 1) * 0.1}s; }
  }
}

@keyframes cell-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.9); background: rgba(236, 72, 153, 0.2); }
  50% { opacity: 1; transform: scale(1); background: rgba(236, 72, 153, 0.5); }
}

.gen-hint {
  font-size: 10px;
  color: rgba(236, 72, 153, 0.7);
  font-weight: 600;
  letter-spacing: 0.05em;
}

.size-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px 8px;

  .size-label {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: rgba(236, 72, 153, 0.7);
    background: rgba(236, 72, 153, 0.1);
    border: 1px solid rgba(236, 72, 153, 0.2);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .quality-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 1px 6px;
    border-radius: 4px;
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
    background: rgba(236, 72, 153, 0.1);
    color: #ec4899;
    border: 1px solid rgba(236, 72, 153, 0.2);
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

  &.spinning { animation: spin 1s linear infinite; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

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

  &.selected {
    box-shadow: 0 8px 32px color-mix(in srgb, v-bind(nodeColor) 30%, transparent), 0 0 0 2px color-mix(in srgb, v-bind(nodeColor) 30%, transparent);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px color-mix(in srgb, v-bind(nodeColor) 20%, transparent);
    transform: translateY(-1px);
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

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border: 1px solid;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;

  .badge-icon { width: 11px; height: 11px; }
}

.action-btn {
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

  &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); }

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
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text, #e5e5e5);
  outline: none;
  transition: all 0.15s ease;

  &::placeholder { color: rgba(255, 255, 255, 0.3); }
  &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); }
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
  gap: 6px;

  .info-label { font-size: 10px; color: rgba(255, 255, 255, 0.4); }
  .info-value { font-size: 11px; color: rgba(255, 255, 255, 0.7); font-family: 'JetBrains Mono', monospace; }
}

.preview-row .preview-text {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.expanded-config {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 8px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.config-section { display: flex; flex-direction: column; gap: 5px; }

.config-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.4);
}

:deep(.el-select),
:deep(.el-input),
:deep(.el-input-number) {
  width: 100%;

  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: none !important;
    border-radius: 6px;
  }

  .el-input__inner { color: var(--node-text, #e5e5e5) !important; font-size: 12px !important; }
}

.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 500px; }

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: rgba(10, 10, 18, 0.95);
  border: 2px solid v-bind(nodeColor);
  border-radius: 50%;

  &:hover { background: v-bind(nodeColor); transform: scale(1.3); }
}

:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #ec4899; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #ec4899; --node-text: #1e1e2e; } }
</style>
