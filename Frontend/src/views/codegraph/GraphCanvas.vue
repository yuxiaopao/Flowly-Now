<template>
  <div
    class="graph-canvas-wrapper"
    :aria-busy="loading || engineLoading"
  >
    <div class="canvas-controls">
      <div class="control-group glass">
        <el-radio-group
          v-model="currentLayoutType"
          size="small"
          @change="handleLayoutChange"
        >
          <el-radio-button
            v-for="item in CODE_GRAPH.layouts"
            :key="item.value"
            :value="item.value"
          >
            {{ item.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="control-group glass">
        <el-button
          size="small"
          text
          :icon="Maximize"
          title="适应画布"
          aria-label="适应画布"
          @click="handleFitView"
        />
        <el-button
          size="small"
          text
          :icon="ZoomIn"
          title="放大"
          aria-label="放大"
          @click="handleZoomIn"
        />
        <el-button
          size="small"
          text
          :icon="ZoomOut"
          title="缩小"
          aria-label="缩小"
          @click="handleZoomOut"
        />
        <el-button
          v-if="currentLayoutType === '3d'"
          size="small"
          text
          :icon="RotateCw"
          title="自动环绕"
          aria-label="自动环绕"
          :aria-pressed="autoOrbit"
          :class="{ active: autoOrbit }"
          @click="toggleOrbit"
        />
        <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
      </div>
    </div>

    <div
      ref="chartContainer"
      class="chart-container"
      :class="{ 'mode-3d': currentLayoutType === '3d', 'mode-2d': currentLayoutType !== '3d' }"
    >
      <div
        class="depth-atmosphere"
        aria-hidden="true"
      />

      <div
        v-if="loading || engineLoading"
        class="loading-overlay"
        role="status"
      >
        <div class="loading-orb" />
        <span>{{ engineLoading ? '初始化三维引擎...' : '加载图数据...' }}</span>
      </div>

      <div
        v-else-if="!nodes.length"
        class="empty-state"
      >
        <el-empty :description="emptyDescription">
          <el-button
            type="primary"
            class="cg-btn-glow"
            :disabled="!canRefresh"
            @click="$emit('refresh')"
          >
            {{ emptyAction }}
          </el-button>
        </el-empty>
      </div>

      <!-- 3D WebGL canvas host -->
      <div
        v-show="currentLayoutType === '3d' && nodes.length > 0"
        ref="graph3dRef"
        class="graph-3d-host"
      />

      <!-- 2D / perspective SVG -->
      <div
        v-show="currentLayoutType !== '3d' && nodes.length > 0"
        class="svg-stage"
      >
        <svg
          ref="svgRef"
          class="graph-svg"
        >
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="7"
              refX="20"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="rgba(148,163,184,0.7)"
              />
            </marker>
            <marker
              id="arrowhead-selected"
              markerWidth="10"
              markerHeight="7"
              refX="20"
              refY="3.5"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3.5, 0 7"
                fill="#22d3ee"
              />
            </marker>
            <linearGradient
              id="cg-edge-grad"
              x1="0%"
              y1="0%"
              x2="100%"
              y2="0%"
            >
              <stop
                offset="0%"
                stop-color="#22d3ee"
                stop-opacity="0.15"
              />
              <stop
                offset="50%"
                stop-color="#2dd4bf"
                stop-opacity="0.85"
              />
              <stop
                offset="100%"
                stop-color="#38bdf8"
                stop-opacity="0.15"
              />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div
        v-if="tooltip.visible"
        class="node-tooltip"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
      >
        <div class="tip-name">
          {{ tooltip.name }}
        </div>
        <div class="tip-meta">
          {{ tooltip.meta }}
        </div>
      </div>
    </div>

    <div
      v-if="currentLayoutType !== '3d'"
      class="minimap glass"
    >
      <svg
        ref="minimapSvg"
        class="minimap-svg"
      />
    </div>

    <div
      class="graph-summary"
      aria-live="polite"
    >
      <span>{{ fileGraphNodes.length }} 文件 · {{ renderedEdges.length }} / {{ fileGraphEdges.length }} 依赖</span>
      <el-checkbox
        v-if="fileGraphEdges.length > CODE_GRAPH.overviewEdgeLimit"
        v-model="showAllEdges"
        size="small"
      >
        全部连线
      </el-checkbox>
      <span class="graph-help">{{ currentLayoutType === '3d' ? '拖动旋转 · 滚轮缩放' : '拖动画布 · 点击定位文件' }}</span>
    </div>
  </div>
</template>

<script setup>
/**
 * GraphCanvas — CodeGraph visualization
 * Modes: 3D (WebGL force) + enhanced 2D (force / tree / dagre) with glow & depth
 */

import { ref, watch, onMounted, onUnmounted, nextTick, computed } from 'vue'
import * as d3 from 'd3'
import dagre from 'dagre'
import { Maximize, ZoomIn, ZoomOut, RotateCw } from 'lucide-vue-next'
import { getTypeColor, hexToRgba } from './graphColors'
import { CODE_GRAPH } from '@/config/codeGraph'
import { drawEdges, fileNodes } from '@/utils/codeGraph'

const props = defineProps({
  nodes: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
  selectedNode: { type: Object, default: null },
  layout: { type: String, default: CODE_GRAPH.defaultLayout },
  loading: { type: Boolean, default: false },
  emptyDescription: { type: String, default: CODE_GRAPH.messages.empty },
  emptyAction: { type: String, default: CODE_GRAPH.messages.retry },
  canRefresh: { type: Boolean, default: true },
})

const emit = defineEmits(['node-click', 'node-hover', 'zoom-change', 'refresh', 'layout-change'])

const chartContainer = ref(null)
const svgRef = ref(null)
const graph3dRef = ref(null)
const minimapSvg = ref(null)

const width = ref(800)
const height = ref(600)
const zoom = ref(1)
const hoveredNodeId = ref(null)
const currentLayoutType = ref(props.layout || CODE_GRAPH.defaultLayout)
const engineLoading = ref(false)
const autoOrbit = ref(!window.matchMedia('(prefers-reduced-motion: reduce)').matches)
const tooltip = ref({ visible: false, x: 0, y: 0, name: '', meta: '' })

const showAllEdges = ref(false)
const fileGraphNodes = computed(() => fileNodes(props.nodes))
const fileGraphEdges = computed(() => {
  const ids = new Set(fileGraphNodes.value.map(node => node.id))
  return props.edges.filter(edge => ids.has(edgeSource(edge)) && ids.has(edgeTarget(edge)))
})
const renderedEdges = computed(() => drawEdges(fileGraphNodes.value, fileGraphEdges.value, props.selectedNode?.id, showAllEdges.value))

let simulation = null
let svg = null
let mainGroup = null
let zoomBehavior = null
let graph3d = null
let THREE = null
let resizeObserver = null
let renderRaf = null
let neighborMap = null
let graphBuilt = false
let edgePathSel = null
let nodeGroupSel = null
let layoutLock = false
let pendingLayout = null
let disposed = false
let init3dToken = 0
let sceneEvents = null
let fitCameraDistance = 1
const initTimers = new Set()
let renderWakeTimer = null
let renderPaused = false
let controlsInteracting = false
let sharedSphereGeo = null
let softGlowTexture = null
let hoverPaintRaf = null
let pendingHoverNode = undefined // undefined = no pending; null = clear
/** Immediate click selection before parent Pinia catches up */
let pendingSelectedId = null
let glowPulsePhase = 0

function wake3dRender(holdMs = 12000) {
  if (!graph3d) return
  if (renderPaused) {
    try { graph3d.resumeAnimation() } catch { /* ignore */ }
    renderPaused = false
  }
  if (renderWakeTimer) clearTimeout(renderWakeTimer)
  // Keep rendering while orbiting/dragging; only soft-pause after long idle
  renderWakeTimer = setTimeout(() => {
    if (!graph3d || autoOrbit.value || controlsInteracting) return
    try { graph3d.pauseAnimation() } catch { /* ignore */ }
    renderPaused = true
  }, holdMs)
}

const nodePositionMap = new Map()
const highlightNeighbors = new Set()
const highlightLinks = new Set()

function getVisibleNodes() {
  return { fileNodes: fileGraphNodes.value }
}

function edgeSource(edge) {
  return typeof edge.source === 'object' ? edge.source.id : edge.source
}

function edgeTarget(edge) {
  return typeof edge.target === 'object' ? edge.target.id : edge.target
}

function getNodeRadius(node) {
  const base = node.type === 'function' ? 6 : 9
  const centralityBonus = (node.centrality || 0) * 22
  return Math.min(base + centralityBonus, 26)
}

function getNodeColor(node) {
  return getTypeColor(node.type)
}

function isEdgeHighlighted(edge) {
  const sid = edgeSource(edge)
  const tid = edgeTarget(edge)
  if (highlightLinks.size && highlightLinks.has(edge)) return true
  const activeId = hoveredNodeId.value || props.selectedNode?.id
  if (!activeId) return false
  return sid === activeId || tid === activeId
}

function getEdgePath(edge) {
  // Straight lines are far cheaper than arcs on every force tick
  return getStraightEdgePath(edge)
}

function getStraightEdgePath(edge) {
  const sourcePos = nodePositionMap.get(edgeSource(edge))
  const targetPos = nodePositionMap.get(edgeTarget(edge))
  if (!sourcePos || !targetPos) return ''
  return `M${sourcePos.x},${sourcePos.y} L${targetPos.x},${targetPos.y}`
}

function buildNeighborIndex(nodes, edges) {
  const map = new Map(nodes.map(n => [n.id, { ...n, neighbors: [], links: [] }]))
  edges.forEach(edge => {
    const s = map.get(edgeSource(edge))
    const t = map.get(edgeTarget(edge))
    if (!s || !t) return
    s.neighbors.push(t)
    t.neighbors.push(s)
    s.links.push(edge)
    t.links.push(edge)
  })
  return map
}

// ==================== 3D Engine ====================

async function loadForceGraph3D() {
  try {
    const threeMod = await import('three')
    THREE = threeMod
    // three-forcegraph prefers window.THREE when present
    if (typeof window !== 'undefined') {
      window.THREE = threeMod
    }
    const mod = await import('3d-force-graph')
    return mod.default || mod
  } catch (err) {
    // The bundled 2D engine remains available without an external network dependency.
    console.warn('Local 3D engine unavailable:', err)
    throw err
  }
}

function toGraphData() {
  const { fileNodes } = getVisibleNodes()
  const nCount = fileNodes.length
  // Compact seed sphere — keeps camera close so nodes stay readable
  const nodes = fileNodes.map((n, i) => {
    const phi = Math.acos(1 - (2 * (i + 0.5)) / Math.max(nCount, 1))
    const theta = Math.PI * (1 + Math.sqrt(5)) * i
    const r = 36 + Math.min(nCount, 400) * 0.22
    return {
      id: n.id,
      name: n.name,
      type: n.type,
      path: n.path,
      module: n.module,
      centrality: n.centrality || 0,
      indegree: n.indegree || 0,
      outdegree: n.outdegree || 0,
      val: Math.max(2, 2.5 + (n.centrality || 0) * 10 + Math.min((n.indegree || 0) + (n.outdegree || 0), 12) * 0.2),
      // Stretch Y/Z so the cloud has volume (avoids flat "pancake" look)
      x: r * Math.sin(phi) * Math.cos(theta),
      y: r * Math.sin(phi) * Math.sin(theta) * 1.15,
      z: r * Math.cos(phi) * 1.25,
    }
  })
  const links = renderedEdges.value
    .map(e => ({
      source: edgeSource(e),
      target: edgeTarget(e),
      type: e.type,
    }))
  return { nodes, links }
}

function getSharedSphereGeo() {
  if (!sharedSphereGeo && THREE) {
    // Enough segments for clear spherical shading (3D cue)
    sharedSphereGeo = new THREE.SphereGeometry(1, 20, 20)
  }
  return sharedSphereGeo
}

/** Soft radial sprite texture — natural nebula bloom (no hard sphere halo) */
function getSoftGlowTexture() {
  if (softGlowTexture || !THREE) return softGlowTexture
  const size = 128
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  g.addColorStop(0, 'rgba(255,255,255,0.95)')
  g.addColorStop(0.2, 'rgba(255,255,255,0.55)')
  g.addColorStop(0.45, 'rgba(255,255,255,0.18)')
  g.addColorStop(0.72, 'rgba(255,255,255,0.04)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, size, size)
  softGlowTexture = new THREE.CanvasTexture(canvas)
  softGlowTexture.needsUpdate = true
  return softGlowTexture
}

function getActiveSelectedId() {
  return props.selectedNode?.id || pendingSelectedId || null
}

function addStarfield(scene) {
  if (!THREE || !scene || scene.userData.__cgStars) return
  const count = 320
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i += 1) {
    const r = 260 + Math.random() * 620
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.7
    positions[i * 3 + 2] = r * Math.cos(phi)
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  const mat = new THREE.PointsMaterial({
    color: 0xe2e8f0,
    size: 2.2,
    transparent: true,
    opacity: 0.65,
    depthWrite: false,
    sizeAttenuation: true,
  })
  const stars = new THREE.Points(geo, mat)
  stars.name = 'cg-starfield'
  scene.add(stars)
  scene.userData.__cgStars = stars
}

/**
 * Phong core only by default.
 * Soft additive sprite glow stays hidden until the node is clicked/selected.
 */
function createNebulaNode(node) {
  const hex = getNodeColor(node)
  const color = new THREE.Color(hex)
  const group = new THREE.Group()

  // Soft nebula bloom — opacity 0 until selected (click only)
  const glowMat = new THREE.SpriteMaterial({
    map: getSoftGlowTexture(),
    color,
    transparent: true,
    opacity: 0,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  })
  const glow = new THREE.Sprite(glowMat)
  glow.scale.set(4.8, 4.8, 1)
  glow.name = 'glow'
  glow.visible = false

  // Matte-lit core: almost no emissive so the cloud doesn't look self-glowing
  const coreMat = new THREE.MeshPhongMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.05,
    specular: new THREE.Color(0xdbeafe),
    shininess: 48,
    transparent: true,
    opacity: 1,
  })
  const core = new THREE.Mesh(getSharedSphereGeo(), coreMat)
  core.name = 'core'

  group.add(glow, core)
  const s = 6.8 + (node.val || 2) * 2.1
  group.scale.setScalar(s)
  group.userData.nodeId = node.id
  group.userData.baseColor = hex
  group.userData.baseScale = s
  group.userData.glowBase = 4.8
  return group
}

/**
 * @param {'idle'|'selected'|'neighbor'|'dim'} state
 */
function paintNodeGroup(obj, hex, opacity, scale, state = 'idle') {
  if (!obj) return
  obj.scale.setScalar(scale)
  const glow = obj.children?.find?.(c => c.name === 'glow')
  const core = obj.children?.find?.(c => c.name === 'core')

  if (core?.material) {
    const mat = core.material
    mat.color?.set(hex)
    if (mat.emissive) {
      mat.emissive.set(hex)
      // Only the selected node gets a gentle self-light; others stay sculpted by scene lights
      mat.emissiveIntensity = state === 'selected' ? 0.28 : state === 'neighbor' ? 0.08 : 0.05
    }
    if ('opacity' in mat) mat.opacity = opacity
  }

  if (glow?.material) {
    const gmat = glow.material
    gmat.color?.set(hex)
    if (state === 'selected') {
      glow.visible = true
      gmat.opacity = 0.72
      const gb = obj.userData.glowBase || 4.8
      glow.scale.set(gb * 1.15, gb * 1.15, 1)
    } else {
      glow.visible = false
      gmat.opacity = 0
    }
  }
}

/** Glow + neighbor dimming ONLY for the clicked/selected node — never on hover */
function paintNebulaHighlight() {
  if (!graph3d) return
  wake3dRender(12000)
  const selectedId = getActiveSelectedId()
  const nodes = graph3d.graphData()?.nodes || []

  for (const n of nodes) {
    const obj = n.__threeObj
    if (!obj) continue
    const base = obj.userData.baseColor || getNodeColor(n)
    const baseScale = obj.userData.baseScale || 6
    if (!selectedId) {
      paintNodeGroup(obj, base, 0.98, baseScale, 'idle')
    } else if (n.id === selectedId) {
      // Keep type color — soft cyan wash via glow sprite, not a hard recolor
      paintNodeGroup(obj, base, 1, baseScale * 1.28, 'selected')
    } else if (highlightNeighbors.has(n.id)) {
      paintNodeGroup(obj, base, 0.92, baseScale * 1.06, 'neighbor')
    } else {
      paintNodeGroup(obj, base, 0.38, baseScale * 0.9, 'dim')
    }
  }

  const links = graph3d.graphData()?.links || []
  for (const l of links) {
    const line = l.__lineObj
    const mat = line?.material
    if (!mat) continue
    const hot = selectedId && highlightLinks.has(l)
    if (mat.color) mat.color.set(hot ? '#67e8f9' : '#94a3b8')
    if ('opacity' in mat) mat.opacity = hot ? 0.95 : (selectedId ? 0.1 : 0.42)
  }

  try {
    graph3d
      .linkDirectionalParticles(l => (selectedId && highlightLinks.has(l) ? 5 : 1))
      .linkDirectionalParticleWidth(l => (selectedId && highlightLinks.has(l) ? 2.4 : 1.2))
      .linkWidth(l => (selectedId && highlightLinks.has(l) ? 2 : 0.65))
  } catch {
    /* ignore */
  }
}

function pulseSelectedGlow() {
  if (!graph3d) return
  const selectedId = getActiveSelectedId()
  if (!selectedId) return
  glowPulsePhase += 0.035
  const node = graph3d.graphData()?.nodes?.find(n => n.id === selectedId)
  const glow = node?.__threeObj?.children?.find?.(c => c.name === 'glow')
  if (!glow?.material) return
  const gb = node.__threeObj.userData.glowBase || 4.8
  const breathe = 1 + Math.sin(glowPulsePhase) * 0.08
  glow.scale.set(gb * 1.15 * breathe, gb * 1.15 * breathe, 1)
  glow.material.opacity = 0.62 + Math.sin(glowPulsePhase) * 0.1
}

/** Hover only tracks id for labels — never enables glow */
function scheduleHoverPaint(node) {
  pendingHoverNode = node
  if (hoverPaintRaf) return
  hoverPaintRaf = requestAnimationFrame(() => {
    hoverPaintRaf = null
    const node = pendingHoverNode
    pendingHoverNode = undefined
    const nextId = node?.id || null
    if (nextId === hoveredNodeId.value) return
    hoveredNodeId.value = nextId
    // Intentionally no paintNebulaHighlight() — glow is click/select only
  })
}

async function init3dGraph() {
  if (!graph3dRef.value || !props.nodes.length) return

  const token = ++init3dToken
  engineLoading.value = true
  try {
    const ForceGraph3D = await loadForceGraph3D()
    if (token !== init3dToken || disposed || currentLayoutType.value !== '3d') return
    destroy3dGraph()

    const data = toGraphData()
    neighborMap = buildNeighborIndex(data.nodes, data.links)
    const largeGraph = data.nodes.length > 160 || data.links.length > 220
    let didFit = false

    graph3d = ForceGraph3D({
      controlType: 'orbit',
      rendererConfig: {
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
        preserveDrawingBuffer: true,
      },
    })(graph3dRef.value)
      .backgroundColor('#1e2a3a')
      .showNavInfo(false)
      .nodeLabel(n => {
        const label = document.createElement('div')
        label.textContent = `${n.name}\n${n.path || n.module || ''}`
        label.style.whiteSpace = 'pre-line'
        return label
      })
      .nodeVal(n => n.val)
      .nodeRelSize(8)
      .nodeOpacity(0.96)
      .nodeColor(n => getNodeColor(n))
      // Custom Phong spheres for volume + specular highlight (true 3D read)
      .nodeThreeObject((n) => {
        try {
          return createNebulaNode(n)
        } catch (err) {
          console.warn('createNebulaNode failed', err)
          return undefined
        }
      })
      .nodeThreeObjectExtend(false)
      .linkColor(() => '#cbd5e1')
      .linkOpacity(0.62)
      .linkWidth(1.15)
      .linkDirectionalParticles(1)
      .linkDirectionalParticleWidth(1.2)
      .linkDirectionalParticleSpeed(0.006)
      .linkDirectionalParticleColor(() => '#67e8f9')
      .warmupTicks(largeGraph ? 18 : 32)
      .cooldownTicks(largeGraph ? 55 : 90)
      .cooldownTime(largeGraph ? 2400 : 3600)
      .d3AlphaDecay(largeGraph ? 0.05 : 0.026)
      .d3VelocityDecay(0.3)
      .enableNodeDrag(true)
      .enablePointerInteraction(true)
      .onNodeClick((node) => {
        wake3dRender(20000)
        const full = props.nodes.find(n => n.id === node.id) || node
        // Click-only glow: set pending selection before parent Pinia updates
        pendingSelectedId = node.id
        glowPulsePhase = 0
        highlightNeighbors.clear()
        highlightLinks.clear()
        const nb = neighborMap?.get(node.id)
        highlightNeighbors.add(node.id)
        nb?.neighbors?.forEach(n => highlightNeighbors.add(n.id))
        nb?.links?.forEach(l => highlightLinks.add(l))
        paintNebulaHighlight()
        emit('node-click', full)
      })
      .onNodeDrag(() => {
        wake3dRender(15000)
      })
      .onNodeDragEnd(() => {
        try { graph3d.d3AlphaTarget(0) } catch { /* ignore */ }
        wake3dRender(10000)
      })
      .onNodeHover((node) => {
        wake3dRender(4000)
        // Hover must NOT enable glow — only track id
        scheduleHoverPaint(node)
      })
      .onBackgroundClick(() => {
        pendingSelectedId = null
        highlightNeighbors.clear()
        highlightLinks.clear()
        scheduleHoverPaint(null)
        paintNebulaHighlight()
        emit('node-click', null)
      })
      .onEngineTick(() => {
        if (!didFit) wake3dRender(1200)
        if (getActiveSelectedId()) pulseSelectedGlow()
      })
      .onEngineStop(() => {
        if (!didFit && graph3d) {
          didFit = true
          ensureVolumeDepth()
          if (props.selectedNode) focusNode(props.selectedNode)
          else applyCinematicCamera(1100)
          zoom.value = 1
        }
        wake3dRender(autoOrbit.value ? 180_000 : 20000)
      })
      .graphData(data)

    try {
      const charge = graph3d.d3Force('charge')
      if (charge?.strength) {
        charge.strength(largeGraph ? -100 : -140)
        if (charge.distanceMax) charge.distanceMax(largeGraph ? 480 : 620)
      }
      const linkForce = graph3d.d3Force('link')
      if (linkForce?.distance) {
        linkForce.distance(largeGraph ? 56 : 72).strength(0.35)
      }
    } catch {
      /* optional */
    }

    const el = graph3dRef.value
    graph3d.width(el.clientWidth).height(el.clientHeight)

    try {
      const renderer = graph3d.renderer?.()
      if (renderer) {
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5))
        renderer.setClearColor(0x1e2a3a, 1)
        if (renderer.outputColorSpace !== undefined && THREE?.SRGBColorSpace) {
          renderer.outputColorSpace = THREE.SRGBColorSpace
        }
      }
      const camera = graph3d.camera?.()
      if (camera) {
        camera.fov = 50
        camera.near = 0.5
        camera.far = 5000
        camera.updateProjectionMatrix?.()
      }
      const controls = graph3d.controls?.()
      if (controls) {
        controls.enableDamping = true
        controls.dampingFactor = 0.08
        controls.rotateSpeed = 0.65
        controls.zoomSpeed = 1.05
        controls.panSpeed = 0.8
        controls.autoRotate = !!autoOrbit.value
        controls.autoRotateSpeed = 0.85
        controls.minDistance = 30
        controls.maxDistance = 1800
        controls.addEventListener('start', () => {
          controlsInteracting = true
          wake3dRender(20000)
        })
        controls.addEventListener('end', () => {
          controlsInteracting = false
          wake3dRender(12000)
        })
        controls.addEventListener('change', () => {
          const distance = graph3d?.camera()?.position.distanceTo(controls.target)
          if (distance) zoom.value = Math.round(fitCameraDistance / distance * 100) / 100
        })
      }
      const scene = graph3d.scene()
      scene.fog = null
      const lights = scene.children.filter(o => o.isLight)
      lights.forEach(l => scene.remove(l))
      // Strong key from one side → clear sphere terminator (3D cue)
      const amb = new THREE.AmbientLight(0x9aabbe, 0.42)
      const key = new THREE.DirectionalLight(0xffffff, 1.75)
      key.position.set(320, 260, 120)
      const fill = new THREE.DirectionalLight(0x7dd3fc, 0.45)
      fill.position.set(-280, -40, -160)
      const rim = new THREE.PointLight(0xe9d5ff, 1.05, 1200)
      rim.position.set(-40, 180, 280)
      scene.add(amb, key, fill, rim)
      if (controls) controls.autoRotateSpeed = autoOrbit.value ? 1.15 : 0.4
      addStarfield(scene)
      sceneEvents = new AbortController()
      el.addEventListener('pointerdown', () => wake3dRender(15000), { signal: sceneEvents.signal })
      el.addEventListener('wheel', () => wake3dRender(10000), { passive: true, signal: sceneEvents.signal })
      el.addEventListener('pointermove', () => {
        if (renderPaused) wake3dRender(8000)
      }, { passive: true, signal: sceneEvents.signal })
    } catch (err) {
      console.warn('3D scene polish failed', err)
    }

    zoom.value = 1
    renderPaused = false
    try { graph3d.resumeAnimation() } catch { /* ignore */ }
    if (autoOrbit.value) startOrbit()
    // Ensure first frames paint even if pause helpers mis-fire
    wake3dRender(180_000)
    // Default: all node glows off until a click selection
    const scheduleInitialFrame = (callback, delay) => {
      const timer = setTimeout(() => {
        initTimers.delete(timer)
        if (token === init3dToken && graph3d && !disposed) callback()
      }, delay)
      initTimers.add(timer)
    }
    scheduleInitialFrame(() => {
      try {
        paintNebulaHighlight()
      } catch { /* ignore */ }
    }, 80)
    scheduleInitialFrame(() => {
      try {
        graph3d?.resumeAnimation?.()
        if (props.selectedNode) refresh3dSelection()
        else applyCinematicCamera(800)
        paintNebulaHighlight()
      } catch { /* ignore */ }
    }, 600)
  } catch (err) {
    if (token !== init3dToken || disposed) return
    console.error('Failed to init 3D graph, falling back to force layout', err)
    destroy3dGraph()
    currentLayoutType.value = 'force'
    emit('layout-change', 'force')
    await nextTick()
    initSvg()
    applyForceLayout()
  } finally {
    if (token === init3dToken) engineLoading.value = false
  }
}

