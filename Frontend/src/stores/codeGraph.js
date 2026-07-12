/**
 * CodeGraph Pinia Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as codegraphApi from '@/api/codegraph'

export const useCodeGraphStore = defineStore('codegraph', () => {
  // ============ 状态 ============
  const projects = ref([])
  const currentProject = ref(null)
  const nodes = ref([])
  const edges = ref([])
  const stats = ref({})
  const cycles = ref([])
  const hotspots = ref([])
  const modules = ref([])
  const moduleDependencies = ref([])

  const loading = ref(false)
  const analyzing = ref(false)
  const wsConnected = ref(false)
  const error = ref(null)

  const searchQuery = ref('')
  const searchResults = ref([])
  const searchLoading = ref(false)

  const selectedNode = ref(null)
  const hoveredNode = ref(null)

  const filters = ref({
    module: null,
    type: null,
    minCentrality: 0,
  })

  const layout = ref('force') // force | tree | dagre
  const zoom = ref(1)
  const viewCenter = ref({ x: 0, y: 0 })

  let ws = null
  let wsReconnectTimer = null

  // ============ 计算属性 ============
  const filteredNodes = computed(() => {
    let result = nodes.value

    if (filters.value.module) {
      result = result.filter(n => n.module === filters.value.module)
    }
    if (filters.value.type) {
      result = result.filter(n => n.type === filters.value.type)
    }
    if (filters.value.minCentrality > 0) {
      result = result.filter(n => n.centrality >= filters.value.minCentrality)
    }

    return result
  })

  const filteredEdges = computed(() => {
    if (filteredNodes.value.length === nodes.value.length) {
      return edges.value
    }

    const nodeIds = new Set(filteredNodes.value.map(n => n.id))
    return edges.value.filter(e =>
      nodeIds.has(e.source) && nodeIds.has(e.target)
    )
  })

  const nodesByModule = computed(() => {
    const grouped = {}
    filteredNodes.value.forEach(node => {
      if (!grouped[node.module]) {
        grouped[node.module] = []
      }
      grouped[node.module].push(node)
    })
    return grouped
  })

  const hasCycles = computed(() => cycles.value.length > 0)

  // ============ Actions ============

  function unwrapList(response) {
    if (Array.isArray(response)) return response
    if (Array.isArray(response?.results)) return response.results
    return []
  }

  /**
   * 获取项目列表
   */
  async function fetchProjects() {
    loading.value = true
    error.value = null
    try {
      const response = await codegraphApi.getProjects()
      projects.value = response.projects || unwrapList(response)
    } catch (err) {
      error.value = err.message || '获取项目列表失败'
      console.error('Failed to fetch projects:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 选择项目
   */
  async function selectProject(projectId) {
    const project = projects.value.find(p => p.id === projectId)
    if (project) {
      currentProject.value = project
      await fetchGraphData(projectId)
      connectWebSocket(projectId)
    }
  }

  /**
   * 获取图数据
   */
  async function fetchGraphData(projectId, forceRefresh = false) {
    loading.value = true
    error.value = null
    try {
      const response = await codegraphApi.getGraphData(projectId, forceRefresh)
      const data = response

      nodes.value = data.nodes || []
      edges.value = data.edges || []
      stats.value = data.stats || {}
      cycles.value = data.cycles || []
      hotspots.value = data.hotspots || []
    } catch (err) {
      error.value = err.message || '获取图数据失败'
      console.error('Failed to fetch graph data:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * 重新分析
   */
  async function reanalyze() {
    if (!currentProject.value) return

    analyzing.value = true
    error.value = null
    try {
      await codegraphApi.analyzeProject(currentProject.value.id, {
        force_refresh: true,
        include_cycles: true,
        include_hotspots: true,
      })
      await fetchGraphData(currentProject.value.id, true)
    } catch (err) {
      error.value = err.message || '分析失败'
      console.error('Failed to reanalyze:', err)
    } finally {
      analyzing.value = false
    }
  }

  /**
   * 获取模块列表
   */
  async function fetchModules() {
    if (!currentProject.value) return

    try {
      const response = await codegraphApi.getModules(currentProject.value.id)
      modules.value = response.modules || []
    } catch (err) {
      console.error('Failed to fetch modules:', err)
    }
  }

  /**
   * 获取模块依赖关系
   */
  async function fetchModuleDependencies() {
    if (!currentProject.value) return

    try {
      const response = await codegraphApi.getModuleDependencies(currentProject.value.id)
      moduleDependencies.value = response.dependencies || []
    } catch (err) {
      console.error('Failed to fetch module dependencies:', err)
    }
  }

  /**
   * 搜索文件
   */
  async function search(query) {
    if (!currentProject.value || !query.trim()) {
      searchResults.value = []
      return
    }

    searchLoading.value = true
    searchQuery.value = query
    try {
      const response = await codegraphApi.searchFiles(currentProject.value.id, query, {
        limit: 50,
      })
      searchResults.value = response.results || []
    } catch (err) {
      console.error('Failed to search:', err)
      searchResults.value = []
    } finally {
      searchLoading.value = false
    }
  }

  /**
   * 获取文件内容
   */
  async function fetchFileContent(filePath) {
    if (!currentProject.value) return null

    try {
      const response = await codegraphApi.getFileContent(
        currentProject.value.id,
        filePath
      )
      return response
    } catch (err) {
      console.error('Failed to fetch file content:', err)
      return null
    }
  }

  /**
   * 选择节点
   */
  function selectNode(node) {
    selectedNode.value = node
  }

  /**
   * 悬停节点
   */
  function hoverNode(node) {
    hoveredNode.value = node
  }

  /**
   * 清除选择
   */
  function clearSelection() {
    selectedNode.value = null
    hoveredNode.value = null
  }

  /**
   * 设置过滤器
   */
  function setFilter(key, value) {
    filters.value[key] = value
  }

  /**
   * 重置过滤器
   */
  function resetFilters() {
    filters.value = {
      module: null,
      type: null,
      minCentrality: 0,
    }
  }

  /**
   * 设置布局
   */
  function setLayout(newLayout) {
    layout.value = newLayout
  }

  /**
   * 设置缩放
   */
  function setZoom(newZoom) {
    zoom.value = Math.max(0.1, Math.min(3, newZoom))
  }

  /**
   * 设置视图中心
   */
  function setViewCenter(x, y) {
    viewCenter.value = { x, y }
  }

  /**
   * 连接 WebSocket
   */
  function connectWebSocket(projectId) {
    disconnectWebSocket()

    const wsUrl = codegraphApi.getWebSocketUrl(projectId)

    try {
      ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        wsConnected.value = true
        console.log('WebSocket connected')
        ws.send(JSON.stringify({ type: 'subscribe' }))
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWSMessage(data)
        } catch (err) {
          console.error('Failed to parse WS message:', err)
        }
      }

      ws.onclose = () => {
        wsConnected.value = false
        console.log('WebSocket disconnected')
        // 自动重连
        wsReconnectTimer = setTimeout(() => {
          if (currentProject.value) {
            connectWebSocket(currentProject.value.id)
          }
        }, 5000)
      }

      ws.onerror = (err) => {
        console.error('WebSocket error:', err)
        wsConnected.value = false
      }
    } catch (err) {
      console.error('Failed to connect WebSocket:', err)
    }
  }

  /**
   * 断开 WebSocket
   */
  function disconnectWebSocket() {
    if (ws) {
      ws.close()
      ws = null
    }
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }
    wsConnected.value = false
  }

  /**
   * 处理 WebSocket 消息
   */
  function handleWSMessage(data) {
    switch (data.type) {
      case 'graph_update':
        if (data.event === 'full_refresh') {
          fetchGraphData(currentProject.value.id, false)
        }
        break

      case 'full_refresh':
        fetchGraphData(currentProject.value.id, false)
        break

      case 'file_modified':
        // 文件变化，标记需要刷新
        console.log('File modified:', data.file)
        break

      case 'pong':
        // 心跳响应
        break

      case 'connected':
      case 'subscribed':
      case 'subscription_confirmed':
        break

      case 'error':
        console.error('CodeGraph WS error:', data.message || data)
        break

      default:
        console.log('Unknown WS message type:', data.type)
    }
  }

  /**
   * 请求刷新
   */
  function requestRefresh() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'request_refresh' }))
    }
  }

  /**
   * 发送心跳
   */
  function sendPing() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }))
    }
  }

  /**
   * 重置状态
   */
  function reset() {
    disconnectWebSocket()
    currentProject.value = null
    nodes.value = []
    edges.value = []
    stats.value = {}
    cycles.value = []
    hotspots.value = []
    modules.value = []
    moduleDependencies.value = []
    selectedNode.value = null
    hoveredNode.value = null
    searchResults.value = []
    error.value = null
  }

  return {
    // 状态
    projects,
    currentProject,
    nodes,
    edges,
    stats,
    cycles,
    hotspots,
    modules,
    moduleDependencies,
    loading,
    analyzing,
    wsConnected,
    error,
    searchQuery,
    searchResults,
    searchLoading,
    selectedNode,
    hoveredNode,
    filters,
    layout,
    zoom,
    viewCenter,

    // 计算属性
    filteredNodes,
    filteredEdges,
    nodesByModule,
    hasCycles,

    // Actions
    fetchProjects,
    selectProject,
    fetchGraphData,
    reanalyze,
    fetchModules,
    fetchModuleDependencies,
    search,
    fetchFileContent,
    selectNode,
    hoverNode,
    clearSelection,
    setFilter,
    resetFilters,
    setLayout,
    setZoom,
    setViewCenter,
    connectWebSocket,
    disconnectWebSocket,
    requestRefresh,
    sendPing,
    reset,
  }
})
