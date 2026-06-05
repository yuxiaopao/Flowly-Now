<template>
  <div
    class="workflow-preview"
    :class="{ 'is-empty': !nodes || nodes.length === 0 }"
  >
    <svg
      v-if="nodes && nodes.length > 0"
      class="preview-svg"
      :viewBox="`0 0 ${VW} ${VH}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <pattern
          id="preview-grid"
          width="16"
          height="16"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M 16 0 L 0 0 0 16"
            fill="none"
            stroke="currentColor"
            stroke-width="0.3"
          />
        </pattern>
      </defs>
      <rect
        width="100%"
        height="100%"
        fill="url(#preview-grid)"
        class="preview-grid-rect"
      />

      <!-- Edges -->
      <g class="preview-edges">
        <polyline
          v-for="edge in renderedEdges"
          :key="edge.id"
          :points="edge.isPoly
            ? `${edge.x1},${edge.y1} ${edge.polyX || edge.x1},${edge.polyY || edge.y1} ${edge.x2},${edge.y2}`
            : `${edge.x1},${edge.y1} ${edge.x2},${edge.y2}`
          "
          class="preview-edge"
        />
      </g>

      <!-- Nodes -->
      <g class="preview-nodes">
        <g
          v-for="node in renderedNodes"
          :key="node.id"
          :transform="`translate(${node.cx}, ${node.cy})`"
          class="preview-node"
        >
          <rect
            :width="NODE_W"
            :height="NODE_H"
            :rx="4"
            :ry="4"
            class="preview-node-bg"
            :style="{ fill: node.bgColor, stroke: node.color }"
          />
          <text
            :x="NODE_W / 2"
            :y="NODE_H / 2 + 1"
            class="preview-node-label"
            dominant-baseline="middle"
            text-anchor="middle"
          >{{ node.shortLabel }}</text>
        </g>
      </g>

      <!-- Empty hint -->
      <text
        v-if="!nodes || nodes.length === 0"
        :x="VW / 2"
        :y="VH / 2"
        class="preview-empty-text"
        dominant-baseline="middle"
        text-anchor="middle"
      >暂无节点</text>
    </svg>
    <div
      v-else
      class="preview-empty"
    >
      <GitBranch class="preview-empty-icon" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { GitBranch } from 'lucide-vue-next'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  }
})

// 节点尺寸
const NODE_W = 36
const NODE_H = 18
const NODE_R = 4  // 节点圆角

