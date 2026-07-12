import { describe, it, expect } from 'vitest'
import {
  resolveWorkflowCanvasPreview,
  resolveWorkflowPreviewNodes,
  resolveWorkflowPreviewEdges,
} from '@/utils/workflowPreview'

describe('workflowPreview utils', () => {
  it('resolves canvas preview from top-level camelCase field', () => {
    const preview = 'data:image/jpeg;base64,abc'
    expect(resolveWorkflowCanvasPreview({ canvasPreview: preview })).toBe(preview)
  })

  it('resolves canvas preview from config snake_case field', () => {
    const preview = 'data:image/jpeg;base64,xyz'
    expect(resolveWorkflowCanvasPreview({ config: { canvas_preview: preview } })).toBe(preview)
  })

  it('returns empty string when preview missing', () => {
    expect(resolveWorkflowCanvasPreview({ name: 'test' })).toBe('')
  })

  it('resolves preview nodes and edges with snake_case fallback', () => {
    const nodes = [{ id: '1' }]
    const edges = [{ id: 'e1' }]
    expect(resolveWorkflowPreviewNodes({ nodes_preview: nodes })).toEqual(nodes)
    expect(resolveWorkflowPreviewEdges({ edges_preview: edges })).toEqual(edges)
  })
})
