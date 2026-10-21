import { CODE_GRAPH } from '@/config/codeGraph'

export function edgeEndpoint(endpoint) {
  return typeof endpoint === 'object' && endpoint !== null ? endpoint.id : endpoint
}

export function fileNodes(nodes) {
  return nodes.filter(node => node.type !== 'function')
}

export function graphRelationships(nodes, edges) {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const relationships = new Map(nodes.map(node => [node.id, { imports: new Set(), importedBy: new Set() }]))
  for (const edge of edges) {
    const source = edgeEndpoint(edge.source)
    const target = edgeEndpoint(edge.target)
    if (!byId.has(source) || !byId.has(target)) continue
    relationships.get(source).imports.add(target)
    relationships.get(target).importedBy.add(source)
  }
  return { byId, relationships }
}

// Preserve all dependencies of the selected file when drawing a large graph overview.
export function drawEdges(nodes, edges, selectedId, showAll = false) {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const valid = edges.filter(edge => byId.has(edgeEndpoint(edge.source)) && byId.has(edgeEndpoint(edge.target)))
  if (showAll || valid.length <= CODE_GRAPH.overviewEdgeLimit) return valid
  const score = edge => (byId.get(edgeEndpoint(edge.source))?.centrality || 0)
    + (byId.get(edgeEndpoint(edge.target))?.centrality || 0)
  const overview = new Set([...valid].sort((a, b) => score(b) - score(a)).slice(0, CODE_GRAPH.overviewEdgeLimit))
  return valid.filter(edge => overview.has(edge)
    || edgeEndpoint(edge.source) === selectedId || edgeEndpoint(edge.target) === selectedId)
}

export function graphError(error, fallback) {
  return error?.response?.data?.error || error?.response?.data?.message || error?.message || fallback
}

export function normalizeCycles(cycles) {
  return cycles.map(cycle => ({ nodes: Array.isArray(cycle) ? cycle : cycle.nodes || [] }))
    .filter(cycle => cycle.nodes.length > 0)
}
