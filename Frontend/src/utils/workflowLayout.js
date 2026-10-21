/**
 * 工作流节点自动布局算法
 * 基于拓扑排序的 DAG 分层布局
 * 支持水平（默认）和垂直两种排列方向
 * 核心思路：
 *  1. 通过 Kahn 算法对节点进行拓扑分层（根节点在前，后续节点按依赖关系往后排）
 *  2. 每层节点垂直居中排布（水平模式）或水平居中（垂直模式）
 *  3. 支持分支/合并/孤立节点
 *  4. 节点间距确保防碰撞（gapX/gapY）
 */

export const DEFAULT_NODE_WIDTH = 220
export const DEFAULT_NODE_HEIGHT = 140
export const LAYER_GAP_X = 180
export const LAYER_GAP_Y = 80
export const NODE_GAP_X = 60
export const NODE_GAP_Y = 60
export const START_X = 80
export const START_Y = 80
const POSITION_PRECISION = 2

function roundCanvasCoordinate(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 0
  return Number(number.toFixed(POSITION_PRECISION))
}

function normalizePosition(position) {
  return {
    x: roundCanvasCoordinate(position?.x),
    y: roundCanvasCoordinate(position?.y),
  }
}

function getNodeDimensions(node, opts) {
  const style = node?.style || node?.data?.style || {}
  const uiSize = node?.data?.uiSize || style.uiSize || {}
  const width = Number(node?.width ?? node?.dimensions?.width ?? uiSize.width ?? style.width)
  const height = Number(node?.height ?? node?.dimensions?.height ?? uiSize.height ?? style.height)
  return {
    width: Number.isFinite(width) && width > 0 ? width : opts.nodeWidth,
    height: Number.isFinite(height) && height > 0 ? height : opts.nodeHeight,
  }
}

function getNodeRect(node, opts, positionOverride = null) {
  const position = normalizePosition(positionOverride || node?.position)
  const { width, height } = getNodeDimensions(node, opts)
  return {
    x: position.x,
    y: position.y,
    width,
    height,
    right: position.x + width,
    bottom: position.y + height,
  }
}

function normalizeLayoutOptions(options = {}) {
  return {
    nodeWidth: options.nodeWidth ?? DEFAULT_NODE_WIDTH,
    nodeHeight: options.nodeHeight ?? DEFAULT_NODE_HEIGHT,
    gapX: options.gapX ?? LAYER_GAP_X,
    gapY: options.gapY ?? LAYER_GAP_Y,
    nodeGapX: options.nodeGapX ?? NODE_GAP_X,
    nodeGapY: options.nodeGapY ?? NODE_GAP_Y,
    startX: options.startX ?? START_X,
    startY: options.startY ?? START_Y,
    direction: options.direction
  }
}

export function isZeroPosition(position) {
  if (!position) return true
  const x = Number(position.x)
  const y = Number(position.y)
  return !Number.isFinite(x) || !Number.isFinite(y)
}

function buildEdgeMaps(edges = []) {
  const inEdges = {}
  const outEdges = {}

  edges.forEach((edge) => {
    const source = String(edge.source)
    const target = String(edge.target)
    if (!inEdges[target]) inEdges[target] = []
    if (!outEdges[source]) outEdges[source] = []
    inEdges[target].push(source)
    outEdges[source].push(target)
  })

  return { inEdges, outEdges }
}

function computeLayers(nodes, edges) {
  const nodeMap = {}
  nodes.forEach((node) => {
    nodeMap[node.id] = true
  })

  const { inEdges, outEdges } = buildEdgeMaps(edges)
  const nodeLayer = {}
  const remainingInDegree = {}

  nodes.forEach((node) => {
    remainingInDegree[node.id] = (inEdges[node.id] || []).filter((source) => nodeMap[source]).length
  })

  const queue = []
  nodes.forEach((node) => {
    if (remainingInDegree[node.id] === 0) {
      queue.push(node.id)
      nodeLayer[node.id] = 0
    }
  })

  if (queue.length === 0 && nodes.length > 0) {
    nodeLayer[nodes[0].id] = 0
    queue.push(nodes[0].id)
  }

  while (queue.length > 0) {
    const nodeId = queue.shift()
    const currentLayer = nodeLayer[nodeId] || 0
    ;(outEdges[nodeId] || []).forEach((targetId) => {
      if (!nodeMap[targetId]) return
      const newLayer = currentLayer + 1
      if (!nodeLayer[targetId] || nodeLayer[targetId] < newLayer) {
        nodeLayer[targetId] = newLayer
      }
      if (!queue.includes(targetId)) {
        queue.push(targetId)
      }
    })
  }

  nodes.forEach((node) => {
    if (nodeLayer[node.id] === undefined) {
      nodeLayer[node.id] = 0
    }
  })

  let maxLayer = 0
  Object.values(nodeLayer).forEach((layer) => {
    maxLayer = Math.max(maxLayer, layer)
  })

  const layers = []
  for (let i = 0; i <= maxLayer; i += 1) layers.push([])
  Object.entries(nodeLayer).forEach(([nodeId, layer]) => {
    layers[layer].push(nodeId)
  })

  return layers
}

