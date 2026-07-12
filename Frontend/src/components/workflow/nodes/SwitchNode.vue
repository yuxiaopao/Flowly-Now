<template>
  <div
    class="switch-node"
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
        v-if="localConfig.expression"
        class="expression-display"
      >
        <Code class="expr-icon" />
        <span class="expr-value">{{ truncateExpression(localConfig.expression) }}</span>
      </div>
      <div class="branches-count">
        <span class="count-label">分支数</span>
        <span class="count-value">{{ branches.length }}</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">分支表达式</label>
          <el-input
            v-model="localConfig.expression"
            size="small"
            placeholder="例如: status === 'active'"
            @change="handleChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">分支列表</label>
          <div class="branches-list">
            <div
              v-for="(branch, index) in branches"
              :key="branch.id"
              class="branch-item"
              :style="{ borderColor: getBranchColor(index), backgroundColor: getBranchColor(index) + '15' }"
            >
              <span
                class="branch-label"
                :style="{ color: getBranchColor(index) }"
              >
                {{ branch.label || `分支 ${index + 1}` }}
              </span>
            </div>
          </div>
        </div>

        <div class="config-section">
          <label class="config-label">添加分支</label>
          <div class="add-branch-row">
            <el-input
              v-model="newBranchLabel"
              size="small"
              placeholder="分支名称"
              @keydown.enter="addBranch"
            />
            <button
              class="add-btn"
              @click="addBranch"
            >
              <Plus class="add-icon" />
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <div class="branch-handles">
      <Handle
        v-for="(branch, index) in branches"
        :id="branch.id"
        :key="branch.id"
        type="source"
        :position="Position.Right"
        :style="{ top: `${50 + index * 15}%` }"
      />
    </div>

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
        <span>{{ nodeOutput?.selectedBranch || branches[0]?.label || '完成' }}</span>
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
import { GitBranch, ChevronDown, Code, Plus, Loader, Check, X } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'switch'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const isExpanded = ref(false)
const localName = ref(props.data.label || '分支')
const localConfig = ref({
  expression: props.data.config?.expression || '',
  branches: props.data.config?.branches || [
    { id: 'case1', label: 'Case 1' },
    { id: 'case2', label: 'Case 2' },
    { id: 'default', label: 'Default' }
  ]
})
const newBranchLabel = ref('')

const branches = computed(() => localConfig.value.branches || [])

const branchColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4']

const getBranchColor = (index) => branchColors[index % branchColors.length]

const truncateExpression = (expr) => {
  if (!expr) return ''
  return expr.length > 30 ? expr.slice(0, 30) + '...' : expr
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '分支'
    localConfig.value = {
      expression: d.config?.expression || '',
      branches: d.config?.branches || [
        { id: 'case1', label: 'Case 1' },
        { id: 'case2', label: 'Case 2' },
        { id: 'default', label: 'Default' }
      ],
      ...d.config
    }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
  isExpanded.value = !isExpanded.value
}

function addBranch() {
  if (newBranchLabel.value.trim()) {
    const newId = `case${localConfig.value.branches.length + 1}`
    localConfig.value.branches.push({ id: newId, label: newBranchLabel.value.trim() })
    newBranchLabel.value = ''
    handleChange()
  }
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
.switch-node {
  background: var(--node-bg, #0f172a);
  border: 2px solid var(--node-border, #3b82f6);
  border-radius: 12px;
  min-width: 180px;
  max-width: 280px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;
  position: relative;

  &.selected {
    border-color: var(--node-border, #3b82f6);
    box-shadow: 0 8px 32px rgba(59, 130, 246, 0.25), 0 0 0 2px rgba(59, 130, 246, 0.3);
    transform: translateY(-2px);
  }

  &:hover:not(.selected) {
    border-color: #60a5fa;
    box-shadow: 0 6px 24px rgba(59, 130, 246, 0.15);
    transform: translateY(-1px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(59, 130, 246, 0.08);
}

.node-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: rgba(59, 130, 246, 0.2);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 20px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #3b82f6;

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
    border-color: rgba(59, 130, 246, 0.5);
    background: rgba(59, 130, 246, 0.05);
  }
}

.compact-view {
  display: flex;
  gap: 8px;
  padding: 0 12px 10px;
  flex-direction: column;
}

.expression-display {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 6px;

  .expr-icon {
    width: 12px;
    height: 12px;
    color: #60a5fa;
    flex-shrink: 0;
  }

  .expr-value {
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    color: #93c5fd;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.branches-count {
  display: flex;
  align-items: center;
  gap: 4px;

  .count-label {
    font-size: 10px;
    color: rgba(255, 255, 255, 0.4);
  }

  .count-value {
    font-size: 12px;
    font-weight: 600;
    color: #3b82f6;
    font-family: 'JetBrains Mono', monospace;
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

.branches-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.branch-item {
  padding: 5px 8px;
  border-radius: 6px;
  border: 1px solid;

  .branch-label {
    font-size: 11px;
    font-weight: 600;
  }
}

.add-branch-row {
  display: flex;
  gap: 6px;

  .el-input {
    flex: 1;
  }

  .add-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(59, 130, 246, 0.2);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 6px;
    cursor: pointer;
    color: #3b82f6;
    transition: all 0.15s ease;

    &:hover {
      background: rgba(59, 130, 246, 0.3);
    }

    .add-icon {
      width: 14px;
      height: 14px;
    }
  }
}

:deep(.el-select),
:deep(.el-input) {
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

.branch-handles {
  position: absolute;
  right: -8px;
  top: 0;
  height: 100%;
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
  background: var(--node-bg, #0f172a);
  border: 2px solid var(--node-border, #3b82f6);
  border-radius: 50%;

  &:hover {
    background: #3b82f6;
    transform: scale(1.3);
  }
}

:global(.dark) {
  .switch-node {
    --node-bg: #0f172a;
    --node-border: #3b82f6;
    --node-text: #e5e5e5;
  }
}

:global(.light) {
  .switch-node {
    --node-bg: #fff;
    --node-border: #3b82f6;
    --node-text: #0f172a;
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
