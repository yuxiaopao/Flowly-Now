import { applyWorkflowLayout, pickLayoutDirection } from '@/utils/workflowLayout'
import { wireWorkflowVariableRefs } from '@/utils/nodeVariableWiring'

const BACKEND_RENDER_TYPES = {
  data_transform: 'transform',
  http_request: 'http',
  trigger: 'manual',
  template: 'text_template',
}

export function getBackendNodeType(node) {
  const original = node.data?.nodeType
  if (original && (BACKEND_RENDER_TYPES[original] || original) === node.type) return original
  return node.type === 'transform' ? 'data_transform' : node.type === 'http' ? 'http_request' : node.type
}

/**
 * 工作流数据格式转换工具
 * 处理前端 Vue Flow 格式与后端 API 格式之间的转换
 *
 * 重要：API 拦截器 (api/index.js) 会自动将后端返回的 snake_case 字段
 * 转换为 camelCase。因此这里使用 camelCase 字段名。
 *
 * 后端字段 -> API 响应字段 (转换后):
 *   position_x -> positionX
 *   position_y -> positionY
 *   node_type  -> nodeType
 *   sort_order -> sortOrder
 *   source_node_id -> sourceNodeId
 *   target_node_id -> targetNodeId
 *   source_node -> sourceNode
 *   target_node -> targetNode
 *   error_handling -> errorHandling
 *   max_retries -> maxRetries
 *   retry_delay -> retryDelay
 *   fallback_value -> fallbackValue
 *   node_type_display -> nodeTypeDisplay
 *   error_handling_display -> errorHandlingDisplay
 *   source_node_name -> sourceNodeName
 *   target_node_name -> targetNodeName
 */

/**
 * 将后端节点数据转换为 Vue Flow 格式
 * @param {Object} node - 后端节点对象（已经是 camelCase，因为 API 拦截器已转换）
 * @returns {Object} Vue Flow 格式的节点
 */
/**
 * 统一 Input/Output 节点 config 字段（前后端命名不一致）
 */
export function normalizeNodeConfig(config = {}, nodeType) {
  const cfg = { ...(config || {}) }

  if (nodeType === 'input') {
    const varName = cfg.variableName || cfg.input_name || cfg.inputName || ''
    if (varName) {
      cfg.variableName = varName
      cfg.input_name = varName
    }
  }

  if (nodeType === 'output') {
    const outVar = cfg.outputVariable || cfg.output_variable || ''
    if (outVar) {
      cfg.outputVariable = outVar
      cfg.output_variable = outVar
    }
  }

  return cfg
}

export function unwrapNodeExecutionOutput(output) {
  if (output == null) return output
  if (typeof output === 'string') return output
  if (typeof output !== 'object') return output
  if (output.output != null && typeof output.output === 'object') {
    const inner = output.output
  if (inner.images || inner.video_url || inner.videoUrl || inner.url || inner.audio_url) {
      return inner
    }
  }
  return output
}

/**
 * 保存工作流后，将画布节点/连线与后端响应对齐。
 * 优先按节点 ID 匹配（后端现已保留 UUID），避免按数组下标错配导致连线/配置错乱。
 */
function buildNodeMatchKey(node) {
  const type = node?.type || node?.data?.nodeType || node?.data?.type || ''
  const sortOrder = node?.data?.sortOrder ?? node?.sort_order ?? node?.data?.sort_order ?? ''
  const label = node?.data?.label ?? node?.name ?? ''
  return `${type}::${sortOrder}::${label}`
}

function remapEdgesWithIdMap(edges = [], idMap = {}) {
  return (edges || []).map((edge) => ({
    ...edge,
    source: idMap[edge.source] || edge.source,
    target: idMap[edge.target] || edge.target,
  }))
}

function hasFiniteCanvasPosition(position) {
  return Number.isFinite(Number(position?.x)) && Number.isFinite(Number(position?.y))
}

function normalizeCanvasPosition(position) {
  return {
    x: Number(Number(position?.x).toFixed(2)),
    y: Number(Number(position?.y).toFixed(2)),
  }
}