function destroy3dGraph() {
  stopOrbit()
  sceneEvents?.abort()
  sceneEvents = null
  for (const timer of initTimers) clearTimeout(timer)
  initTimers.clear()
  if (hoverPaintRaf) {
    cancelAnimationFrame(hoverPaintRaf)
    hoverPaintRaf = null
  }
  pendingHoverNode = undefined
  if (renderWakeTimer) {
    clearTimeout(renderWakeTimer)
    renderWakeTimer = null
  }
  renderPaused = false
  controlsInteracting = false
  if (graph3d) {
    try {
      const geometries = new Set()
      const materials = new Set()
      graph3d.scene()?.traverse(object => {
        if (object.geometry) geometries.add(object.geometry)
        const items = Array.isArray(object.material) ? object.material : [object.material]
        items.filter(Boolean).forEach(material => materials.add(material))
      })
      graph3d._destructor?.()
      geometries.forEach(geometry => geometry.dispose())
      materials.forEach(material => material.dispose())
      graph3d.renderer()?.dispose()
    } catch {
      /* ignore */
    }
    if (graph3dRef.value) {
      graph3dRef.value.innerHTML = ''
    }
    graph3d = null
  }
  // Recreate geometry next init (allows LOD/segment upgrades after HMR)
  if (sharedSphereGeo) {
    sharedSphereGeo.dispose?.()
    sharedSphereGeo = null
  }
  if (softGlowTexture) {
    softGlowTexture.dispose?.()
    softGlowTexture = null
  }
  pendingSelectedId = null
  glowPulsePhase = 0
}

