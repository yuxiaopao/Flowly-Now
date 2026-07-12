<template>
  <div
    class="llm-node"
    :class="{ selected, expanded: isExpanded, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    :style="{ '--node-accent': nodeColor }"
    @click.stop="handleSelect"
  >
    <Handle
      id="input"
      type="target"
      :position="Position.Left"
    />

    <div class="node-header">
      <NodeTypeBadge :node-type="NODE_TYPE" compact />
    </div>

    <div class="node-name-section">
      <input
        :id="id ? `node-label-${id}` : undefined"
        v-model="localName"
        class="node-name-input"
        name="node-label"
        placeholder="节点名称..."
        @blur="handleNameChange"
        @keydown.enter="handleNameChange"
        @click.stop="handleSelect"
      >
    </div>

    <div class="compact-view">
      <div class="model-display">
        <span class="model-label">模型</span>
        <span class="model-value">{{ displayModel }}</span>
      </div>
      <div class="temp-display">
        <span class="temp-label">温度</span>
        <span class="temp-value">{{ localConfig.temperature }}</span>
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
          <span>生成中...</span>
          <span
            v-if="tokenCount > 0"
            class="token-count"
          >{{ tokenCount }} tokens</span>
        </div>
        <div
          v-else-if="isCompleted"
          class="status-done"
        >
          <span class="status-dot" />
          <span>已完成</span>
          <span
            v-if="tokenCount > 0"
            class="token-count"
          >{{ tokenCount }} tokens</span>
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
      v-if="isRunning || isCompleted"
      class="output-preview-zone"
    >
      <div class="output-header">
        <Terminal class="output-icon" />
        <span class="output-label">输出预览</span>
        <span
          v-if="isStreaming || isRunning"
          class="stream-indicator"
        >
          <span class="stream-dot" />
          <span class="stream-text">流式</span>
        </span>
      </div>
      <div class="output-content">
        <div
          v-if="streamingText"
          class="streaming-text"
        >
          <span class="text-content">{{ streamingText }}</span>
          <span class="cursor-blink">|</span>
        </div>
        <div
          v-else-if="outputSummary"
          class="output-summary"
        >
          <span class="summary-text">{{ outputSummary }}</span>
        </div>
        <div
          v-else
          class="output-empty"
        >
          <span
            v-if="isRunning"
            class="empty-hint"
          >AI 思考中...</span>
          <span
            v-else
            class="empty-hint"
          >等待输入</span>
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
          <label class="config-label">模型选择</label>
          <el-select
            v-model="localConfig.model"
            placeholder="选择模型"
            filterable
            size="small"
            :loading="modelsLoading"
            @change="handleConfigChange"
          >
            <template v-if="modelOptions">
              <el-option-group
                v-for="(models, provider) in modelOptions"
                :key="provider"
                :label="provider"
              >
                <el-option
                  v-for="opt in models"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-option-group>
            </template>
            <template v-else>
              <el-option
                value=""
                label="加载中..."
                disabled
              />
            </template>
          </el-select>
        </div>

        <div class="config-section">
          <label class="config-label">温度参数</label>
          <div class="temp-control">
            <el-slider
              v-model="localConfig.temperature"
              :min="0"
              :max="2"
              :step="0.1"
              size="small"
              @change="handleConfigChange"
            />
            <span class="temp-number">{{ localConfig.temperature }}</span>
          </div>
        </div>

        <div class="config-section">
          <label class="config-label">系统提示词</label>
          <el-input
            v-model="localConfig.systemPrompt"
            type="textarea"
            :rows="3"
            size="small"
            placeholder="你是一个有帮助的AI助手..."
            @input="handleConfigChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">用户模板</label>
          <el-input
            v-model="localConfig.userTemplate"
            type="textarea"
            :rows="2"
            size="small"
            placeholder="{input}"
            @input="handleConfigChange"
          />
        </div>

        <div class="config-section">
          <label class="config-label">最大 Token</label>
          <el-input-number
            v-model="localConfig.maxTokens"
            :min="1"
            :max="128000"
            size="small"
            controls-position="right"
            @change="handleConfigChange"
          />
        </div>

        <div class="config-section">
          <button
            class="toggle-advanced"
            @click="showAdvanced = !showAdvanced"
          >
            <Settings class="toggle-icon" />
            <span>高级选项</span>
            <ChevronRight
              class="toggle-arrow"
              :class="{ rotated: showAdvanced }"
            />
          </button>
        </div>

        <Transition name="fade">
          <div
            v-if="showAdvanced"
            class="advanced-config"
          >
            <div class="config-row">
              <label>流式输出</label>
              <el-switch
                v-model="localConfig.streaming"
                size="small"
                @change="handleConfigChange"
              />
            </div>
            <div class="config-row">
              <label>顶部P</label>
              <el-input-number
                v-model="localConfig.topP"
                :min="0"
                :max="1"
                :step="0.05"
                :precision="2"
                size="small"
                controls-position="right"
                @change="handleConfigChange"
              />
            </div>
            <div class="config-row">
              <label>频率惩罚</label>
              <el-input-number
                v-model="localConfig.frequencyPenalty"
                :min="-2"
                :max="2"
                :step="0.1"
                :precision="1"
                size="small"
                controls-position="right"
                @change="handleConfigChange"
              />
            </div>
            <div class="config-row">
              <label>存在惩罚</label>
              <el-input-number
                v-model="localConfig.presencePenalty"
                :min="-2"
                :max="2"
                :step="0.1"
                :precision="1"
                size="small"
                controls-position="right"
                @change="handleConfigChange"
              />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <Handle
      id="output"
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { Zap, ChevronDown, ChevronRight, Settings, Loader, Terminal } from 'lucide-vue-next'
import { APP_CONFIG } from '@/config'
import { useWorkflowStore } from '@/stores/workflow'
import { useExecutionStore } from '@/stores/execution'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { useNodePresentation } from '@/composables/useNodePresentation'


