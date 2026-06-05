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
export function backendNodeToVueFlow(node) {
  // 后端 node_type -> 前端 VueFlow type 的反向映射
  // constants.py 中 DATA_TRANSFORM = "data_transform"，但前端注册为 "transform"
  const REVERSE_TYPE_MAP = {
    data_transform: 'transform',
    csv_transform: 'transform',
    json_transform: 'transform',
  }
  const rawType = node.nodeType || node.node_type
  const type = REVERSE_TYPE_MAP[rawType] || rawType

  return {
    id: String(node.id),
    type,
    position: {
      x: Number(node.positionX) || Number(node.position_x) || Number(node.position?.x) || 0,
      y: Number(node.positionY) || Number(node.position_y) || Number(node.position?.y) || 0
    },
    data: {
      id: node.id,
      label: node.name,
      description: node.description || '',
      nodeType: node.nodeType || node.node_type,
      config: node.config || {},
      style: node.style || {},
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
    node_type: node.type,
    name: node.data?.label || node.data?.name || 'Node',
    description: node.data?.description || '',
    position_x: node.position?.x || 0,
    position_y: node.position?.y || 0,
    sort_order: node.data?.sortOrder || node.sortOrder || 0,
    config: node.data?.config || {},
    style: node.style || node.data?.style || {}
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
 * Marketplace/template normalization helpers
 */
export function getTemplateCategory(template) {
  return template?.category_slug || template?.category_name || template?.category || 'uncategorized'
}

export function getTemplateNodeCount(template) {
  return template?.node_count || template?.nodes?.length || template?.workflow_data?.nodes?.length || 0
}

export function getTemplateUseCount(template) {
  return template?.use_count ?? template?.install_count ?? template?.usage_count ?? template?.installs ?? 0
}

export function getTemplateInstallCount(template) {
  return getTemplateUseCount(template)
}

export function getTemplateRating(template) {
  return Number(template?.rating ?? template?.avg_rating ?? 0)
}

export function getTemplateAuthor(template) {
  return template?.author_name || template?.author || '未知'
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
  return Boolean(template?.is_public ?? template?.is_published)
}
