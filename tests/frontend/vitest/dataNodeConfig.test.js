import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import JsonTransformNode from '@/components/workflow/nodes/JsonTransformNode.vue'
import CsvTransformNode from '@/components/workflow/nodes/CsvTransformNode.vue'
import VariableNode from '@/components/workflow/nodes/VariableNode.vue'
import SubworkflowNode from '@/components/workflow/nodes/SubworkflowNode.vue'
import { getBoundaryNodeLabel } from '@/config/dataTransformOperations'

const { updateNodeData, executionState } = vi.hoisted(() => ({ updateNodeData: vi.fn(), executionState: { nodeStatusMap: {}, nodeOutputs: {} } }))
vi.mock('@vue-flow/core', () => ({
  Handle: { template: '<span />' }, Position: { Left: 'left', Right: 'right' },
  useVueFlow: () => ({ updateNodeData }),
}))
vi.mock('@/stores/execution', () => ({
  useExecutionStore: () => executionState,
}))

describe('data node configuration', () => {
  beforeEach(() => {
    updateNodeData.mockClear()
    executionState.nodeStatusMap = {}
    executionState.nodeOutputs = {}
  })

  it.each([
    [JsonTransformNode, { operation: 'map', schema: { mappings: { out: 'a' } } }, '字段映射'],
    [CsvTransformNode, { operation: 'aggregate', params: { column: '金额', aggFunc: 'sum' } }, '数据聚合'],
    [VariableNode, { assignments: [{ name: '金额', value: 0, type: 'number' }] }, '金额'],
  ])('preserves execution parameters when editing a node name', async (component, config, label) => {
    const wrapper = mount(component, {
      props: { id: 'node-1', data: { label: '原节点', config } },
      global: { stubs: { Handle: true } },
    })
    expect(wrapper.text()).toContain(label)
    const nameInput = wrapper.find('input[name="node-label"]')
    await nameInput.setValue('中文节点名称')
    await nameInput.trigger('blur')
    expect(updateNodeData).toHaveBeenLastCalledWith('node-1', {
      label: '中文节点名称', config: expect.objectContaining(config),
    })
    wrapper.unmount()
  })

  it('translates boundary labels without modifying custom business names', () => {
    expect(getBoundaryNodeLabel('Start', 'start')).toBe('开始')
    expect(getBoundaryNodeLabel('End', 'end')).toBe('结束')
    expect(getBoundaryNodeLabel('订单处理入口', 'start')).toBe('订单处理入口')
  })

  it('renders the latest subworkflow version without passing strings to numeric controls', async () => {
    const wrapper = mount(SubworkflowNode, { props: { id: 'sub-1', data: { config: { version: 'latest' } } }, global: { stubs: { Handle: true } } })
    await wrapper.find('.action-btn').trigger('click')
    const input = wrapper.find('input[placeholder="最新版本"]')
    expect(input.element.value).toBe('')
    expect(wrapper.text()).toContain('最新版本')
    wrapper.unmount()
  })

  it('opens and closes a data node configuration using the expansion button', async () => {
    const wrapper = mount(CsvTransformNode, { props: { id: 'csv-1' }, global: { stubs: { Handle: true } } })
    expect(wrapper.classes()).not.toContain('expanded')
    await wrapper.find('.action-btn').trigger('click')
    expect(wrapper.classes()).toContain('expanded')
    await wrapper.find('.action-btn').trigger('click')
    expect(wrapper.classes()).not.toContain('expanded')
    wrapper.unmount()
  })

  it('preserves subworkflow references and mappings when selecting an explicit version', async () => {
    const config = { version: 'latest', subworkflowId: 'child-workflow', inputMapping: [{ parentVar: '订单', childParam: 'order' }], outputMapping: [{ childOutput: 'result', parentVar: '结果' }] }
    const wrapper = mount(SubworkflowNode, { props: { id: 'sub-1', data: { label: '订单流程', config } }, global: { stubs: { Handle: true } } })
    await wrapper.find('.action-btn').trigger('click')
    const input = wrapper.find('input[placeholder="最新版本"]')
    await input.setValue('3')
    await input.trigger('change')
    expect(updateNodeData).toHaveBeenLastCalledWith('sub-1', { label: '订单流程', config: expect.objectContaining({ ...config, version: 3 }) })
    wrapper.unmount()
  })

  it.each([
    [JsonTransformNode, { data: { out: 1 } }, '转换完成'],
    [CsvTransformNode, { data: [{ 金额: 0 }] }, '1 行已处理'],
  ])('shows the actual completion result without inventing a zero count', (component, output, label) => {
    executionState.nodeStatusMap['node-1'] = 'completed'
    executionState.nodeOutputs['node-1'] = output
    const wrapper = mount(component, { props: { id: 'node-1' }, global: { stubs: { Handle: true } } })
    expect(wrapper.text()).toContain(label)
    expect(wrapper.text()).not.toContain('0 条已转换')
    wrapper.unmount()
  })
})
