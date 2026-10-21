<template>
  <div
    :style="{ '--node-accent': nodeColor }"
    class="domain-node"
    :class="{ selected, expanded: isExpanded }"
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
        v-model="localName"
        name="node-label"
        class="node-name-input"
        placeholder="节点名称..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div
        v-if="displayFormat"
        class="info-row"
      >
        <span class="info-label">格式</span>
        <span class="info-value">{{ displayFormat }}</span>
      </div>
      <div
        v-if="displayPath"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(displayPath, 35) }}</span>
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
            v-model="localConfig.path"
            size="small"
            placeholder="/path/to/output.txt"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">文件格式</label>
          <el-select
            v-model="localConfig.format"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="text"
              label="纯文本 (TEXT)"
            />
            <el-option
              value="txt"
              label="文本 (TXT)"
            />
            <el-option
              value="docx"
              label="Word (DOCX)"
            />
            <el-option
              value="md"
              label="Markdown (MD)"
            />
            <el-option
              value="markdown"
              label="Markdown"
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
              value="html"
              label="HTML"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">写入内容</label>
          <el-input
            v-model="localConfig.content"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="要写入的内容或模板..."
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
              value="ascii"
              label="ASCII"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">写入模式</label>
          <el-select
            v-model="localConfig.writeMode"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="overwrite"
              label="覆盖"
            />
            <el-option
              value="append"
              label="追加"
            />
            <el-option
              value="create"
              label="创建 (不存在则创建)"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">描述</label>
          <el-input
            v-model="localConfig.description"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="写入操作描述..."
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
import { ChevronDown } from 'lucide-vue-next'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'

const FORMAT_LABELS = {
  text: '纯文本',
  txt: 'TXT',
  docx: 'Word (DOCX)',
  md: 'Markdown',
  markdown: 'Markdown',
  json: 'JSON',
  csv: 'CSV',
  xml: 'XML',
  yaml: 'YAML',
  html: 'HTML',
  parquet: 'Parquet',
  excel: 'Excel',
}

function normalizeFileWriterConfig(config = {}) {
  const format = config.format || config.fileType || 'text'
  const path = config.path || config.filePath || ''
  return {
    path,
    format,
    filePath: path,
    fileType: format,
    content: config.content || '',
    encoding: config.encoding || 'utf-8',
    writeMode: config.writeMode || 'overwrite',
    overwrite: config.overwrite ?? (config.writeMode !== 'append'),
    description: config.description || '',
  }
}

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'file_writer'
const { nodeColor } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const isExpanded = ref(false)

const localName = ref(props.data.label || '文件写入')
const localConfig = ref(normalizeFileWriterConfig(props.data.config))

const displayFormat = computed(() => {
  const raw = localConfig.value.format || localConfig.value.fileType
  return raw ? (FORMAT_LABELS[raw] || raw) : ''
})

const displayPath = computed(() => {
  return localConfig.value.path || localConfig.value.filePath || localConfig.value.description || ''
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '文件写入'
    localConfig.value = normalizeFileWriterConfig(d.config)
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
}

function handleChange() {
  if (props.id) {
    const normalized = normalizeFileWriterConfig(localConfig.value)
    localConfig.value = normalized
    updateNodeData(props.id, { label: localName.value, config: normalized })
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
    --node-border: #10b981;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .domain-node {
    --node-bg: #fff;
    --node-border: #10b981;
    --node-text: #1e1e2e;
  }
}
</style>
