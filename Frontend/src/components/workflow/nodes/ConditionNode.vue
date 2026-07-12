<template>
  <div
    class="condition-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    :style="{ '--node-accent': nodeColor }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />

    <!-- Header -->
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

    <!-- Name -->
    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        class="node-name-input"
        name="node-label"
        placeholder="条件节点..."
        @blur="handleChange"
        @keydown.enter="handleChange"
        @click.stop="handleSelect"
      >
    </div>

    <!-- Compact view -->
    <div
      v-if="!isExpanded"
      class="compact-view"
    >
      <div class="conditions-preview">
        <span
          v-for="(c, i) in (localConfig.conditions || []).slice(0, 2)"
          :key="i"
          class="cond-tag"
        >
          {{ c.field || '?' }} {{ c.operator || 'equals' }} {{ c.value || '?' }}
        </span>
        <span
          v-if="(localConfig.conditions || []).length > 2"
          class="cond-more"
        >
          +{{ localConfig.conditions.length - 2 }}
        </span>
      </div>
      <div class="output-count">
        <span class="out-badge">{{ (localConfig.conditions || []).length + 1 }} 个分支</span>
      </div>
    </div>

    <!-- Expanded inline config -->
    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <!-- Conditions -->
        <div class="config-section">
          <label class="config-label">条件分支</label>
          <div class="cond-list">
            <div
              v-for="(cond, i) in localConfig.conditions"
              :key="i"
              class="cond-item"
            >
              <el-select
                v-model="cond.field"
                size="small"
                @change="handleChange"
              >
                <el-option
                  label="last_output"
                  value="last_output"
                />
                <el-option
                  label="input"
                  value="input"
                />
                <el-option
                  label="var"
                  value="var"
                />
              </el-select>
              <el-select
                v-model="cond.operator"
                size="small"
                @change="handleChange"
              >
                <el-option
                  label="等于"
                  value="equals"
                />
                <el-option
                  label="不等于"
                  value="not_equals"
                />
                <el-option
                  label="包含"
                  value="contains"
                />
                <el-option
                  label="大于"
                  value="greater_than"
                />
                <el-option
                  label="小于"
                  value="less_than"
                />
                <el-option
                  label="为空"
                  value="is_empty"
                />
                <el-option
                  label="不为空"
                  value="is_not_empty"
                />
              </el-select>
              <el-input
                v-model="cond.value"
                size="small"
                placeholder="值"
                @input="handleChange"
              />
              <button
                class="cond-remove"
                @click="removeCond(i)"
              >
                <X class="remove-icon" />
              </button>
            </div>
            <button
              class="add-cond-btn"
              @click="addCond"
            >
              <Plus class="add-icon" />
              添加条件
            </button>
          </div>
        </div>

        <!-- Default branch -->
        <div class="config-section">
          <label class="config-label">默认分支</label>
          <el-input
            v-model="localConfig.defaultBranch"
            size="small"
            placeholder="默认"
            @input="handleChange"
          />
        </div>
      </div>
    </Transition>

    <!-- Multiple outputs -->
    <div
      v-if="isExpanded"
      class="output-handles"
    >
      <div
        v-for="(cond, i) in (localConfig.conditions || [])"
        :key="'handle-' + i"
        class="output-label"
      >
        <span>{{ cond.branch || '条件 ' + (i + 1) }}</span>
      </div>
      <div class="output-label default">
        <span>{{ localConfig.defaultBranch || '默认' }}</span>
      </div>
    </div>

    <Handle
      id="true"
      type="source"
      :position="Position.Bottom"
      :style="{ left: '30%' }"
    />
    <Handle
      id="false"
      type="source"
      :position="Position.Bottom"
      :style="{ left: '70%' }"
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
        <span>{{ nodeOutput?.result || '条件满足' }}</span>
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
import { GitBranch, ChevronDown, Plus, X, Loader, Check } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'condition'
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
const localName = ref(props.data.label || '条件判断')
const localConfig = ref({
  conditions: props.data.config?.conditions || [],
  defaultBranch: props.data.config?.defaultBranch || '默认',
})

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '条件判断'
    localConfig.value = {
      conditions: d.config?.conditions || [],
      defaultBranch: d.config?.defaultBranch || '默认',
    }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
  isExpanded.value = !isExpanded.value
}

function handleChange() {
  if (props.id) {
    updateNodeData(props.id, {
      label: localName.value,
      config: { ...localConfig.value }
    })
  }
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}

function addCond() {
  if (!localConfig.value.conditions) localConfig.value.conditions = []
  localConfig.value.conditions.push({ field: 'last_output', operator: 'equals', value: '', branch: '' })
  handleChange()
}

function removeCond(index) {
  localConfig.value.conditions.splice(index, 1)
  handleChange()
}
</script>

<style lang="scss" scoped>
.condition-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid var(--node-border, #3b82f6);
  border-radius: 12px;
  min-width: 200px;
  max-width: 300px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.selected {
    box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2), 0 0 0 2px rgba(59, 130, 246, 0.3);
    transform: translateY(-2px);
  }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: rgba(59, 130, 246, 0.08);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
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
  color: #60a5fa;

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
  &:focus { border-color: rgba(59, 130, 246, 0.5); background: rgba(59, 130, 246, 0.05); }
}

.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 6px; }

.conditions-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.cond-tag {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  color: #60a5fa;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
}

.cond-more {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  padding: 2px 4px;
}

.out-badge {
  font-size: 10px;
  font-weight: 600;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  padding: 2px 8px;
  border-radius: 10px;
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

.cond-list { display: flex; flex-direction: column; gap: 6px; }

.cond-item {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 4px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 6px;

  .el-select, .el-input { flex: 1; min-width: 0; }
  .el-input__wrapper {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: none !important;
  }
  .el-input__inner { color: var(--node-text, #e2e8f0) !important; font-size: 10px !important; }
}

.cond-remove {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 4px;
  cursor: pointer;
  color: #ef4444;
  flex-shrink: 0;
  &:hover { background: rgba(239, 68, 68, 0.2); }
  .remove-icon { width: 10px; height: 10px; }
}

.add-cond-btn {
  display: flex; align-items: center; gap: 6px;
  width: 100%; padding: 6px 8px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.4);
  font-size: 11px;
  transition: all 0.15s;
  &:hover { background: rgba(59, 130, 246, 0.06); border-color: rgba(59, 130, 246, 0.3); color: #60a5fa; }
  .add-icon { width: 12px; height: 12px; }
}

.output-handles {
  padding: 6px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.output-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  color: #10b981;
  font-weight: 600;

  span {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.2);
    padding: 2px 8px;
    border-radius: 4px;
  }

  &.default span {
    color: #94a3b8;
    background: rgba(148, 163, 184, 0.1);
    border-color: rgba(148, 163, 184, 0.2);
  }
}

.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }

:deep(.vue-flow__handle) {
  width: 10px; height: 10px;
  background: #1e1e2e;
  border: 2px solid #3b82f6;
  border-radius: 50%;
  &:hover { background: #3b82f6; transform: scale(1.3); }
}

:global(.dark) { .condition-node { --node-bg: #1e1e2e; --node-border: #3b82f6; --node-text: #e2e8f0; } }
:global(.light) { .condition-node { --node-bg: #fff; --node-border: #3b82f6; --node-text: #1e293b; } }

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