/**
 * 根据 DAG 形状自动选择水平或垂直布局
 *
 * 术语：
 * - horizontal：层从左到右推进，同层兄弟上下排列（适合简单长链）
 * - vertical：层从上到下推进，同层兄弟左右横排（适合宽扇出/并行分镜）
 */
export function pickLayoutDirection(nodes, edges) {
  if (!nodes?.length) return 'horizontal'

  const layers = computeLayers(nodes, edges)
  const layerCount = layers.length
  const maxLayerSize = Math.max(...layers.map((layer) => layer.length), 1)

  // 宽并行扇出（≥3 同层兄弟）：同类节点必须横排 → vertical
  if (maxLayerSize >= 3) return 'vertical'
  // 深链少分支：也可竖排推进，避免画布过长
  if (layerCount >= 6 && maxLayerSize <= 2) return 'vertical'
  return 'horizontal'
}

function nodeRectsCollide(a, b, opts) {
  const marginX = opts.nodeGapX
  const marginY = opts.nodeGapY
  return (
    a.x < b.right + marginX
    && a.right + marginX > b.x
    && a.y < b.bottom + marginY
    && a.bottom + marginY > b.y
  )
}

function findBlockingRect(rect, occupiedRects, opts) {
  return occupiedRects.find((occupied) => nodeRectsCollide(rect, occupied, opts)) || null
}

function chooseCollisionSeparation(rect, occupied, originalPos, opts) {
  const candidates = [
    { x: occupied.x - opts.nodeGapX - rect.width, y: rect.y },
    { x: occupied.right + opts.nodeGapX, y: rect.y },
    { x: rect.x, y: occupied.y - opts.nodeGapY - rect.height },
    { x: rect.x, y: occupied.bottom + opts.nodeGapY },
  ].map(normalizePosition)

  candidates.sort((a, b) => {
    const da = Math.hypot(a.x - originalPos.x, a.y - originalPos.y)
    const db = Math.hypot(b.x - originalPos.x, b.y - originalPos.y)
    return da - db
  })

  return candidates[0]
}

/**
 * 检测节点之间是否存在重叠（含最小间距）
 */
export function hasOverlappingPositions(nodes, options = {}) {
  const opts = normalizeLayoutOptions(options)
  for (let i = 0; i < nodes.length; i += 1) {
    if (isZeroPosition(nodes[i]?.position)) continue
    for (let j = i + 1; j < nodes.length; j += 1) {
      if (isZeroPosition(nodes[j]?.position)) continue
      if (nodeRectsCollide(getNodeRect(nodes[i], opts), getNodeRect(nodes[j], opts), opts)) {
        return true
      }
    }
  }
  return false
}

/**
 * 判断是否需要自动布局（仅全零坐标 / 存在未定位节点）
 * 已保存的用户坐标即使重叠也不自动重排，由拖拽防碰撞处理
 */
export function needsAutoLayout(nodes) {
  if (!nodes?.length) return false
  if (nodes.every((node) => isZeroPosition(node.position))) return true
  if (nodes.some((node) => isZeroPosition(node.position))) return true
  return false
}

/**
 * 拖拽结束后解析节点碰撞，返回不重叠的坐标
 */
export function resolveNodeCollision(node, allNodes, options = {}) {
  const opts = normalizeLayoutOptions(options)
  const pos = normalizePosition(node.position)
  const occupied = allNodes
    .filter((n) => n.id !== node.id)
    .filter((n) => !isZeroPosition(n.position))
    .map((n) => getNodeRect(n, opts))

  const movingRect = getNodeRect(node, opts, pos)
  const collides = findBlockingRect(movingRect, occupied, opts)
  if (!collides) return pos

  return findNonOverlappingPosition(node, pos, occupied, opts)
}