/** If the sim collapsed into a pancake, reinflate Z so orbit shows parallax */
function ensureVolumeDepth() {
  if (!graph3d) return
  const nodes = graph3d.graphData()?.nodes || []
  if (nodes.length < 8) return
  let cz = 0
  let n = 0
  let maxXY = 1
  for (const node of nodes) {
    if (node.x == null) continue
    cz += node.z || 0
    n += 1
    maxXY = Math.max(maxXY, Math.hypot(node.x, node.y))
  }
  if (!n) return
  cz /= n
  let zVar = 0
  for (const node of nodes) {
    if (node.x == null) continue
    const dz = (node.z || 0) - cz
    zVar += dz * dz
  }
  zVar = Math.sqrt(zVar / n)
  // Too flat relative to XY spread — push nodes off the plane
  if (zVar < maxXY * 0.18) {
    const amp = maxXY * 0.42
    nodes.forEach((node, i) => {
      if (node.x == null) return
      const t = (i / nodes.length) * Math.PI * 2
      node.z = cz + Math.sin(t * 1.7) * amp * (0.55 + (i % 5) * 0.1)
    })
  }
}

/** Place camera on a clear 3/4 angle — zoomToFit alone looks like a flat diagram */
function applyCinematicCamera(durationMs = 900) {
  if (!graph3d) return
  const nodes = graph3d.graphData()?.nodes || []
  if (!nodes.length) return
  let cx = 0
  let cy = 0
  let cz = 0
  let count = 0
  let maxR = 80
  for (const n of nodes) {
    if (n.x == null) continue
    cx += n.x
    cy += n.y
    cz += n.z
    count += 1
  }
  if (!count) return
  cx /= count
  cy /= count
  cz /= count
  for (const n of nodes) {
    if (n.x == null) continue
    const dx = n.x - cx
    const dy = n.y - cy
    const dz = n.z - cz
    maxR = Math.max(maxR, Math.sqrt(dx * dx + dy * dy + dz * dz))
  }
  const camera = graph3d.camera()
  const verticalFov = camera.fov * Math.PI / 180
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
  const dist = (maxR + 30) / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.1
  const direction = new THREE.Vector3(1.05, 0.78, 0.72).normalize().multiplyScalar(dist)
  fitCameraDistance = dist
  const controls = graph3d.controls()
  controls.maxDistance = Math.max(controls.maxDistance, dist * 3)
  camera.far = Math.max(camera.far, dist + maxR * 4)
  camera.updateProjectionMatrix()
  // High elevation + side angle — classic “isometric nebula” read
  graph3d.cameraPosition(
    {
      x: cx + direction.x,
      y: cy + direction.y,
      z: cz + direction.z,
    },
    { x: cx, y: cy, z: cz },
    durationMs
  )
  wake3dRender(Math.max(durationMs + 2000, 12000))
}

