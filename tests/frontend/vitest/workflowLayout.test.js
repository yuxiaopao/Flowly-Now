import { describe, expect, it } from 'vitest'
import {
  hasOverlappingPositions,
  needsAutoLayout,
  resolveNodeCollision,
} from '@/utils/workflowLayout'
import { syncCanvasAfterSave, vueFlowNodeToBackend } from '@/utils/workflowTransform'

describe('workflow canvas layout behavior', () => {
  it('keeps an intentional origin position instead of treating it as missing', () => {
    expect(needsAutoLayout([{ id: 'start', position: { x: 0, y: 0 } }])).toBe(false)
  })

  it('moves a dropped node by the nearest non-overlapping distance', () => {
    const existing = [
      { id: 'a', position: { x: 100, y: 100 }, width: 220, height: 140 },
      { id: 'b', position: { x: 500, y: 100 }, width: 220, height: 140 },
    ]
    const resolved = resolveNodeCollision(
      { id: 'moving', position: { x: 150, y: 130 }, width: 220, height: 140 },
      existing,
    )

    const nextNodes = [...existing, { id: 'moving', position: resolved, width: 220, height: 140 }]
    expect(hasOverlappingPositions(nextNodes)).toBe(false)
    expect(resolved).toEqual({ x: 150, y: 300 })
  })

  it('preserves decimal canvas coordinates when serializing nodes', () => {
    const backendNode = vueFlowNodeToBackend({
      id: 'n1',
      type: 'llm',
      position: { x: 12.345, y: 67.891 },
      data: { label: 'LLM', config: {} },
    }, 'workflow-1')

    expect(backendNode.position_x).toBe(12.35)
    expect(backendNode.position_y).toBe(67.89)
  })

  it('does not let save responses overwrite the current dragged position', () => {
    const oldNodes = [{
      id: 'node-1',
      type: 'llm',
      position: { x: 321.23, y: 98.76 },
      data: { label: 'LLM', config: { model: 'gpt' } },
    }]
    const savedWorkflow = {
      nodes: [{
        id: 'node-1',
        nodeType: 'llm',
        name: 'LLM',
        positionX: '10.00',
        positionY: '20.00',
        config: {},
      }],
      edges: [],
    }

    const synced = syncCanvasAfterSave(oldNodes, [], savedWorkflow)

    expect(synced.nodes[0].position).toEqual({ x: 321.23, y: 98.76 })
  })
})
