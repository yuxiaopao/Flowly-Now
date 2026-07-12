<template>
  <div
    class="planner-node"
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
        v-if="localConfig.plannerType || localConfig.approach"
        class="info-row"
      >
        <span class="info-label">方法</span>
        <span class="info-value">{{ localConfig.plannerType || localConfig.approach || '-' }}</span>
      </div>
      <div
        v-if="localConfig.description || localConfig.task"
        class="preview-row"
      >
        <span class="preview-text">{{ truncate(localConfig.description || localConfig.task, 35) }}</span>
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
          <span>规划中...</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="stepCount > 0"
            class="result-count"
          >{{ stepCount }} 步</span>
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
      v-if="isCompleted || isRunning"
      class="plan-zone"
    >
      <div class="plan-header">
        <ListTodo class="plan-icon" />
        <span class="plan-label">执行计划</span>
        <span
          v-if="stepCount > 0"
          class="step-count-badge"
        >{{ stepCount }} 步</span>
      </div>
      <div class="plan-steps">
        <div
          v-for="(step, i) in planSteps.slice(0, 4)"
          :key="i"
          class="plan-step"
          :class="{ done: isStepDone(i), active: isStepActive(i) }"
        >
          <div class="step-indicator">
            <CheckCircle2
              v-if="isStepDone(i)"
              class="step-check"
            />
            <Circle
              v-else-if="isStepActive(i)"
              class="step-active"
            />
            <CircleDashed
              v-else
              class="step-waiting"
            />
          </div>
          <div class="step-content">
            <span class="step-num">{{ i + 1 }}.</span>
            <span class="step-text">{{ truncate(getStepText(step), 28) }}</span>
          </div>
        </div>
        <div
          v-if="stepCount === 0"
          class="plan-empty"
        >
          <span>等待生成计划</span>
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
          <label class="config-label">规划方法</label>
          <el-select
            v-model="localConfig.plannerType"
            size="small"
            @change="handleChange"
          >
            <el-option
              value="llm"
              label="LLM 规划"
            />
            <el-option
              value="fixed"
              label="固定计划"
            />
            <el-option
              value="hierarchical"
              label="层级规划"
            />
            <el-option
              value="react"
              label="ReAct"
            />
          </el-select>
        </div>
        <div class="config-section">
          <label class="config-label">规划方法描述</label>
          <el-input
            v-model="localConfig.approach"
            size="small"
            placeholder="规划方法描述"
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">任务描述</label>
          <el-input
            v-model="localConfig.task"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="要规划的任务描述..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">目标</label>
          <el-input
            v-model="localConfig.goal"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="最终目标描述..."
            @change="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">最大步骤数</label>
          <el-input-number
            v-model="localConfig.maxSteps"
            :min="1"
            :max="50"
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
            placeholder="规划器描述..."
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
import { ListTodo, ChevronDown, Loader, CheckCircle2, Circle, CircleDashed } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'planner'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['select'])
const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)

const localName = ref(props.data.label || '任务规划')
const localConfig = ref({
  plannerType: props.data.config?.plannerType || 'llm',
  approach: props.data.config?.approach || '',
  task: props.data.config?.task || '',
  goal: props.data.config?.goal || '',
  maxSteps: props.data.config?.maxSteps || 10,
  description: props.data.config?.description || ''
})

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const planSteps = computed(() => {
  if (!nodeOutput.value) return []
  if (Array.isArray(nodeOutput.value.steps)) return nodeOutput.value.steps
  if (Array.isArray(nodeOutput.value.plan)) return nodeOutput.value.plan
  if (Array.isArray(nodeOutput.value.tasks)) return nodeOutput.value.tasks
  if (Array.isArray(nodeOutput.value)) return nodeOutput.value
  return []
})

const stepCount = computed(() => planSteps.value.length)

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function getStepText(step) {
  if (typeof step === 'string') return step
  return step.text || step.description || step.name || step.title || step.action || JSON.stringify(step)
}

function isStepDone(i) {
  if (!nodeOutput.value) return false
  const currentStep = nodeOutput.value.currentStep || nodeOutput.value.step
  if (isCompleted.value) return true
  if (typeof currentStep === 'number') return i < currentStep
  return false
}

function isStepActive(i) {
  if (!nodeOutput.value) return false
  const currentStep = nodeOutput.value.currentStep || nodeOutput.value.step
  if (typeof currentStep === 'number') return i === currentStep
  if (isRunning.value && i === 0 && stepCount.value === 0) return true
  return false
}

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '任务规划'
    localConfig.value = { plannerType: d.config?.plannerType || 'llm', approach: d.config?.approach || '', task: d.config?.task || '', goal: d.config?.goal || '', maxSteps: d.config?.maxSteps || 10, description: d.config?.description || '', ...d.config }
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
.planner-node {
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

  &.is-running { animation: plan-pulse 1.8s ease-in-out infinite; }
  &.is-completed .plan-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes plan-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(139, 92, 246, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(139, 92, 246, 0); }
}

.plan-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(139, 92, 246, 0.2);
  background: rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transition: all 0.3s ease;
}

.plan-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.15);
  background: rgba(139, 92, 246, 0.05);

  .plan-icon { width: 11px; height: 11px; color: rgba(139, 92, 246, 0.6); }
  .plan-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(139, 92, 246, 0.7); flex: 1; }
  .step-count-badge { font-size: 9px; font-weight: 600; background: rgba(139, 92, 246, 0.15); color: #a78bfa; padding: 1px 6px; border-radius: 10px; border: 1px solid rgba(139, 92, 246, 0.3); }
}

.plan-steps { padding: 6px 8px; display: flex; flex-direction: column; gap: 3px; }

.plan-step {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  background: rgba(139, 92, 246, 0.03);
  border: 1px solid transparent;
  transition: all 0.2s ease;

  &.done {
    opacity: 0.6;
    .step-text { text-decoration: line-through; color: rgba(255, 255, 255, 0.4); }
  }

  &.active {
    background: rgba(139, 92, 246, 0.1);
    border-color: rgba(139, 92, 246, 0.25);
    .step-num { color: #a78bfa; }
    .step-text { color: rgba(255, 255, 255, 0.9); }
  }
}

.step-indicator { display: flex; align-items: center; justify-content: center; width: 14px; flex-shrink: 0; }
.step-check { width: 12px; height: 12px; color: #4ade80; }
.step-active { width: 12px; height: 12px; color: #a78bfa; animation: step-pulse 1.2s ease-in-out infinite; }
.step-waiting { width: 12px; height: 12px; color: rgba(139, 92, 246, 0.3); }

@keyframes step-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.step-content { display: flex; align-items: baseline; gap: 3px; flex: 1; min-width: 0; }
.step-num { font-size: 9px; font-weight: 700; color: rgba(139, 92, 246, 0.5); font-family: 'JetBrains Mono', monospace; flex-shrink: 0; }
.step-text { font-size: 9px; color: rgba(255, 255, 255, 0.7); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.plan-empty { text-align: center; padding: 12px 0; font-size: 10px; color: rgba(139, 92, 246, 0.3); font-style: italic; }

.status-bar {
  margin-top: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.result-count { font-size: 9px; font-family: 'JetBrains Mono', monospace; color: rgba(139, 92, 246, 0.6); margin-left: auto; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

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
:global(.dark) { .planner-node { --node-bg: rgba(20, 20, 30, 0.95); --node-border: #8b5cf6; --node-text: #e5e5e5; } }
:global(.light) { .planner-node { --node-bg: #fff; --node-border: #8b5cf6; --node-text: #1e1e2e; } }
</style>
