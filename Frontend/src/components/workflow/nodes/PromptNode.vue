<template>
  <div
    class="prompt-node"
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

    <div
      v-if="!isExpanded"
      class="compact-view"
    >
      <div class="template-preview">
        {{ templatePreview }}
      </div>
      <div class="var-count">
        <span class="var-badge">{{ localConfig.variables?.length || 0 }} 个变量</span>
      </div>
    </div>

    <div
      v-if="isCompleted || isRunning || isFailed"
      class="render-preview"
    >
      <div class="render-header">
        <Eye class="render-icon" />
        <span class="render-label">渲染预览</span>
        <span
          v-if="isRunning"
          class="render-badge running"
        >
          <Loader class="badge-icon spinning" /> 渲染中
        </span>
        <span
          v-else-if="isFailed"
          class="render-badge failed"
        >渲染失败</span>
        <span
          v-else
          class="render-badge"
        >变量已填充</span>
      </div>
      <div
        v-if="isFailed"
        class="render-error"
      >
        <AlertCircle class="error-icon" />
        <span>{{ nodeOutput?.error || '渲染失败' }}</span>
      </div>
      <div
        v-else-if="renderedOutput"
        class="render-content"
      >
        <div class="render-text">
          {{ renderedOutput }}
        </div>
      </div>
      <div
        v-else-if="isRunning"
        class="render-loading"
      >
        <span>正在替换变量...</span>
      </div>
      <div
        v-else
        class="render-empty"
      >
        <span>等待渲染</span>
      </div>
    </div>

    <Transition name="expand">
      <div
        v-if="isExpanded"
        class="expanded-config"
        @click.stop
      >
        <div class="config-section">
          <label class="config-label">模板内容</label>
          <el-input
            v-model="localConfig.template"
            type="textarea"
            :rows="4"
            size="small"
            placeholder="使用 {变量名} 定义变量..."
            @input="handleChange"
          />
        </div>
        <div class="config-section">
          <label class="config-label">变量定义</label>
          <div class="var-list">
            <div
              v-for="(v, i) in localConfig.variables"
              :key="i"
              class="var-item"
            >
              <el-input
                v-model="v.name"
                size="small"
                placeholder="变量名"
                @input="handleChange"
              />
              <el-input
                v-model="v.value"
                size="small"
                placeholder="默认值"
                @input="handleChange"
              />
              <button
                class="var-remove"
                @click="removeVar(i)"
              >
                <X class="remove-icon" />
              </button>
            </div>
            <button
              class="add-var-btn"
              @click="addVar"
            >
              <Plus class="add-icon" />
              添加变量
            </button>
          </div>
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
import { ref, computed, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { ChevronDown, Plus, X, Eye, Loader, AlertCircle } from 'lucide-vue-next'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'prompt'

const emit = defineEmits(['select'])

const { updateNodeData } = useVueFlow()
const executionStore = useExecutionStore()

const isExpanded = ref(false)
const localName = ref(props.data.label || '提示词')
const localConfig = ref({
  template: props.data.config?.template || '',
  variables: props.data.config?.variables || [],
})

const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const renderedOutput = computed(() => {
  if (!nodeOutput.value) return null
  const text = typeof nodeOutput.value === 'string' ? nodeOutput.value : nodeOutput.value.text || nodeOutput.value.output || nodeOutput.value.result || ''
  if (!text) return null
  return text.length > 150 ? text.slice(0, 150) + '...' : text
})

const templatePreview = computed(() => {
  const t = localConfig.value.template
  if (!t) return '未设置模板'
  return t.length > 60 ? t.slice(0, 60) + '...' : t
})

watch(() => props.data, (d) => {
  if (d) {
    localName.value = d.label || '提示词'
    localConfig.value = { template: d.config?.template || '', variables: d.config?.variables || [] }
  }
}, { deep: true })

function toggleExpand() {
  const expanded = !isExpanded.value
  emit('select')
  isExpanded.value = expanded
}

function handleChange() {
  if (props.id) updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}

function addVar() {
  if (!localConfig.value.variables) localConfig.value.variables = []
  localConfig.value.variables.push({ name: '', value: '' })
  handleChange()
}

function removeVar(index) {
  localConfig.value.variables.splice(index, 1)
  handleChange()
}
</script>

<style lang="scss" scoped>
.prompt-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid var(--node-border, #f59e0b);
  border-radius: 12px;
  min-width: 200px;
  max-width: 300px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

  &.selected { box-shadow: 0 8px 32px rgba(245, 158, 11, 0.2), 0 0 0 2px rgba(245, 158, 11, 0.3); transform: translateY(-2px); }
  &:hover:not(.selected) { box-shadow: 0 6px 24px rgba(245, 158, 11, 0.12); transform: translateY(-1px); }
  &.is-completed .render-preview { border-color: rgba(16, 185, 129, 0.4); }
}

.render-preview {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(245, 158, 11, 0.2);
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.render-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-bottom: 1px solid rgba(245, 158, 11, 0.15);
  background: rgba(245, 158, 11, 0.05);

  .render-icon { width: 11px; height: 11px; color: rgba(245, 158, 11, 0.6); }
  .render-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(245, 158, 11, 0.7); flex: 1; }
}

