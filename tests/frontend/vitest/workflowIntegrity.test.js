import { describe, expect, it } from 'vitest'
import { backendNodeToVueFlow, vueFlowNodeToBackend } from '@/utils/workflowTransform'
import { mergeWorkflowValidation } from '@/utils/workflowValidation'
import { highlightErrorNodes, clearNodeHighlights } from '@/utils/workflow-schema'

describe('workflow execution integrity', () => {
  it.each(['csv_transform', 'json_transform', 'data_transform', 'http_request', 'trigger', 'template'])(
    'preserves %s through canvas load and save', (type) => {
      const node = { id: 'node-1', node_type: type, name: '原始节点', config: { operation: 'original' } }
      const canvasNode = backendNodeToVueFlow(node)
      const savedNode = vueFlowNodeToBackend(canvasNode, 'workflow-1')
      expect(savedNode.node_type).toBe(type)
      expect(savedNode.config.operation).toBe('original')
      expect(savedNode.name).toBe('原始节点')
      if (type === 'csv_transform' || type === 'json_transform') expect(canvasNode.type).toBe(type)
    },
  )

  it('maps a newly created transform to its native executor type', () => {
    expect(vueFlowNodeToBackend({ id: 'new', type: 'transform', data: {} }, 'workflow-1').node_type).toBe('data_transform')
  })

  it('shows backend incompatibility and highlights its node', () => {
    const result = mergeWorkflowValidation({ errors: [], warnings: [], nodeErrors: {} }, {
      errors: ['节点尚未兼容'], warnings: ['需要测试输入'],
      nodeIssues: [{ nodeId: 'node-1', message: '节点尚未兼容', code: 'n8n_compatibility' }],
    })
    expect(result.valid).toBe(false)
    expect(result.nodeErrors['node-1']).toEqual(['节点尚未兼容'])
    expect(result.warnings[0].message).toBe('需要测试输入')
  })

  it('keeps local failures and does not duplicate remote errors', () => {
    const local = { errors: [{ message: '缺少地址' }], warnings: [], nodeErrors: { a: ['缺少地址'] } }
    expect(mergeWorkflowValidation(local, { errors: ['缺少地址'] }).errors).toHaveLength(1)
    expect(local.nodeErrors.a).toEqual(['缺少地址'])
  })

  it('applies visible error classes and clears them without losing custom classes', () => {
    const nodes = [{ id: 'a', class: 'custom-node', data: {} }, { id: 'b', data: {} }]
    highlightErrorNodes(nodes, { a: ['节点尚未兼容'] })
    expect(nodes[0].class).toEqual({ 'custom-node': true, 'has-error': true })
    expect(nodes[0].data.errorMessages).toEqual(['节点尚未兼容'])
    expect(nodes[1].class['has-error']).toBe(false)
    clearNodeHighlights(nodes)
    expect(nodes[0].class['custom-node']).toBe(true)
    expect(nodes[0].class['has-error']).toBe(false)
    expect(nodes[0].data.errorMessages).toEqual([])
  })
})
