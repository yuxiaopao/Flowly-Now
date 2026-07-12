<template>
  <div class="graph-canvas-wrapper">
    <!-- 控制栏 -->
    <div class="canvas-controls">
      <div class="control-group">
        <el-radio-group
          v-model="currentLayoutType"
          size="small"
          @change="handleLayoutChange"
        >
          <el-radio-button value="force">
            力导向图
          </el-radio-button>
          <el-radio-button value="tree">
            树形图
          </el-radio-button>
          <el-radio-button value="dagre">
            层次图
          </el-radio-button>
        </el-radio-group>
      </div>
      <div class="control-group">
        <el-button
          size="small"
          :icon="Maximize"
          @click="handleFitView"
        >
          适应画布
        </el-button>
        <el-button
          size="small"
          :icon="ZoomIn"
          @click="handleZoomIn"
        >
          放大
        </el-button>
        <el-button
          size="small"
          :icon="ZoomOut"
          @click="handleZoomOut"
        >
          缩小
        </el-button>
        <span class="zoom-level">{{ Math.round(zoom * 100) }}%</span>
      </div>
    </div>

    <!-- 图表容器 -->
    <div
      ref="chartContainer"
      class="chart-container"
    >
      <!-- 加载状态 -->
      <div
        v-if="loading"
        class="loading-overlay"
      >
        <el-icon class="is-loading">
          <Loading />
        </el-icon>
        <span>加载图数据...</span>
      </div>

      <!-- 空状态 -->
      <div
        v-else-if="nodes.length === 0"
        class="empty-state"
      >
        <el-empty description="暂无图数据">
          <el-button
            type="primary"
            @click="$emit('fit-view')"
          >
            刷新
          </el-button>
        </el-empty>
      </div>

      <!-- D3 图表 - 使用 v-show 避免 ref 丢失 -->
      <svg
        v-show="nodes.length > 0"
        ref="svgRef"
        class="graph-svg"
      >
        <defs>
          <!-- 箭头标记 -->
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
              fill="var(--text-secondary)"
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
              fill="var(--color-primary)"
            />
          </marker>
        </defs>
        <!-- 主组由 D3 控制 -->
      </svg>
    </div>

    <!-- MiniMap -->
    <div class="minimap">
      <svg
        ref="minimapSvg"
        class="minimap-svg"
      />
    </div>
  </div>
</template>

<script setup>
/**
 * GraphCanvas - 基于 D3 的代码依赖图可视化组件
 * 支持三种布局：力导向图、树形图、层次图
 * 支持文件节点 + 函数节点两层渲染
 */