export function syncCanvasAfterSave(oldNodes = [], oldEdges = [], savedWorkflow = {}) {
  const converted = backendWorkflowToFrontend(savedWorkflow)
  const newNodes = converted.nodes || []
  const oldById = Object.fromEntries(
    (oldNodes || []).filter((node) => node?.id).map((node) => [String(node.id), node]),
  )
  const oldByKey = Object.fromEntries(
    (oldNodes || []).map((node) => [buildNodeMatchKey(node), node]),
  )
  const idMap = {}

  const syncedNodes = newNodes.map((newNode) => {
    const oldNode = oldById[String(newNode.id)] || oldByKey[buildNodeMatchKey(newNode)] || null
    if (oldNode?.id && newNode?.id && oldNode.id !== newNode.id) {
      idMap[oldNode.id] = newNode.id
    }
    if (!oldNode) return newNode
    return {
      ...newNode,
      type: oldNode.type || newNode.type,
      position: hasFiniteCanvasPosition(oldNode.position)
        ? normalizeCanvasPosition(oldNode.position)
        : newNode.position,
      data: {
        ...newNode.data,
        label: oldNode.data?.label ?? newNode.data?.label,
        description: oldNode.data?.description ?? newNode.data?.description,
        uiSize: oldNode.data?.uiSize ?? newNode.data?.uiSize ?? null,
        _runtime: oldNode.data?._runtime ?? newNode.data?._runtime ?? null,
        config: {
          ...(newNode.data?.config || {}),
          ...(oldNode.data?.config || {}),
        },
      },
    }
  })

  let syncedEdges = (converted.edges || []).map((edge) => ({ ...edge }))
  if (!syncedEdges.length && (oldEdges || []).length) {
    syncedEdges = remapEdgesWithIdMap(oldEdges, idMap)
  }

  return { nodes: syncedNodes, edges: syncedEdges, idMap }
}

const MULTIMODAL_CHAIN_EDGE_TYPES = [
  ['start', 'input'],
  ['input', 'image_generation'],
  ['image_generation', 'video_generation'],
  ['video_generation', 'output'],
  ['output', 'end'],
]

/**
 * 补齐多模态标准链路连线：开始 → 输入 → 文生图 → 图生视频 → 输出 → 结束
 */
export function ensureMultimodalChainEdges(nodes = [], edges = []) {
  const getType = (node) => node?.type || node?.data?.nodeType || node?.data?.type
  const hasMultimodal = (nodes || []).some((node) => ['image_generation', 'video_generation'].includes(getType(node)))
  if (!hasMultimodal) {
    return { nodes, edges, patched: false }
  }

  const byType = {}
  const typeCounts = {}
  ;(nodes || []).forEach((node) => {
    const nodeType = getType(node)
    typeCounts[nodeType] = (typeCounts[nodeType] || 0) + 1
    if (nodeType && !byType[nodeType]) {
      byType[nodeType] = node
    }
  })

  // A template cannot infer which media branch belongs to which output.
  // Preserve authored multi-shot graphs instead of connecting their first nodes.
  if (MULTIMODAL_CHAIN_EDGE_TYPES.some(([source, target]) =>
    typeCounts[source] > 1 || typeCounts[target] > 1)) {
    return { nodes, edges, patched: false }
  }

  const nextEdges = [...(edges || [])]
  const existing = new Set(nextEdges.map((edge) => `${edge.source}->${edge.target}`))
  let patched = false

  const hasPath = (source, target) => {
    const queue = [source]
    const visited = new Set()
    for (let index = 0; index < queue.length; index++) {
      const current = queue[index]
      if (current === target) return true
      if (visited.has(current)) continue
      visited.add(current)
      nextEdges.forEach((edge) => {
        if (edge.source === current && !visited.has(edge.target)) queue.push(edge.target)
      })
    }
    return false
  }

  MULTIMODAL_CHAIN_EDGE_TYPES.forEach(([sourceType, targetType]) => {
    const sourceNode = byType[sourceType]
    const targetNode = byType[targetType]
    if (!sourceNode?.id || !targetNode?.id) return
    const key = `${sourceNode.id}->${targetNode.id}`
    if (existing.has(key) || hasPath(sourceNode.id, targetNode.id)) return
    nextEdges.push(createEdgeFromConnection({ source: sourceNode.id, target: targetNode.id }))
    existing.add(key)
    patched = true
  })

  return { nodes, edges: nextEdges, patched }
}

/**
 * 自动补齐多模态链路配置与连线
 */
