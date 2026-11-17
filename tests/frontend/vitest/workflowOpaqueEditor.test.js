import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { createCommentVNode, defineComponent, h } from 'vue'
import Editor from '@/views/workflow/Editor.vue'
import api from '@/api/index'

const originalAdapter = api.defaults.adapter
let wrapper
afterEach(() => { wrapper?.unmount(); api.defaults.adapter = originalAdapter })

// This test exercises the editor and actual property form. Rendering the painted
// third-party canvas is reserved for Chrome MCP; a comment has no raster to capture.
const Canvas = defineComponent({ name: 'VueFlow', props: ['nodes', 'edges'], emits: ['node-click'], setup: () => () => createCommentVNode('canvas paint boundary') })

describe('editor load, label edit and save through the real API boundary', () => {
  it('keeps JSON key spelling, collisions, literal ids and node aliases unchanged in the saved graph', async () => {
    const id = '11111111-1111-4111-8111-111111111111'
    const nodeId = '22222222-2222-4222-8222-222222222222'
    const config = { language: 'python', code: `result = {"literal":"${nodeId}", "alias":node_outputs.get("${nodeId}")}`,
      user_snake_key: { foo_bar: 1, fooBar: 2, Customer_ID: 'keep' }, modelArtifactManifest: { bestWeightPath: '/qa-only/best.pt' } }
    let persisted = { id, name: 'Opaque workflow', can_edit: true, nodes: [{ id: nodeId, node_type: 'code', name: 'Original code', position_x: 100, position_y: 100,
      config: structuredClone(config), style: { custom_style: { dataKey: 1 } } }], edges: [] }
    let saved
    api.defaults.adapter = async request => {
      let data = []
      if (request.url === `/workflows/${id}/`) {
        if (request.method === 'patch') { saved = JSON.parse(request.data); persisted = { ...persisted, ...saved } }
        data = structuredClone(persisted)
      }
      return { status: 200, statusText: 'OK', headers: {}, config: request, data: { code: 200, data } }
    }
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/workflows/:id/edit', name: 'WorkflowEdit', component: Editor }] })
    await router.push(`/workflows/${id}/edit`)
    await router.isReady()
    wrapper = mount(defineComponent({ setup: () => () => h(RouterView) }), { attachTo: document.body, global: {
      plugins: [pinia, router], directives: { loading: {} },
      stubs: { VueFlow: Canvas, Background: true, Controls: true, MiniMap: true, VariablePanel: true, TriggerConfig: true, WorkflowAssistant: true, WorkflowNodeHost: true, ExecutionOutputViewer: true, ThemeSwitcher: true, ElDialog: true, ElDrawer: true, ElDropdown: true },
    } })
    await flushPromises()
    const canvas = wrapper.findComponent(Canvas)
    expect(canvas.props('nodes')[0].data.config).toEqual(config)
    canvas.vm.$emit('node-click', { node: canvas.props('nodes')[0] })
    await flushPromises()
    await wrapper.get('input[placeholder="输入节点名称"]').setValue('Renamed only')
    await wrapper.get('button[aria-label="保存工作流"]').trigger('click')
    await vi.waitFor(() => expect(saved).toBeDefined())
    await flushPromises()
    expect(saved).toBeDefined()
    expect(saved.nodes[0].name).toBe('Renamed only')
    expect(saved.nodes[0].config).toEqual(config)
    expect(saved.nodes[0].id).toBe(nodeId)
    expect(saved.nodes[0].style.custom_style).toEqual({ dataKey: 1 })
    expect(canvas.props('nodes')[0].data.config).toEqual(config)
  })
})
