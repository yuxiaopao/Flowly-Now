/**
 * 工作流节点自动布局算法
 * 基于拓扑排序的 DAG 分层布局（左到右流向）
 * 核心思路：
 *  1. 通过 Kahn 算法对节点进行拓扑分层（根节点在左，后续节点按依赖关系往后排）
 *  2. 每层节点垂直居中排布
 *  3. 支持分支/合并/孤立节点
 */

const DEFAULT_NODE_WIDTH = 220
const DEFAULT_NODE_HEIGHT = 140
const LAYER_GAP_X = 160
const NODE_GAP_Y = 60
const START_X = 80
const START_Y = 80

export function autoLayoutWorkflow(nodes, edges, options) {
  const opts = options || {}
  const nodeWidth = opts.nodeWidth || DEFAULT_NODE_WIDTH
  const nodeHeight = opts.nodeHeight || DEFAULT_NODE_HEIGHT
  const gapX = opts.gapX || LAYER_GAP_X
  const gapY = opts.gapY || NODE_GAP_Y
  const startX = opts.startX || START_X
  const startY = opts.startY || START_Y

  if (!nodes || nodes.length === 0) return nodes

  // ---------- 构建图结构 ----------
  const nodeMap = {}
  nodes.forEach(function(n) { nodeMap[n.id] = true })

  const inEdges = {}
  const outEdges = {}
  nodes.forEach(function(n) {
    inEdges[n.id] = []
    outEdges[n.id] = []
  })

  edges.forEach(function(e) {
    const source = String(e.source)
    const target = String(e.target)
    if (nodeMap[source] && nodeMap[target]) {
      inEdges[target].push(source)
      outEdges[source].push(target)
    }
  })

  // ---------- Kahn 拓扑分层 ----------
  const nodeLayer = {}
  const remainingInDegree = {}

  nodes.forEach(function(n) {
    remainingInDegree[n.id] = inEdges[n.id].length
  })

  const queue = []
  nodes.forEach(function(n) {
    if (remainingInDegree[n.id] === 0) {
      queue.push(n.id)
      nodeLayer[n.id] = 0
    }
  })

  if (queue.length === 0 && nodes.length > 0) {
    nodeLayer[nodes[0].id] = 0
    queue.push(nodes[0].id)
  }

  while (queue.length > 0) {
    const nodeId = queue.shift()
    const currentLayer = nodeLayer[nodeId] || 0
    const targets = outEdges[nodeId] || []

    targets.forEach(function(targetId) {
      if (nodeMap[targetId]) {
        const newLayer = currentLayer + 1
        if (!nodeLayer[targetId] || nodeLayer[targetId] < newLayer) {
          nodeLayer[targetId] = newLayer
        }
        if (queue.indexOf(targetId) === -1) {
          queue.push(targetId)
        }
      }
    })
  }

  // 孤立节点（无入边也无出边）分配到层 0
  nodes.forEach(function(n) {
    if (nodeLayer[n.id] === undefined) {
      nodeLayer[n.id] = 0
    }
  })

  // ---------- 按层分组 ----------
  let maxLayer = 0
  Object.keys(nodeLayer).forEach(function(k) {
    maxLayer = Math.max(maxLayer, nodeLayer[k])
  })

  const layers = []
  for (let i = 0; i <= maxLayer; i++) layers.push([])
  Object.keys(nodeLayer).forEach(function(nodeId) {
    layers[nodeLayer[nodeId]].push(nodeId)
  })

  // 每层内按拓扑顺序排序（减少连线交叉）
  layers.forEach(function(layer, layerIdx) {
    if (layerIdx > 0) {
      layer.sort(function(a, b) {
        const aSources = inEdges[a] || []
        const bSources = inEdges[b] || []
        if (aSources.length === 0 && bSources.length > 0) return -1
        if (bSources.length === 0 && aSources.length > 0) return 1
        const aSourcesIdx = aSources.length > 0 ? nodeLayer[aSources[0]] : 0
        const bSourcesIdx = bSources.length > 0 ? nodeLayer[bSources[0]] : 0
        return aSourcesIdx - bSourcesIdx
      })
    }
  })

  // ---------- 计算每层的实际高度 ----------
  const layerHeights = layers.map(function(layer) {
    // 该层节点总高度 + 节点间间隙
    return layer.length > 0
      ? layer.length * nodeHeight + (layer.length - 1) * gapY
      : 0
  })

  // ---------- 计算每层的起始 Y（累积高度） ----------
  const layerStartY = []
  let accumulatedY = startY
  layerHeights.forEach(function(h) {
    layerStartY.push(accumulatedY)
    accumulatedY += h + gapY
  })

  // ---------- 分配位置 ----------
  const positions = {}
  layers.forEach(function(layer, layerIdx) {
    const layerX = startX + layerIdx * (nodeWidth + gapX)
    const layerContentHeight = layer.length * nodeHeight + (layer.length - 1) * gapY

    // 该层垂直居中于 layerStartY ~ (layerStartY + layerContentHeight)
    const layerY = layerStartY[layerIdx]

    layer.forEach(function(nodeId, nodeIdx) {
      positions[nodeId] = {
        x: Math.round(layerX),
        y: Math.round(layerY + nodeIdx * (nodeHeight + gapY))
      }
    })
  })

  return nodes.map(function(n) {
    const pos = positions[n.id] || { x: startX, y: startY }
    return { ...n, position: { x: pos.x, y: pos.y } }
  })
}