export function ensureMultimodalWorkflowGraph(nodes = [], edges = []) {
  const edgePatch = ensureMultimodalChainEdges(nodes, edges)
  const configPatch = ensureMultimodalChainConfig(edgePatch.nodes, edgePatch.edges)
  return {
    nodes: configPatch.nodes,
    edges: edgePatch.edges,
    patched: edgePatch.patched || configPatch.patched,
  }
}

/**
 * 当视频节点上游连接文生图时，自动补齐图生视频链路配置。
 */
function getNodeType(node) {
  return node?.type || node?.data?.type
}

function hasUpstreamType(nodeId, edges, nodeById, sourceTypes = []) {
  return (edges || []).some((edge) => {
    if (edge.target !== nodeId) return false
    const sourceType = getNodeType(nodeById[edge.source])
    return sourceTypes.includes(sourceType)
  })
}

function getUpstreamNodes(nodeId, edges, nodeById, sourceTypes = []) {
  return (edges || [])
    .filter((edge) => edge.target === nodeId)
    .map((edge) => nodeById[edge.source])
    .filter((node) => node && sourceTypes.includes(getNodeType(node)))
}

/**
 * 自动补齐多模态链路配置：输入 → 文生图 → 图生视频 → 输出
 */
export function ensureMultimodalChainConfig(nodes = [], edges = []) {
  // 通用按边传参（空字段才填），再叠加多模态 provider / 标签特例
  const wired = wireWorkflowVariableRefs(nodes, edges)
  nodes = wired.nodes
  const nodeById = Object.fromEntries((nodes || []).map((node) => [node.id, node]))
  let patched = wired.patched

  ;(nodes || []).forEach((node) => {
    const nodeType = getNodeType(node)
    const config = { ...(node.data?.config || {}) }
    let label = node.data?.label
    let changed = false

    if (nodeType === 'image_generation' && hasUpstreamType(node.id, edges, nodeById, ['input'])) {
      // 交给 wireWorkflowVariableRefs；这里仅在仍为空时按上游 input 变量名兜底
      if (!config.prompt && !config.text) {
        const inputNodes = getUpstreamNodes(node.id, edges, nodeById, ['input'])
        const inputCfg = inputNodes[0]?.data?.config || {}
        const varName = inputCfg.input_name || inputCfg.variable_name || inputCfg.variableName || 'prompt'
        config.prompt = `{${varName}}`
        changed = true
      }
    }

    if (nodeType === 'video_generation' && hasUpstreamType(
      node.id,
      edges,
      nodeById,
      ['image_generation', 'image_editing'],
    )) {
      // 图边只补图片槽；文案槽仅在确有 input/llm 上游时再填，避免图连线乱填 prompt
      if (!config.inputImage && !config.input_image && !config.image) {
        config.inputImage = '{images.0.url}'
        changed = true
      }
      const hasTextUpstream = hasUpstreamType(
        node.id,
        edges,
        nodeById,
        ['input', 'llm', 'prompt'],
      )
      if (hasTextUpstream && !config.prompt && !config.text) {
        if (hasUpstreamType(node.id, edges, nodeById, ['llm', 'prompt'])) {
          config.prompt = '{text}'
        } else {
          const inputNodes = getUpstreamNodes(node.id, edges, nodeById, ['input'])
          const inputCfg = inputNodes[0]?.data?.config || {}
          const varName = inputCfg.input_name || inputCfg.variable_name || inputCfg.variableName || 'prompt'
          config.prompt = `{${varName}}`
        }
        changed = true
      }
      const upstreamImageNodes = getUpstreamNodes(
        node.id,
        edges,
        nodeById,
        ['image_generation', 'image_editing'],
      )
      const upstreamProvider = upstreamImageNodes
        .map((n) => n?.data?.config?.provider)
        .find(Boolean)
      // 上游文生图用 Agnes 时，图生视频也走 Agnes（当前环境 DashScope Key 常不可用）
      const preferredProvider = upstreamProvider === 'agnes' ? 'agnes' : (config.provider || 'dashscope')
      if (!config.provider || (config.provider === 'dashscope' && upstreamProvider === 'agnes')) {
        config.provider = preferredProvider
        if (preferredProvider === 'agnes') {
          config.model = config.model?.startsWith('agnes-video') ? config.model : 'agnes-video-v2.0'
        } else {
          config.model = config.model && String(config.model).includes('i2v')
            ? config.model
            : 'wanx2.1-i2v-turbo'
        }
        changed = true
      }
      if (label === '文生视频') {
        label = '图生视频'
        changed = true
      }
    }

    if (nodeType === 'output' && hasUpstreamType(
      node.id,
      edges,
      nodeById,
      ['video_generation', 'image_generation', 'image_editing'],
    )) {
      const upstreamVideo = hasUpstreamType(node.id, edges, nodeById, ['video_generation'])
      const upstreamImage = hasUpstreamType(node.id, edges, nodeById, ['image_generation', 'image_editing'])
      if (!config.template) {
        config.template = upstreamVideo ? '{video_url}' : (upstreamImage ? '{images.0.url}' : config.template)
        changed = true
      }
    }

    if (changed) {
      patched = true
      node.data = {
        ...(node.data || {}),
        config,
        ...(label ? { label } : {}),
      }
    }
  })

  return { nodes, patched }
}

