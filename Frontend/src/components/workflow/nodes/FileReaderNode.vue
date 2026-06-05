<template>
  <div
    class="domain-node file-reader-node"
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
        <FileInput
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">文件读取</span>
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
        v-if="localConfig.fileType || localConfig.format"
        class="info-row"
      >
        <span class="info-label">格式</span>
        <span class="info-value">{{ localConfig.fileType || localConfig.format || '-' }}</span>
      </div>
      <div
        v-if="localConfig.filePath"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.filePath, 35) }}</span>
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
          <span>读取中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="lineCount > 0"
            class="line-count"
          >{{ lineCount }} 行</span>
        </div>
        <div
          v-else-if="isFailed"
          class="status-error"
        >
          <span class="status-dot" />
          <span>读取失败</span>
        </div>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning"
      class="file-preview-zone"
    >
      <div class="preview-header">
        <FileCode class="preview-icon" />
        <span class="preview-label">文件内容</span>
        <span
          v-if="localConfig.fileType"
          class="preview-format"
        >{{ localConfig.fileType.toUpperCase() }}</span>
      </div>
      <div class="preview-content">
        <div
          v-if="fileContent"
          class="file-fragment"
        >
          <pre class="fragment-text">{{ truncate(fileContent, 300) }}</pre>
        </div>
        <div
          v-else
          class="preview-empty"
        >
          <span v-if="isRunning">正在读取文件...</span>
          <span v-else>无内容</span>
        </div>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">文件路径</label>
          <el-input
            v-model="localConfig.filePath"
            size="small"
            placeholder="/path/to/file.txt"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">文件格式</label>
          <el-select
            v-model="localConfig.fileType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="txt"
              label="文本 (TXT)"
            />
            <el-option
              value="json"
              label="JSON"
            />
            <el-option
              value="csv"
              label="CSV"
            />
            <el-option
              value="xml"
              label="XML"
            />
            <el-option
              value="yaml"
              label="YAML"
            />
            <el-option
              value="md"
              label="Markdown"
            />
            <el-option
              value="log"
              label="日志文件"
            />
          </el-select>
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
              value="ascii"
              label="ASCII"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">起始行</label>
          <el-input-number
            v-model="localConfig.startLine"
            :min="1"
            size="small"
            controls-position="right"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">最大行数</label>
          <el-input-number
            v-model="localConfig.maxLines"
            :min="0"
            size="small"
            controls-position="right"
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
            placeholder="读取操作描述..."
            @change="handleChange"
          />
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
import { FileInput, ChevronDown, FileCode, Loader } from 'lucide-vue-next'
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
const nodeColor = '#6366f1'

const localName = ref(props.data.label || '文件读取')
const localConfig = ref({
  filePath: props.data.config?.filePath || '',
  fileType: props.data.config?.fileType || 'txt',
  encoding: props.data.config?.encoding || 'utf-8',
  startLine: props.data.config?.startLine || 1,
  maxLines: props.data.config?.maxLines || 0,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const fileContent = computed(() => {
  if (!nodeOutput.value) return null
  const content = typeof nodeOutput.value === 'string' ? nodeOutput.value
    : nodeOutput.value.content || nodeOutput.value.text || nodeOutput.value.data || nodeOutput.value.output || ''
  return content || null
})

const lineCount = computed(() => {
  if (!fileContent.value) return 0
  return fileContent.value.split('\n').length
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '\n...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '文件读取'
    localConfig.value = { filePath: d.config?.filePath || '', fileType: d.config?.fileType || 'txt', encoding: d.config?.encoding || 'utf-8', startLine: d.config?.startLine || 1, maxLines: d.config?.maxLines || 0, description: d.config?.description || '', ...d.config }
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
.file-reader-node {
  &.is-running { animation: file-pulse 1.8s ease-in-out infinite; }
  &.is-completed .file-preview-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes file-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(99, 102, 241, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(99, 102, 241, 0); }
}

.file-preview-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(99, 102, 241, 0.2);
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.15);
  background: rgba(99, 102, 241, 0.05);

  .preview-icon { width: 11px; height: 11px; color: rgba(99, 102, 241, 0.6); }
  .preview-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(99, 102, 241, 0.7); flex: 1; }
}

.preview-format {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid rgba(99, 102, 241, 0.3);
}

.preview-content { padding: 8px 10px; max-height: 80px; overflow: auto; }

.file-fragment {
  .fragment-text {
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
    color: #a5b4fc;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
  }
}

.preview-empty { font-size: 10px; color: rgba(99, 102, 241, 0.4); font-style: italic; }

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(99, 102, 241, 0.1); color: #6366f1; border: 1px solid rgba(99, 102, 241, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.line-count { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(99, 102, 241, 0.6); margin-left: auto; }
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
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 10px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e5e5e5); outline: none; transition: all 0.15s ease; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: v-bind(nodeColor); background: color-mix(in srgb, v-bind(nodeColor) 10%, transparent); } }
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
:global(.dark) { .domain-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #6366f1; --node-text: #e5e5e5; } }
:global(.light) { .domain-node { --node-bg: #fff; --node-border: #6366f1; --node-text: #1e1e2e; } }
</style>
