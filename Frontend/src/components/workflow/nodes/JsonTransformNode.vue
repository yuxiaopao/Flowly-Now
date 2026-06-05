<template>
  <div
    class="domain-node"
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
        <Braces
          class="badge-icon"
          :style="{ color: nodeColor }"
        />
        <span :style="{ color: nodeColor }">JSON转换</span>
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
        v-if="localConfig.transformType || localConfig.operation"
        class="info-row"
      >
        <span class="info-label">操作</span>
        <span class="info-value">{{ localConfig.transformType || localConfig.operation || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description || localConfig.operation"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description || localConfig.operation, 35) }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">转换操作</label>
          <el-select
            v-model="localConfig.transformType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="json_to_object"
              label="JSON → 对象"
            />
            <el-option
              value="object_to_json"
              label="对象 → JSON"
            />
            <el-option
              value="json_to_xml"
              label="JSON → XML"
            />
            <el-option
              value="xml_to_json"
              label="XML → JSON"
            />
            <el-option
              value="json_schema"
              label="JSON Schema 验证"
            />
            <el-option
              value="json_path"
              label="JSON Path 查询"
            />
            <el-option
              value="json_merge"
              label="JSON 合并"
            />
            <el-option
              value="json_query"
              label="JSON 查询"
            />
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">源数据</label>
          <el-input
            v-model="localConfig.source"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="输入 JSON 数据"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">JSON Path / 查询</label>
          <el-input
            v-model="localConfig.query"
            size="small"
            placeholder="$.data.items[*]"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">格式化</label>
          <el-select
            v-model="localConfig.formatting"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="pretty"
              label="格式化 (缩进)"
            />
            <el-option
              value="minify"
              label="压缩 (Minify)"
            />
            <el-option
              value="none"
              label="无"
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
            placeholder="转换描述..."
            @change="handleChange"
          />
        </div>
      </div>
    </Transition>

    <Handle
      type="source"
      :position="Position.Right"
    />

    <!-- Result Zone -->
    <div
      v-if="isRunning || isCompleted || isFailed"
      class="result-zone"
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
        class="result-done"
      >
        <Check class="result-icon" />
        <span>{{ resultSummary }}</span>
      </div>
      <div
        v-else-if="isFailed"
        class="result-error"
      >
        <X class="result-icon" />
        <span>{{ nodeOutput?.error || '执行失败' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Braces, ChevronDown, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'

const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const resultSummary = computed(() => {
  if (!nodeOutput.value) return '完成'
  const count = nodeOutput.value.count || nodeOutput.value.result_count || 0
  return `${count} 条已转换`
})

const isExpanded = ref(false)
const nodeColor = '#10b981'

const localName = ref(props.data.label || 'JSON转换')
const localConfig = ref({
  transformType: props.data.config?.transformType || 'json_to_object',
  source: props.data.config?.source || '',
  query: props.data.config?.query || '',
  formatting: props.data.config?.formatting || 'pretty',
  description: props.data.config?.description || ''
})

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || 'JSON转换'
    localConfig.value = {
      transformType: d.config?.transformType || 'json_to_object',
      source: d.config?.source || '',
      query: d.config?.query || '',
      formatting: d.config?.formatting || 'pretty',
      description: d.config?.description || '',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
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

.result-zone {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: 'JetBrains Mono', monospace;
  .result-icon { width: 12px; height: 12px; flex-shrink: 0; }
  &.result-running { background: rgba(59,130,246,.1); border: 1px solid rgba(59,130,246,.3); color: #3b82f6; }
  &.result-done { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); color: #10b981; }
  &.result-error { background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); color: #ef4444; }
}
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
