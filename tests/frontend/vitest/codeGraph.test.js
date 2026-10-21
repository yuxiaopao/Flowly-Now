import { describe, expect, it } from 'vitest'
import { drawEdges, edgeEndpoint, fileNodes, graphRelationships, normalizeCycles } from '@/utils/codeGraph'
import { CODE_GRAPH } from '@/config/codeGraph'

describe('code graph data', () => {
  it('normalizes API cycle paths and legacy cycle objects without losing order', () => {
    expect(normalizeCycles([['a', 'b', 'a'], { nodes: ['c', 'c'] }, [], {}]))
      .toEqual([{ nodes: ['a', 'b', 'a'] }, { nodes: ['c', 'c'] }])
  })
  it('excludes function nodes from file counts without mutating the graph', () => {
    const nodes = Object.freeze([Object.freeze({ id: 'a', type: 'vue' }), Object.freeze({ id: 'f', type: 'function' })])
    expect(fileNodes(nodes)).toEqual([nodes[0]])
    expect(nodes).toHaveLength(2)
  })

  it('resolves both API and force-engine endpoints', () => {
    expect(edgeEndpoint('a')).toBe('a')
    expect(edgeEndpoint({ id: 'a', x: 20 })).toBe('a')
    expect(edgeEndpoint(null)).toBe(null)
  })

  it('indexes both dependency directions, deduplicating imports and ignoring dangling edges', () => {
    const nodes = [{ id: 'a' }, { id: 'b' }, { id: 'isolated' }]
    const { byId, relationships } = graphRelationships(nodes, [
      { source: 'a', target: 'b' }, { source: { id: 'a' }, target: { id: 'b' } },
      { source: 'missing', target: 'b' },
    ])
    expect(byId.get('a')).toBe(nodes[0])
    expect([...relationships.get('a').imports]).toEqual(['b'])
    expect([...relationships.get('b').importedBy]).toEqual(['a'])
    expect([...relationships.get('isolated').imports]).toEqual([])
  })

  it('draws all valid edges in small graphs including cycles and self references', () => {
    const nodes = [{ id: 'a' }, { id: 'b' }]
    const edges = [{ source: 'a', target: 'b' }, { source: 'b', target: 'a' }, { source: 'a', target: 'a' }]
    expect(drawEdges(nodes, [...edges, { source: 'a', target: 'missing' }])).toEqual(edges)
  })

  it('keeps all selected-file dependencies outside the large graph overview', () => {
    const nodes = [{ id: 'hub', centrality: 1 }, { id: 'selected', centrality: 0 }]
    const edges = []
    for (let i = 0; i < CODE_GRAPH.overviewEdgeLimit + 20; i++) {
      nodes.push({ id: String(i), centrality: 0 })
      edges.push(Object.freeze({ source: 'hub', target: String(i) }))
    }
    const selectedEdges = [{ source: 'selected', target: '0' }, { source: '1', target: 'selected' }]
    edges.push(...selectedEdges)
    Object.freeze(edges)
    const overview = drawEdges(nodes, edges, 'selected')
    expect(overview).toHaveLength(CODE_GRAPH.overviewEdgeLimit + selectedEdges.length)
    expect(overview).toEqual(expect.arrayContaining(selectedEdges))
    expect(drawEdges(nodes, edges, null, true)).toEqual(edges)
    expect(edges[0].source).toBe('hub')
  })
})