export function backendNodeToVueFlow(node) {
  // 后端 node_type -> 前端 VueFlow type 的反向映射
  // constants.py 中 DATA_TRANSFORM = "data_transform"，但前端注册为 "transform"
  const rawType = node.nodeType || node.node_type
  const type = BACKEND_RENDER_TYPES[rawType] || rawType

  return {
    id: String(node.id),
    type,
    position: {
      x: Number(node.positionX ?? node.position_x ?? node.position?.x ?? 0),
      y: Number(node.positionY ?? node.position_y ?? node.position?.y ?? 0)
    },
    data: {
      id: node.id,
      label: node.name,
      description: node.description || '',
      nodeType: node.nodeType || node.node_type,
      config: normalizeNodeConfig(node.config || {}, type),
      style: node.style || {},
      uiSize: node.style?.uiSize || node.uiSize || null,
      _runtime: node.style?._runtime || null,
      sortOrder: node.sortOrder || node.sort_order || 0,
      // Error handling
      errorHandling: node.errorHandling || node.error_handling || 'stop',
      maxRetries: node.maxRetries || node.max_retries || 3,
      retryDelay: node.retryDelay || node.retry_delay || 1.0,
      fallbackValue: node.fallbackValue || node.fallback_value,
      ...(node.extraData || node.extra_data || {})
    },
    style: node.style || {}
  }
}

/**
 * 将 Vue Flow 节点转换为后端格式
 * @param {Object} node - Vue Flow 节点对象
 * @param {number|string} workflowId - 工作流 ID
 * @returns {Object} 后端格式的节点数据
 */
export function vueFlowNodeToBackend(node, workflowId) {
  return {
    id: node.id,
    workflow: workflowId,
    node_type: getBackendNodeType(node),
    name: node.data?.label || node.data?.name || '节点',
    description: node.data?.description || '',
    position_x: hasFiniteCanvasPosition(node.position) ? normalizeCanvasPosition(node.position).x : 0,
    position_y: hasFiniteCanvasPosition(node.position) ? normalizeCanvasPosition(node.position).y : 0,
    sort_order: node.data?.sortOrder || node.sortOrder || 0,
    config: normalizeNodeConfig(node.data?.config || {}, node.type),
    style: {
      ...(node.data?.style || node.style || {}),
      ...(node.data?.uiSize ? { uiSize: node.data.uiSize } : {}),
      ...(node.data?._runtime ? { _runtime: node.data._runtime } : {}),
    },
  }
}

/**
 * 将后端边数据转换为 Vue Flow 格式
 * @param {Object} edge - 后端边对象（已经是 camelCase）
 * @returns {Object} Vue Flow 格式的边
 */
