<template>
  <section class="execution-graph">
    <div class="execution-graph__header">
      <div class="execution-graph__title-row">
        <h4>工作流运行图</h4>
        <span class="execution-graph__counts">
          <span>{{ stats.completed }}/{{ stats.total }} 完成</span>
          <span v-if="stats.running"> · {{ stats.running }} 运行中</span>
          <span
            v-if="stats.failed"
            class="is-fail"
          > · {{ stats.failed }} 失败</span>
        </span>
      </div>
      <ul class="execution-graph__legend">
        <li><i class="lg lg-pending" />等待</li>
        <li><i class="lg lg-running" />运行</li>
        <li><i class="lg lg-completed" />完成</li>
        <li><i class="lg lg-failed" />失败</li>
      </ul>
    </div>

    <div
      v-if="graphNodes.length === 0"
      class="execution-graph__empty"
    >
      工作流节点尚未加载
    </div>
    <div
      v-else
      class="execution-graph__canvas"
    >
      <VueFlow
        :id="flowId"
        ref="vueFlowRef"
        v-model:nodes="graphNodes"
        v-model:edges="graphEdges"
        :node-types="nodeTypes"
        :min-zoom="0.08"
        :max-zoom="2.2"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :elements-selectable="true"
        :pan-on-scroll="true"
        fit-view-on-init
        @node-click="onNodeClick"
        @nodes-initialized="fitGraph"
      >
        <Background
          :gap="20"
          :size="1"
        />
        <Controls :show-interactive="false" />
        <MiniMap
          :node-color="minimapColor"
          :mask-color="minimapMask"
        />
      </VueFlow>
    </div>
    <p
      v-if="selectedHint"
      class="execution-graph__hint"
    >
      {{ selectedHint }}
    </p>
  </section>
</template>

<script setup>
import { computed, markRaw, nextTick, ref, watch } from 'vue'
import { MarkerType, VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import ExecutionStatusNode from '@/components/workflow/ExecutionStatusNode.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => [],
  },
  edges: {
    type: Array,
    default: () => [],
  },
  nodeStatus: {
    type: Object,
    default: () => ({}),
  },
  selectedNodeId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select'])

const flowId = `exec-graph-${Math.random().toString(36).slice(2, 8)}`
const vueFlowRef = ref(null)
const nodeTypes = { exec: markRaw(ExecutionStatusNode) }
const graphNodes = ref([])
const graphEdges = ref([])
let fittedOnce = false

function resolveStatus(nodeId) {
  const raw = props.nodeStatus?.[nodeId]
  if (!raw) return { status: 'pending', duration: '', error: '', name: '' }
  if (typeof raw === 'string') return { status: raw, duration: '', error: '', name: '' }
  return {
    status: raw.status || 'pending',
    duration: raw.duration || '',
    error: raw.error || '',
    name: raw.name || '',
  }
}

function mapNodes(sourceNodes) {
  return (sourceNodes || []).map((node) => {
    const id = String(node.id || node.node_id || '')
    const info = resolveStatus(id)
    const label = info.name
      || node.data?.label
      || node.label
      || node.name
      || id
    return {
      id,
      type: 'exec',
      position: {
        x: Number(node.position?.x) || 0,
        y: Number(node.position?.y) || 0,
      },
      selectable: true,
      draggable: false,
      connectable: false,
      class: `vf-exec is-${info.status}`,
      data: {
        label,
        status: info.status,
        duration: info.duration,
        error: info.error,
      },
    }
  })
}

function mapEdges(sourceEdges) {
  return (sourceEdges || []).map((edge, index) => {
    const source = String(edge.source || edge.source_node || '')
    const target = String(edge.target || edge.target_node || '')
    const srcStatus = resolveStatus(source).status
    const tgtStatus = resolveStatus(target).status
    const done = srcStatus === 'completed' && (tgtStatus === 'completed' || tgtStatus === 'running')
    const failed = srcStatus === 'failed' || tgtStatus === 'failed'
    const running = srcStatus === 'running' || tgtStatus === 'running'
    let stroke = 'rgba(148,163,184,0.45)'
    if (failed) stroke = 'rgba(239,68,68,0.75)'
    else if (done) stroke = 'rgba(34,197,94,0.7)'
    else if (running) stroke = 'rgba(245,158,11,0.8)'
    return {
      id: String(edge.id || `e-${index}-${source}-${target}`),
      source,
      target,
      animated: running,
      markerEnd: MarkerType.ArrowClosed,
      style: { stroke, strokeWidth: running || failed ? 2 : 1.4 },
    }
  })
}

