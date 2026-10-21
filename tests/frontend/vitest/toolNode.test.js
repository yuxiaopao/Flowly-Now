import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ToolNode from '@/components/workflow/nodes/ToolNode.vue'

const { updateNodeData } = vi.hoisted(() => ({ updateNodeData: vi.fn() }))
vi.mock('@vue-flow/core', () => ({ Handle: { template: '<span />' }, Position: { Left:'left',Right:'right' }, useVueFlow: () => ({ updateNodeData }) }))
vi.mock('@/stores/execution', () => ({ useExecutionStore: () => ({ nodeStatusMap: { test:'completed' },nodeOutputs: { test:{ result:'完整三维产物已保存' } } }) }))

describe('completed native tool node', () => {
  it('renders completed output and preserves JSON tool parameters while renaming', async () => {
    const config = { tool:'embroidery_3d',parameters:{operation:'prepare',preset:'butterfly_symbiosis_60'},custom:{retry:2} }
    const wrapper=mount(ToolNode,{props:{id:'test',data:{label:'原节点',config}}})
    expect(wrapper.text()).toContain('三维数字刺绣')
    expect(wrapper.text()).toContain('完整三维产物已保存')
    await wrapper.setProps({data:{label:'切换节点',config:{...config,parameters:{...config.parameters,operation:'render'}}}})
    await wrapper.find('.tool-node').trigger('click')
    expect(JSON.parse(wrapper.find('textarea').element.value).operation).toBe('render')
    await wrapper.find('input.node-name-input').setValue('渲染节点')
    await wrapper.find('input.node-name-input').trigger('blur')
    expect(updateNodeData).toHaveBeenLastCalledWith('test',expect.objectContaining({label:'渲染节点',config:expect.objectContaining({tool:'embroidery_3d',custom:{retry:2},parameters:{operation:'render',preset:'butterfly_symbiosis_60'}})}))
    wrapper.unmount()
  })
})