export function backendEdgeToVueFlow(edge) {
  // After camelCase conversion: source_node->sourceNode, source_node_id->sourceNodeId
  // After camelCase conversion: target_node->targetNode, target_node_id->targetNodeId
  let source = edge.sourceNodeId || edge.source_node_id || edge.sourceNode
  let target = edge.targetNodeId || edge.target_node_id || edge.targetNode

  // If source/target are strings, use directly
  if (typeof source === 'string') {
    // already a string UUID
  } else if (typeof edge.sourceNode === 'string' || typeof edge.source_node === 'string') {
    source = edge.sourceNode || edge.source_node
  } else if (typeof edge.source === 'string' && edge.sourceNode == null && edge.source_node == null) {
    source = edge.source
  }

  if (typeof target === 'string') {
    // already a string UUID
  } else if (typeof edge.targetNode === 'string' || typeof edge.target_node === 'string') {
    target = edge.targetNode || edge.target_node
  } else if (typeof edge.target === 'string' && edge.targetNode == null && edge.target_node == null) {
    target = edge.target
  }

  return {
    id: String(edge.id),
    source: String(source || ''),
    target: String(target || ''),
    label: edge.label || '',
    type: edge.type || 'default',
    animated: edge.animated || false,
    style: edge.style || {},
    data: {
      condition: edge.condition || {}
    }
  }
}

/**
 * 将 Vue Flow 边转换为后端格式
 * @param {Object} edge - Vue Flow 边对象
 * @param {number|string} workflowId - 工作流 ID
 * @returns {Object} 后端格式的边数据
 */
export function vueFlowEdgeToBackend(edge, workflowId) {
  return {
    id: edge.id,
    workflow: workflowId,
    source_node: edge.source,
    target_node: edge.target,
    label: edge.label || '',
    type: edge.type || 'default',
    animated: edge.animated || false,
    condition: edge.data?.condition || {}
  }
}

/**
 * 将后端工作流数据转换为前端格式
 * @param {Object} workflow - 后端工作流对象
 * @returns {Object} 前端格式的工作流数据
 */
export function backendWorkflowToFrontend(workflow) {
  return {
    ...workflow,
    nodes: (workflow.nodes || []).map(n => backendNodeToVueFlow(n)),
    edges: (workflow.edges || []).map(e => backendEdgeToVueFlow(e))
  }
}

/**
 * 将前端工作流数据转换为后端格式
 * @param {Object} workflow - 前端工作流对象
 * @param {number|string} workflowId - 工作流 ID
 * @returns {Object} 后端格式的工作流数据
 */
export function frontendWorkflowToBackend(workflow, workflowId) {
  return {
    name: workflow.name,
    description: workflow.description,
    status: workflow.status,
    is_public: workflow.isPublic || workflow.is_public,
    tags: workflow.tags || [],
    settings: workflow.settings || {},
    nodes: (workflow.nodes || []).map(n => vueFlowNodeToBackend(n, workflowId)),
    edges: (workflow.edges || []).map(e => vueFlowEdgeToBackend(e, workflowId))
  }
}

/**
 * 批量转换节点数组
 * @param {Array} nodes - 节点数组
 * @param {number|string} workflowId - 工作流 ID
 * @returns {Array} 后端格式的节点数组
 */
export function batchConvertNodes(nodes, workflowId) {
  return nodes.map(n => vueFlowNodeToBackend(n, workflowId))
}

/**
 * 批量转换边数组
 * @param {Array} edges - 边数组
 * @param {number|string} workflowId - 工作流 ID
 * @returns {Array} 后端格式的边数组
 */
export function batchConvertEdges(edges, workflowId) {
  return edges.map(e => vueFlowEdgeToBackend(e, workflowId))
}

/**
 * 从 Vue Flow 连接事件创建边数据
 * @param {Object} connection - Vue Flow 连接对象
 * @returns {Object} 边数据
 */
