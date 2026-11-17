import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import api from '@/api/index'
import { gatewayChat } from '@/api/gateway'
import { useGatewayStore } from '@/stores/gateway'
import { authSession } from '@/utils/authSession'
import Models from '@/views/model/Index.vue'

const originalAdapter = api.defaults.adapter
let wrapper
let calls
let keysFail
let modelFail
const key = { id: 'key-1', name: 'Local fixture key', provider: 'custom', masked_key: 'fixt...1234', is_active: true, endpoint: 'http://127.0.0.1:1/v1', model: 'fixture-chat', created_at: '2026-11-01T10:00:00Z' }
const models = [
  { id: 'model-1', name: 'Fixture chat', model_id: 'fixture-chat', model_type: 'chat', provider_slug: 'custom', provider_name: 'Custom', is_active: true, is_default: true, supports_streaming: true, supports_function_calling: true, supports_vision: false, input_price: '0.0100', output_price: '0.0200' },
  { id: 'model-2', name: 'Fixture embeddings', model_id: 'fixture-embed', model_type: 'embedding', provider_slug: 'custom', provider_name: 'Custom', is_active: true, is_default: false },
]
beforeEach(() => {
  calls = []
  keysFail = false
  modelFail = false
  models[0].is_default = true
  api.defaults.adapter = async config => {
    const payload = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    calls.push({ method: config.method, url: config.url, payload, params: config.params })
    let data
    if (config.url === '/gateway/providers/') data = { results: [{ id: 'p1', name: 'Custom', slug: 'custom', is_active: true }], next: null }
    else if (config.url === '/gateway/models/') data = { results: models, next: null }
    else if (config.url === '/gateway/models/default_models/') data = { chat: models.find(model => model.model_type === 'chat' && model.is_default) }
    else if (config.url === '/gateway/models/model-1/set_default/') {
      models[0].is_default = payload.is_default
      data = { ...models[0] }
    }
    else if (config.url === '/gateway/api-keys/' && config.method === 'get') {
      if (keysFail) return reject(config, 'Fixture key service offline')
      data = { results: [key, { ...key, id: 'key-disabled', name: 'Disabled key', is_active: false }], next: null }
    } else if (config.url === '/gateway/api-keys/key-1/' && config.method === 'put') data = { ...key, ...payload }
    else if (config.url === '/gateway/logs/aggregate/') data = { overall: { total_calls: 2, total_tokens: 3, total_cost: '0.01', avg_latency: 12 }, by_provider: [], by_model: [] }
    else if (config.url === '/gateway/models/model-1/test/') {
      if (modelFail === 'http') return reject(config, 'Fixture model unavailable')
      data = modelFail === 'body' ? { success: false, error: 'Fixture rejected' } : { success: true, response: modelFail === 'empty' ? '' : 'Fixture model reply' }
    } else if (config.url === '/gateway/chat/') data = { content: 'done', tool_calls: [{ function: { arguments: { Customer_ID: 'kept', foo_bar: 1, fooBar: 2 } } }] }
    else data = {}
    return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data } }
  }
})
function reject(config, message) {
  const error = new Error(message)
  error.config = config
  error.response = { status: 503, config, data: { error: message } }
  throw error
}
afterEach(() => {
  wrapper?.unmount()
  wrapper = null
  api.defaults.adapter = originalAdapter
  authSession.user = null
  document.querySelectorAll('.el-overlay, .el-popper').forEach(element => element.remove())
})
async function open() {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/models', component: Models }] })
  await router.push('/models')
  wrapper = mount(Models, { attachTo: document.body, global: { plugins: [pinia, router, ElementPlus] } })
  await flushPromises()
  return useGatewayStore(pinia)
}
async function clickModelAction(text) {
  await wrapper.findAll('[role="tab"]').find(tab => tab.text() === '模型配置').trigger('click')
  await wrapper.get('.model-card .el-dropdown button').trigger('click')
  await flushPromises()
  const item = [...document.querySelectorAll('.el-dropdown-menu__item')].find(element => element.textContent.includes(text))
  expect(item).toBeDefined()
  item.click()
  await flushPromises()
}