function getBoundingBox(positions) {
  const valid = positions.filter((pos) => !isZeroPosition(pos))
  if (!valid.length) {
    return { minX: START_X, minY: START_Y, maxX: START_X, maxY: START_Y }
  }

  let minX = Infinity
  let minY = Infinity
  let maxX = -Infinity
  let maxY = -Infinity

  valid.forEach((pos) => {
    minX = Math.min(minX, pos.x)
    minY = Math.min(minY, pos.y)
    maxX = Math.max(maxX, pos.right ?? pos.x)
    maxY = Math.max(maxY, pos.bottom ?? pos.y)
  })

  return { minX, minY, maxX, maxY }
}

function findNonOverlappingPosition(node, initialPos, occupiedRects, opts) {
  const originalPos = normalizePosition(initialPos)
  let pos = { ...originalPos }
  let attempts = 0

  while (attempts < 64) {
    const rect = getNodeRect(node, opts, pos)
    const blocking = findBlockingRect(rect, occupiedRects, opts)
    if (!blocking) return pos

    attempts += 1
    pos = chooseCollisionSeparation(rect, blocking, originalPos, opts)
  }

  return pos
}

function placeNewNodes(nodes, edges, options = {}) {
  const opts = normalizeLayoutOptions(options)
  const direction = opts.direction || pickLayoutDirection(nodes, edges) || 'horizontal'
  const resolvedOpts = { ...opts, direction }
  const { inEdges, outEdges } = buildEdgeMaps(edges)
  const posMap = Object.fromEntries(
    nodes.map((node) => [node.id, isZeroPosition(node.position) ? null : normalizePosition(node.position)])
  )

  const unpositioned = nodes.filter((node) => isZeroPosition(posMap[node.id]))
  if (!unpositioned.length) return nodes

  const occupied = nodes
    .filter((node) => !isZeroPosition(posMap[node.id]))
    .map((node) => getNodeRect(node, opts, posMap[node.id]))

  unpositioned.forEach((node) => {
    const sources = (inEdges[node.id] || []).filter((id) => !isZeroPosition(posMap[id]))
    const targets = (outEdges[node.id] || []).filter((id) => !isZeroPosition(posMap[id]))

    let candidate = null

    if (sources.length) {
      const anchor = posMap[sources[0]]
      candidate = direction === 'vertical'
        ? { x: anchor.x, y: anchor.y + resolvedOpts.nodeHeight + resolvedOpts.gapY }
        : { x: anchor.x + resolvedOpts.nodeWidth + resolvedOpts.gapX, y: anchor.y }
    } else if (targets.length) {
      const anchor = posMap[targets[0]]
      candidate = direction === 'vertical'
        ? { x: anchor.x, y: anchor.y - resolvedOpts.nodeHeight - resolvedOpts.gapY }
        : { x: anchor.x - resolvedOpts.nodeWidth - resolvedOpts.gapX, y: anchor.y }
    } else if (occupied.length) {
      const bbox = getBoundingBox(occupied)
      candidate = direction === 'vertical'
        ? { x: bbox.minX, y: bbox.maxY + resolvedOpts.nodeHeight + resolvedOpts.gapY }
        : { x: bbox.maxX + resolvedOpts.gapX, y: bbox.minY }
    } else {
      candidate = { x: resolvedOpts.startX, y: resolvedOpts.startY }
    }

    const resolved = findNonOverlappingPosition(node, candidate, occupied, resolvedOpts)
    posMap[node.id] = resolved
    occupied.push(getNodeRect(node, resolvedOpts, resolved))
  })

  return nodes.map((node) => ({
    ...node,
    position: posMap[node.id]
  }))
}

/**
 * 合并已有画布位置：保留用户拖拽后的坐标，仅对新节点/无效坐标做布局
 */
export function applyWorkflowLayout(nodes, edges, existingNodes = [], options = {}) {
  if (!nodes?.length) return nodes

  const opts = normalizeLayoutOptions(options)
  const layoutDirection = opts.direction || pickLayoutDirection(nodes, edges)
  const resolvedOpts = { ...opts, direction: layoutDirection }
  const preservedIds = new Set(
    (existingNodes || [])
      .filter((node) => !isZeroPosition(node.position))
      .map((node) => node.id)
  )

  const existingMap = new Map(
    (existingNodes || []).map((node) => [node.id, node.position])
  )

  let mergedNodes = nodes.map((node) => {
    const preserved = existingMap.get(node.id)
    if (preserved && !isZeroPosition(preserved)) {
      return {
        ...node,
        position: normalizePosition(preserved)
      }
    }
    return node
  })

  const hasPreserved = preservedIds.size > 0
  const unpositionedCount = mergedNodes.filter((node) => isZeroPosition(node.position)).length
  const overlapping = hasOverlappingPositions(
    mergedNodes.filter((node) => !preservedIds.has(node.id) || isZeroPosition(node.position)),
    resolvedOpts
  )

  if (hasPreserved && unpositionedCount > 0) {
    mergedNodes = placeNewNodes(mergedNodes, edges, resolvedOpts)
    return mergedNodes
  }

  if (hasPreserved && !overlapping && unpositionedCount === 0) {
    return mergedNodes
  }

  if (needsAutoLayout(mergedNodes, resolvedOpts)) {
    return autoLayoutWorkflow(mergedNodes, edges, resolvedOpts)
  }

  return mergedNodes
}