function startOrbit() {
  autoOrbit.value = true
  const controls = graph3d?.controls?.()
  if (controls) {
    controls.autoRotate = true
    controls.autoRotateSpeed = 1.15
  }
  wake3dRender(180_000)
}

function stopOrbit() {
  const controls = graph3d?.controls?.()
  if (controls) controls.autoRotate = false
}

function toggleOrbit() {
  autoOrbit.value = !autoOrbit.value
  if (autoOrbit.value) startOrbit()
  else {
    stopOrbit()
    wake3dRender(1200)
  }
}

function focusNode(nodeOrId) {
  if (!nodeOrId) return
  const id = typeof nodeOrId === 'string' ? nodeOrId : nodeOrId.id
  if (currentLayoutType.value !== '3d') {
    const position = nodePositionMap.get(id)
    if (!position || !svg || !zoomBehavior) return
    const scale = Math.max(zoom.value, CODE_GRAPH.zoom.focus)
    svg.transition().duration(CODE_GRAPH.zoom.durationMs).call(zoomBehavior.transform,
      d3.zoomIdentity.translate(width.value / 2 - position.x * scale, height.value / 2 - position.y * scale).scale(scale))
    return
  }
  if (!graph3d) return
  const node = graph3d.graphData()?.nodes?.find(n => n.id === id)
  if (!node || node.x == null) return
  wake3dRender(20000)
  // Approach from an elevated angle so the sphere stays obviously 3D
  const dist = 110
  graph3d.cameraPosition(
    {
      x: (node.x || 0) + dist * 0.9,
      y: (node.y || 0) + dist * 0.55,
      z: (node.z || 0) + dist * 0.95,
    },
    node,
    750
  )
  // Keep slow orbit so depth keeps reading after focus
  const controls = graph3d.controls?.()
  if (controls && autoOrbit.value) {
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.4
  }
}

