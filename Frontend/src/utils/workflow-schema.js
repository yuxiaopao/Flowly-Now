/**
 * Workflow Schema Validation Utility
 * Validates workflow structure, connectivity, and node configurations
 */

import { ElMessage } from 'element-plus'

/**
 * @typedef {Object} ValidationError
 * @property {string} type - Error type identifier
 * @property {string} message - Human-readable error message
 * @property {string} [nodeId] - Affected node ID
 * @property {string} [field] - Affected field name
 * @property {'error'|'warning'} severity
 */

/**
 * @typedef {Object} ValidationResult
 * @property {boolean} valid - Whether the workflow is valid
 * @property {ValidationError[]} errors - Critical errors
 * @property {ValidationError[]} warnings - Non-critical warnings
 * @property {Record<string, string[]>} [nodeErrors] - nodeId -> error message array map for highlighting
 */

/**
 * 验证工作流 Schema
 * @param {Array} nodes - Workflow nodes
 * @param {Array} edges - Workflow edges
 * @returns {ValidationResult}
 */
export function validateWorkflowSchema(nodes = [], edges = []) {
  const errors = []
  const warnings = []
  const nodeErrors = {}

  // 1. 结构验证：Start/End 节点（可选，不强制要求）
  const startNodes = nodes.filter(n => n.type === 'start')
  const endNodes = nodes.filter(n => n.type === 'end')

  if (startNodes.length > 1) {
    errors.push({
      type: 'multiple_start',
      message: `存在 ${startNodes.length} 个开始节点，只能有一个`,
      nodeId: startNodes[1]?.id,
      severity: 'error'
    })
  }

  if (startNodes.length === 0) {
    warnings.push({
      type: 'no_start',
      message: '建议添加开始节点作为工作流入口（可选）',
      severity: 'warning'
    })
  }

  if (endNodes.length === 0) {
    warnings.push({
      type: 'no_end',
      message: '建议添加结束节点作为工作流终点（可选）',
      severity: 'warning'
    })
  }

  // 2. 连通性验证
  const connectivityResult = checkConnectivity(nodes, edges)
  errors.push(...connectivityResult.errors)
  warnings.push(...connectivityResult.warnings)

  // 3. 类型特定验证
  for (const node of nodes) {
    const nodeValidation = validateNodeConfig(node)
    errors.push(...nodeValidation.errors.map(e => ({ ...e, nodeId: node.id })))
    warnings.push(...nodeValidation.warnings.map(w => ({ ...w, nodeId: node.id })))
  }

  // 4. 变量引用验证
  const varValidation = validateVariableReferences(nodes)
  errors.push(...varValidation.errors)
  warnings.push(...varValidation.warnings)

  // 5. 循环引用检测
  const cycleResult = detectCycles(nodes, edges)
  if (cycleResult.hasCycle) {
    errors.push({
      type: 'cycle_detected',
      message: `检测到循环引用: ${cycleResult.path.join(' → ')}`,
      severity: 'error'
    })
  }

  // 6. 子工作流嵌套循环检测
  const subworkflowCycle = detectSubworkflowCycles(nodes)
  if (subworkflowCycle.hasCycle) {
    errors.push({
      type: 'subworkflow_cycle',
      message: `子工作流嵌套循环: ${subworkflowCycle.path.join(' → ')}`,
      severity: 'error'
    })
  }

  // 构建 nodeErrors 映射（用于画布高亮）
  for (const err of errors) {
    if (err.nodeId) {
      if (!nodeErrors[err.nodeId]) {
        nodeErrors[err.nodeId] = []
      }
      nodeErrors[err.nodeId].push(err.message)
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    nodeErrors
  }
}

/**
 * 检查连通性
 */
function checkConnectivity(nodes, edges) {
  const errors = []
  const warnings = []

  if (nodes.length === 0) {
    errors.push({
      type: 'empty_workflow',
      message: '工作流为空',
      severity: 'error'
    })
    return { errors, warnings }
  }

  // 构建邻接表
  const adjacency = new Map()
  const inDegree = new Map()
  const outDegree = new Map()

  for (const node of nodes) {
    adjacency.set(node.id, [])
    inDegree.set(node.id, 0)
    outDegree.set(node.id, 0)
  }

  for (const edge of edges) {
    if (adjacency.has(edge.source) && adjacency.has(edge.target)) {
      adjacency.get(edge.source).push(edge.target)
      inDegree.set(edge.target, (inDegree.get(edge.target) || 0) + 1)
      outDegree.set(edge.source, (outDegree.get(edge.source) || 0) + 1)
    }
  }

  // 找起始节点（入度为0的非start节点，排除孤立节点）
  const orphanedNodes = nodes.filter(n => {
    const indeg = inDegree.get(n.id) || 0
    const outdeg = outDegree.get(n.id) || 0
    return indeg === 0 && outdeg === 0 && n.type !== 'start' && n.type !== 'end'
  })

  for (const node of orphanedNodes) {
    warnings.push({
      type: 'isolated_node',
      message: `节点 "${node.data?.label || node.id}" 是孤立节点，既无上游也无下游`,
      nodeId: node.id,
      severity: 'warning'
    })
  }

  // BFS 检查从 start 到 end 的可达性
  const startNode = nodes.find(n => n.type === 'start')
  if (startNode) {
    const reachable = bfs(startNode.id, adjacency)

    const unreachable = nodes.filter(n => {
      return n.type !== 'start' && n.type !== 'end' && !reachable.has(n.id)
    })

    for (const node of unreachable) {
      errors.push({
        type: 'unreachable',
        message: `节点 "${node.data?.label || node.id}" 从开始节点不可达`,
        nodeId: node.id,
        severity: 'error'
      })
    }

    // 检查是否有节点无法到达结束节点
    const reverseAdjacency = new Map()
    for (const node of nodes) {
      reverseAdjacency.set(node.id, [])
    }
    for (const edge of edges) {
      if (reverseAdjacency.has(edge.target)) {
        reverseAdjacency.get(edge.target).push(edge.source)
      }
    }

    const endNode = nodes.find(n => n.type === 'end')
    if (endNode) {
      const canReachEnd = bfs(endNode.id, reverseAdjacency)
      const cantReachEnd = nodes.filter(n => {
        return n.type !== 'end' && n.type !== 'start' && !canReachEnd.has(n.id)
      })
      for (const node of cantReachEnd) {
        errors.push({
          type: 'cant_reach_end',
          message: `节点 "${node.data?.label || node.id}" 无法到达结束节点`,
          nodeId: node.id,
          severity: 'error'
        })
      }
    }
  }

  return { errors, warnings }
}

/**
 * BFS 遍历
 */
function bfs(startId, adjacency) {
  const visited = new Set()
  const queue = [startId]
  visited.add(startId)

  while (queue.length > 0) {
    const current = queue.shift()
    const neighbors = adjacency.get(current) || []
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor)
        queue.push(neighbor)
      }
    }
  }

  return visited
}

