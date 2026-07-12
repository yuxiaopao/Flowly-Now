<template>
  <div
    :style="{ '--node-accent': nodeColor }" class="domain-node"
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
        v-if="localConfig.loaderType || localConfig.source"
        class="info-row"
      >
        <span class="info-label">类型</span>
        <span class="info-value">{{ localConfig.loaderType || localConfig.source || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description || localConfig.filePath"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description || localConfig.filePath, 35) }}</span>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning || isFailed"
      class="result-zone"
    >
      <div
        v-if="isRunning"
        class="result-running"
      >
        <Loader class="result-icon spinning" />
        <span>加载中...</span>
      </div>
      <div
        v-else-if="isCompleted"
        class="result-completed"
      >
        <div class="result-meta">
          <span class="meta-badge pages">{{ nodeOutput?.page_count || nodeOutput?.pages || '?' }} 页</span>
          <span
            v-if="nodeOutput?.format"
            class="meta-badge format"
          >{{ nodeOutput.format.toUpperCase() }}</span>
        </div>
        <div
          v-if="nodeOutput?.char_count || nodeOutput?.word_count"
          class="result-info"
        >
          <span class="info-chip">{{ nodeOutput?.char_count ? nodeOutput.char_count + ' 字符' : '' }}</span>
          <span class="info-chip">{{ nodeOutput?.word_count ? nodeOutput.word_count + ' 词' : '' }}</span>
        </div>
      </div>
      <div
        v-else-if="isFailed"
        class="result-failed"
      >
        <AlertCircle class="result-icon" />
        <span>{{ nodeOutput?.error || '加载失败' }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">加载器类型</label>
          <el-select
            v-model="localConfig.loaderType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="pdf"
              label="PDF"
            />
            <el-option
              value="docx"
              label="Word (DOCX)"
            />
            <el-option
              value="txt"
              label="文本 (TXT)"
            />
            <el-option
              value="markdown"
              label="Markdown"
            />
            <el-option
              value="csv"
              label="CSV"
            />
            <el-option
              value="json"
              label="JSON"
            />
            <el-option
              value="html"
              label="HTML"
            />
            <el-option
              value="url"
              label="URL"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">数据源</label>
          <el-input
            v-model="localConfig.source"
            size="small"
            placeholder="文件路径或 URL"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">文件路径</label>
          <el-input
            v-model="localConfig.filePath"
            size="small"
            placeholder="本地文件路径"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="文档描述..."
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">编码</label>
          <el-select
            v-model="localConfig.encoding"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="utf-8"
              label="UTF-8"
            />
            <el-option
              value="gbk"
              label="GBK"
            />
            <el-option
              value="gb2312"
              label="GB2312"
            />
            <el-option
              value="auto"
              label="自动检测"
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
import { FileText, ChevronDown, Loader, AlertCircle } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'document_loader'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const isExpanded = ref(false)

const localName = ref(props.data.label || '文档加载')
const localConfig = ref({
  loaderType: props.data.config?.loaderType || 'pdf',
  source: props.data.config?.source || '',
  filePath: props.data.config?.filePath || '',
  description: props.data.config?.description || '',
  encoding: props.data.config?.encoding || 'utf-8'
})

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '文档加载'
    localConfig.value = {
      loaderType: d.config?.loaderType || 'pdf',
      source: d.config?.source || '',
      filePath: d.config?.filePath || '',
      description: d.config?.description || '',
      encoding: d.config?.encoding || 'utf-8',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
  isExpanded.value = !isExpanded.value
}

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
    border-color: var(--node-border, v-bind(nodeColor));
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

  .badge-icon {
    width: 11px;
    height: 11px;
  }
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

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: rgba(255, 255, 255, 0.9);
  }

  .action-icon {
    width: 14px;
    height: 14px;
    transition: transform 0.2s ease;

    &.rotated {
      transform: rotate(180deg);
    }
  }
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
    border-color: v-bind(nodeColor);
    background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent);
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
  gap: 6px;

  .info-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
  }

  .info-value {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.7);
    font-family: 'JetBrains Mono', monospace;
  }
}

.preview-row {
  .preview-text {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.6);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.result-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(6, 182, 212, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.result-running {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  font-size: 11px;
  color: #06b6d4;
}

.result-completed {
  padding: 8px 10px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.meta-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(6, 182, 212, 0.15);
  color: #06b6d4;
  border: 1px solid rgba(6, 182, 212, 0.3);

  &.format {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
  }
}

.result-info {
  display: flex;
  gap: 6px;
}

.info-chip {
  font-size: 9px;
  color: rgba(255, 255, 255, 0.5);
}

.result-failed {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 10px;
  color: #ef4444;
}

.result-icon {
  width: 14px;
  height: 14px;

  &.spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.domain-node {
  &.is-running {
    animation: doc-pulse 1.8s ease-in-out infinite;
  }

  &.is-completed .result-zone {
    border-color: rgba(16, 185, 129, 0.4);
  }

  &.is-failed {
    border-color: rgba(239, 68, 68, 0.6) !important;
  }
}

@keyframes doc-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(6, 182, 212, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(6, 182, 212, 0); }
}

.expanded-config {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 8px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
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

  .el-input__inner {
    color: var(--node-text, #e5e5e5) !important;
    font-size: 12px !important;
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
  max-height: 500px;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: rgba(10, 10, 18, 0.95);
  border: 2px solid v-bind(nodeColor);
  border-radius: 50%;

  &:hover {
    background: v-bind(nodeColor);
    transform: scale(1.3);
  }
}

:global(.dark) {
  .domain-node {
    --node-bg: rgba(20, 20, 30, 0.95);
    --node-border: #06b6d4;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .domain-node {
    --node-bg: #fff;
    --node-border: #06b6d4;
    --node-text: #1e1e2e;
  }
}
</style>
