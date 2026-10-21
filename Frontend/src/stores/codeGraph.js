import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import * as codegraphApi from '@/api/codegraph'
import { CODE_GRAPH } from '@/config/codeGraph'
import { edgeEndpoint, fileNodes, graphError, graphRelationships } from '@/utils/codeGraph'

export const useCodeGraphStore = defineStore('codegraph', () => {
  const projects = ref([])
  const currentProject = ref(null)
  // Layout engines own mutable coordinates; API graph data stays immutable.
  const nodes = shallowRef([])
  const edges = shallowRef([])
  const stats = shallowRef({})
  const cycles = shallowRef([])
  const hotspots = shallowRef([])
  const loading = ref(false)
  const analyzing = ref(false)
  const wsConnected = ref(false)
  const error = ref(null)
  const searchQuery = ref('')
  const searchResults = shallowRef([])
  const searchLoading = ref(false)
  const searchError = ref(null)
  const selectedNode = ref(null)
  const fileExplanation = shallowRef(null)
  const fileExplainLoading = ref(false)
  const fileExplainError = ref(null)
  const filters = ref({ module: null, type: null, minCentrality: 0 })
  const layout = ref(CODE_GRAPH.defaultLayout)
  let projectVersion = 0
  let projectsSeq = 0
  let graphSeq = 0
  let searchSeq = 0
  let explainSeq = 0
  let graphController = null
  let searchController = null
  let explainController = null
  let ws = null
  let wsReconnectTimer = null
  let reconnectAttempt = 0
  let graphRevision = ''

  const allFiles = computed(() => fileNodes(nodes.value))
  const moduleOptions = computed(() => [...new Set(allFiles.value.map(node => node.module || 'root'))].sort())
  const typeOptions = computed(() => [...new Set(allFiles.value.map(node => node.type))].sort())
  const filteredNodes = computed(() => nodes.value.filter(node =>
    (!filters.value.module || (node.module || 'root') === filters.value.module)
    && (!filters.value.type || node.type === filters.value.type)
    && (node.centrality || 0) >= filters.value.minCentrality))
  const filteredEdges = computed(() => {
    const ids = new Set(filteredNodes.value.map(node => node.id))
    return edges.value.filter(edge => ids.has(edgeEndpoint(edge.source)) && ids.has(edgeEndpoint(edge.target)))
  })
  const relationships = computed(() => graphRelationships(nodes.value, edges.value))
  const hasCycles = computed(() => cycles.value.length > 0)
  const hasFilters = computed(() => Boolean(filters.value.module || filters.value.type || filters.value.minCentrality))

  function applyGraph(response) {
    const data = response?.data ?? response
    nodes.value = data.nodes || []
    edges.value = data.edges || []
    stats.value = data.stats || {}
    cycles.value = data.cycles || []
    hotspots.value = data.hotspots || []
    graphRevision = data.lastUpdated || data.last_updated || ''
    if (selectedNode.value) selectNode(nodes.value.find(node => node.id === selectedNode.value.id) || null)
  }

  async function fetchProjects() {
    const seq = ++projectsSeq
    loading.value = true
    error.value = null
    try {
      const response = await codegraphApi.getProjects()
      if (seq !== projectsSeq) return
      const data = response?.data ?? response
      projects.value = data?.projects || data?.results || (Array.isArray(data) ? data : [])
    } catch (err) {
      if (seq === projectsSeq) error.value = graphError(err, CODE_GRAPH.messages.projectsFailed)
    } finally {
      if (seq === projectsSeq) loading.value = false
    }
  }

  async function selectProject(projectId) {
    const project = projects.value.find(item => String(item.id) === String(projectId))
    if (!project) return false
    reset()
    currentProject.value = project
    const version = projectVersion
    const success = await fetchGraphData(project.id)
    if (version === projectVersion && success) connectWebSocket(project.id)
    return success
  }

  async function fetchGraphData(projectId, forceRefresh = false) {
    const seq = ++graphSeq
    const version = projectVersion
    graphController?.abort()
    graphController = new AbortController()
    loading.value = true
    error.value = null
    try {
      const response = await codegraphApi.getGraphData(projectId, forceRefresh, { signal: graphController.signal })
      if (seq !== graphSeq || version !== projectVersion) return false
      applyGraph(response)
      return true
    } catch (err) {
      if (seq === graphSeq && version === projectVersion && err.code !== 'ERR_CANCELED') {
        error.value = graphError(err, CODE_GRAPH.messages.graphFailed)
      }
      return false
    } finally {
      if (seq === graphSeq && version === projectVersion) loading.value = false
    }
  }

  async function reanalyze() {
    if (!currentProject.value || analyzing.value) return false
    const projectId = currentProject.value.id
    const version = projectVersion
    ++graphSeq
    graphController?.abort()
    loading.value = false
    analyzing.value = true
    error.value = null
    try {
      const response = await codegraphApi.analyzeProject(projectId, {
        force_refresh: true, include_cycles: true, include_hotspots: true,
      })
      if (version !== projectVersion) return false
      const data = response?.data ?? response
      // Analyze already returns the graph; do not parse the project twice.
      if (data.analysis) applyGraph(data.analysis)
      else if (!await fetchGraphData(projectId)) return false
      if (version !== projectVersion) return false
      if (!ws) connectWebSocket(projectId)
      return true
    } catch (err) {
      if (version === projectVersion) error.value = graphError(err, CODE_GRAPH.messages.analysisFailed)
      return false
    } finally {
      if (version === projectVersion) analyzing.value = false
    }
  }

  function clearSearch() {
    ++searchSeq
    searchController?.abort()
    searchQuery.value = ''
    searchResults.value = []
    searchError.value = null
    searchLoading.value = false
  }

  async function search(query) {
    clearSearch()
    searchQuery.value = query
    if (!currentProject.value || !query.trim()) return
    const seq = searchSeq
    const version = projectVersion
    searchController = new AbortController()
    searchLoading.value = true
    try {
      const response = await codegraphApi.searchFiles(currentProject.value.id, query.trim(), {
        limit: CODE_GRAPH.searchLimit,
      }, { signal: searchController.signal })
      if (seq === searchSeq && version === projectVersion) searchResults.value = response.results || []
    } catch (err) {
      if (seq === searchSeq && version === projectVersion && err.code !== 'ERR_CANCELED') {
        searchError.value = graphError(err, CODE_GRAPH.messages.searchFailed)
      }
    } finally {
      if (seq === searchSeq && version === projectVersion) searchLoading.value = false
    }
  }

  function selectNode(node) {
    if (selectedNode.value?.id !== node?.id || !node) {
      ++explainSeq
      explainController?.abort()
      fileExplanation.value = null
      fileExplainError.value = null
      fileExplainLoading.value = false
    }
    selectedNode.value = node
  }

  async function explainFile(node) {
    if (!currentProject.value || !node?.path) return null
    const seq = ++explainSeq
    const version = projectVersion
    explainController?.abort()
    explainController = new AbortController()
    fileExplanation.value = null
    fileExplainLoading.value = true
    fileExplainError.value = null
    try {
      const result = await codegraphApi.explainFile(currentProject.value.id, {
        path: node.path, module: node.module, type: node.type,
        indegree: node.indegree || 0, outdegree: node.outdegree || 0, centrality: node.centrality || 0,
      }, { signal: explainController.signal })
      if (seq !== explainSeq || version !== projectVersion) return null
      fileExplanation.value = result
      return result
    } catch (err) {
      if (seq === explainSeq && version === projectVersion && err.code !== 'ERR_CANCELED') {
        fileExplainError.value = graphError(err, CODE_GRAPH.messages.explainFailed)
      }
      return null
    } finally {
      if (seq === explainSeq && version === projectVersion) fileExplainLoading.value = false
    }
  }

  function clearSelection() { selectNode(null) }
  function setFilter(key, value) { filters.value[key] = value }
  function resetFilters() { filters.value = { module: null, type: null, minCentrality: 0 } }
  function setLayout(value) {
    if (CODE_GRAPH.layouts.some(item => item.value === value)) layout.value = value
  }

  function disconnectWebSocket() {
    if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
    const socket = ws
    ws = null
    if (socket) {
      // A deliberate close must never schedule a reconnect.
      socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null
      socket.close()
    }
    wsConnected.value = false
  }

  function connectWebSocket(projectId) {
    disconnectWebSocket()
    const version = projectVersion
    const isCurrent = socket => ws === socket && version === projectVersion
    const scheduleReconnect = () => {
      if (version !== projectVersion || !currentProject.value) return
      const delay = Math.min(CODE_GRAPH.reconnectMs * (2 ** reconnectAttempt++), CODE_GRAPH.reconnectMaxMs)
      wsReconnectTimer = setTimeout(() => connectWebSocket(projectId), delay)
    }
    try {
      const socket = new WebSocket(codegraphApi.getWebSocketUrl(projectId))
      ws = socket
      socket.onopen = () => {
        if (!isCurrent(socket)) return
        reconnectAttempt = 0
        wsConnected.value = true
        socket.send(JSON.stringify({ type: 'subscribe' }))
      }
      socket.onmessage = event => {
        if (!isCurrent(socket)) return
        try {
          const data = JSON.parse(event.data)
          const revision = data.data?.last_updated || data.data?.lastUpdated
          if (revision && revision === graphRevision) return
          if ((data.type === 'full_refresh' || (data.type === 'graph_update' && data.event === 'full_refresh'))
            && !analyzing.value && !loading.value) fetchGraphData(projectId)
        } catch (err) { console.warn('Invalid CodeGraph message:', err) }
      }
      socket.onclose = () => {
        if (!isCurrent(socket)) return
        ws = null
        wsConnected.value = false
        scheduleReconnect()
      }
      socket.onerror = () => { if (isCurrent(socket)) wsConnected.value = false }
    } catch { scheduleReconnect() }
  }

  function sendPing() {
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
  }

  function reset() {
    ++projectVersion
    ++projectsSeq
    ++graphSeq
    graphController?.abort()
    disconnectWebSocket()
    reconnectAttempt = 0
    graphRevision = ''
    clearSearch()
    clearSelection()
    resetFilters()
    currentProject.value = null
    nodes.value = []
    edges.value = []
    stats.value = {}
    cycles.value = []
    hotspots.value = []
    loading.value = analyzing.value = false
    error.value = null
  }

  return {
    projects, currentProject, nodes, edges, stats, cycles, hotspots, loading, analyzing,
    wsConnected, error, searchQuery, searchResults, searchLoading, searchError,
    selectedNode, fileExplanation, fileExplainLoading, fileExplainError, filters, layout,
    allFiles, moduleOptions, typeOptions, filteredNodes, filteredEdges, relationships, hasCycles, hasFilters,
    fetchProjects, selectProject, fetchGraphData, reanalyze, search, clearSearch, explainFile,
    selectNode, clearSelection, setFilter, resetFilters, setLayout, connectWebSocket,
    disconnectWebSocket, sendPing, reset,
  }
})
