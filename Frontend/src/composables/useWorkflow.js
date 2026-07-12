/**
 * 工作流编辑器 Composable
 * 提供工作流编辑器相关的逻辑
 */

import { ref, computed, watch } from 'vue'
import { useWorkflowStore } from '@/stores/workflow'
import { useAppStore } from '@/stores/app'
import {
  createEdgeFromConnection
} from '@/utils/workflowTransform'

export function useWorkflow(_options = {}) {
  const workflowStore = useWorkflowStore()
  const appStore = useAppStore()

  // 编辑器状态
  const isEditing = ref(false)
  const isDragging = ref(false)
  const isConnecting = ref(false)
  const showGrid = ref(true)
  const snapToGrid = ref(true)
  const autoSaveEnabled = ref(true)
  const autoSaveInterval = ref(30000) // 30秒自动保存

  let autoSaveTimer = null

  // ==================== Undo/Redo ====================
  const MAX_HISTORY_SIZE = 50
  const undoStack = ref([])
  const redoStack = ref([])
  let isUndoRedoAction = false

  function _getCurrentState() {
    return {
      nodes: JSON.parse(JSON.stringify(nodes.value)),
      edges: JSON.parse(JSON.stringify(edges.value))
    }
  }

  function _pushUndoState() {
    if (isUndoRedoAction) return
    undoStack.value.push(_getCurrentState())
    if (undoStack.value.length > MAX_HISTORY_SIZE) {
      undoStack.value.shift()
    }
    redoStack.value = []
  }

  function undo() {
    if (undoStack.value.length === 0) return
    isUndoRedoAction = true
    try {
      const currentState = _getCurrentState()
      redoStack.value.push(currentState)
      const previousState = undoStack.value.pop()
      workflowStore.setNodesAndEdges(previousState.nodes, previousState.edges)
      workflowStore.isDirty = true
    } finally {
      isUndoRedoAction = false
    }
  }

  function redo() {
    if (redoStack.value.length === 0) return
    isUndoRedoAction = true
    try {
      const currentState = _getCurrentState()
      undoStack.value.push(currentState)
      const nextState = redoStack.value.pop()
      workflowStore.setNodesAndEdges(nextState.nodes, nextState.edges)
      workflowStore.isDirty = true
    } finally {
      isUndoRedoAction = false
    }
  }

  function clearHistory() {
    undoStack.value = []
    redoStack.value = []
  }

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  // Intercept store mutations to record undo history
  function _setupUndoInterception() {
    const originalAddNode = workflowStore.addNode.bind(workflowStore)
    workflowStore.addNode = (nodeData) => {
      _pushUndoState()
      return originalAddNode(nodeData)
    }

    const originalUpdateNode = workflowStore.updateNode.bind(workflowStore)
    workflowStore.updateNode = (nodeId, data) => {
      _pushUndoState()
      return originalUpdateNode(nodeId, data)
    }

    const originalRemoveNode = workflowStore.removeNode.bind(workflowStore)
    workflowStore.removeNode = (nodeId) => {
      _pushUndoState()
      return originalRemoveNode(nodeId)
    }

    const originalAddEdge = workflowStore.addEdge.bind(workflowStore)
    workflowStore.addEdge = (edgeData) => {
      _pushUndoState()
      return originalAddEdge(edgeData)
    }

    const originalRemoveEdge = workflowStore.removeEdge.bind(workflowStore)
    workflowStore.removeEdge = (edgeId) => {
      _pushUndoState()
      return originalRemoveEdge(edgeId)
    }

    const originalBatchUpdatePositions = workflowStore.batchUpdatePositions.bind(workflowStore)
    workflowStore.batchUpdatePositions = (positions) => {
      _pushUndoState()
      return originalBatchUpdatePositions(positions)
    }
  }

  _setupUndoInterception()

  // 计算属性
  const nodes = computed(() => workflowStore.nodes)
  const edges = computed(() => workflowStore.edges)
  const currentWorkflow = computed(() => workflowStore.currentWorkflow)
  const selectedNode = computed(() => workflowStore.selectedNode)
  const selectedNodeData = computed(() => workflowStore.selectedNodeData)
  const hasUnsavedChanges = computed(() => workflowStore.hasUnsavedChanges)

  // ==================== 节点操作 ====================

  /**
   * 添加节点到画布
   */
  function addNode(nodeData) {
    const newNode = {
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type: nodeData.type,
      position: nodeData.position || { x: 100, y: 100 },
      data: {
        label: nodeData.label || '新节点',
        description: '',
        config: nodeData.config || {},
        ...(nodeData.data || {})
      }
    }

    workflowStore.addNode(newNode)
    workflowStore.selectNode(newNode.id)
    return newNode
  }

  /**
   * 从节点面板拖拽添加节点
   */
  function addNodeFromPalette(paletteNode, position) {
    return addNode({
      type: paletteNode.type,
      label: paletteNode.label || paletteNode.name,
      position,
      config: paletteNode.defaultConfig || {}
    })
  }

  /**
   * 更新节点
   */
  function updateNode(nodeId, updates) {
    const node = nodes.value.find(n => n.id === nodeId)
    if (!node) return

    const updatedNode = {
      ...node,
      ...updates,
      data: {
        ...node.data,
        ...(updates.data || {})
      }
    }

    workflowStore.updateNode(nodeId, updatedNode)
  }

  /**
   * 更新节点位置
   */
  function updateNodePosition(nodeId, position) {
    workflowStore.updateNodePosition(nodeId, position)
  }

  /**
   * 批量更新节点位置
   */
  function batchUpdateNodePositions(updates) {
    workflowStore.batchUpdatePositions(updates)
  }

  /**
   * 删除节点
   */
  function deleteNode(nodeId) {
    workflowStore.removeNode(nodeId)
  }

  /**
   * 复制节点
   */
  function duplicateNode(nodeId) {
    const originalNode = nodes.value.find(n => n.id === nodeId)
    if (!originalNode) return null

    const newNode = {
      ...JSON.parse(JSON.stringify(originalNode)),
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      position: {
        x: originalNode.position.x + 50,
        y: originalNode.position.y + 50
      }
    }

    workflowStore.addNode(newNode)
    workflowStore.selectNode(newNode.id)
    return newNode
  }

  // ==================== 连线操作 ====================

  /**
   * 添加连线
   */
  function addEdge(connection) {
    const edge = createEdgeFromConnection(connection)
    workflowStore.addEdge(edge)
    return edge
  }

  /**
   * 更新连线
   */
  function updateEdge(edgeId, updates) {
    workflowStore.updateEdge(edgeId, updates)
  }

  /**
   * 删除连线
   */
  function deleteEdge(edgeId) {
    workflowStore.removeEdge(edgeId)
  }

  // ==================== 选择操作 ====================

  /**
   * 选择节点
   */
  function selectNode(nodeId) {
    workflowStore.selectNode(nodeId)
  }

  /**
   * 选择连线
   */
  function selectEdge(edgeId) {
    workflowStore.selectEdge(edgeId)
  }

  /**
   * 清除选择
   */
  function clearSelection() {
    workflowStore.clearSelection()
  }

  /**
   * 删除选中元素
   */
  function deleteSelected() {
    if (selectedNode.value) {
      deleteNode(selectedNode.value)
    }
    if (workflowStore.selectedEdge) {
      deleteEdge(workflowStore.selectedEdge)
    }
  }

  // ==================== 工作流操作 ====================

  /**
   * 加载工作流
   */
  async function loadWorkflow(workflowId) {
    try {
      clearHistory()
      await workflowStore.fetchWorkflow(workflowId)
      isEditing.value = true
      startAutoSave()
      return currentWorkflow.value
    } catch (error) {
      appStore.error('加载工作流失败')
      throw error
    }
  }

  /**
   * 创建新工作流
   */
  async function createNewWorkflow(data) {
    try {
      clearHistory()
      const newWorkflow = await workflowStore.createWorkflow(data)
      workflowStore.clearEditor()
      currentWorkflow.value = newWorkflow
      isEditing.value = true
      startAutoSave()
      return newWorkflow
    } catch (error) {
      appStore.error('创建工作流失败')
      throw error
    }
  }

  /**
   * 保存工作流
   */
  async function saveWorkflow() {
    if (!hasUnsavedChanges.value) {
      return currentWorkflow.value
    }

    try {
      await workflowStore.saveWorkflow()
      appStore.success('保存成功')
      return currentWorkflow.value
    } catch (error) {
      appStore.error('保存失败')
      throw error
    }
  }

  /**
   * 执行工作流
   */
  async function executeWorkflow(inputs = {}) {
    if (hasUnsavedChanges.value) {
      appStore.warning('请先保存工作流')
      return
    }

    try {
      const result = await workflowStore.executeWorkflow(inputs)
      return result
    } catch (error) {
      appStore.error('执行失败')
      throw error
    }
  }

  /**
   * 验证工作流
   */
  async function validateWorkflow() {
    try {
      const result = await workflowStore.validateWorkflow(currentWorkflow.value?.id)
      if (result.valid) {
        appStore.success('工作流验证通过')
      } else {
        appStore.warning(`工作流验证失败: ${result.errors.join(', ')}`)
      }
      return result
    } catch (error) {
      appStore.error('验证失败')
      throw error
    }
  }

  /**
   * 清空编辑器
   */
  function clearEditor() {
    stopAutoSave()
    workflowStore.clearEditor()
    isEditing.value = false
    clearHistory()
  }

  // ==================== 自动保存 ====================

  /**
   * 启动自动保存
   */
  function startAutoSave() {
    if (!autoSaveEnabled.value) return

    stopAutoSave()
    autoSaveTimer = setInterval(async () => {
      if (hasUnsavedChanges.value && currentWorkflow.value?.id) {
        try {
          await saveWorkflow()
        } catch (error) {
          // Auto-save failure is silent; user can manually save
        }
      }
    }, autoSaveInterval.value)
  }

  /**
   * 停止自动保存
   */
  function stopAutoSave() {
    if (autoSaveTimer) {
      clearInterval(autoSaveTimer)
      autoSaveTimer = null
    }
  }

  // ==================== 画布操作 ====================

  /**
   * 全选节点
   */
  function selectAllNodes() {
    const nodeIds = nodes.value.map(n => n.id)
    // 假设 store 支持批量选择
    nodeIds.forEach(id => workflowStore.selectNode(id))
  }

  /**
   * 对齐到网格
   */
  function alignToGrid() {
    const alignedPositions = nodes.value.map(node => {
      const gridSize = 16
      return {
        id: node.id,
        position: {
          x: Math.round(node.position.x / gridSize) * gridSize,
          y: Math.round(node.position.y / gridSize) * gridSize
        }
      }
    })

    batchUpdateNodePositions(alignedPositions)
  }

  /**
   * 复制选中节点
   */
  function copySelectedNodes() {
    if (!selectedNode.value) return []

    const originalNode = nodes.value.find(n => n.id === selectedNode.value)
    if (!originalNode) return []

    const offset = 50
    const newNode = {
      ...JSON.parse(JSON.stringify(originalNode)),
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      position: {
        x: originalNode.position.x + offset,
        y: originalNode.position.y + offset
      }
    }

    workflowStore.addNode(newNode)
    workflowStore.selectNode(newNode.id)
    return [newNode]
  }

  // ==================== 快捷键处理 ====================

  /**
   * 处理键盘快捷键
   */
  function handleKeyboardShortcuts(event) {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
    const ctrlKey = isMac ? event.metaKey : event.ctrlKey

    // Ctrl/Cmd + S: 保存
    if (ctrlKey && event.key === 's') {
      event.preventDefault()
      saveWorkflow()
      return
    }

    // Ctrl/Cmd + Z: 撤销
    if (ctrlKey && event.key === 'z' && !event.shiftKey) {
      event.preventDefault()
      undo()
      return
    }

    // Ctrl/Cmd + Shift + Z: 重做
    if (ctrlKey && event.key === 'z' && event.shiftKey) {
      event.preventDefault()
      redo()
      return
    }

    // Ctrl/Cmd + Y: 重做 (alternative)
    if (ctrlKey && event.key === 'y') {
      event.preventDefault()
      redo()
      return
    }

    // Ctrl/Cmd + D: 复制
    if (ctrlKey && event.key === 'd') {
      event.preventDefault()
      copySelectedNodes()
      return
    }

    // Delete/Backspace: 删除选中
    if (event.key === 'Delete' || event.key === 'Backspace') {
      if (document.activeElement.tagName !== 'INPUT' && 
          document.activeElement.tagName !== 'TEXTAREA') {
        event.preventDefault()
        deleteSelected()
      }
      return
    }

    // Escape: 清除选择
    if (event.key === 'Escape') {
      clearSelection()
      return
    }
  }

  // 监听 Ctrl/Cmd + S 保存
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', handleKeyboardShortcuts)
  }

  // 清理
  watch(isEditing, (editing) => {
    if (!editing) {
      stopAutoSave()
    }
  })

  return {
    // 状态
    isEditing,
    isDragging,
    isConnecting,
    showGrid,
    snapToGrid,
    autoSaveEnabled,

    // 计算属性
    nodes,
    edges,
    currentWorkflow,
    selectedNode,
    selectedNodeData,
    hasUnsavedChanges,

    // 节点操作
    addNode,
    addNodeFromPalette,
    updateNode,
    updateNodePosition,
    batchUpdateNodePositions,
    deleteNode,
    duplicateNode,

    // 连线操作
    addEdge,
    updateEdge,
    deleteEdge,

    // 选择操作
    selectNode,
    selectEdge,
    clearSelection,
    deleteSelected,

    // 工作流操作
    loadWorkflow,
    createNewWorkflow,
    saveWorkflow,
    executeWorkflow,
    validateWorkflow,
    clearEditor,

    // 画布操作
    selectAllNodes,
    alignToGrid,
    copySelectedNodes,

    // 撤销/重做
    undo,
    redo,
    clearHistory,
    canUndo,
    canRedo,

    // 生命周期
    startAutoSave,
    stopAutoSave
  }
}

export default useWorkflow