const props = defineProps({
  id: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false }
})

const NODE_TYPE = 'llm'
const { nodeIcon, nodeColor, nodeLabel } = useNodePresentation(NODE_TYPE)

const emit = defineEmits(['update:data', 'select'])

const { updateNodeData } = useVueFlow()
const workflowStore = useWorkflowStore()
const executionStore = useExecutionStore()

const localName = ref(props.data.label || 'AI 对话')
const isExpanded = ref(false)
const showAdvanced = ref(false)

const localConfig = ref({
  model: props.data.config?.model || APP_CONFIG.llm.defaultModel || 'gpt-3.5-turbo',
  temperature: props.data.config?.temperature ?? 0.7,
  systemPrompt: props.data.config?.systemPrompt || '',
  userTemplate: props.data.config?.userTemplate || '{input}',
  maxTokens: props.data.config?.maxTokens || 2000,
  streaming: props.data.config?.streaming ?? false,
  topP: props.data.config?.topP ?? 1,
  frequencyPenalty: props.data.config?.frequencyPenalty ?? 0,
  presencePenalty: props.data.config?.presencePenalty ?? 0,
})

const availableModels = ref([])
const modelsLoading = ref(false)

const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])
const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')
const streamingOutput = computed(() => executionStore.streamingOutput)
const isStreaming = computed(() => executionStore.isStreaming)

const tokenCount = computed(() => {
  const stats = executionStore.tokenStats
  return stats.total || (nodeOutput.value && nodeOutput.value.tokens) || 0
})

const streamingText = computed(() => {
  if (isRunning.value && streamingOutput.value) return streamingOutput.value
  return ''
})

