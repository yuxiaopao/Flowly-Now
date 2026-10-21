import { describe, expect, it } from 'vitest'
import { ensureMultimodalChainEdges } from '@/utils/workflowTransform'

const node = (id, type) => ({ id, type, data: { config: {} } })
const edge = (source, target) => ({ id: `${source}-${target}`, source, target })

describe('multimodal graph repair preserves finishing and branches', () => {
  it('does not bypass merge, verification and subtitle burning in a multi-shot workflow', () => {
    const nodes = [node('start', 'start'), node('image1', 'image_generation'), node('image2', 'image_generation'),
      node('video1', 'video_generation'), node('video2', 'video_generation'), node('merge', 'merge'),
      node('gate', 'code'), node('subtitles', 'subtitle_burn'), node('output', 'output'), node('end', 'end')]
    const edges = [edge('start', 'image1'), edge('start', 'image2'), edge('image1', 'video1'),
      edge('image2', 'video2'), edge('video1', 'merge'), edge('video2', 'merge'), edge('merge', 'gate'),
      edge('gate', 'subtitles'), edge('subtitles', 'output'), edge('output', 'end')]
    const result = ensureMultimodalChainEdges(nodes, edges)
    expect(result.patched).toBe(false)
    expect(result.edges).toEqual(edges)
  })

  it('preserves intermediate processing in a single-shot workflow', () => {
    const nodes = [node('start', 'start'), node('input', 'input'), node('prompt', 'prompt'),
      node('image', 'image_generation'), node('video', 'video_generation'), node('subtitles', 'subtitle_burn'),
      node('output', 'output'), node('end', 'end')]
    const edges = [edge('start', 'input'), edge('input', 'prompt'), edge('prompt', 'image'),
      edge('image', 'video'), edge('video', 'subtitles'), edge('subtitles', 'output'), edge('output', 'end')]
    expect(ensureMultimodalChainEdges(nodes, edges)).toEqual({ nodes, edges, patched: false })
  })

  it('still repairs missing connections in an unambiguous standard chain', () => {
    const nodes = ['start', 'input', 'image_generation', 'video_generation', 'output', 'end'].map(type => node(type, type))
    const result = ensureMultimodalChainEdges(nodes, [])
    expect(result.patched).toBe(true)
    expect(result.edges.map(item => [item.source, item.target])).toEqual([
      ['start', 'input'], ['input', 'image_generation'], ['image_generation', 'video_generation'],
      ['video_generation', 'output'], ['output', 'end'],
    ])
  })
})