function refresh3dSelection() {
  if (!graph3d) return
  const data = graph3d.graphData()
  const links = renderedEdges.value.map(edge => ({ source: edgeSource(edge), target: edgeTarget(edge), type: edge.type }))
  graph3d.graphData({ nodes: data.nodes, links })
  neighborMap = buildNeighborIndex(data.nodes, links)
  // Parent selection is source of truth once it arrives
  pendingSelectedId = props.selectedNode?.id || null
  highlightNeighbors.clear()
  highlightLinks.clear()
  if (props.selectedNode) {
    const full = neighborMap?.get(props.selectedNode.id)
    highlightNeighbors.add(props.selectedNode.id)
    full?.neighbors?.forEach(n => highlightNeighbors.add(n.id))
    full?.links?.forEach(l => highlightLinks.add(l))
  }
  paintNebulaHighlight()
  if (props.selectedNode) focusNode(props.selectedNode)
}

// ==================== 2D layouts ====================

/** File nodes only — function nodes hang off files after layout */
function getLayoutFileNodes() {
  return fileGraphNodes.value
}

/** Clone edges with string endpoints so d3.forceLink never mutates store edges */
function getLayoutEdgePairs() {
  const fileNodes = getLayoutFileNodes()
  const ids = new Set(fileNodes.map(n => n.id))
  const pairs = []
  const seen = new Set()
  for (const edge of props.edges) {
    if (edge.type === 'function') continue
    const s = edgeSource(edge)
    const t = edgeTarget(edge)
    if (!ids.has(s) || !ids.has(t) || s === t) continue
    const key = `${s}->${t}`
    if (seen.has(key)) continue
    seen.add(key)
    pairs.push({ source: s, target: t, type: edge.type })
  }
  return pairs
}

/** Drop back-edges so tree/dagre can run on cyclic dependency graphs */
function getAcyclicEdgePairs(nodes, edges) {
  const idSet = new Set(nodes.map(n => n.id))
  const adj = new Map([...idSet].map(id => [id, []]))
  const result = []

  function canReach(from, to) {
    const stack = [from]
    const seen = new Set()
    while (stack.length) {
      const u = stack.pop()
      if (u === to) return true
      if (seen.has(u)) continue
      seen.add(u)
      for (const v of adj.get(u) || []) stack.push(v)
    }
    return false
  }

  for (const edge of edges) {
    const s = edge.source
    const t = edge.target
    if (!idSet.has(s) || !idSet.has(t) || s === t) continue
    // skip if t already reaches s (would form a cycle)
    if (canReach(t, s)) continue
    adj.get(s).push(t)
    result.push(edge)
  }
  return result
}