/**
 * 验证单个节点配置
 */
function validateNodeConfig(node) {
  const errors = []
  const warnings = []
  const config = node.data?.config || {}

  switch (node.type) {
    case 'llm':
      if (!config.model) {
        errors.push({
          type: 'llm_missing_model',
          message: 'LLM 节点未选择模型',
          field: 'model',
          severity: 'error'
        })
      }
      if (!config.systemPrompt && !config.userTemplate) {
        warnings.push({
          type: 'llm_missing_prompt',
          message: 'LLM 节点缺少提示词配置',
          field: 'prompt',
          severity: 'warning'
        })
      }
      break

    case 'http':
      if (!config.url) {
        errors.push({
          type: 'http_missing_url',
          message: 'HTTP 节点未配置 URL',
          field: 'url',
          severity: 'error'
        })
      } else if (!isValidUrl(config.url)) {
        errors.push({
          type: 'http_invalid_url',
          message: `HTTP 节点 URL 格式无效: ${config.url}`,
          field: 'url',
          severity: 'error'
        })
      }
      break

    case 'code': {
      const codeText = String(config.code || config.script || config.source || '').trim()
      if (!codeText) {
        errors.push({
          type: 'code_missing',
          message: '代码节点未输入代码',
          field: 'code',
          severity: 'error'
        })
      }
      // 危险代码模式检测
      const dangerousPatterns = [
        { pattern: /import\s+os\s*/, msg: '禁止导入 os 模块' },
        { pattern: /import\s+subprocess/, msg: '禁止导入 subprocess 模块' },
        { pattern: /import\s+sys\s*/, msg: '禁止导入 sys 模块' },
        { pattern: /__import__/, msg: '禁止使用 __import__' },
        { pattern: /exec\s*\(/, msg: '禁止使用 exec()' },
        { pattern: /eval\s*\(/, msg: '禁止使用 eval()' },
        { pattern: /open\s*\(/, msg: '禁止使用 open()' },
      ]
      for (const { pattern, msg } of dangerousPatterns) {
        if (pattern.test(codeText)) {
          errors.push({
            type: 'code_dangerous_pattern',
            message: `代码节点 ${msg}`,
            field: 'code',
            severity: 'error'
          })
        }
      }
      break
    }

    case 'switch': {
      const branches = config.branches || []
      if (branches.length === 0) {
        errors.push({
          type: 'switch_no_branches',
          message: 'Switch 节点没有配置任何分支',
          field: 'branches',
          severity: 'error'
        })
      }
      const emptyBranches = branches.filter(b => {
        if (b.conditionType === 'expression') return !b.expression
        return !b.field || !b.operator
      })
      if (emptyBranches.length > 0) {
        warnings.push({
          type: 'switch_empty_condition',
          message: `Switch 节点有 ${emptyBranches.length} 个分支缺少条件配置`,
          field: 'branches',
          severity: 'warning'
        })
      }
      break
    }

    case 'subworkflow':
      if (!config.subworkflowId) {
        errors.push({
          type: 'subworkflow_missing',
          message: '子工作流节点未选择子工作流',
          field: 'subworkflowId',
          severity: 'error'
        })
      }
      break

    case 'loop':
      if (!config.items && !config.itemsSource) {
        warnings.push({
          type: 'loop_no_items',
          message: '循环节点未配置循环数据源',
          field: 'items',
          severity: 'warning'
        })
      }
      if (config.maxIterations && config.maxIterations < 1) {
        errors.push({
          type: 'loop_invalid_iterations',
          message: '最大迭代次数必须大于 0',
          field: 'maxIterations',
          severity: 'error'
        })
      }
      break

    case 'variable': {
      const assignments = config.assignments || []
      if (assignments.length === 0) {
        warnings.push({
          type: 'variable_no_assignments',
          message: '变量节点没有配置任何赋值',
          field: 'assignments',
          severity: 'warning'
        })
      }
      break
    }

    case 'condition': {
      const conditions = config.conditions || []
      if (conditions.length === 0) {
        warnings.push({
          type: 'condition_no_conditions',
          message: '条件节点没有配置任何条件',
          field: 'conditions',
          severity: 'warning'
        })
      }
      break
    }

    case 'delay':
      if (!config.duration && !config.delayType) {
        warnings.push({
          type: 'delay_no_duration',
          message: '延迟节点未配置延迟时间',
          field: 'duration',
          severity: 'warning'
        })
      }
      break

    case 'prompt':
      if (!config.template) {
        warnings.push({
          type: 'prompt_missing_template',
          message: '提示词节点未配置模板',
          field: 'template',
          severity: 'warning'
        })
      }
      break

    case 'input': {
      const inputVarName = config.variableName || config.input_name || config.inputName
      if (!inputVarName) {
        warnings.push({
          type: 'input_missing_variable',
          message: '输入节点未配置变量名',
          field: 'variableName',
          severity: 'warning'
        })
      }
      break
    }

    case 'tool':
      if (!config.tool) {
        errors.push({
          type: 'tool_not_selected',
          message: '工具节点未选择工具',
          field: 'tool',
          severity: 'error'
        })
      }
      break
  }

  return { errors, warnings }
}

/**
 * 验证变量引用
 */
function validateVariableReferences(nodes) {
  const errors = []
  const warnings = []

  // 提取所有定义的变量名
  const definedVars = new Set()
  for (const node of nodes) {
    const config = node.data?.config || {}
    if (node.type === 'variable') {
      const assignments = config.assignments || []
      for (const a of assignments) {
        if (a.name) definedVars.add(a.name)
      }
    }
    if (node.type === 'input') {
      const varName = config.variableName
        || config.input_name
        || config.inputName
      if (varName) definedVars.add(varName)
    }
    if (node.type === 'loop') {
      const itemVar = config.item_variable || config.item_var || config.itemVar
      if (itemVar) definedVars.add(itemVar)
      const indexVar = config.index_variable || config.index_var || 'index'
      if (indexVar) definedVars.add(indexVar)
    }
    if (node.type === 'json_transform' || node.type === 'json') {
      if (config.target_field) definedVars.add(config.target_field)
    }
    if (node.type === 'set' || node.type === 'variable_set') {
      if (config.name) definedVars.add(config.name)
      if (config.key) definedVars.add(config.key)
    }
    // Common multimodal / pipeline outputs produced by executors
    if (node.type === 'image_generation') {
      definedVars.add('images')
      definedVars.add('images.0.url')
      definedVars.add('prompt')
    }
    if (node.type === 'video_generation') {
      definedVars.add('video_url')
      definedVars.add('images.0.url')
    }
    if (node.type === 'subtitle_generation') {
      definedVars.add('subtitles')
      definedVars.add('video_url')
    }
    if (node.type === 'code') {
      definedVars.add('result')
      definedVars.add('enriched_shots')
    }
  }
  // Built-in / edge-fed names commonly used across pipelines
  ['input', 'output', 'result', 'data', 'prompt', 'text', 'content'].forEach((name) => {
    definedVars.add(name)
  })

  // 提取所有引用的变量
  const usedVars = new Set()
  const varPattern = /\{\{\s*([^}]+)\s*\}\}/g

  for (const node of nodes) {
    const dataStr = JSON.stringify(node.data || {})
    let match
    while ((match = varPattern.exec(dataStr)) !== null) {
      usedVars.add(match[1].trim())
    }
  }

  // 检查未定义的引用
  for (const varName of usedVars) {
    if (!definedVars.has(varName)) {
      // 检查是否是内置变量
      const builtinVars = ['workflow.id', 'workflow.name', 'workflow.created_at',
        'execution.id', 'execution.started_at', 'timestamp', 'env.NODE_ENV',
        'env.DATE', 'env.TIME', 'random.id', 'input', 'output', 'result']
      if (!builtinVars.includes(varName)) {
        warnings.push({
          type: 'undefined_variable',
          message: `引用了未定义的变量: ${varName}`,
          severity: 'warning'
        })
      }
    }
  }

  return { errors, warnings }
}

/**
 * 检测循环引用（普通节点）
 */
function detectCycles(nodes, edges) {
  const adjacency = new Map()
  for (const node of nodes) {
    adjacency.set(node.id, [])
  }
  for (const edge of edges) {
    if (adjacency.has(edge.source)) {
      adjacency.get(edge.source).push(edge.target)
    }
  }

  // DFS 检测环
  const visited = new Set()
  const recursionStack = new Set()
  const path = []

  function dfs(nodeId) {
    visited.add(nodeId)
    recursionStack.add(nodeId)
    path.push(nodeId)

    const neighbors = adjacency.get(nodeId) || []
    for (const neighbor of neighbors) {
      if (!visited.has(neighbor)) {
        if (dfs(neighbor)) return true
      } else if (recursionStack.has(neighbor)) {
        path.push(neighbor)
        return true
      }
    }

    path.pop()
    recursionStack.delete(nodeId)
    return false
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (dfs(node.id)) {
        return { hasCycle: true, path }
      }
    }
  }

  return { hasCycle: false, path: [] }
}

/**
 * 检测子工作流嵌套循环
 */
function detectSubworkflowCycles(nodes) {
  const subworkflowNodes = nodes.filter(n => n.type === 'subworkflow')
  if (subworkflowNodes.length < 2) {
    return { hasCycle: false, path: [] }
  }

  // 简化的子工作流循环检测
  // 构建子工作流 ID 的使用图
  const subworkflowIds = new Map()
  for (const node of subworkflowNodes) {
    const id = node.data?.config?.subworkflowId
    if (id) {
      if (!subworkflowIds.has(id)) {
        subworkflowIds.set(id, [])
      }
      subworkflowIds.get(id).push(node.id)
    }
  }

  // 检查是否有节点调用了包含自身的工作流
  // （这里简化了，实际需要后端数据）
  return { hasCycle: false, path: [] }
}

/**
 * URL 验证辅助函数
 */
function isValidUrl(string) {
  try {
    new URL(string)
    return true
  } catch (_) {
    // 可能是相对路径或不含协议的 URL
    return /^[a-zA-Z0-9][a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=%]*$/.test(string)
  }
}

/**
 * 更新节点数据的辅助函数
 * @param {Array} nodes - 节点数组
 * @param {string} nodeId - 节点 ID
 * @param {Object} dataUpdates - 要更新的数据
 */
function updateNodeData(nodes, nodeId, dataUpdates) {
  const nodeIndex = nodes.findIndex(n => n.id === nodeId)
  if (nodeIndex !== -1) {
    nodes[nodeIndex] = {
      ...nodes[nodeIndex],
      data: {
        ...nodes[nodeIndex].data,
        ...dataUpdates
      }
    }
  }
}

/**
 * 在编辑器中高亮错误节点
 * @param {Array} nodes - 节点数组（响应式）
 * @param {Record<string, string[]>} nodeErrors - nodeId -> 错误消息数组
 * @param {Function} updateNode - 更新节点的方法
 */
export function highlightErrorNodes(nodes, nodeErrors, updateNode) {
  for (const node of nodes) {
    const hasError = !!nodeErrors[node.id]
    const errorMessages = nodeErrors[node.id] || []
    node.class = { ...(typeof node.class === 'object' ? node.class : Object.fromEntries(String(node.class || '').split(/\s+/).filter(Boolean).map(name => [name, true]))), 'has-error': hasError }

    if (updateNode) {
      // 如果提供了 updateNode 函数，使用它更新
      updateNode(node.id, {
        hasError,
        errorMessages
      })
    } else {
      // 否则直接更新节点数据
      node.data = {
        ...node.data,
        hasError,
        errorMessages
      }
    }
  }
}

/**
 * 清除所有节点的高亮状态
 * @param {Array} nodes - 节点数组
 */
export function clearNodeHighlights(nodes) {
  for (const node of nodes) {
    if (node.class && typeof node.class === 'object') node.class = { ...node.class, 'has-error': false, 'has-warning': false }
    if (node.data?.hasError || node.data?.hasWarning) {
      node.data = {
        ...node.data,
        hasError: false,
        hasWarning: false,
        errorMessages: [],
        warningMessages: []
      }
    }
  }
}

/**
 * 显示验证结果
 * @param {ValidationResult} result
 * @param {Function} [highlightCallback] - 高亮回调
 */
export function showValidationResult(result, highlightCallback) {
  if (result.valid && result.warnings.length === 0) {
    ElMessage.success('工作流验证通过')
    return
  }

  if (result.errors.length > 0) {
    const errorMsgs = result.errors.slice(0, 3).map(e => e.message).join('\n')
    if (result.errors.length > 3) {
      ElMessage.error({
        message: `发现 ${result.errors.length} 个错误:\n${errorMsgs}\n...`,
        duration: 5000
      })
    } else {
      ElMessage.error(errorMsgs)
    }
  }

  if (result.warnings.length > 0) {
    const warningMsgs = result.warnings.slice(0, 3).map(w => w.message).join('\n')
    ElMessage.warning({
      message: `发现 ${result.warnings.length} 个警告:\n${warningMsgs}`,
      duration: 4000
    })
  }

  // 高亮错误节点
  if (highlightCallback) {
    highlightCallback(result.nodeErrors)
  }
}

export default {
  validateWorkflowSchema,
  highlightErrorNodes,
  clearNodeHighlights,
  showValidationResult,
  updateNodeData
}
