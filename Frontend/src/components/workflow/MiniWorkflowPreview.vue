<template>
  <div
    class="workflow-preview"
    :class="{ 'is-empty': !nodes || nodes.length === 0 }"
  >
    <svg
      v-if="nodes && nodes.length > 0"
      class="preview-svg"
      :viewBox="`0 0 ${viewWidth} ${viewHeight}`"
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <pattern
          :id="gridPatternId"
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
        :fill="`url(#${gridPatternId})`"
        class="preview-grid-rect"
      />

      <g class="preview-edges">
        <polyline
          v-for="edge in renderedEdges"
          :key="edge.id"
          :points="edge.points"
          class="preview-edge"
        />
      </g>

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
    default: () => [],
  },
  edges: {
    type: Array,
    default: () => [],
  },
})

const gridPatternId = `preview-grid-${Math.random().toString(36).slice(2, 9)}`

const NODE_W = 36
const NODE_H = 18
const VW = 220
const VH = 100
const PAD = 12
const H_GAP = 40
const V_GAP = 30
const COLS = 4

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
  website_generator: 'WG', backend_setup: 'BE', frontend_setup: 'FE', ui_beautify: 'UI', site_code_review: 'CR',
  environment_provision: 'EP', site_qa: 'QA', site_preview: 'PV', project_agent: 'PA',
  image_editing: 'IE', subtitle_generation: 'SG',
  reranker: 'RR',
}

function getNodeStyle(type) {
  return TYPE_COLORS[type] || DEFAULT_COLOR
}

function getShortLabel(type) {
  return TYPE_LABELS[type] || type?.charAt(0)?.toUpperCase() || '?'
}

function hasRealPositions(nodeList) {
  return nodeList.some((n) => {
    const x = Number(n.position?.x)
    const y = Number(n.position?.y)
    return Number.isFinite(x) && Number.isFinite(y) && (x !== 0 || y !== 0)
  })
}

const layout = computed(() => {
  const ns = (props.nodes || []).slice(0, 30)
  if (!ns.length) {
    return { viewWidth: VW, viewHeight: VH, nodes: [], edges: [] }
  }

  if (hasRealPositions(ns)) {
    const positions = ns.map((n) => ({
      x: Number(n.position?.x) || 0,
      y: Number(n.position?.y) || 0,
    }))
    const minX = Math.min(...positions.map((p) => p.x))
    const minY = Math.min(...positions.map((p) => p.y))
    const maxX = Math.max(...positions.map((p) => p.x))
    const maxY = Math.max(...positions.map((p) => p.y))
    const contentW = Math.max(maxX - minX + NODE_W + PAD * 2, 80)
    const contentH = Math.max(maxY - minY + NODE_H + PAD * 2, 48)
    const scale = Math.min(VW / contentW, VH / contentH, 1.5)

    const nodeMap = {}
    const renderedNodes = ns.map((n) => {
      const style = getNodeStyle(n.type)
      const cx = Math.round(((Number(n.position?.x) || 0) - minX + PAD) * scale)
      const cy = Math.round(((Number(n.position?.y) || 0) - minY + PAD) * scale)
      nodeMap[String(n.id)] = { cx, cy }
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

    const renderedEdges = (props.edges || [])
      .map((edge, index) => {
        const source = nodeMap[String(edge.source)]
        const target = nodeMap[String(edge.target)]
        if (!source || !target) return null
        return {
          id: edge.id || `edge-${index}`,
          points: `${source.cx + NODE_W / 2},${source.cy + NODE_H / 2} ${target.cx + NODE_W / 2},${target.cy + NODE_H / 2}`,
        }
      })
      .filter(Boolean)

    return {
      viewWidth: VW,
      viewHeight: VH,
      nodes: renderedNodes,
      edges: renderedEdges,
    }
  }

  const renderedNodes = ns.map((n, i) => {
    const row = Math.floor(i / COLS)
    const col = i % COLS
    const style = getNodeStyle(n.type)
    return {
      id: n.id,
      cx: PAD + col * (NODE_W + H_GAP),
      cy: PAD + row * (NODE_H + V_GAP),
      type: n.type,
      shortLabel: getShortLabel(n.type),
      color: style.color,
      bgColor: style.bg,
    }
  })

  const renderedEdges = []
  for (let i = 0; i < renderedNodes.length - 1; i += 1) {
    const a = renderedNodes[i]
    const b = renderedNodes[i + 1]
    renderedEdges.push({
      id: `e-${i}`,
      points: `${a.cx + NODE_W},${a.cy + NODE_H / 2} ${b.cx},${b.cy + NODE_H / 2}`,
    })
  }

  return {
    viewWidth: VW,
    viewHeight: VH,
    nodes: renderedNodes,
    edges: renderedEdges,
  }
})

const viewWidth = computed(() => layout.value.viewWidth)
const viewHeight = computed(() => layout.value.viewHeight)
const renderedNodes = computed(() => layout.value.nodes)
const renderedEdges = computed(() => layout.value.edges)
</script>

<style lang="scss" scoped>
.workflow-preview {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--canvas-bg, var(--bg-tertiary));
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
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
  fill: none;
  opacity: 0.55;
}

.preview-node-label {
  font-size: 8px;
  font-weight: 700;
  fill: var(--text-primary);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
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