function applyForceLayout() {
  const fileNodes = getLayoutFileNodes()
  if (!fileNodes.length) return
  if (simulation) simulation.stop()

  const simNodes = fileNodes.map((n, i) => ({
    id: n.id,
    name: n.name,
    type: n.type,
    centrality: n.centrality || 0,
    x: Number.isFinite(n.x) ? n.x : width.value / 2 + Math.cos(i) * 80,
    y: Number.isFinite(n.y) ? n.y : height.value / 2 + Math.sin(i) * 80,
  }))
  const simEdges = getLayoutEdgePairs().map(e => ({ ...e }))

  const large = simNodes.length > 160
  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d => d.id).distance(large ? 70 : 90).strength(0.3))
    .force('charge', d3.forceManyBody()
      .strength(large ? -120 : -240)
      .distanceMax(large ? 320 : 600))
    .force('center', d3.forceCenter(width.value / 2, height.value / 2))
    .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + (large ? 4 : 8)))
    .alphaDecay(large ? 0.06 : 0.035)
    .velocityDecay(0.4)
    .on('tick', () => {
      for (const n of simNodes) nodePositionMap.set(n.id, { x: n.x, y: n.y })
      if (renderRaf) return
      renderRaf = requestAnimationFrame(() => {
        renderRaf = null
        if (!graphBuilt) buildGraphStructure()
        else updateGraphPositions()
      })
    })
    .on('end', () => {
      updateGraphPositions()
      updateMinimap()
      if (props.selectedNode) focusNode(props.selectedNode)
      else handleFitView()
    })
}

function applyTreeLayout() {
  const fileNodes = getLayoutFileNodes()
  if (!fileNodes.length) return
  if (simulation) { simulation.stop(); simulation = null }

  const nodeMap = new Map(fileNodes.map(n => [n.id, { id: n.id, name: n.name, children: [] }]))
  const acyclic = getAcyclicEdgePairs(fileNodes, getLayoutEdgePairs())

  const childOf = new Map() // child -> parent (first wins → spanning forest)
  for (const edge of acyclic) {
    if (childOf.has(edge.target)) continue
    const parent = nodeMap.get(edge.source)
    const child = nodeMap.get(edge.target)
    if (!parent || !child) continue
      parent.children.push(child)
    childOf.set(edge.target, edge.source)
  }

  const roots = fileNodes
    .filter(n => !childOf.has(n.id))
    .map(n => nodeMap.get(n.id))
    .filter(Boolean)

  if (!roots.length) {
    applyForceLayout()
    return
  }

  const forestRoot = { id: '__forest_root__', name: 'root', children: roots }
  let hierarchy
  try {
    hierarchy = d3.hierarchy(forestRoot)
  } catch (err) {
    console.warn('Tree hierarchy failed, falling back to force', err)
    applyForceLayout()
    return
  }

  const h = Math.max(height.value - 80, 400)
  const w = Math.max(width.value - 160, 400)
  d3.tree().size([h, w])(hierarchy)

  hierarchy.descendants().forEach((d) => {
    if (d.data.id === '__forest_root__') return
    nodePositionMap.set(d.data.id, {
      x: d.y + 80,
      y: d.x + 40,
    })
  })

  // Place any nodes missed by the forest
  fileNodes.forEach((n, i) => {
    if (!nodePositionMap.has(n.id)) {
      nodePositionMap.set(n.id, {
        x: 80 + (i % 10) * 40,
        y: 80 + Math.floor(i / 10) * 40,
      })
    }
  })

  renderGraph()
  nextTick(() => props.selectedNode ? focusNode(props.selectedNode) : handleFitView())
}

function applyDagreLayout() {
  const fileNodes = getLayoutFileNodes()
  if (!fileNodes.length) return
  if (simulation) { simulation.stop(); simulation = null }

  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: 'LR',
    nodesep: 36,
    ranksep: 64,
    marginx: 24,
    marginy: 24,
    edgesep: 16,
  })
  g.setDefaultEdgeLabel(() => ({}))

  fileNodes.forEach(node => {
    g.setNode(node.id, {
      label: node.name,
      width: Math.min(getNodeRadius(node) * 2 + 72, 140),
      height: Math.min(getNodeRadius(node) * 2 + 24, 40),
    })
  })

  const acyclic = getAcyclicEdgePairs(fileNodes, getLayoutEdgePairs())
  acyclic.forEach((edge) => {
    if (
      g.hasNode(edge.source)
      && g.hasNode(edge.target)
      && !g.hasEdge(edge.source, edge.target)
    ) {
      g.setEdge(edge.source, edge.target)
    }
  })

  try {
    dagre.layout(g)
  } catch (err) {
    console.warn('Dagre layout failed, falling back to force', err)
    applyForceLayout()
    return
  }

  let placed = 0
  g.nodes().forEach(nodeId => {
    const nodeData = g.node(nodeId)
    if (nodeData && Number.isFinite(nodeData.x) && Number.isFinite(nodeData.y)) {
      nodePositionMap.set(nodeId, { x: nodeData.x, y: nodeData.y })
      placed += 1
    }
  })

  // If dagre produced a collapsed layout, fall back
  if (placed < fileNodes.length * 0.5) {
    console.warn('Dagre placed too few nodes, falling back to force')
    applyForceLayout()
    return
  }

  renderGraph()
  nextTick(() => props.selectedNode ? focusNode(props.selectedNode) : handleFitView())
}

async function applyLayout(layoutType) {
  if (disposed) return
  currentLayoutType.value = layoutType
  pendingLayout = layoutType
  ++init3dToken
  if (layoutLock) return
  layoutLock = true
  try {
    // Serialize engine initialization and always process the newest pending request.
    while (pendingLayout && !disposed) {
      layoutType = pendingLayout
      pendingLayout = null
      graphBuilt = false
      edgePathSel = null
      nodeGroupSel = null
      if (simulation) { simulation.stop(); simulation = null }
      if (renderRaf) { cancelAnimationFrame(renderRaf); renderRaf = null }
      destroy3dGraph()
      engineLoading.value = false
      nodePositionMap.clear()
      mainGroup?.selectAll('*').remove()
      d3.select(minimapSvg.value).selectAll('*').remove()
      tooltip.value.visible = false
      await nextTick()
      if (pendingLayout || disposed || !props.nodes.length) continue
      if (layoutType === '3d') {
        await init3dGraph()
        continue
      }

      if (chartContainer.value) {
        width.value = chartContainer.value.clientWidth || 800
        height.value = chartContainer.value.clientHeight || 600
      }
      initSvg()
      switch (layoutType) {
        case 'tree':
          applyTreeLayout()
          break
        case 'dagre':
          applyDagreLayout()
          break
        default:
          applyForceLayout()
      }
      updateMinimap()
    }
  } finally {
    layoutLock = false
  }
}

function getDrawEdges2d() {
  return renderedEdges.value
}

function edgePathFor(d) {
  return currentLayoutType.value === 'force' ? getEdgePath(d) : getStraightEdgePath(d)
}

