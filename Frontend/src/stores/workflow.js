import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { workflowApi } from '@/api/workflow'
import gatewayApi from '@/api/gateway'
import {
  backendWorkflowToFrontend,
  frontendWorkflowToBackend
} from '@/utils/workflowTransform'

export const useWorkflowStore = defineStore('workflow', () => {
  // State
  const workflows = ref([])
  const currentWorkflow = ref(null)
  const nodes = ref([])
  const edges = ref([])
  const selectedNode = ref(null)
  const selectedEdge = ref(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const isDirty = ref(false) // 是否有未保存的更改
  const error = ref(null)
  const executionHistory = ref([])
  const currentExecution = ref(null)

  // Canvas 状态
  const canvasViewport = ref({ x: 0, y: 0, zoom: 1 })
  const canvasSize = ref({ width: 4000, height: 3000 })

  // AI 模型和工具列表（从 API 获取）
  const availableModels = ref([])
  const availableTools = ref([])
  const availableNodeTypes = ref([])
  const modelsLoading = ref(false)
  const toolsLoading = ref(false)
  const nodeTypesLoading = ref(false)

  // Getters
  const hasUnsavedChanges = computed(() => isDirty.value)

  const workflowNodes = computed(() => nodes.value)

  const workflowEdges = computed(() => edges.value)

  const selectedNodeData = computed(() => {
    if (!selectedNode.value) return null
    return nodes.value.find(n => n.id === selectedNode.value)
  })

  // Actions
  async function fetchWorkflows(params = {}) {
    isLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.getList(params)
      workflows.value = response.results || response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchWorkflow(id) {
    isLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.getById(id)
      // 转换后端数据为前端格式
      const converted = backendWorkflowToFrontend(response)
      currentWorkflow.value = converted
      nodes.value = converted.nodes || []
      edges.value = converted.edges || []
      isDirty.value = false
      return converted
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createWorkflow(data) {
    isLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.create(data)
      workflows.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function updateWorkflow(id, data) {
    isSaving.value = true
    error.value = null
    try {
      const response = await workflowApi.update(id, data)
      currentWorkflow.value = { ...currentWorkflow.value, ...response }
      isDirty.value = false
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deleteWorkflow(id) {
    isLoading.value = true
    error.value = null
    try {
      await workflowApi.delete(id)
      workflows.value = workflows.value.filter(w => w.id !== id)
      if (currentWorkflow.value?.id === id) {
        currentWorkflow.value = null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function duplicateWorkflow(id) {
    try {
      const response = await workflowApi.duplicate(id)
      workflows.value.unshift(response)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 节点操作
  function addNode(nodeData) {
    const newNode = {
      id: nodeData.id || `node_${Date.now()}`,
      ...nodeData
    }
    nodes.value.push(newNode)
    isDirty.value = true
    return newNode
  }

  function updateNode(nodeId, data) {
    const index = nodes.value.findIndex(n => n.id === nodeId)
    if (index !== -1) {
      nodes.value[index] = { ...nodes.value[index], ...data }
      isDirty.value = true
    }
  }

  function removeNode(nodeId) {
    nodes.value = nodes.value.filter(n => n.id !== nodeId)
    // 同时删除关联的边
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
    if (selectedNode.value === nodeId) {
      selectedNode.value = null
    }
    isDirty.value = true
  }

  function updateNodePosition(nodeId, position) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (node) {
      node.position = position
      isDirty.value = true
    }
  }

  function batchUpdatePositions(positions) {
    positions.forEach(({ id, position }) => {
      const node = nodes.value.find(n => n.id === id)
      if (node) {
        node.position = position
      }
    })
    isDirty.value = true
  }

  // 连线操作
  function addEdge(edgeData) {
    const newEdge = {
      id: edgeData.id || `edge_${Date.now()}`,
      ...edgeData
    }
    edges.value.push(newEdge)
    isDirty.value = true
    return newEdge
  }

  function updateEdge(edgeId, data) {
    const index = edges.value.findIndex(e => e.id === edgeId)
    if (index !== -1) {
      edges.value[index] = { ...edges.value[index], ...data }
      isDirty.value = true
    }
  }

  function removeEdge(edgeId) {
    edges.value = edges.value.filter(e => e.id !== edgeId)
    if (selectedEdge.value === edgeId) {
      selectedEdge.value = null
    }
    isDirty.value = true
  }

  // 选择状态
  function selectNode(nodeId) {
    selectedNode.value = nodeId
    selectedEdge.value = null
  }

  function selectEdge(edgeId) {
    selectedEdge.value = edgeId
    selectedNode.value = null
  }

  function clearSelection() {
    selectedNode.value = null
    selectedEdge.value = null
  }

  // Canvas 状态
  function updateViewport(viewport) {
    canvasViewport.value = viewport
  }

  // 保存工作流
  async function saveWorkflow() {
    if (!currentWorkflow.value?.id) return

    isSaving.value = true
    error.value = null
    try {
      const backendData = frontendWorkflowToBackend(currentWorkflow.value, currentWorkflow.value.id)
      await workflowApi.update(currentWorkflow.value.id, backendData)
      isDirty.value = false
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isSaving.value = false
    }
  }

  // 执行相关
  async function executeWorkflow(inputs = {}) {
    if (!currentWorkflow.value?.id) return

    isLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.execute(currentWorkflow.value.id, inputs)
      currentExecution.value = response
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function cancelExecution(executionId) {
    return workflowApi.cancelExecution(executionId)
  }

  async function deleteExecution(executionId) {
    return workflowApi.deleteExecution(executionId)
  }

  async function fetchExecutionHistory(workflowId) {
    try {
      const response = await workflowApi.getExecutionHistory(workflowId)
      executionHistory.value = response.results || response
    } catch (err) {
      error.value = err.message
    }
  }

  // 清空编辑器
  function clearEditor() {
    currentWorkflow.value = null
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    selectedEdge.value = null
    isDirty.value = false
    executionHistory.value = []
    currentExecution.value = null
    canvasViewport.value = { x: 0, y: 0, zoom: 1 }
  }

  // 设置节点和连线（用于撤销/重做）
  function setNodesAndEdges(newNodes, newEdges) {
    nodes.value = newNodes
    edges.value = newEdges
  }

  // 获取可用的 AI 模型列表
  async function fetchAvailableModels(params = {}) {
    modelsLoading.value = true
    error.value = null
    try {
      const response = await gatewayApi.getAvailableModels(params)
      availableModels.value = Array.isArray(response) ? response : (response.results || [])
      return availableModels.value
    } catch (err) {
      try {
        const fallback = await gatewayApi.getModels(params)
        availableModels.value = fallback.results || fallback || []
        return availableModels.value
      } catch {
        availableModels.value = []
      }
    } finally {
      modelsLoading.value = false
    }
  }

  // 获取可用的工具列表
  async function fetchAvailableTools() {
    toolsLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.getTools()
      availableTools.value = response || []
      return availableTools.value
    } catch (err) {
      error.value = err.message
      availableTools.value = []
    } finally {
      toolsLoading.value = false
    }
  }

  // 验证工作流
  async function validateWorkflow(workflowId) {
    try {
      const response = await workflowApi.validate(workflowId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 获取可用的节点类型
  async function fetchAvailableNodeTypes() {
    nodeTypesLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.getAvailableNodeTypes()
      availableNodeTypes.value = response.types || []
      return availableNodeTypes.value
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      nodeTypesLoading.value = false
    }
  }

  // 获取单个模板
  async function fetchTemplate(templateId) {
    isLoading.value = true
    error.value = null
    try {
      const response = await workflowApi.getTemplate(templateId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // 重试执行
  async function retryExecution(executionId) {
    try {
      const response = await workflowApi.retryExecution(executionId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 暂停执行
  async function pauseExecution(executionId) {
    try {
      const response = await workflowApi.pauseExecution(executionId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 恢复执行
  async function resumeExecution(executionId) {
    try {
      const response = await workflowApi.resumeExecution(executionId)
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 获取执行统计
  async function fetchExecutionStatistics() {
    try {
      const response = await workflowApi.getExecutionStatistics()
      return response
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    // State
    workflows,
    currentWorkflow,
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    isLoading,
    isSaving,
    isDirty,
    error,
    executionHistory,
    currentExecution,
    canvasViewport,
    canvasSize,
    availableModels,
    availableTools,
    availableNodeTypes,
    modelsLoading,
    toolsLoading,
    nodeTypesLoading,
    // Getters
    hasUnsavedChanges,
    workflowNodes,
    workflowEdges,
    selectedNodeData,
    // Actions
    fetchWorkflows,
    fetchWorkflow,
    createWorkflow,
    updateWorkflow,
    deleteWorkflow,
    duplicateWorkflow,
    addNode,
    updateNode,
    removeNode,
    updateNodePosition,
    batchUpdatePositions,
    addEdge,
    updateEdge,
    removeEdge,
    selectNode,
    selectEdge,
    clearSelection,
    updateViewport,
    saveWorkflow,
    executeWorkflow,
    fetchExecutionHistory,
    clearEditor,
    setNodesAndEdges,
    fetchAvailableModels,
    fetchAvailableTools,
    fetchAvailableNodeTypes,
    validateWorkflow,
    cancelExecution,
    deleteExecution,
    retryExecution,
    pauseExecution,
    resumeExecution,
    fetchTemplate,
    fetchExecutionStatistics
  }
})