const outputSummary = computed(() => {
  if (!nodeOutput.value) return null
  const text = typeof nodeOutput.value === 'string' ? nodeOutput.value : nodeOutput.value.text || nodeOutput.value.content || nodeOutput.value.output || ''
  if (!text) return null
  return text.length > 100 ? text.slice(0, 100) + '...' : text
})

const displayModel = computed(() => {
  if (localConfig.value.model) return localConfig.value.model
  return APP_CONFIG.llm.defaultModel || '未选择'
})

async function loadModels() {
  modelsLoading.value = true
  try {
    const models = await workflowStore.fetchAvailableModels({ type: 'chat' })
    if (models) {
      availableModels.value = models.map(m => ({
        id: m.modelId || m.model_id || m.id,
        name: m.name,
        model_id: m.modelId || m.model_id,
        provider: (typeof m.provider === 'string') ? m.provider : (m.provider?.name || m.providerName || 'Unknown'),
        supportsVision: m.supportsVision || m.supports_vision,
        supportsFunctionCalling: m.supportsFunctionCalling || m.supports_function_calling,
        supportsStreaming: m.supportsStreaming || m.supports_streaming,
      }))
    }
  } catch (err) {
    console.warn('Failed to load models:', err)
  } finally {
    modelsLoading.value = false
  }
}

const modelOptions = computed(() => {
  if (availableModels.value.length > 0) {
    const grouped = {}
    availableModels.value.forEach(m => {
      const provider = m.provider || 'Unknown'
      if (!grouped[provider]) grouped[provider] = []
      grouped[provider].push({
        value: m.modelId || m.model_id || m.id,
        label: m.name,
      })
    })
    return grouped
  }
  return null
})

watch(() => props.data, (newData) => {
  if (newData) {
    localName.value = newData.label || 'AI 对话'
    localConfig.value = {
      model: newData.config?.model || APP_CONFIG.llm.defaultModel || 'gpt-3.5-turbo',
      temperature: newData.config?.temperature ?? 0.7,
      systemPrompt: newData.config?.systemPrompt || '',
      userTemplate: newData.config?.userTemplate || '{input}',
      maxTokens: newData.config?.maxTokens || 2000,
      streaming: newData.config?.streaming ?? false,
      topP: newData.config?.topP ?? 1,
      frequencyPenalty: newData.config?.frequencyPenalty ?? 0,
      presencePenalty: newData.config?.presencePenalty ?? 0,
      ...(newData.config || {})
    }
  }
}, { deep: true })

function toggleExpand() {
  handleSelect()
  isExpanded.value = !isExpanded.value
}

function handleNameChange() {
  if (props.id) {
    updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
  }
  emit('update:data', { ...props.data, label: localName.value, config: { ...localConfig.value } })
}

function handleConfigChange() {
  if (props.id) {
    updateNodeData(props.id, { label: localName.value, config: { ...localConfig.value } })
  }
  emit('update:data', { ...props.data, label: localName.value, config: { ...localConfig.value } })
}

function handleSelect() {
  emit('select')
  if (!isExpanded.value) isExpanded.value = true
}

onMounted(() => { loadModels() })
</script>

