<template>
  <div
    class="transform-node"
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
      <div class="transform-type-badge">
        {{ getTransformTypeLabel(localConfig.transformType) }}
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">转换类型</label>
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
              value="map"
              label="映射"
            />
            <el-option
              value="filter"
              label="过滤"
            />
            <el-option
              value="sort"
              label="排序"
            />
            <el-option
              value="merge"
              label="合并"
            />
            <el-option
              value="split"
              label="拆分"
            />
            <el-option
              value="extract"
              label="提取"
            />
            <el-option
              value="custom"
              label="自定义"
            />
          </el-select>
        </div>

        <div
          v-if="localConfig.transformType === 'custom'"
          class="config-section"
        >
          <label class="config-label">自定义转换脚本</label>
          <el-input
            v-model="localConfig.script"
            type="textarea"
            :rows="4"
            size="small"
            placeholder="// 自定义转换逻辑&#10;return input.map(item => ({...}))"
            @change="handleChange"
          />
        </div>

        <div
          v-if="['map', 'filter', 'extract'].includes(localConfig.transformType)"
          class="config-section"
        >
          <label class="config-label">字段映射</label>
          <el-input
            v-model="localConfig.mapping"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="key1: value1&#10;key2: value2"
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
      :class="{ 'zone-running': isRunning, 'zone-completed': isCompleted, 'zone-failed': isFailed }"
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
        class="result-summary"
      >
        <Check class="result-icon" />
        <span>{{ getTransformTypeLabel(localConfig.transformType) }}</span>
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
import { ChevronDown, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'transform'

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const isExpanded = ref(false)
const localName = ref(props.data.label || '数据转换')
const localConfig = ref({
  transformType: props.data.config?.transformType || 'map',
  script: props.data.config?.script || '',
  mapping: props.data.config?.mapping || ''
})

const getTransformTypeLabel = (type) => {
  const labels = {
    json_to_object: 'JSON → 对象',
    object_to_json: '对象 → JSON',
    map: '映射',
    filter: '过滤',
    sort: '排序',
    merge: '合并',
    split: '拆分',
    extract: '提取',
    custom: '自定义'
  }
  return labels[type] || type || '数据转换'
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '数据转换'
    localConfig.value = {
      transformType: d.config?.transformType || 'map',
      script: d.config?.script || '',
      mapping: d.config?.mapping || '',
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
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
.transform-node {
  background: var(--node-bg, #8b5cf6);
  border: 2px solid var(--node-border, #8b5cf6);
  border-radius: 12px;
  min-width: 160px;
  max-width: 260px;
  box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected {
    border-color: var(--node-border, #8b5cf6);
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.35), 0 0 0 2px rgba(139, 92, 246, 0.3);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    box-shadow: 0 6px 24px rgba(139, 92, 246, 0.35);
    transform: translateY(-1px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: white;

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
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    color: white;
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
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: white;
  outline: none;
  transition: all 0.15s ease;

  &::placeholder {
    color: rgba(255, 255, 255, 0.5);
  }

  &:focus {
    border-color: rgba(255, 255, 255, 0.4);
    background: rgba(255, 255, 255, 0.15);
  }
}

.compact-view {
  padding: 0 12px 10px;
}

.transform-type-badge {
  display: inline-flex;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.9);
}

.expanded-config {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
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
  color: rgba(255, 255, 255, 0.6);
}

:deep(.el-select),
:deep(.el-input),
:deep(.el-input-number) {
  width: 100%;

  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    box-shadow: none !important;
    border-radius: 6px;
  }

  .el-input__inner {
    color: white !important;
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
  max-height: 400px;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: #8b5cf6;
  border: 2px solid white;
  border-radius: 50%;

  &:hover {
    background: white;
    transform: scale(1.3);
  }
}

:global(.dark) {
  .transform-node {
    --node-bg: linear-gradient(145deg, #8b5cf6 0%, #a78bfa 100%);
    --node-border: #8b5cf6;
  }
}

:global(.light) {
  .transform-node {
    --node-bg: linear-gradient(145deg, #a78bfa 0%, #c4b5fd 100%);
    --node-border: #8b5cf6;
  }
}

// Result Zone
.result-zone {
  margin: 0 12px 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 6px;

  &.zone-running {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #3b82f6;
  }

  &.zone-completed {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #10b981;
  }

  &.zone-failed {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #ef4444;
  }

  .result-icon {
    width: 12px;
    height: 12px;
    flex-shrink: 0;
  }

  .result-summary, .result-error {
    display: flex;
    align-items: center;
    gap: 6px;
    word-break: break-all;
    font-family: 'JetBrains Mono', monospace;
  }
}

.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
