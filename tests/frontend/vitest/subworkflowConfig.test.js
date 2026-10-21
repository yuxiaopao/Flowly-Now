import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import SubworkflowConfig from '@/components/workflow/SubworkflowConfig.vue'
import PropertyPanel from '@/components/workflow/PropertyPanel.vue'
import WebsiteGeneratorConfig from '@/components/workflow/configs/WebsiteGeneratorConfig.vue'

vi.mock('@/stores/workflow', () => ({
  useWorkflowStore: () => ({
    nodes: [],
    fetchAvailableModels: vi.fn().mockResolvedValue([]),
    fetchAvailableTools: vi.fn().mockResolvedValue([]),
  }),
}))

describe('subworkflow configuration data flow', () => {
  it('renders missing configuration with registry defaults and emits new mappings', async () => {
    const wrapper = mount(SubworkflowConfig)
    expect(wrapper.text()).toContain('输入映射')
    const add = wrapper.findAll('button').find(button => button.text().includes('添加映射'))
    await add.trigger('click')
    const data = wrapper.emitted('update:modelValue').at(-1)[0]
    expect(data.config.inputMapping).toEqual([{ parentVar: '', childParam: '' }])
    expect(data.config.executionMode).toBe('sync')
    wrapper.unmount()
  })

  it('preserves existing configuration without mutating the input model', async () => {
    const input = { label: '订单处理', description: '业务配置', config: { timeout: 120, fallbackValue: false, inputMapping: [{ parentVar: '订单', childParam: 'input' }], custom: '保留' } }
    const wrapper = mount(SubworkflowConfig, { props: { modelValue: input } })
    const add = wrapper.findAll('button').filter(button => button.text().includes('添加映射'))[1]
    await add.trigger('click')
    const data = wrapper.emitted('update:modelValue').at(-1)[0]
    expect(data.config).toMatchObject({ timeout: 120, fallbackValue: false, custom: '保留', inputMapping: input.config.inputMapping, outputMapping: [{ childOutput: '', parentVar: '' }] })
    expect(input.config).not.toHaveProperty('outputMapping')
    expect(input.config.inputMapping).toEqual([{ parentVar: '订单', childParam: 'input' }])
    wrapper.unmount()
  })

  it('passes the whole node to the property form and saves a flat execution config', async () => {
    const wrapper = mount(PropertyPanel, { props: { selectedNode: { id: 'sub-1', type: 'subworkflow', data: { label: '原名称', description: '原说明', config: { inputMapping: [], outputMapping: [], timeout: 300 } } } } })
    const form = wrapper.findComponent(SubworkflowConfig)
    expect(form.props('modelValue')).toMatchObject({ label: '原名称', description: '原说明', config: { timeout: 300 } })
    await form.find('input[placeholder="输入节点名称"]').setValue('中文子流程')
    const change = wrapper.emitted('change').at(-1)[0]
    expect(change).toMatchObject({ id: 'sub-1', data: { label: '中文子流程', description: '原说明', config: { timeout: 300 } } })
    expect(change.data.config).not.toHaveProperty('config')
    await form.findAll('button').find(button => button.text().includes('添加映射')).trigger('click')
    expect(wrapper.emitted('change').at(-1)[0].data.config.inputMapping).toHaveLength(1)
    wrapper.unmount()
  })

  it('replaces mappings when another node is selected', async () => {
    const wrapper = mount(SubworkflowConfig, { props: { modelValue: { label: '第一个', config: { inputMapping: [{ parentVar: 'a', childParam: 'b' }] } } } })
    expect(wrapper.find('input[placeholder="父工作流变量"]').element.value).toBe('a')
    await wrapper.setProps({ modelValue: { label: '第二个', config: { inputMapping: [] } } })
    expect(wrapper.find('input[placeholder="父工作流变量"]').exists()).toBe(false)
    expect(wrapper.find('input[placeholder="输入节点名称"]').element.value).toBe('第二个')
    wrapper.unmount()
  })

  it('keeps the website wizard reactive across successive configuration changes', async () => {
    const wrapper = mount(WebsiteGeneratorConfig, { global: { stubs: { TrainingSiteWizard: { name: 'TrainingSiteWizard', props: ['modelValue', 'profile'], template: '<div />' } } } })
    const wizard = wrapper.findComponent({ name: 'TrainingSiteWizard' })
    const original = wizard.props('modelValue')
    wizard.vm.$emit('change', { ...original, siteName: '中文站点', scenario: '产品识别' })
    await wrapper.vm.$nextTick()
    expect(wizard.props('modelValue')).toBe(original)
    expect(wizard.props('modelValue').siteName).toBe('中文站点')
    wizard.vm.$emit('change', { ...wizard.props('modelValue'), usageDescription: '识别产品图片', wizardStep: 2 })
    await wrapper.vm.$nextTick()
    expect(wizard.props('modelValue').siteName).toBe('中文站点')
    expect(wizard.props('modelValue').wizardStep).toBe(2)
    expect(wrapper.emitted('update:modelValue').at(-1)[0].wizard.siteName).toBe('中文站点')
    wrapper.unmount()
  })
})