.render-badge {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;

  &.running {
    display: flex;
    align-items: center;
    gap: 3px;
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);

    .badge-icon {
      width: 9px;
      height: 9px;

      &.spinning {
        animation: spin 1s linear infinite;
      }
    }
  }

  &.failed {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  &:not(.running):not(.failed) {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }
}

.render-error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-size: 10px;
  color: #ef4444;

  .error-icon { width: 12px; height: 12px; }
}

.render-loading,
.render-empty {
  padding: 8px 10px;
  font-size: 10px;
  color: rgba(245, 158, 11, 0.5);
  font-style: italic;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.render-content { padding: 8px 10px; max-height: 80px; overflow: hidden; }

.render-text {
  font-size: 10px;
  font-family: 'JetBrains Mono', monospace;
  color: #fbbf24;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
}

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: rgba(245, 158, 11, 0.08); border-bottom: 1px solid rgba(255, 255, 255, 0.06); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; background: rgba(245, 158, 11, 0.2); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #fbbf24; .badge-icon { width: 11px; height: 11px; } }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 8px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e2e8f0); outline: none; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: rgba(245, 158, 11, 0.5); background: rgba(245, 158, 11, 0.05); } }
.compact-view { padding: 0 12px 10px; display: flex; flex-direction: column; gap: 6px; }
.template-preview { font-size: 11px; color: rgba(255, 255, 255, 0.5); font-family: 'JetBrains Mono', monospace; line-height: 1.4; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 6px 8px; max-height: 48px; overflow: hidden; }
.var-count { .var-badge { font-size: 10px; font-weight: 600; color: #fbbf24; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); padding: 2px 8px; border-radius: 10px; } }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
.var-list { display: flex; flex-direction: column; gap: 6px; }
.var-item { display: flex; gap: 4px; align-items: center; .el-input { flex: 1; } .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; box-shadow: none !important; } .el-input__inner { color: var(--node-text, #e2e8f0) !important; font-size: 11px !important; } }
.var-remove { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 4px; cursor: pointer; color: #ef4444; flex-shrink: 0; transition: all 0.15s; &:hover { background: rgba(239, 68, 68, 0.2); } .remove-icon { width: 12px; height: 12px; } }
.add-var-btn { display: flex; align-items: center; gap: 6px; width: 100%; padding: 6px 8px; background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255, 255, 255, 0.1); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.4); font-size: 11px; transition: all 0.15s; &:hover { background: rgba(245, 158, 11, 0.06); border-color: rgba(245, 158, 11, 0.3); color: #fbbf24; } .add-icon { width: 12px; height: 12px; } }
:deep(.el-textarea__inner) { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; color: var(--node-text, #e2e8f0) !important; font-size: 11px !important; font-family: 'JetBrains Mono', monospace !important; }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: #1e1e2e; border: 2px solid #f59e0b; border-radius: 50%; &:hover { background: #f59e0b; transform: scale(1.3); box-shadow: 0 0 8px rgba(245, 158, 11, 0.6); } }
:global(.dark) { .prompt-node { --node-bg: #1e1e2e; --node-border: #f59e0b; --node-text: #e2e8f0; } }
:global(.light) { .prompt-node { --node-bg: #fff; --node-border: #f59e0b; --node-text: #1e293b; } }
</style>