// 类型 -> 颜色映射
const TYPE_COLORS = {
  start:  { color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  end:    { color: '#ef4444', bg: 'rgba(239,68,68,0.15)' },
  llm:    { color: '#3b82f6', bg: 'rgba(59,130,246,0.15)' },
  prompt: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  input:  { color: '#06b6d4', bg: 'rgba(6,182,212,0.15)' },
  output: { color: '#84cc16', bg: 'rgba(132,204,22,0.15)' },
  code:   { color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  variable:  { color: '#a855f7', bg: 'rgba(168,85,247,0.15)' },
  tool:   { color: '#ec4899', bg: 'rgba(236,72,153,0.15)' },
  http:   { color: '#6366f1', bg: 'rgba(99,102,241,0.15)' },
  email:  { color: '#14b8a6', bg: 'rgba(20,184,166,0.15)' },
  delay:  { color: '#78716c', bg: 'rgba(120,113,108,0.15)' },
  condition: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  loop:   { color: '#d946ef', bg: 'rgba(217,70,239,0.15)' },
  transform: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.15)' },
  switch: { color: '#f43f5e', bg: 'rgba(244,63,94,0.15)' },
  subworkflow: { color: '#0ea5e9', bg: 'rgba(14,165,233,0.15)' },
  image_generation: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  video_generation: { color: '#f97316', bg: 'rgba(249,115,22,0.15)' },
  audio_generation: { color: '#84cc16', bg: 'rgba(132,204,22,0.15)' },
  document_loader: { color: '#22d3ee', bg: 'rgba(34,211,238,0.15)' },
  embedding: { color: '#a78bfa', bg: 'rgba(167,139,250,0.15)' },
  vector_store: { color: '#34d399', bg: 'rgba(52,211,153,0.15)' },
  retriever: { color: '#38bdf8', bg: 'rgba(56,189,248,0.15)' },
  agent: { color: '#fb923c', bg: 'rgba(251,146,60,0.15)' },
  planner: { color: '#c084fc', bg: 'rgba(192,132,252,0.15)' },
  executor: { color: '#86efac', bg: 'rgba(134,239,172,0.15)' },
  memory: { color: '#f9a8d4', bg: 'rgba(249,168,212,0.15)' },
  file_reader: { color: '#38bdf8', bg: 'rgba(56,189,248,0.15)' },
  file_writer: { color: '#38bdf8', bg: 'rgba(56,189,248,0.15)' },
  web_scraper: { color: '#22d3ee', bg: 'rgba(34,211,238,0.15)' },
}

const DEFAULT_COLOR = { color: '#6b7280', bg: 'rgba(107,114,128,0.15)' }

function getNodeStyle(type) {
  return TYPE_COLORS[type] || DEFAULT_COLOR
}

// 节点短名称映射
const TYPE_LABELS = {
  start: 'S', end: 'E', llm: 'L', prompt: 'P',
  input: 'I', output: 'O', code: 'X', variable: 'V',
  tool: 'T', http: 'H', email: 'M', delay: 'D',
  condition: 'C', loop: 'LP', transform: 'TF', switch: 'SW',
  subworkflow: 'SF', image_generation: 'IG', video_generation: 'VG',
  audio_generation: 'AG', document_loader: 'DL', embedding: 'EM',
  vector_store: 'VS', retriever: 'RT', agent: 'A',
  planner: 'PL', executor: 'EX', memory: 'MM',
  file_reader: 'FR', file_writer: 'FW', web_scraper: 'WS',
  csv_transform: 'CT', json_transform: 'JT',
  dataset_upload: 'DU', data_annotation: 'DA', data_augmentation: 'Dx',
  model_training: 'MT', model_evaluation: 'ME', model_deployment: 'MD',
  website_generator: 'WG', image_editing: 'IE', subtitle_generation: 'SG',
  reranker: 'RR',
}

function getShortLabel(type) {
  return TYPE_LABELS[type] || type?.charAt(0).toUpperCase() || '?'
}

// 视图尺寸
const VW = 220
const VH = 100

// 将节点映射到 SVG 坐标
const PAD = 16
const H_GAP = 40  // 节点水平间隔
const V_GAP = 30  // 节点垂直换行间距
const COLS = 4    // 每行最多节点数

const renderedNodes = computed(() => {
  if (!props.nodes || props.nodes.length === 0) return []

  const ns = props.nodes.slice(0, 20)  // 最多 20 个
  const NW = NODE_W
  const NH = NODE_H

  return ns.map((n, i) => {
    const row = Math.floor(i / COLS)
    const col = i % COLS
    // 自动布局：每行 COLS 个，自动换行
    const cx = PAD + col * (NW + H_GAP)
    const cy = PAD + row * (NH + V_GAP)
    const style = getNodeStyle(n.type)
    return {
      id: n.id,
      cx,
      cy,
      type: n.type,
      shortLabel: getShortLabel(n.type),
      color: style.color,
      bgColor: style.bg,
    }
  })
})

// 按布局顺序相邻节点自动连线
const renderedEdges = computed(() => {
  const ns = renderedNodes.value
  if (ns.length < 2) return []

  const edges = []
  for (let i = 0; i < ns.length - 1; i++) {
    const a = ns[i]
    const b = ns[i + 1]
    const sameRow = Math.floor(i / COLS) === Math.floor((i + 1) / COLS)
    if (sameRow) {
      edges.push({
        id: `e-${i}`,
        x1: a.cx + NODE_W,
        y1: a.cy + NODE_H / 2,
        x2: b.cx,
        y2: b.cy + NODE_H / 2,
      })
    } else {
      // 换行：先从上一行末尾水平线走，再垂直向下，再水平进入下一行开头
      const lastOfRow = ns[Math.floor(i / COLS) * COLS + COLS - 1]
      if (lastOfRow) {
        const midX = lastOfRow.cx + NODE_W + 10
        const midY = a.cy + NODE_H / 2
        const midY2 = b.cy + NODE_H / 2
        edges.push({
          id: `e-${i}-h1`,
          x1: a.cx + NODE_W,
          y1: midY,
          x2: midX,
          y2: midY,
          isPoly: true,
          polyY: midY2,
          polyX: midX,
        })
        edges.push({
          id: `e-${i}-v`,
          x1: midX,
          y1: midY,
          x2: midX,
          y2: midY2,
          isPoly: true,
        })
        edges.push({
          id: `e-${i}-h2`,
          x1: midX,
          y1: midY2,
          x2: b.cx,
          y2: midY2,
          isPoly: true,
        })
      }
    }
  }
  return edges
})
</script>

<style lang="scss" scoped>
.workflow-preview {
  width: 100%;
  height: 100px;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--canvas-bg, var(--bg-tertiary));
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-primary);
}

.preview-svg {
  width: 100%;
  height: 100%;
  display: block;
}

.preview-grid-rect {
  color: var(--canvas-pattern, var(--border-primary));
}

.preview-edge {
  stroke: var(--border-primary);
  stroke-width: 1;
  opacity: 0.5;
}

.preview-node-label {
  font-size: 8px;
  font-weight: 700;
  fill: var(--text-primary);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.preview-empty-text {
  font-size: 10px;
  fill: var(--text-tertiary);
  font-family: inherit;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.preview-empty-icon {
  width: 24px;
  height: 24px;
  color: var(--text-tertiary);
  opacity: 0.4;
}
</style>