<style lang="scss" scoped>
.llm-node {
  background: var(--node-bg, #1e1e2e);
  border: 2px solid var(--node-border, #3b82f6);
  border-radius: 12px;
  min-width: 200px;
  max-width: 320px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(59, 130, 246, 0.1);
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
  cursor: pointer;
  overflow: hidden;

  &.selected { border-color: var(--node-border, #3b82f6); box-shadow: 0 8px 32px rgba(59, 130, 246, 0.25), 0 0 0 2px rgba(59, 130, 246, 0.3), 0 4px 20px rgba(0, 0, 0, 0.4); transform: translateY(-2px); }
  &:hover:not(.selected) { border-color: #60a5fa; box-shadow: 0 6px 24px rgba(59, 130, 246, 0.15), 0 0 0 1px rgba(59, 130, 246, 0.15); transform: translateY(-1px); }
  &.is-running { animation: llm-pulse 1.8s ease-in-out infinite; }
  &.is-completed .output-preview-zone { border-color: rgba(16, 185, 129, 0.4); }
  &.is-failed { border-color: rgba(239, 68, 68, 0.6) !important; }
}

@keyframes llm-pulse {
  0%, 100% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 0 rgba(59, 130, 246, 0.3); }
  50% { box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3), 0 0 0 6px rgba(59, 130, 246, 0); }
}

.output-preview-zone {
  margin: 0 12px 8px;
  border-radius: 8px;
  border: 2px solid rgba(59, 130, 246, 0.2);
  background: rgba(0, 0, 0, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.output-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.15);
  background: rgba(59, 130, 246, 0.05);

  .output-icon { width: 11px; height: 11px; color: rgba(59, 130, 246, 0.6); }
  .output-label { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: rgba(59, 130, 246, 0.7); }
}

.stream-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;

  .stream-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #3b82f6;
    animation: stream-blink 1s ease-in-out infinite;
  }

  .stream-text { font-size: 9px; color: rgba(59, 130, 246, 0.6); font-weight: 600; }
}

@keyframes stream-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.output-content {
  padding: 8px 10px;
  max-height: 80px;
  overflow: hidden;
}

.streaming-text {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  color: #a5d6ff;
  line-height: 1.5;
  display: flex;
  align-items: baseline;

  .text-content { flex: 1; word-break: break-word; }
}

.cursor-blink {
  color: #3b82f6;
  animation: blink 0.8s step-end infinite;
  font-weight: 300;
}

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

.output-summary {
  .summary-text {
    font-size: 11px;
    color: #a5d6ff;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.5;
    word-break: break-word;
  }
}

.output-empty {
  .empty-hint { font-size: 10px; color: rgba(59, 130, 246, 0.4); font-style: italic; }
}

.token-count {
  font-size: 9px;
  font-family: 'JetBrains Mono', monospace;
  color: rgba(59, 130, 246, 0.6);
  margin-left: auto;
}

.status-bar {
  margin-top: 6px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 5px;

  &.running { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); }
  &.completed { background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2); }
  &.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.2); }
}