import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'
import dagre from 'dagre'
import { Maximize, ZoomIn, ZoomOut } from 'lucide-vue-next'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps({
  nodes: {
    type: Array,
    default: () => []
  },
  edges: {
    type: Array,
    default: () => []
  },
  selectedNode: {
    type: Object,
    default: null
  },
  layout: {
    type: String,
    default: 'force'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['node-click', 'node-hover', 'zoom-change', 'fit-view', 'layout-change'])

const chartContainer = ref(null)
const svgRef = ref(null)
const minimapSvg = ref(null)

const width = ref(800)
const height = ref(600)
const zoom = ref(1)
const hoveredNodeId = ref(null)
// 初始化时使用传入的 layout，后续由 handleLayoutChange 同步更新
const currentLayoutType = ref(props.layout)

// D3 相关
let simulation = null
let svg = null
let mainGroup = null
let zoomBehavior = null

// 节点位置 Map — { nodeId: { x, y } }，覆盖文件节点和函数节点
const nodePositionMap = new Map()

// 当前可见节点 ID Set（由过滤条件决定）
const visibleNodeIds = ref(new Set())

// 根据过滤条件计算可见边（两端节点都在 visibleNodeIds 中才可见）
function getVisibleEdges() {
  if (visibleNodeIds.value.size === 0 || visibleNodeIds.value.size === props.nodes.length) {
    return props.edges
  }
  return props.edges.filter(e =>
    visibleNodeIds.value.has(e.source) && visibleNodeIds.value.has(e.target)
  )
}

// 分离文件节点和函数节点（受 visibleNodeIds 过滤条件约束）
function getVisibleNodes() {
  const allNodes = visibleNodeIds.value.size === 0 || visibleNodeIds.value.size === props.nodes.length
    ? props.nodes
    : props.nodes.filter(n => visibleNodeIds.value.has(n.id))
  return {
    fileNodes: allNodes.filter(n => n.type !== 'function'),
    funcNodes: allNodes.filter(n => n.type === 'function'),
  }
}

// 计算函数节点的位置：挂靠在所属文件的右侧
function positionFuncNodes(fileNodes, nodePositionMap) {
  const allFuncNodes = props.nodes.filter(n => n.type === 'function')
  fileNodes.forEach(fileNode => {
    const filePos = nodePositionMap.get(fileNode.id)
    if (!filePos) return

    // 找到该文件下的所有函数（id 前缀匹配 fileNode.id::）
    const funcsInFile = allFuncNodes.filter(fn => fn.id.startsWith(fileNode.id + '::'))
    funcsInFile.forEach((fn, i) => {
      nodePositionMap.set(fn.id, {
        x: filePos.x + 80,
        y: filePos.y + (i - funcsInFile.length / 2) * 40,
      })
    })
  })
}

// 节点类型到颜色的映射
const typeColors = {
  vue: '#42b883',
  js: '#f7df1e',
  ts: '#3178c6',
  py: '#3776ab',
  json: '#cbcb41',
  md: '#083fa1',
}

function getNodeRadius(node) {
  const baseRadius = 8
  const centralityBonus = (node.centrality || 0) * 20
  return Math.min(baseRadius + centralityBonus, 20)
}

function isEdgeHighlighted(edge) {
  const activeId = hoveredNodeId.value || props.selectedNode?.id
  if (!activeId) return false
  return edge.source === activeId || edge.target === activeId
}

function getEdgePath(edge) {
  const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source
  const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target

  const sourcePos = nodePositionMap.get(sourceId)
  const targetPos = nodePositionMap.get(targetId)
  if (!sourcePos || !targetPos) return ''

  const dx = targetPos.x - sourcePos.x
  const dy = targetPos.y - sourcePos.y
  const dr = Math.sqrt(dx * dx + dy * dy) * 0.5

  return `M${sourcePos.x},${sourcePos.y} A${dr},${dr} 0 0,1 ${targetPos.x},${targetPos.y}`
}

function getStraightEdgePath(edge) {
  const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source
  const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target

  const sourcePos = nodePositionMap.get(sourceId)
  const targetPos = nodePositionMap.get(targetId)
  if (!sourcePos || !targetPos) return ''

  return `M${sourcePos.x},${sourcePos.y} L${targetPos.x},${targetPos.y}`
}

function getNodeColor(node) {
  return typeColors[node.type] || typeColors[node.type?.replace(/^file:/, '').split('.').pop()] || '#999'
}

// ==================== 布局算法 ====================

function applyForceLayout() {
  if (!props.nodes.length) return

  // 初始化节点位置（力导向图只处理文件节点）
  props.nodes.forEach((node) => {
    if (!node.x) node.x = width.value / 2 + (Math.random() - 0.5) * 200
    if (!node.y) node.y = height.value / 2 + (Math.random() - 0.5) * 200
  })

  if (simulation) {
    simulation.stop()
  }

  simulation = d3.forceSimulation(props.nodes)
    .force('link', d3.forceLink(props.edges)
      .id(d => d.id)
      .distance(100)
    )
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width.value / 2, height.value / 2))
    .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 10))
    .on('tick', () => {
      // 同步位置到 Map（力导向图只驱动文件节点）
      props.nodes.forEach(n => nodePositionMap.set(n.id, { x: n.x, y: n.y }))
      renderGraph()
    })

  currentLayoutType.value = 'force'
}

function applyTreeLayout() {
  if (!props.nodes.length) return

  if (simulation) {
    simulation.stop()
    simulation = null
  }

  // 构建树结构
  const nodeMap = new Map(props.nodes.map(n => [n.id, { ...n, children: [] }]))

  // 建立父子关系
  props.edges.forEach(edge => {
    const parent = nodeMap.get(edge.source)
    const child = nodeMap.get(edge.target)
    if (parent && child) {
      parent.children.push(child)
    }
  })

  // 找到根节点（没有父节点的节点）
  let treeRoot = null
  for (const node of props.nodes) {
    const hasParent = props.edges.some(e => e.target === node.id)
    if (!hasParent) {
      treeRoot = nodeMap.get(node.id)
      break
    }
  }

  if (!treeRoot) {
    treeRoot = nodeMap.get(props.nodes[0].id)
  }

  if (!treeRoot) {
    applyForceLayout()
    return
  }

  // 构建 d3 hierarchy
  const hierarchy = d3.hierarchy(treeRoot)

  // 使用 d3.tree 布局 (水平方向)
  const treeLayout = d3.tree()
    .size([height.value - 100, width.value - 200])

  treeLayout(hierarchy)

  // 更新节点位置并同步到 Map
  hierarchy.descendants().forEach((d) => {
    const node = props.nodes.find(n => n.id === d.data.id)
    if (node) {
      node.x = d.y + 100
      node.y = d.x + height.value / 2
      nodePositionMap.set(node.id, { x: node.x, y: node.y })
    }
  })

  currentLayoutType.value = 'tree'
  renderGraph()
}

