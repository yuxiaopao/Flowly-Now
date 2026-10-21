<template>
  <div
    v-if="summary.hasResult"
    class="node-exec-result nodrag nopan"
    @click.stop="openResult"
    @mousedown.stop
  >
    <img
      v-if="summary.images[0]?.url"
      :src="summary.images[0].url"
      class="node-exec-result__thumb"
      :alt="summary.images[0].title || '节点图片'"
    >
    <div class="node-exec-result__body">
      <span class="node-exec-result__meta">
        <template v-if="summary.totals.images">图 {{ summary.totals.images }}</template>
        <template v-if="summary.totals.documents">
          {{ summary.totals.images ? ' · ' : '' }}文档 {{ summary.totals.documents }}
        </template>
        <template v-if="!summary.totals.images && !summary.totals.documents && summary.path">
          文件
        </template>
        <template v-if="!summary.totals.images && !summary.totals.documents && !summary.path">
          输出
        </template>
      </span>
      <p class="node-exec-result__text">
        {{ previewText }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useExecutionStore } from '@/stores/execution'
import { summarizeNodeExecution } from '@/utils/executionOutputViewer'
import { WORKFLOW_FOCUS_EXECUTION_NODE_KEY } from '@/config/workflowCanvas'

const props = defineProps({
  nodeId: { type: String, required: true },
  data: { type: Object, default: () => ({}) },
})

const executionStore = useExecutionStore()
const focusExecutionNode = inject(WORKFLOW_FOCUS_EXECUTION_NODE_KEY, null)

const nodeOutput = computed(() => executionStore.nodeOutputs?.[props.nodeId] ?? props.data?._runtime?.output ?? null)

const summary = computed(() => summarizeNodeExecution({
  nodeId: props.nodeId,
  name: props.data?.label || props.data?.name,
  output: nodeOutput.value,
}))

const previewText = computed(() => {
  if (summary.value.documents[0]?.title) return summary.value.documents[0].title
  if (summary.value.images[0]?.title) return summary.value.images[0].title
  if (summary.value.path) return summary.value.path.replace(/\\/g, '/')
  return summary.value.excerpt || '查看节点输出'
})

function openResult() {
  if (typeof focusExecutionNode === 'function') {
    focusExecutionNode(props.nodeId)
  }
}
</script>

<style lang="scss" scoped>
.node-exec-result {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  padding: 6px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--bg-tertiary);
  cursor: pointer;
  max-width: 260px;
  text-align: left;
}

.node-exec-result__thumb {
  width: 56px;
  height: 42px;
  object-fit: cover;
  border-radius: 4px;
  background: #fff;
  flex-shrink: 0;
}

.node-exec-result__body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.node-exec-result__meta {
  font-size: 10px;
  color: var(--text-tertiary);
}

.node-exec-result__text {
  margin: 0;
  font-size: 11px;
  line-height: 1.35;
  color: var(--text-secondary);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