.status-running, .status-done, .status-error { display: flex; align-items: center; gap: 5px; }
.status-icon { width: 12px; height: 12px; &.spinning { animation: spin 1s linear infinite; } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

.node-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); background: rgba(59, 130, 246, 0.08); }
.node-type-badge { display: flex; align-items: center; gap: 6px; padding: 3px 10px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 20px; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #60a5fa; .badge-icon { width: 11px; height: 11px; } }
.node-actions { display: flex; gap: 4px; }
.action-btn { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.5); transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.9); } .action-icon { width: 14px; height: 14px; transition: transform 0.2s ease; &.rotated { transform: rotate(180deg); } } }
.node-name-section { padding: 10px 12px 6px; }
.node-name-input { width: 100%; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-weight: 600; color: var(--node-text, #e2e8f0); outline: none; transition: all 0.15s ease; &::placeholder { color: rgba(255, 255, 255, 0.3); } &:focus { border-color: rgba(59, 130, 246, 0.5); background: rgba(59, 130, 246, 0.05); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); } }
.compact-view { display: flex; gap: 8px; padding: 0 12px 10px; flex-direction: column; }
.model-display, .temp-display { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 5px 8px; background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; }
.model-label, .temp-label { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.35); }
.model-value { font-size: 11px; font-weight: 500; color: #60a5fa; font-family: 'JetBrains Mono', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.temp-value { font-size: 12px; font-weight: 600; color: #a78bfa; font-family: 'JetBrains Mono', monospace; }
.expanded-config { border-top: 1px solid rgba(255, 255, 255, 0.06); padding: 8px 12px 10px; display: flex; flex-direction: column; gap: 10px; }
.config-section { display: flex; flex-direction: column; gap: 5px; }
.config-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255, 255, 255, 0.4); }
.temp-control { display: flex; align-items: center; gap: 8px; :deep(.el-slider) { flex: 1; .el-slider__runway { background: rgba(255, 255, 255, 0.1); height: 4px; } .el-slider__bar { background: linear-gradient(90deg, #3b82f6, #a78bfa); height: 4px; } .el-slider__button { width: 12px; height: 12px; border: 2px solid #3b82f6; background: #1e1e2e; } } .temp-number { min-width: 32px; font-size: 12px; font-weight: 700; color: #a78bfa; font-family: 'JetBrains Mono', monospace; text-align: right; } }
:deep(.el-input-number) { width: 100%; .el-input-number__decrease, .el-input-number__increase { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.1); color: rgba(255, 255, 255, 0.5); &:hover { color: #60a5fa; } } .el-input__inner { text-align: left; } }
:deep(.el-select), :deep(.el-input), :deep(.el-input-number) { .el-input__wrapper { background: rgba(255, 255, 255, 0.05) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; box-shadow: none !important; border-radius: 6px; &:hover, &:focus { border-color: rgba(59, 130, 246, 0.4) !important; } } .el-input__inner { color: var(--node-text, #e2e8f0) !important; font-size: 12px !important; } .el-input__suffix .el-select__caret { color: rgba(255, 255, 255, 0.4) !important; } }
.toggle-advanced { display: flex; align-items: center; gap: 6px; width: 100%; padding: 6px 8px; background: rgba(255, 255, 255, 0.03); border: 1px dashed rgba(255, 255, 255, 0.1); border-radius: 6px; cursor: pointer; color: rgba(255, 255, 255, 0.4); font-size: 11px; font-weight: 500; transition: all 0.15s ease; &:hover { background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.15); color: rgba(255, 255, 255, 0.6); } .toggle-icon { width: 12px; height: 12px; } .toggle-arrow { width: 12px; height: 12px; margin-left: auto; transition: transform 0.2s ease; &.rotated { transform: rotate(90deg); } } }
.advanced-config { display: flex; flex-direction: column; gap: 8px; padding: 8px; background: rgba(0, 0, 0, 0.2); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 8px; }
.config-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; label { font-size: 11px; color: rgba(255, 255, 255, 0.5); white-space: nowrap; } :deep(.el-input-number) { width: 100px; .el-input__wrapper { background: rgba(255, 255, 255, 0.04) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; box-shadow: none !important; } .el-input__inner { color: var(--node-text, #e2e8f0) !important; font-size: 11px !important; } } :deep(.el-switch) { --el-switch-off-color: rgba(255, 255, 255, 0.1); --el-switch-on-color: #3b82f6; } }
.expand-enter-active, .expand-leave-active { transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1); overflow: hidden; }
.expand-enter-from, .expand-leave-to { opacity: 0; max-height: 0; padding-top: 0; padding-bottom: 0; }
.expand-enter-to, .expand-leave-from { opacity: 1; max-height: 400px; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
:deep(.vue-flow__handle) { width: 10px; height: 10px; background: #1e1e2e; border: 2px solid #3b82f6; border-radius: 50%; transition: all 0.15s ease; &:hover { background: #3b82f6; transform: scale(1.3); box-shadow: 0 0 8px rgba(59, 130, 246, 0.6); } }
:global(.dark) { .llm-node { --node-bg: #1e1e2e; --node-border: #3b82f6; --node-text: #e2e8f0; } }
:global(.light) { .llm-node { --node-bg: #ffffff; --node-border: #3b82f6; --node-text: #1e293b; } }
:global(.pure-bw) { .llm-node { --node-bg: #ffffff; --node-border: #111111; --node-text: #111111; } }
:global(.high-contrast) { .llm-node { --node-bg: #000000; --node-border: #ffff00; --node-text: #ffffff; } }
</style>