/** Full DOM build once per layout / data change */
function buildGraphStructure() {
  if (!svg || !mainGroup || currentLayoutType.value === '3d') return

  mainGroup.selectAll('*').remove()
  edgePathSel = null
  nodeGroupSel = null

  const { fileNodes } = getVisibleNodes()
  const visibleEdges = getDrawEdges2d()
  const showLabels = zoom.value >= 0.55 || fileNodes.length < 120

  const edgeGroup = mainGroup.append('g').attr('class', 'edges')
  edgePathSel = edgeGroup.selectAll('path.edge-path')
    .data(visibleEdges, d => `${edgeSource(d)}>${edgeTarget(d)}`)
    .enter()
    .append('path')
    .attr('class', d => `edge-path${d.type === 'function' ? ' func-edge' : ''}`)
    .attr('d', edgePathFor)

  const fileNodeGroup = mainGroup.append('g').attr('class', 'file-nodes')
  nodeGroupSel = fileNodeGroup.selectAll('g.node-group')
    .data(fileNodes, d => d.id)
    .enter()
    .append('g')
    .attr('class', 'node-group')
    .attr('data-id', d => d.id)
    .attr('role', 'button')
    .attr('tabindex', 0)
    .attr('aria-label', d => d.path || d.name)
    .attr('transform', d => {
      const pos = nodePositionMap.get(d.id)
      return `translate(${pos?.x || 0}, ${pos?.y || 0})`
    })
    .on('click', (event, d) => { event.stopPropagation(); emit('node-click', d) })
    .on('keydown', (event, d) => {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); emit('node-click', d) }
    })
    .on('mouseenter', (event, d) => {
      hoveredNodeId.value = d.id
      emit('node-hover', d)
      showTooltip(event, d)
      paintHighlight2d()
    })
    .on('mousemove', (event, d) => showTooltip(event, d))
    .on('mouseleave', () => {
      hoveredNodeId.value = null
      emit('node-hover', null)
      tooltip.value.visible = false
      paintHighlight2d()
    })

  nodeGroupSel.each(function (d) {
      const g = d3.select(this)
    const r = getNodeRadius(d)
    const color = getNodeColor(d)
    g.append('circle')
      .attr('class', 'node-halo')
      .attr('r', r * 1.7)
      .style('fill', hexToRgba(color, 0.14))
      g.append('circle')
        .attr('class', 'node-circle')
      .attr('r', r)
      .style('fill', hexToRgba(color, 0.42))
      .style('stroke', color)
    if (showLabels) {
      g.append('text')
        .attr('class', 'node-label')
        .attr('dy', '0.35em')
        .attr('x', r + 6)
        .text(d.name.length > 18 ? `${d.name.slice(0, 17)}…` : d.name)
    }
  })

  graphBuilt = true
  paintHighlight2d()
}

/** Cheap per-tick update — only transforms + edge paths */
function updateGraphPositions() {
  if (!graphBuilt || !mainGroup || currentLayoutType.value === '3d') return
  if (edgePathSel) edgePathSel.attr('d', edgePathFor)
  if (nodeGroupSel) {
    nodeGroupSel.attr('transform', d => {
      const pos = nodePositionMap.get(d.id)
      return `translate(${pos?.x || 0}, ${pos?.y || 0})`
    })
  }
}

/** Class/opacity paint without rebuilding DOM */
function paintHighlight2d() {
  if (!graphBuilt || !mainGroup) return
  const activeId = hoveredNodeId.value || props.selectedNode?.id || null
  const neighbors = new Set()
  if (activeId && edgePathSel) {
    edgePathSel.each((d) => {
      const s = edgeSource(d)
      const t = edgeTarget(d)
      if (s === activeId) neighbors.add(t)
      if (t === activeId) neighbors.add(s)
    })
  }

  if (nodeGroupSel) {
    nodeGroupSel
      .classed('hovered', d => d.id === hoveredNodeId.value)
      .classed('selected', d => d.id === props.selectedNode?.id)
      .style('opacity', d => {
        if (!activeId) return 1
        if (d.id === activeId || neighbors.has(d.id)) return 1
        return 0.22
      })
  }

  if (edgePathSel) {
    edgePathSel
      .classed('highlighted', d => isEdgeHighlighted(d))
      .style('opacity', d => {
        if (!activeId) return null
        return isEdgeHighlighted(d) ? 1 : 0.06
      })
  }
}

function renderGraph() {
  if (!svg || !mainGroup || currentLayoutType.value === '3d') return
  buildGraphStructure()
  updateMinimap()
}

function showTooltip(event, d) {
  const rect = chartContainer.value?.getBoundingClientRect()
  if (!rect) return
  tooltip.value = {
    visible: true,
    x: event.clientX - rect.left + 14,
    y: event.clientY - rect.top + 14,
    name: d.name,
    meta: `${d.type || ''} · ${d.module || d.path || ''}`,
  }
}

function updateMinimap() {
  if (!minimapSvg.value || currentLayoutType.value === '3d') return
  const msvg = d3.select(minimapSvg.value)
  msvg.selectAll('*').remove()
  const mw = 150
  const mh = 100
  msvg.attr('viewBox', `0 0 ${mw} ${mh}`)

  const positions = [...nodePositionMap.values()]
  if (!positions.length) return
  const xs = positions.map(p => p.x)
  const ys = positions.map(p => p.y)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const sx = (mw - 12) / Math.max(maxX - minX, 1)
  const sy = (mh - 12) / Math.max(maxY - minY, 1)
  const s = Math.min(sx, sy)

  const { fileNodes } = getVisibleNodes()
  msvg.selectAll('circle')
    .data(fileNodes)
    .enter()
    .append('circle')
    .attr('cx', d => {
      const p = nodePositionMap.get(d.id)
      return 6 + ((p?.x || 0) - minX) * s
    })
    .attr('cy', d => {
      const p = nodePositionMap.get(d.id)
      return 6 + ((p?.y || 0) - minY) * s
    })
    .attr('r', 2)
    .attr('fill', d => getNodeColor(d))
    .attr('opacity', 0.85)
}

function initSvg() {
  if (!svgRef.value || !chartContainer.value) return
  const container = chartContainer.value
  width.value = container.clientWidth || 800
  height.value = container.clientHeight || 600

  svg = d3.select(svgRef.value)
  svg.selectAll('g.main-group').remove()
  svg.attr('viewBox', `0 0 ${width.value} ${height.value}`)
    .attr('width', '100%')
    .attr('height', '100%')

  // keep defs, only recreate main group
  mainGroup = svg.append('g').attr('class', 'main-group')

  let zoomEmitAt = 0
  zoomBehavior = d3.zoom()
    .scaleExtent([CODE_GRAPH.zoom.min, CODE_GRAPH.zoom.max])
    .on('zoom', (event) => {
      mainGroup.attr('transform', event.transform)
      zoom.value = event.transform.k
      const now = performance.now()
      if (now - zoomEmitAt > 120) {
        zoomEmitAt = now
      emit('zoom-change', event.transform.k)
      }
    })

  svg.call(zoomBehavior)
  svg.on('click', () => emit('node-click', null))
}

function handleLayoutChange(val) {
  const layout = typeof val === 'string' ? val : currentLayoutType.value
  if (!CODE_GRAPH.layouts.some(item => item.value === layout)) return
  emit('layout-change', layout)
  applyLayout(layout)
}

function handleFitView() {
  if (currentLayoutType.value === '3d' && graph3d) {
    applyCinematicCamera(900)
    zoom.value = 1
    return
  }
  if (!svg || !zoomBehavior || !props.nodes.length) return

  let minX = Infinity; let minY = Infinity; let maxX = -Infinity; let maxY = -Infinity
  props.nodes.forEach(node => {
    const p = nodePositionMap.get(node.id) || node
    if (p.x == null) return
    minX = Math.min(minX, p.x - 50)
    minY = Math.min(minY, p.y - 50)
    maxX = Math.max(maxX, p.x + 50)
    maxY = Math.max(maxY, p.y + 50)
  })
  if (!isFinite(minX)) return

  const bw = Math.max(maxX - minX, 1)
  const bh = Math.max(maxY - minY, 1)
  const scale = Math.min(0.9 * width.value / bw, 0.9 * height.value / bh, 1.6)
  if (!Number.isFinite(scale) || scale <= 0) return
  const tx = width.value / 2 - scale * (minX + bw / 2)
  const ty = height.value / 2 - scale * (minY + bh / 2)

  svg.transition().duration(650).ease(d3.easeCubicOut)
    .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale))
}

