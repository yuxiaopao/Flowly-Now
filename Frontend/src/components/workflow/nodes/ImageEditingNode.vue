<template>
  <div
    ref="rootEl"
    :style="{ '--node-accent': nodeColor, ...resize.sizeStyle.value }"
    class="domain-node image-edit-node"
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
        v-if="localConfig.instruction || localConfig.prompt"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.instruction || localConfig.prompt, 35) }}</span>
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
          <span>编辑中...</span>
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
      class="compare-zone"
    >
      <div
        v-if="isFailed"
        class="compare-error"
      >
        <AlertCircle class="error-icon" />
        <span>{{ nodeOutput?.error || '图像编辑失败' }}</span>
      </div>
      <template v-else>
        <div class="compare-header">
          <span class="compare-label input-side">
            <ArrowLeft class="compare-icon" />输入
          </span>
          <span class="compare-divider">→</span>
          <span class="compare-label output-side">
            输出<ArrowRight class="compare-icon" />
          </span>
        </div>
        <div class="compare-grid">
          <div
            v-if="inputImage"
            class="compare-cell input-cell"
          >
            <img
              :src="inputImage"
              alt="Input"
              class="compare-img"
            >
            <div class="cell-tag input-tag">
              Before
            </div>
          </div>
          <div
            v-else
            class="compare-cell input-placeholder"
          >
            <ImageIcon class="placeholder-icon" />
            <span>输入图像</span>
          </div>
          <div
            v-if="showPreview"
            class="compare-cell output-cell"
          >
            <img
              :src="previewImage"
              alt="Output"
              class="compare-img"
            >
            <div class="cell-tag output-tag">
              After
            </div>
          </div>
          <div
            v-else
            class="compare-cell output-placeholder"
          >
            <div
              v-if="isRunning"
              class="editing-animation"
            >
              <div class="edit-grid">
                <div
                  v-for="i in 4"
                  :key="i"
                  class="edit-cell"
                />
              </div>
            </div>
            <div v-else>
              <ImageIcon class="placeholder-icon" />
              <span>输出图像</span>
            </div>
          </div>
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
          <label class="config-label">服务商</label>
          <el-input
            v-model="localConfig.provider"
            size="small"
            placeholder="输入服务商"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">编辑指令</label>
          <el-input
            v-model="localConfig.instruction"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="描述想要的编辑效果..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">输入图像</label>
          <el-input
            v-model="localConfig.image"
            size="small"
            placeholder="输入图像 URL 或路径"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">蒙版</label>
          <el-input
            v-model="localConfig.mask"
            size="small"
            placeholder="蒙版图像 URL 或路径 (可选)"
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
import { Image, ChevronDown, ImageIcon, ArrowLeft, ArrowRight, Loader, AlertCircle } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useNodeResize } from '@/composables/useNodeResize'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'image_editing'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const rootEl = ref(null)
const resize = useNodeResize({
  id: props.id,
  initialWidth: props.data.uiSize?.width,
  initialHeight: props.data.uiSize?.height,
  minWidth: 280,
  minHeight: 200,
  maxWidth: 820,
  maxHeight: 960,
})

const isExpanded = ref(false)

const localName = ref(props.data.label || '图像编辑')
const localConfig = ref({
  model: props.data.config?.model || '',
  provider: props.data.config?.provider || '',
  instruction: props.data.config?.instruction || props.data.config?.prompt || '',
  image: props.data.config?.image || props.data.config?.inputImage || '',
  mask: props.data.config?.mask || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const inputImage = computed(() => {
  return localConfig.value.image || (nodeOutput.value && nodeOutput.value.input) || (nodeOutput.value && nodeOutput.value.inputImage)
})

const previewImage = computed(() => {
  if (!nodeOutput.value) return null
  if (typeof nodeOutput.value === 'string') return nodeOutput.value
  if (nodeOutput.value.url) return nodeOutput.value.url
  if (nodeOutput.value.output) return nodeOutput.value.output
  if (nodeOutput.value.image) return nodeOutput.value.image
  if (nodeOutput.value.data) return nodeOutput.value.data
  return null
})

const showPreview = computed(() => isCompleted.value && previewImage.value)

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '图像编辑'
    localConfig.value = {
      model: d.config?.model || '',
      provider: d.config?.provider || '',
      instruction: d.config?.instruction || d.config?.prompt || '',
      image: d.config?.image || d.config?.inputImage || '',
      mask: d.config?.mask || '',
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
.image-edit-node {
  &.is-running { animation: edit-pulse 1.8s ease-in-out infinite; }
  &.is-completed .compare-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes edit-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(244, 63, 94, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(244, 63, 94, 0); }
}

.compare-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px dashed rgba(244, 63, 94, 0.25);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
  flex: 1 1 auto;
  min-height: 120px;
}

.resize-handle {
  position: absolute;
  right: 4px;
  bottom: 4px;
  width: 14px;
  height: 14px;
  border-right: 2px solid rgba(244, 63, 94, 0.55);
  border-bottom: 2px solid rgba(244, 63, 94, 0.55);
  cursor: nwse-resize;
  opacity: 0.55;
  z-index: 3;

  &:hover { opacity: 1; }
}

.compare-error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 10px;
  font-size: 10px;
  color: #ef4444;

  .error-icon { width: 14px; height: 14px; }
}

.compare-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.compare-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;

  .compare-icon { width: 10px; height: 10px; }

  &.input-side { color: rgba(255, 255, 255, 0.4); }
  &.output-side { color: rgba(244, 63, 94, 0.8); }
}

.compare-divider {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.15);
}

.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
}

.compare-cell {
  position: relative;
  height: 60px;
  overflow: hidden;

  &.input-placeholder, &.output-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 4px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px dashed rgba(255, 255, 255, 0.08);

    .placeholder-icon { width: 16px; height: 16px; color: rgba(255, 255, 255, 0.15); }
    span { font-size: 9px; color: rgba(255, 255, 255, 0.2); }
  }
}

.compare-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cell-tag {
  position: absolute;
  top: 4px;
  left: 4px;
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 1px 5px;
  border-radius: 3px;

  &.input-tag { background: rgba(100, 116, 139, 0.7); color: white; }
  &.output-tag { background: rgba(244, 63, 94, 0.8); color: white; }
}

.editing-animation {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.edit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  width: 36px;
  height: 36px;
}

.edit-cell {
  background: rgba(244, 63, 94, 0.2);
  border-radius: 2px;
  animation: edit-cell-pulse 0.8s ease-in-out infinite;

  @for $i from 1 through 4 {
    &:nth-child(#{$i}) { animation-delay: #{($i - 1) * 0.15}s; }
  }
}

@keyframes edit-cell-pulse {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; background: rgba(244, 63, 94, 0.6); }
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

  &.running { background: rgba(244, 63, 94, 0.1); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.2); }
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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #f43f5e; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #f43f5e; --node-text: #1e1e2e; } }
</style>
