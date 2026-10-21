import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import JsonTransformConfig from '@/components/workflow/configs/JsonTransformConfig.vue'
import CsvTransformConfig from '@/components/workflow/configs/CsvTransformConfig.vue'
import { JSON_OPERATIONS, CSV_OPERATIONS } from '@/config/dataTransformOperations'

describe('data transform property forms', () => {
  it.each([
    [JsonTransformConfig, 'json_query', 'schema', { query: 'items[].name' }, JSON_OPERATIONS],
    [CsvTransformConfig, 'sort', 'params', { column: '金额', ascending: false }, CSV_OPERATIONS],
  ])('keeps imported execution settings when the node name changes', async (component, operation, field, parameters, operations) => {
    const original = { label: '原节点', transformType: operation, [field]: parameters, source: '{{input.data}}', custom: { retry: 2 }, delimiter: ';', data: [] }
    const wrapper = mount(component, { props: { modelValue: original } })
    expect(wrapper.findAllComponents({ name: 'ElOption' }).map(option => option.props('value'))).toEqual(operations.map(item => item.value))
    const name = wrapper.find('input[placeholder="输入节点名称"]')
    await name.setValue('订单转换')
    await name.trigger('change')
    const updated = wrapper.emitted('update:modelValue').at(-1)[0]
    expect(updated).toMatchObject({ label: '订单转换', operation, transformType: operation, source: original.source, custom: original.custom, delimiter: ';' })
    expect(JSON.parse(updated[field])).toEqual(parameters)
    expect(JSON.parse(updated.data)).toEqual([])
    wrapper.unmount()
  })

  it.each([false, 0, [], {}])('does not erase a valid empty or falsy JSON payload: %j', data => {
    const wrapper = mount(JsonTransformConfig, { props: { modelValue: { operation: 'json_to_object', data } } })
    expect(JSON.parse(wrapper.find('textarea[aria-label="备用输入数据"]').element.value)).toEqual(data)
    wrapper.unmount()
  })

  it.each([[JsonTransformConfig, 'schema'], [CsvTransformConfig, 'params']])('shows a Chinese error for invalid operation parameters', async (component, field) => {
    const wrapper = mount(component, { props: { modelValue: { [field]: '{}' } } })
    await wrapper.find('textarea[aria-label="操作参数"]').setValue('{broken')
    await vi.waitFor(() => expect(wrapper.text()).toContain('请输入有效的 JSON'))
    await wrapper.find('textarea[aria-label="操作参数"]').setValue('[]')
    await vi.waitFor(() => expect(wrapper.text()).toContain('操作参数必须是 JSON 对象'))
    wrapper.unmount()
  })

  it('replaces the displayed values when selecting another node without leaking its private settings', async () => {
    const wrapper = mount(JsonTransformConfig, { props: { modelValue: { label: '节点一', operation: 'merge', other: { id: 1 } } } })
    await wrapper.setProps({ modelValue: { label: '节点二', operation: 'filter', schema: { condition: 'item.age > 18' } } })
    const name = wrapper.find('input[placeholder="输入节点名称"]')
    await name.setValue('节点二更新')
    await name.trigger('change')
    expect(wrapper.emitted('update:modelValue').at(-1)[0]).not.toHaveProperty('other')
    wrapper.unmount()
  })
})
