<template>
  <div
    class="variable-node"
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
        placeholder="变量节点..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <div
      v-if="!isExpanded"
      class="compact-view"
    >
      <div class="var-preview">
        <span
          class="op-badge"
          :class="localConfig.operation"
        >
          {{ opLabel }}
        </span>
        <span class="var-name">{{ localConfig.variableName || localConfig.assignments?.map(item => item.name).join('、') || '未命名' }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">操作</label>
          <el-select
            v-model="localConfig.operation"
            size="small"
            @change="handleChange"
          >
            <el-option
              label="设置变量"
              value="set"
            />
            <el-option
              label="获取变量"
              value="get"
            />
            <el-option
              label="删除变量"
              value="delete"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">变量名</label>
          <el-input
            v-model="localConfig.variableName"
            size="small"
            placeholder="myVariable"
            @input="handleChange"
          />
        </div>
        <div
          v-if="localConfig.operation === 'set'"
          class="config-section"
        >
          <label class="config-label">变量值 (支持 {变量名} 引用)</label>
          <el-input
            v-model="localConfig.variableValue"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="{otherVar}"
            @input="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">作用域</label>
          <el-select
            v-model="localConfig.scope"
            size="small"
            @change="handleChange"
          >
            <el-option
              label="局部变量"
              value="local"
            />
            <el-option
              label="全局变量"
              value="global"
            />
          </el-select>
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
        <span>{{ localConfig.variableName }} = {{ nodeOutput?.value || localConfig.variableValue || '-' }}</span>
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
import { ref, computed, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'variable'

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const isExpanded = ref(false)
const localName = ref(props.data.label || '变量')
const localConfig = ref({
  ...props.data.config,
  operation: props.data.config?.operation || 'set',
  variableName: props.data.config?.variableName || props.data.config?.name || props.data.config?.variable_name || '',
  variableValue: props.data.config?.variableValue ?? props.data.config?.value ?? '',
  scope: props.data.config?.scope || 'local',
})

const opLabel = computed(() => ({
  set: '设置', get: '读取', delete: '删除'
}[localConfig.value.operation] || '设置'))

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '变量'
    localConfig.value = {
      ...d.config,
      operation: d.config?.operation || 'set',
      variableName: d.config?.variableName || d.config?.name || d.config?.variable_name || '',
      variableValue: d.config?.variableValue ?? d.config?.value ?? '',
      scope: d.config?.scope || 'local',
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
.variable-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid var(--node-border, #22c55e);
  border-radius: 12px;
  min-width: 180px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.selected {
    box-shadow: 0 8px 32px rgba(34, 197, 94, 0.2), 0 0 0 2px rgba(34, 197, 94, 0.3);
    transform: translateY(-2px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(34, 197, 94, 0.08);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(34, 197, 94, 0.2);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #4ade80;
  .badge-icon { width: 11px; height: 11px; }
}

.action-btn {
  width: 24px; height: 24px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.15s;
  &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); }
  .action-icon { width: 14px; height: 14px; transition: transform 0.2s; &.rotated { transform: rotate(180deg); } }
}

.node-name-section { padding: 8px 12px 6px; }

.node-name-input {
  width: 100%;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--node-text, #e2e8f0);
  outline: none;
  &::placeholder { color: rgba(255, 255, 255, 0.3); }
  &:focus { border-color: rgba(34, 197, 94, 0.5); }
}

.compact-view { padding: 0 12px 10px; }

.var-preview {
  display: flex;
  align-items: center;
  gap: 8px;
}

.op-badge {
  font-size: 10px;
  font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  padding: 2px 8px;
  border-radius: 4px;

  &.set { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
  &.get { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
  &.delete { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
}

.var-name {
  font-size: 12px;
  font-weight: 600;
  color: #4ade80;
  font-family: 'JetBrains Mono', monospace;
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

:deep(.el-select), :deep(.el-input), :deep(.el-textarea) {
  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: none !important;
  }
  .el-input__inner, .el-textarea__inner {
    color: var(--node-text, #e2e8f0) !important;
    font-size: 12px !important;
  }
}

.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }

:deep(.vue-flow__handle) {
  width: 10px; height: 10px;
  background: #1e1e2e;
  border: 2px solid #22c55e;
  border-radius: 50%;
  &:hover { background: #22c55e; transform: scale(1.3); }
}

:global(.dark) { .variable-node { --node-bg: #1e1e2e; --node-border: #22c55e; --node-text: #e2e8f0; } }
:global(.light) { .variable-node { --node-bg: #fff; --node-border: #22c55e; --node-text: #1e293b; } }

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