function handleZoomIn() {
  if (currentLayoutType.value === '3d' && graph3d) {
    wake3dRender(3000)
    zoom3dCamera(0.82)
    return
  }
  if (svg && zoomBehavior) svg.transition().duration(280).call(zoomBehavior.scaleBy, 1.3)
}

function handleZoomOut() {
  if (currentLayoutType.value === '3d' && graph3d) {
    wake3dRender(3000)
    zoom3dCamera(1.2)
    return
  }
  if (svg && zoomBehavior) svg.transition().duration(280).call(zoomBehavior.scaleBy, 0.7)
}

function zoom3dCamera(factor) {
  const controls = graph3d.controls()
  const target = controls.target
  const offset = graph3d.camera().position.clone().sub(target)
  const distance = Math.max(controls.minDistance, Math.min(controls.maxDistance, offset.length() * factor))
  graph3d.cameraPosition(offset.normalize().multiplyScalar(distance).add(target), target, CODE_GRAPH.zoom.durationMs)
}

let resizeRaf = null
function handleVisibilityChange() {
  if (!graph3d) return
  if (document.hidden) {
    graph3d.pauseAnimation()
    renderPaused = true
  } else wake3dRender()
}
function handleResize() {
  if (resizeRaf) return
  resizeRaf = requestAnimationFrame(() => {
    resizeRaf = null
    if (!chartContainer.value) return
    const w = chartContainer.value.clientWidth
    const h = chartContainer.value.clientHeight
    if (w === width.value && h === height.value) return
    width.value = w
    height.value = h
    if (currentLayoutType.value === '3d' && graph3d) {
      wake3dRender(1200)
      graph3d.width(w).height(h)
      if (!props.selectedNode) applyCinematicCamera(CODE_GRAPH.zoom.durationMs)
    } else if (svg) {
      svg.attr('viewBox', `0 0 ${w} ${h}`)
    }
  })
}

watch(() => [props.nodes, props.edges], () => applyLayout(currentLayoutType.value), { flush: 'post' })

watch(() => props.layout, (newLayout) => {
  if (
    newLayout
    && CODE_GRAPH.layouts.some(item => item.value === newLayout)
    && newLayout !== currentLayoutType.value
  ) {
    currentLayoutType.value = newLayout
    applyLayout(newLayout)
  }
})

watch([() => props.selectedNode?.id, showAllEdges], () => {
  if (currentLayoutType.value === '3d') refresh3dSelection()
  else if (graphBuilt) renderGraph()
})

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibilityChange)
  nextTick(() => {
    if (props.nodes.length > 0) {
      applyLayout(currentLayoutType.value)
    } else if (currentLayoutType.value !== '3d') {
      initSvg()
    }
  })
  if (chartContainer.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => handleResize())
    resizeObserver.observe(chartContainer.value)
  }
  window.addEventListener('resize', handleResize)

})

onUnmounted(() => {
  disposed = true
  ++init3dToken
  pendingLayout = null
  if (simulation) simulation.stop()
  if (renderRaf) cancelAnimationFrame(renderRaf)
  if (resizeRaf) cancelAnimationFrame(resizeRaf)
  destroy3dGraph()
  resizeObserver?.disconnect()
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

defineExpose({
  fitView: handleFitView,
  zoomIn: handleZoomIn,
  zoomOut: handleZoomOut,
  focusNode,
})
</script>

<style lang="scss" scoped>
.graph-canvas-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.canvas-controls {
  position: absolute;
  top: 14px;
  left: 14px;
  right: 14px;
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  z-index: 12;
  pointer-events: none;

  > * { pointer-events: auto; }
}

.control-group {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: var(--radius-lg);
  max-width: 100%;
  overflow-x: auto;

  &.glass {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
    box-shadow: var(--shadow-sm);
  }

  :deep(.el-button.active) {
    color: #22d3ee;
  }

  :deep(.el-radio-button__inner) {
    background: transparent;
    border-color: var(--border-primary);
    color: var(--text-secondary);
  }

  :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
    background: var(--bg-active);
    border-color: var(--border-hover);
    color: var(--text-primary);
    box-shadow: none;
  }
}

.zoom-level {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 44px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.chart-container {
  flex: 1;
  min-height: 0;
  position: relative;
  overflow: hidden;
  background: var(--canvas-bg);
}

.depth-atmosphere {
  display: none;
}

.svg-stage {
  position: absolute;
  inset: 0;
  z-index: 2;
  transform-origin: 50% 60%;
  transform-style: preserve-3d;
}

.graph-svg,
.graph-3d-host {
  width: 100%;
  height: 100%;
}

.graph-3d-host {
  position: absolute;
  inset: 0;
  z-index: 2;
  touch-action: none;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

.graph-svg {
  cursor: grab;
  &:active { cursor: grabbing; }
}

.loading-overlay,
.empty-state {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 14px;
  background: var(--bg-secondary);
}

.loading-orb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2px solid rgba(34, 211, 238, 0.25);
  border-top-color: #22d3ee;
  animation: orb-spin 0.7s linear infinite;
}

@keyframes orb-spin {
  to { transform: rotate(360deg); }
}

.node-tooltip {
  position: absolute;
  z-index: 20;
    pointer-events: none;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);

  .tip-name {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-primary);
  }
  .tip-meta {
    margin-top: 2px;
    font-size: 11px;
    color: var(--text-secondary);
  }
}

.graph-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--cg-control-gap);
  padding: var(--cg-control-padding);
  font-size: var(--cg-caption-size);
  color: var(--text-secondary);
  border-top: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;

  .graph-help { margin-left: auto; color: var(--text-tertiary); }
}

.minimap {
  position: absolute;
  bottom: var(--cg-minimap-bottom);
  right: 14px;
  width: 150px;
  height: 100px;
  z-index: 10;
  border-radius: 12px;
  overflow: hidden;
  opacity: 0.85;
  transition: opacity 0.25s, box-shadow 0.25s;

  &.glass {
    background: var(--bg-secondary);
    border: 1px solid var(--border-primary);
  }

  &:hover { opacity: 1; }
}

.minimap-svg {
  width: 100%;
  height: 100%;
}

:deep(.node-group) {
  cursor: pointer;

  .node-circle {
  stroke-width: 2;
  }

  .node-label {
    font-size: 11px;
    fill: #e2e8f0;
    paint-order: stroke;
    stroke: rgba(0, 0, 0, 0.65);
    stroke-width: 2px;
    pointer-events: none;
  }

  &.hovered .node-circle,
  &.selected .node-circle {
    stroke-width: 3.5;
  }

  &.selected .node-halo,
  &.hovered .node-halo {
    fill: rgba(34, 211, 238, 0.28) !important;
  }
}

:deep(.edge-path) {
  fill: none;
  stroke: rgba(148, 163, 184, 0.4);
  stroke-width: 1.2;
  opacity: 0.7;
}

:deep(.edge-path.highlighted) {
  stroke: #22d3ee;
  stroke-width: 2;
    opacity: 1;
}

:deep(.func-edge) {
  stroke: #a78bfa !important;
  stroke-dasharray: 5 3;
}

</style>