function applyDagreLayout() {
  if (!props.nodes.length) return

  if (simulation) {
    simulation.stop()
    simulation = null
  }

  // 创建 dagre 图
  const g = new dagre.graphlib.Graph()
  g.setGraph({
    rankdir: 'LR',
    nodesep: 50,
    ranksep: 80,
    marginx: 30,
    marginy: 30
  })
  g.setDefaultEdgeLabel(() => ({}))

  // 添加节点
  props.nodes.forEach(node => {
    g.setNode(node.id, {
      label: node.name,
      width: getNodeRadius(node) * 2 + 60,
      height: getNodeRadius(node) * 2 + 20
    })
  })

  // 添加边
  props.edges.forEach(edge => {
    if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
      g.setEdge(edge.source, edge.target)
    }
  })

  // 运行 dagre 布局
  dagre.layout(g)

  // 更新节点位置并同步到 Map
  g.nodes().forEach(nodeId => {
    const nodeData = g.node(nodeId)
    const node = props.nodes.find(n => n.id === nodeId)
    if (node && nodeData) {
      node.x = nodeData.x
      node.y = nodeData.y
      nodePositionMap.set(node.id, { x: node.x, y: node.y })
    }
  })

  currentLayoutType.value = 'dagre'
  renderGraph()
}

function applyLayout(layoutType) {
  switch (layoutType) {
    case 'force':
      applyForceLayout()
      break
    case 'tree':
      applyTreeLayout()
      break
    case 'dagre':
      applyDagreLayout()
      break
    default:
      applyForceLayout()
  }
}

// ==================== 渲染 ====================

function renderGraph() {
  if (!svg || !mainGroup) return

  // 清空主组
  mainGroup.selectAll('*').remove()

  const { fileNodes, funcNodes } = getVisibleNodes()

  // 先给函数节点分配位置（基于文件节点位置）
  positionFuncNodes(fileNodes, nodePositionMap)

  // 渲染边（使用 getVisibleEdges 支持函数间边）
  const visibleEdges = getVisibleEdges()
  const edgeGroup = mainGroup.append('g').attr('class', 'edges')
  edgeGroup.selectAll('.edge-group')
    .data(visibleEdges)
    .enter()
    .append('g')
    .attr('class', d => `edge-group ${isEdgeHighlighted(d) ? 'highlighted' : ''}`)
    .append('path')
    .attr('class', d => d.type === 'function' ? 'edge-path func-edge' : 'edge-path')
    .attr('d', d => currentLayoutType.value === 'force' ? getEdgePath(d) : getStraightEdgePath(d))
    .attr('marker-end', d => isEdgeHighlighted(d) ? 'url(#arrowhead-selected)' : 'url(#arrowhead)')

  // 渲染文件节点
  const fileNodeGroup = mainGroup.append('g').attr('class', 'file-nodes')
  fileNodeGroup.selectAll('.node-group')
    .data(fileNodes)
    .enter()
    .append('g')
    .attr('class', d => {
      let classes = `node-group type-${d.type}`
      if (d.id === props.selectedNode?.id) classes += ' selected'
      if (d.id === hoveredNodeId.value) classes += ' hovered'
      return classes
    })
    .attr('transform', d => {
      const pos = nodePositionMap.get(d.id)
      return `translate(${pos ? pos.x : 0}, ${pos ? pos.y : 0})`
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      handleNodeClick(d)
    })
    .on('mouseenter', (event, d) => {
      hoveredNodeId.value = d.id
      emit('node-hover', d)
    })
    .on('mouseleave', () => {
      hoveredNodeId.value = null
      emit('node-hover', null)
    })
    .each(function(d) {
      const g = d3.select(this)
      g.append('circle')
        .attr('class', 'node-circle')
        .attr('r', getNodeRadius(d))
        .style('stroke', getNodeColor(d))
      g.append('text')
        .attr('class', 'node-label')
        .attr('dy', '0.35em')
        .attr('x', getNodeRadius(d) + 5)
        .text(d.name)
    })

  // 渲染函数节点（矩形，挂在文件节点旁边）
  const funcNodeGroup = mainGroup.append('g').attr('class', 'func-nodes')
  funcNodeGroup.selectAll('.node-group')
    .data(funcNodes)
    .enter()
    .append('g')
    .attr('class', d => {
      let classes = `node-group type-function`
      if (d.id === props.selectedNode?.id) classes += ' selected'
      if (d.id === hoveredNodeId.value) classes += ' hovered'
      return classes
    })
    .attr('transform', d => {
      const pos = nodePositionMap.get(d.id)
      return `translate(${pos ? pos.x : 0}, ${pos ? pos.y : 0})`
    })
    .on('click', (event, d) => {
      event.stopPropagation()
      handleNodeClick(d)
    })
    .on('mouseenter', (event, d) => {
      hoveredNodeId.value = d.id
      emit('node-hover', d)
    })
    .on('mouseleave', () => {
      hoveredNodeId.value = null
      emit('node-hover', null)
    })
    .each(function(d) {
      const g = d3.select(this)
      g.append('rect')
        .attr('class', 'node-rect')
        .attr('x', -35)
        .attr('y', -9)
        .attr('width', 70)
        .attr('height', 18)
        .attr('rx', 4)
        .style('fill', 'var(--bg-secondary)')
        .style('stroke', 'var(--color-primary)')
        .style('stroke-width', 1.5)
      g.append('text')
        .attr('class', 'node-label')
        .attr('dy', '0.35em')
        .attr('text-anchor', 'middle')
        .style('font-size', '10px')
        .style('fill', 'var(--text-primary)')
        .text(d.name.length > 8 ? d.name.substring(0, 7) + '..' : d.name)
    })
}