describe('gateway management through actual Axios, store and model page', () => {
  it('uses camelCase metadata for model filters, capabilities and masked key state', async () => {
    const store = await open()
    expect(store.chatModels.map(model => model.modelId)).toEqual(['fixture-chat'])
    expect(store.embeddingModels.map(model => model.modelId)).toEqual(['fixture-embed'])
    expect(store.modelsByProvider('custom')).toHaveLength(2)
    expect(store.activeAPIKeys).toHaveLength(1)
    expect(wrapper.get('.api-key-card').text()).toContain('启用')
    expect(wrapper.get('.api-key-card code').text()).toBe('fixt...1234')
    expect(wrapper.findAll('.api-key-card')[1].findAll('button').find(button => button.text().includes('验证')).element.disabled).toBe(true)
    expect(wrapper.text()).toContain('fixture-chat')
    expect(wrapper.text()).toContain('流式')
    await wrapper.get('input[placeholder="搜索模型..."]').setValue('fixture-embed')
    expect(wrapper.findAll('.model-card')).toHaveLength(1)
    expect(wrapper.get('.model-card').text()).toContain('Fixture embeddings')
  })

  it('disables catalog default writes for ordinary users and explains their scope', async () => {
    await open()
    const action = wrapper.findAllComponents({ name: 'ElDropdownItem' }).find(item => item.text().includes('取消目录默认'))
    expect(action.props('disabled')).toBe(true)
    expect(wrapper.text()).toContain('不会修改知识助手的全局模型设置')
    expect(wrapper.text()).toContain('仅管理员可调整目录默认项')
    expect(calls.some(call => call.url.includes('set_default'))).toBe(false)
  })

  it('lets an administrator change the actual catalog default and refreshes its metadata', async () => {
    authSession.user = { id: 1, isStaff: true }
    const store = await open()
    const action = wrapper.findAllComponents({ name: 'ElDropdownItem' }).find(item => item.text().includes('取消目录默认'))
    expect(action.props('disabled')).toBe(false)
    await clickModelAction('取消目录默认')
    expect(calls.find(call => call.url.includes('set_default')).payload).toEqual({ is_default: false })
    expect(store.models.find(model => model.id === 'model-1').isDefault).toBe(false)
    expect(store.defaultModels.chat).toBeUndefined()
    await clickModelAction('设为目录默认')
    expect(store.defaultModels.chat.modelId).toBe('fixture-chat')
  })

  it.each([['http', 'Fixture model unavailable'], ['body', 'Fixture rejected'], ['empty', '模型服务没有返回可用结果']])('shows %s probe failure instead of a successful blank response', async (mode, expected) => {
    modelFail = mode
    await open()
    await clickModelAction('测试连接')
    const dialog = wrapper.findAllComponents({ name: 'ElDialog' }).find(item => item.props('title') === '测试模型')
    await dialog.findAll('button').find(button => button.text().trim() === '发送测试').trigger('click')
    await flushPromises()
    expect(dialog.text()).toContain(expected)
    expect(dialog.text()).not.toContain('Fixture model reply')
  })

  it('reports key load failure instead of showing a successful empty state', async () => {
    keysFail = true
    await open()
    expect(wrapper.text()).toContain('Fixture key service offline')
    expect(wrapper.text()).not.toContain('暂无 API 密钥')
  })

  it('edits key metadata without reading or requiring the existing plaintext key', async () => {
    await open()
    const edit = wrapper.get('.api-key-card').findAll('button').find(button => button.text().includes('编辑'))
    await edit.trigger('click')
    await flushPromises()
    const dialog = wrapper.findAllComponents({ name: 'ElDialog' }).find(item => item.props('title') === '编辑 API Key')
    const name = dialog.findAllComponents({ name: 'ElInput' }).find(input => input.props('placeholder') === '例如：我的 OpenAI 密钥')
    await name.get('input').setValue('Renamed local key')
    const secret = dialog.findAllComponents({ name: 'ElInput' }).find(input => input.props('type') === 'password')
    expect(secret.get('input').element.value).toBe('')
    await dialog.findAll('button').find(button => button.text().trim() === '保存').trigger('click')
    await flushPromises()
    const saved = calls.find(call => call.method === 'put')
    expect(saved.payload.name).toBe('Renamed local key')
    expect(saved.payload).not.toHaveProperty('api_key')
    expect(saved.payload.is_active).toBe(true)
  })

  it('keeps user tool schema keys opaque while converting response metadata', async () => {
    const schema = { properties: { Customer_ID: { type: 'string' }, foo_bar: { type: 'number' }, fooBar: { type: 'number' } } }
    const response = await gatewayChat({ model: 'fixture-chat', messages: [{ role: 'user', content: 'hello', metadata: { Customer_ID: 'kept' } }], tools: [{ type: 'function', function: { name: 'tool', parameters: schema } }] })
    const sent = calls[0].payload
    expect(sent.tools[0].function.parameters).toEqual(schema)
    expect(sent.messages[0].metadata).toEqual({ Customer_ID: 'kept' })
    expect(response.toolCalls[0].function.arguments).toEqual({ Customer_ID: 'kept', foo_bar: 1, fooBar: 2 })
  })
})
