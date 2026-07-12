<template>
  <div
    class="integration-node"
    :class="{ selected, 'is-running': isRunning, 'is-completed': isCompleted, 'is-failed': isFailed }"
    :style="{ '--brand-color': nodeColor, '--node-accent': nodeColor }"
    @click.stop="handleSelect"
  >
    <Handle
      type="target"
      :position="Position.Left"
    />
    <div class="node-header">
      <NodeTypeBadge
        :node-type="integrationKey"
        compact
      />
      <div
        v-if="operationLabel"
        class="operation-badge"
      >
        {{ operationLabel }}
      </div>
    </div>
    <div class="node-body">
      <div
        class="node-icon-wrapper"
        :style="{ backgroundColor: nodeColor + '18' }"
      >
        <component
          :is="nodeIcon"
          v-if="nodeIcon"
          :size="18"
          :style="{ color: nodeColor }"
        />
      </div>
      <div class="node-info">
        <div class="node-label">
          {{ data.label || nodeLabel }}
        </div>
        <div class="node-sub">
          {{ operationLabel || nodeDescription || '集成节点' }}
        </div>
      </div>
    </div>
    <div
      v-if="isRunning || isCompleted || isFailed"
      class="status-strip"
      :class="{ running: isRunning, completed: isCompleted, failed: isFailed }"
    />
    <div
      v-if="isCompleted && resultPreview"
      class="result-preview"
    >
      {{ resultPreview }}
    </div>
    <Handle
      type="source"
      :position="Position.Right"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import NodeTypeBadge from '@/components/workflow/nodes/NodeTypeBadge.vue'
import { getIntegrationMeta } from '@/config/integrations'
import { useNodePresentation } from '@/composables/useNodePresentation'
import { useExecutionStore } from '@/stores/execution'
import { resolveNodeDisplayContent, truncateText } from '@/composables/useNodeResultDisplay'

const props = defineProps({
  id: { type: String, default: '' },
  type: { type: String, default: '' },
  data: { type: Object, default: () => ({}) },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])

const integrationKey = computed(() => props.type || props.data?.nodeType || props.data?.config?.integrationType || '')
const { nodeIcon, nodeColor, nodeLabel, nodeDescription } = useNodePresentation(integrationKey)

const meta = computed(() => getIntegrationMeta(integrationKey.value))

const config = computed(() => props.data?.config || {})
const operationLabel = computed(() => {
  const op = config.value.operation
  if (!op || !meta.value?.operations) return ''
  const found = meta.value.operations.find((item) => item.value === op)
  return found?.label || op
})

const executionStore = useExecutionStore()
const nodeStatus = computed(() => executionStore.nodeStatusMap[props.id])
const nodeOutput = computed(() => executionStore.nodeOutputs[props.id])

const isRunning = computed(() => nodeStatus.value === 'running')
const isCompleted = computed(() => nodeStatus.value === 'completed')
const isFailed = computed(() => nodeStatus.value === 'failed')

const resultPreview = computed(() => {
  if (!nodeOutput.value) return ''
  const parsed = resolveNodeDisplayContent(nodeOutput.value, config.value)
  if (parsed.imageUrl) return '[图片已生成]'
  if (parsed.videoUrl) return '[视频已生成]'
  if (parsed.audioUrl) return '[音频已生成]'
  return truncateText(parsed.text, 48)
})

function handleSelect() {
  emit('select', props.id)
}
</script>

<style lang="scss" scoped>
.integration-node {
  min-width: 200px;
  max-width: 260px;
  background: var(--flow-node-bg, #fff);
  border: 1.5px solid var(--flow-node-border, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  position: relative;
  overflow: hidden;

  &:hover {
    border-color: var(--brand-color);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.selected {
    border-color: var(--brand-color);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--brand-color) 30%, transparent);
  }

  &.is-running { border-color: #3b82f6; }
  &.is-completed { border-color: #10b981; }
  &.is-failed { border-color: #ef4444; }
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 8px 10px 4px;
}

.operation-badge {
  font-size: 10px;
  color: var(--flow-text-muted, #6b7280);
  background: var(--flow-bg-muted, #f3f4f6);
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 90px;
}

.node-body {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 10px;
}

.node-icon-wrapper {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.node-info { min-width: 0; flex: 1; }

.node-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--flow-text, #111827);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-sub {
  font-size: 11px;
  color: var(--flow-text-muted, #6b7280);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-strip {
  height: 3px;
  &.running { background: #3b82f6; }
  &.completed { background: #10b981; }
  &.failed { background: #ef4444; }
}

.result-preview {
  margin: 0 10px 10px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 10px;
  line-height: 1.4;
  color: var(--flow-text-muted, #6b7280);
  background: var(--flow-bg-muted, #f3f4f6);
  word-break: break-all;
}

:deep(.vue-flow__handle) {
  width: 10px;
  height: 10px;
  background: var(--flow-node-bg, #fff);
  border: 2px solid var(--node-accent);
  border-radius: 50%;

  &:hover {
    background: var(--node-accent);
    transform: scale(1.3);
  }
}
</style>