// ==================== 初始化 ====================

function initSvg() {
  if (!svgRef.value || !chartContainer.value) return

  const container = chartContainer.value
  width.value = container.clientWidth || 800
  height.value = container.clientHeight || 600

  svg = d3.select(svgRef.value)

  // 清空 SVG
  svg.selectAll('*').remove()

  // 设置 viewBox
  svg.attr('viewBox', `0 0 ${width.value} ${height.value}`)
    .attr('width', '100%')
    .attr('height', '100%')

  // 创建主容器组 (用于缩放变换)
  mainGroup = svg.append('g').attr('class', 'main-group')

  // 设置缩放行为
  zoomBehavior = d3.zoom()
    .scaleExtent([0.1, 3])
    .on('zoom', (event) => {
      mainGroup.attr('transform', event.transform)
      zoom.value = event.transform.k
      emit('zoom-change', event.transform.k)
    })

  svg.call(zoomBehavior)
  svg.on('click', () => {
    emit('node-click', null)
  })
}

// ==================== 事件处理 ====================

function handleNodeClick(node) {
  emit('node-click', node)
}

function handleLayoutChange(newLayout) {
  emit('layout-change', newLayout)
  applyLayout(newLayout)
}

function handleFitView() {
  if (!svgRef.value || !zoomBehavior || !props.nodes.length) return

  // 计算边界
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  props.nodes.forEach(node => {
    if (node.x !== undefined && node.y !== undefined) {
      minX = Math.min(minX, node.x - 50)
      minY = Math.min(minY, node.y - 50)
      maxX = Math.max(maxX, node.x + 50)
      maxY = Math.max(maxY, node.y + 50)
    }
  })

  if (!isFinite(minX)) return

  const boundsWidth = maxX - minX
  const boundsHeight = maxY - minY
  const scale = Math.min(0.9 * width.value / boundsWidth, 0.9 * height.value / boundsHeight, 1.5)
  const translateX = width.value / 2 - scale * (minX + boundsWidth / 2)
  const translateY = height.value / 2 - scale * (minY + boundsHeight / 2)

  svg.transition()
    .duration(500)
    .call(
      zoomBehavior.transform,
      d3.zoomIdentity.translate(translateX, translateY).scale(scale)
    )
}

function handleZoomIn() {
  if (svg && zoomBehavior) {
    svg.transition().duration(300).call(zoomBehavior.scaleBy, 1.3)
  }
}

function handleZoomOut() {
  if (svg && zoomBehavior) {
    svg.transition().duration(300).call(zoomBehavior.scaleBy, 0.7)
  }
}

