import { afterEach, beforeEach, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent, h, ref } from 'vue'
import ElementPlus, { ElSelect } from 'element-plus'
import api from '@/api'
import ModelEvaluationConfig from '@/components/workflow/configs/ModelEvaluationConfig.vue'
import EvaluationResourceSelect from '@/components/workflow/configs/EvaluationResourceSelect.vue'
import { evaluationMetricRows } from '@/config/modelEvaluation'
import { authSession } from '@/utils/authSession'

const adapter = api.defaults.adapter
let wrapper, state, requests, fail
beforeEach(() => {
  setActivePinia(createPinia()); requests = []; fail = false; authSession.user = null
  api.defaults.adapter = async config => {
    requests.push(config)
    if (fail) throw new Error('评测资源服务离线')
    const page = config.params.page
    return { status: 200, statusText: 'OK', headers: {}, config,
      data: { results: [{ id: `resource-${page}`, name: `Real record ${page}` }], next: page === 1 ? '?page=2' : null } }
  }
})
afterEach(() => { wrapper?.unmount(); api.defaults.adapter = adapter; document.querySelectorAll('.el-popper').forEach(node => node.remove()) })
async function open(value) {
  state = ref(value)
  const Parent = defineComponent({ setup: () => () => h(ModelEvaluationConfig, {
    modelValue: state.value, 'onUpdate:modelValue': next => { state.value = next },
  }) })
  wrapper = mount(Parent, { global: { plugins: [ElementPlus] } }); await flushPromises()
}
it('switches a legacy path to a registered training record without conflicting stale identifiers', async () => {
  await open({ modelPath: 'registered/old.pt', testDataset: 'registered/old.csv', metrics: 'f1', Vendor_Config: { keep: true } })
  const select = wrapper.findAllComponents(ElSelect)[0]
  select.vm.$emit('update:modelValue', 'registered'); select.vm.$emit('change', 'registered'); await flushPromises()
  expect(wrapper.findComponent(EvaluationResourceSelect).props('kind')).toBe('model')
  wrapper.findComponent(EvaluationResourceSelect).vm.$emit('update:modelValue', 'resource-1'); await flushPromises()
  expect(state.value.trainingJobId).toBe('resource-1')
  expect(state.value.modelPath).toBe('')
  expect(state.value.Vendor_Config).toEqual({ keep: true })
  expect(requests.some(request => request.params.status === 'completed')).toBe(true)
})
it('preserves exact feature names and legacy unsupported metrics instead of silently changing evaluation', async () => {
  await open({ features: ['foo_bar', 'fooBar', 'comma,name'], metrics: 'f1, bleu', threshold: 0 })
  expect(wrapper.text()).toContain('历史指标尚未实现')
  const inputs = wrapper.findAll('input')
  await inputs[0].setValue('Actual evaluation'); await inputs[0].trigger('change')
  expect(state.value.features).toEqual(['foo_bar', 'fooBar', 'comma,name'])
  expect(state.value.metrics).toEqual(['f1', 'bleu'])
  expect(state.value.threshold).toBe(0)
})
it('loads later resource pages and allows a real retry after a failed search', async () => {
  wrapper = mount(EvaluationResourceSelect, { props: { kind: 'training' }, global: { plugins: [ElementPlus] } })
  await flushPromises()
  await wrapper.get('button').trigger('click'); await flushPromises()
  expect(wrapper.findAllComponents({ name: 'ElOption' }).map(option => option.props('value'))).toEqual(['resource-1', 'resource-2'])
  fail = true
  wrapper.findComponent(ElSelect).props('remoteMethod')('query'); await flushPromises()
  expect(wrapper.get('[role="alert"]').text()).toContain('离线')
  fail = false; await wrapper.get('[role="alert"] button').trigger('click'); await flushPromises()
  expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  expect(requests.at(-1).params.search).toBe('query')
})
it('shows the actual nested zero F1 and unavailable AUC without fabricating a score', () => {
  expect(evaluationMetricRows({ metrics: { f1: 0, auc: null, mAP50: .75 } }).map(row => row.display))
    .toEqual(['0.0%', '无法计算', '75.0%'])
})
it('does not show an old identity resource list when its response arrives after an account change', async () => {
  let resolve
  api.defaults.adapter = config => new Promise(done => { resolve = data => done({ status: 200, statusText: 'OK', headers: {}, config, data }) })
  wrapper = mount(EvaluationResourceSelect, { props: { kind: 'training' }, global: { plugins: [ElementPlus] } })
  await flushPromises()
  authSession.user = { id: 'different-user' }; await flushPromises()
  resolve({ results: [{ id: 'old-private', name: 'Old private resource' }], next: null }); await flushPromises()
  expect(wrapper.text()).not.toContain('Old private resource')
  expect(wrapper.text()).toContain('登录身份已变化')
})