function rebuild() {
  graphNodes.value = mapNodes(props.nodes)
  graphEdges.value = mapEdges(props.edges)
}

function patchLiveStatus() {
  graphNodes.value = graphNodes.value.map((node) => {
    const info = resolveStatus(node.id)
    return {
      ...node,
      class: `vf-exec is-${info.status}`,
      selected: props.selectedNodeId === node.id,
      data: {
        ...node.data,
        status: info.status,
        duration: info.duration,
        error: info.error,
        label: info.name || node.data.label,
      },
    }
  })
  graphEdges.value = mapEdges(props.edges)
}

const stats = computed(() => {
  const values = Object.values(props.nodeStatus || {})
  const statuses = values.map((v) => (typeof v === 'string' ? v : v?.status))
  const total = Math.max(props.nodes?.length || 0, statuses.length)
  return {
    total,
    completed: statuses.filter((s) => s === 'completed').length,
    running: statuses.filter((s) => s === 'running').length,
    failed: statuses.filter((s) => s === 'failed').length,
  }
})

const selectedHint = computed(() => {
  if (!props.selectedNodeId) return ''
  const info = resolveStatus(props.selectedNodeId)
  const label = info.name
    || graphNodes.value.find((n) => n.id === props.selectedNodeId)?.data?.label
    || props.selectedNodeId
  if (info.error) return `${label}：${String(info.error).slice(0, 220)}`
  if (info.status === 'running') return `${label} 正在执行`
  if (info.status === 'completed') return `${label} 已完成${info.duration ? ` · ${info.duration}s` : ''}`
  return `${label}`
})

function minimapColor(node) {
  const status = node?.data?.status || 'pending'
  if (status === 'running') return '#f59e0b'
  if (status === 'completed') return '#22c55e'
  if (status === 'failed') return '#ef4444'
  return '#475569'
}

const minimapMask = 'rgba(8, 8, 12, 0.55)'

function fitGraph() {
  nextTick(() => {
    vueFlowRef.value?.fitView?.({ padding: 0.18, maxZoom: 1.05 })
    fittedOnce = true
  })
}

function onNodeClick({ node }) {
  if (!node?.id) return
  emit('select', node.id)
}

watch(
  () => [props.nodes, props.edges],
  () => {
    rebuild()
    if (fittedOnce) nextTick(() => vueFlowRef.value?.fitView?.({ padding: 0.18, maxZoom: 1.05 }))
  },
  { immediate: true, deep: false },
)

watch(
  () => [props.nodeStatus, props.selectedNodeId],
  () => {
    if (!graphNodes.value.length) rebuild()
    else patchLiveStatus()
  },
  { deep: true },
)
</script>

<style lang="scss" scoped>
.execution-graph {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  flex-shrink: 0;
}

.execution-graph__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.execution-graph__title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;

  h4 {
    margin: 0;
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.execution-graph__counts {
  font-size: 12px;
  color: var(--text-tertiary);

  .is-fail {
    color: #ef4444;
  }
}

.execution-graph__legend {
  display: flex;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 11px;
  color: var(--text-tertiary);

  li {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .lg {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }

  .lg-pending { background: #64748b; }
  .lg-running { background: #f59e0b; }
  .lg-completed { background: #22c55e; }
  .lg-failed { background: #ef4444; }
}

.execution-graph__canvas {
  height: 380px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-primary);
  background: var(--canvas-bg, var(--bg-tertiary));
}

.execution-graph__empty,
.execution-graph__hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-tertiary);
}

.execution-graph__empty {
  text-align: center;
  padding: 48px 16px;
  border: 1px dashed var(--border-primary);
  border-radius: 12px;
}

:deep(.vue-flow) {
  width: 100%;
  height: 100%;
}

:deep(.vue-flow__minimap) {
  background: color-mix(in srgb, var(--bg-secondary) 88%, transparent);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
}

:deep(.vue-flow__controls) {
  box-shadow: none;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  overflow: hidden;
}
</style>