function handleResize() {
  if (!chartContainer.value) return
  width.value = chartContainer.value.clientWidth
  height.value = chartContainer.value.clientHeight

  if (svg) {
    svg.attr('viewBox', `0 0 ${width.value} ${height.value}`)
  }

  // 力导向图需要重新设置中心
  if (currentLayoutType.value === 'force' && simulation) {
    simulation.force('center', d3.forceCenter(width.value / 2, height.value / 2))
    simulation.alpha(0.3).restart()
  }
}

// ==================== 监听 ====================

watch(() => props.nodes, () => {
  // 更新可见节点集合（后端返回的 nodes 既包含文件节点也包含函数节点）
  visibleNodeIds.value = new Set(props.nodes.map(n => n.id))
  if (props.nodes.length > 0) {
    applyLayout(props.layout)
  }
}, { deep: true })

watch(() => props.edges, () => {
  if (currentLayoutType.value === 'force' && simulation) {
    simulation.force('link').links(props.edges)
    simulation.alpha(0.3).restart()
  } else {
    renderGraph()
  }
}, { deep: true })

watch(() => props.layout, (newLayout) => {
  applyLayout(newLayout)
})

watch(() => props.selectedNode, () => {
  renderGraph()
})

watch(hoveredNodeId, () => {
  renderGraph()
})

// ==================== 生命周期 ====================

onMounted(() => {
  nextTick(() => {
    initSvg()
    if (props.nodes.length > 0) {
      visibleNodeIds.value = new Set(props.nodes.map(n => n.id))
      applyLayout(props.layout)
    }
  })

  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (simulation) {
    simulation.stop()
  }
  window.removeEventListener('resize', handleResize)
})

// 暴露方法
defineExpose({
  fitView: handleFitView,
  zoomIn: handleZoomIn,
  zoomOut: handleZoomOut,
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
  top: 12px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  z-index: 10;
  pointer-events: none;

  > * {
    pointer-events: auto;
  }
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-secondary);
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.zoom-level {
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 45px;
  text-align: center;
}

.chart-container {
  flex: 1;
  position: relative;
  background: var(--bg-primary);
}

.graph-svg {
  width: 100%;
  height: 100%;
  cursor: grab;

  &:active {
    cursor: grabbing;
  }
}

.loading-overlay,
.empty-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loading-overlay .el-icon {
  font-size: 32px;
}

// 节点样式
:deep(.node-group) {
  cursor: pointer;

  .node-circle {
    fill: var(--bg-secondary);
    stroke-width: 2;
    transition: all 0.2s ease;
  }

  .node-label {
    font-size: 11px;
    fill: var(--text-primary);
    pointer-events: none;
  }

  &.hovered .node-circle,
  &.selected .node-circle {
    stroke-width: 3;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
  }

  &.selected .node-circle {
    fill: var(--color-primary);
  }

  // 类型颜色
  &.type-vue .node-circle { stroke: #42b883; }
  &.type-js .node-circle { stroke: #f7df1e; }
  &.type-ts .node-circle { stroke: #3178c6; }
  &.type-py .node-circle { stroke: #3776ab; }
}

// 边样式
:deep(.edge-path) {
  fill: none;
  stroke: var(--border-color);
  stroke-width: 1.5;
  opacity: 0.6;
  transition: all 0.2s ease;
}

:deep(.edge-group.highlighted .edge-path) {
  stroke: var(--color-primary);
  stroke-width: 2;
  opacity: 1;
}

// 函数节点样式
:deep(.func-nodes .node-rect) {
  fill: var(--bg-secondary);
  stroke: var(--color-primary);
  stroke-width: 1.5;
  transition: all 0.2s ease;
}

:deep(.func-nodes .node-group.hovered .node-rect),
:deep(.func-nodes .node-group.selected .node-rect) {
  stroke-width: 2.5;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

:deep(.func-nodes .node-group.selected .node-rect) {
  fill: var(--color-primary);
}

:deep(.func-nodes .node-group.selected .node-label) {
  fill: white;
}

// 函数调用边样式（蓝色虚线，区分于文件依赖边）
:deep(.func-edge) {
  stroke: #8b5cf6;
  stroke-dasharray: 4 2;
  opacity: 0.7;
}

:deep(.edge-group.highlighted .func-edge) {
  stroke: #8b5cf6;
  opacity: 1;
  stroke-width: 2;
}

.minimap {
  position: absolute;
  bottom: 12px;
  right: 12px;
  width: 150px;
  height: 100px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
  opacity: 0.8;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
}

.minimap-svg {
  width: 100%;
  height: 100%;
}
</style>