/**
 * 自动布局工作流节点
 */
export function autoLayoutWorkflow(nodes, edges, options) {
  const opts = normalizeLayoutOptions(options)
  const direction = opts.direction || pickLayoutDirection(nodes, edges) || 'horizontal'
  const {
    nodeWidth,
    nodeHeight,
    gapX,
    gapY,
    nodeGapX,
    nodeGapY,
    startX,
    startY
  } = opts

  if (!nodes || nodes.length === 0) return nodes

  const nodeMap = {}
  nodes.forEach((node) => {
    nodeMap[node.id] = true
  })

  const { inEdges, outEdges } = buildEdgeMaps(edges)

  const nodeLayer = {}
  const remainingInDegree = {}

  nodes.forEach((node) => {
    remainingInDegree[node.id] = (inEdges[node.id] || []).filter((source) => nodeMap[source]).length
  })

  const queue = []
  nodes.forEach((node) => {
    if (remainingInDegree[node.id] === 0) {
      queue.push(node.id)
      nodeLayer[node.id] = 0
    }
  })

  if (queue.length === 0 && nodes.length > 0) {
    nodeLayer[nodes[0].id] = 0
    queue.push(nodes[0].id)
  }

  while (queue.length > 0) {
    const nodeId = queue.shift()
    const currentLayer = nodeLayer[nodeId] || 0
    ;(outEdges[nodeId] || []).forEach((targetId) => {
      if (!nodeMap[targetId]) return
      const newLayer = currentLayer + 1
      if (!nodeLayer[targetId] || nodeLayer[targetId] < newLayer) {
        nodeLayer[targetId] = newLayer
      }
      if (!queue.includes(targetId)) {
        queue.push(targetId)
      }
    })
  }

  nodes.forEach((node) => {
    if (nodeLayer[node.id] === undefined) {
      nodeLayer[node.id] = 0
    }
  })

  let maxLayer = 0
  Object.values(nodeLayer).forEach((layer) => {
    maxLayer = Math.max(maxLayer, layer)
  })

  const layers = []
  for (let i = 0; i <= maxLayer; i += 1) layers.push([])
  Object.entries(nodeLayer).forEach(([nodeId, layer]) => {
    layers[layer].push(nodeId)
  })

  layers.forEach((layer, layerIdx) => {
    if (layerIdx > 0) {
      layer.sort((a, b) => {
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

  const positions = {}

  if (direction === 'vertical') {
    layers.forEach((layer, layerIdx) => {
      const layerY = startY + layerIdx * (nodeHeight + gapY)
      const layerContentWidth = layer.length * nodeWidth + Math.max(0, layer.length - 1) * nodeGapX
      const layerX = startX - layerContentWidth / 2 + nodeWidth / 2

      layer.forEach((nodeId, nodeIdx) => {
        positions[nodeId] = {
          x: Math.round(layerX + nodeIdx * (nodeWidth + nodeGapX)),
          y: Math.round(layerY)
        }
      })
    })
  } else {
    const layerHeights = layers.map((layer) => (
      layer.length > 0
        ? layer.length * nodeHeight + Math.max(0, layer.length - 1) * nodeGapY
        : 0
    ))

    const layerStartY = []
    let accumulatedY = startY
    layerHeights.forEach((height) => {
      layerStartY.push(accumulatedY)
      accumulatedY += height + gapY
    })

    layers.forEach((layer, layerIdx) => {
      const layerX = startX + layerIdx * (nodeWidth + gapX)
      const layerY = layerStartY[layerIdx]

      layer.forEach((nodeId, nodeIdx) => {
        positions[nodeId] = {
          x: Math.round(layerX),
          y: Math.round(layerY + nodeIdx * (nodeHeight + nodeGapY))
        }
      })
    })
  }

  return nodes.map((node) => {
    const pos = positions[node.id] || { x: startX, y: startY }
    return { ...node, position: { x: pos.x, y: pos.y } }
  })
}