export function createEdgeFromConnection(connection) {
  return {
    id: `edge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle,
    type: 'default',
    animated: false,
    label: ''
  }
}

/**
 * 将编辑器 Vue Flow 数据转为 NL/后端 JSON 工作流格式
 */
export function vueFlowToNlWorkflow(nodes = [], edges = [], meta = {}) {
  return {
    name: meta.name || '未命名工作流',
    description: meta.description || '',
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.type,
      name: n.data?.label || n.data?.name || n.type,
      position: hasFiniteCanvasPosition(n.position) ? normalizeCanvasPosition(n.position) : { x: 0, y: 0 },
      config: n.data?.config || {}
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label || ''
    }))
  }
}

/**
 * 将 NL/后端 JSON 工作流转为 Vue Flow 画布格式
 * @param {Object} workflow - NL 工作流 JSON
 * @param {Object} options
 * @param {Array} options.preserveNodes - 已有画布节点，保留用户拖拽后的位置
 * @param {'horizontal'|'vertical'|'auto'} options.direction - 布局方向，默认 auto
 */
export function nlWorkflowToVueFlow(workflow, options = {}) {
  const rawNodes = workflow?.nodes || []
  const rawEdges = workflow?.edges || []
  if (!rawNodes.length) {
    return { nodes: [], edges: [] }
  }

  const nodes = rawNodes.map((n, idx) => {
    const nested = (n.data && typeof n.data === 'object') ? n.data : {}
    const ntype = n.type || nested.type || 'llm'
    const cfg = (n.config && Object.keys(n.config).length)
      ? n.config
      : (nested.config || {})
    return {
      id: n.id || `node_${idx}`,
      type: ntype,
      position: hasFiniteCanvasPosition(n.position) ? normalizeCanvasPosition(n.position) : null,
      data: {
        label: n.name || n.label || nested.label || ntype,
        nodeType: ntype,
        config: cfg || {},
        description: n.description || nested.description || ''
      }
    }
  })

  // 宽扇出工作流：同类节点横排（vertical direction）。
  // 短剧模板已自带「上中下三行」坐标，保留不覆盖。
  const genMode = String(workflow?._generation_mode || '')
  const keepCustomGrid = genMode.includes('short_drama') || options.preserveLayout === true
  const autoDirection = pickLayoutDirection(nodes, rawEdges)
  if (!keepCustomGrid && autoDirection === 'vertical') {
    nodes.forEach((node) => {
      node.position = null
    })
  }

  const layoutOptions = {
    direction: options.direction === 'auto' || !options.direction
      ? (keepCustomGrid ? undefined : autoDirection)
      : options.direction
  }

  const layoutedNodes = applyWorkflowLayout(
    nodes,
    rawEdges,
    keepCustomGrid ? (options.preserveNodes || []) : [],
    layoutOptions
  )

  const edges = rawEdges.map((e, idx) => ({
    id: e.id || `edge_${idx}`,
    source: e.source,
    target: e.target,
    label: e.label || '',
    type: 'default',
    animated: false
  }))

  return { nodes: layoutedNodes, edges }
}

/**
 * 将 NL 工作流 JSON 转为后端 /workflows/ 保存 payload
 */
export function nlWorkflowToSavePayload(workflow, overrides = {}) {
  if (!workflow?.nodes?.length) return null
  return {
    name: overrides.name || workflow.name || '未命名工作流',
    description: overrides.description || workflow.description || '',
    nodes: workflow.nodes,
    edges: workflow.edges || [],
    status: overrides.status || 'draft',
  }
}

/**
 * Marketplace/template normalization helpers
 */
export function getTemplateCategory(template) {
  if (template?.displayCategory && template.displayCategory !== 'uncategorized') {
    return template.displayCategory
  }

  const categoryObject = template?.category
  if (categoryObject && typeof categoryObject === 'object') {
    return categoryObject.slug || categoryObject.name || 'uncategorized'
  }

  return (
    template?.categorySlug
    ?? template?.category_slug
    ?? template?.categoryName
    ?? template?.category_name
    ?? (typeof template?.category === 'string' ? template.category : null)
    ?? 'uncategorized'
  )
}

export function getTemplateNodeCount(template) {
  return (
    template?.nodeCount
    ?? template?.node_count
    ?? template?.nodes?.length
    ?? template?.workflowData?.nodes?.length
    ?? template?.workflow_data?.nodes?.length
    ?? 0
  )
}

export function getTemplateUseCount(template) {
  return template?.useCount ?? template?.use_count ?? template?.usage_count ?? 0
}

export function getTemplateInstallCount(template) {
  return getTemplateUseCount(template)
}

export function getTemplateRating(template) {
  return Number(template?.rating ?? 0)
}

export function getTemplateAuthor(template) {
  return template?.creatorName ?? template?.creator_name ?? template?.author_name ?? template?.author ?? '未知'
}

export function getTemplateNodes(template) {
  return template?.nodes || template?.workflow_data?.nodes || []
}

export function getTemplateFeatures(template) {
  return template?.features || []
}

export function getTemplateTags(template) {
  return template?.tags || []
}

export function isTemplatePublic(template) {
  return Boolean(template?.isPublic ?? template?.is_public)
}
