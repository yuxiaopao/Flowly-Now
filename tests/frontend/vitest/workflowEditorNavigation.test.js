import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter, RouterView } from 'vue-router'
import { defineComponent, h, KeepAlive } from 'vue'
import Editor from '@/views/workflow/Editor.vue'
import api from '@/api/index'
import { WORKFLOW_OPAQUE_KEYS } from '@/api/workflow'
import { useAppStore } from '@/stores/app'

// Raster capture requires a painted browser canvas; navigation tests exercise the save pipeline without it.
vi.mock('@/utils/workflowCanvasCapture', async (loadOriginal) => ({
  ...await loadOriginal(), captureWorkflowCanvas: vi.fn().mockResolvedValue(null),
}))

const fixtures = {
  A: { id: 'A', name: 'Workflow A', nodes: [], edges: [], owner: { id: 1 } },
  B: { id: 'B', name: 'Workflow B', nodes: [], edges: [], owner: { id: 1 } },
  H: { id: 'H', name: 'History fixture', edges: [], nodes: [{ id: 'h1', node_type: 'prompt', name: 'Prompt', position_x: 100, position_y: 100, config: { template: 'Before' }, style: { _runtime: { status: 'completed', output: { long_data: 'runtime-result' } } } }] },
}
const wrappers = []
let httpGet
beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  httpGet = vi.spyOn(api, 'get').mockImplementation(async (url) => {
    const id = url.match(/^\/workflows\/([^/]+)\/$/)?.[1]
    return id && fixtures[id] ? structuredClone(fixtures[id]) : []
  })
})
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); vi.restoreAllMocks() })

async function openEditor(id = 'A') {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/workflows/new', name: 'WorkflowCreate', component: Editor },
    { path: '/workflows/:id/edit', name: 'WorkflowEdit', component: Editor },
    { path: '/elsewhere', component: { template: '<div>Elsewhere</div>' } },
  ] })
  await router.push(id === 'new' ? '/workflows/new' : `/workflows/${id}/edit`)
  await router.isReady()
  const Root = defineComponent({ setup: () => () => h(RouterView, {}, { default: ({ Component }) => h(KeepAlive, {}, () => Component) }) })
  const wrapper = mount(Root, { global: {
    plugins: [pinia, router],
    directives: { loading: {} },
    stubs: {
      VueFlow: true, Background: true, Controls: true, MiniMap: true,
      PropertyPanel: true, VariablePanel: true, TriggerConfig: true, WorkflowAssistant: true,
      WorkflowNodeHost: true, ExecutionOutputViewer: true, ThemeSwitcher: true,
      ElTooltip: { template: '<span><slot /></span>' },
      ElButton: { template: '<button><slot /></button>' },
      ElDialog: true, ElDrawer: true, ElDropdown: true, ElAlert: true,
    },
  } })
  wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, router, app: useAppStore(pinia) }
}

describe('workflow editor document navigation', () => {
  it('loads B when the same cached editor changes from A to B', async () => {
    const { wrapper, router } = await openEditor()
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Workflow A')
    await router.push('/workflows/B/edit')
    await flushPromises()
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Workflow B')
  })

  it('allows canceling an unsaved route update and retains the edited document', async () => {
    const { wrapper, router, app } = await openEditor()
    vi.spyOn(app, 'confirm').mockResolvedValue(false)
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Unsaved A')
    await wrapper.get('input[aria-label="工作流名称"]').trigger('blur')
    await router.push('/workflows/B/edit')
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('A')
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Unsaved A')
  })

  it('protects browser refresh even when a name edit has not blurred', async () => {
    const { wrapper } = await openEditor()
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Unsaved A')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it('ignores the previous document response when navigation overtakes an initial load', async () => {
    let resolveA
    httpGet.mockImplementation(async (url) => {
      if (url === '/workflows/A/') return new Promise(resolve => { resolveA = resolve })
      return url === '/workflows/B/' ? structuredClone(fixtures.B) : []
    })
    const { wrapper, router } = await openEditor()
    await router.push('/workflows/B/edit')
    await flushPromises()
    resolveA(structuredClone(fixtures.A))
    await flushPromises()
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Workflow B')
  })

  it('discards only after confirmation and saves B to the B endpoint', async () => {
    const { wrapper, router, app } = await openEditor()
    vi.spyOn(app, 'confirm').mockResolvedValue(true)
    const update = vi.spyOn(api, 'patch').mockImplementation(async (url, data) => ({ ...fixtures.B, ...data }))
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Unsaved A')
    await router.push('/workflows/B/edit')
    await flushPromises()
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Saved B')
    await wrapper.get('button[aria-label="保存工作流"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith('/workflows/B/', expect.objectContaining({ name: 'Saved B' }), { opaqueKeys: WORKFLOW_OPAQUE_KEYS })
  })

  it('keeps new-document edits made while create is in flight and adopts the created id', async () => {
    const { wrapper, router, app } = await openEditor('new')
    const confirm = vi.spyOn(app, 'confirm').mockResolvedValue(false)
    let finishCreate
    vi.spyOn(api, 'post').mockImplementation(() => new Promise(resolve => { finishCreate = resolve }))
    const update = vi.spyOn(api, 'patch').mockImplementation(async (url, data) => ({ id: 'C', ...data }))
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Sent name')
    await wrapper.get('button[aria-label="保存工作流"]').trigger('click')
    await flushPromises()
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Edited during save')
    finishCreate({ id: 'C', name: 'Sent name', nodes: [], edges: [] })
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('C')
    expect(confirm).not.toHaveBeenCalled()
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Edited during save')
    await wrapper.get('button[aria-label="保存工作流"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith('/workflows/C/', expect.objectContaining({ name: 'Edited during save' }), { opaqueKeys: WORKFLOW_OPAQUE_KEYS })
  })

  it('blocks document navigation while saving and permits it after success', async () => {
    const { wrapper, router } = await openEditor()
    let finishSave
    vi.spyOn(api, 'patch').mockImplementation(() => new Promise(resolve => { finishSave = resolve }))
    await wrapper.get('input[aria-label="工作流名称"]').setValue('Saved A')
    await wrapper.get('button[aria-label="保存工作流"]').trigger('click')
    await flushPromises()
    await router.push('/workflows/B/edit')
    expect(router.currentRoute.value.params.id).toBe('A')
    finishSave({ ...fixtures.A, name: 'Saved A' })
    await flushPromises()
    await router.push('/workflows/B/edit')
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('B')
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('Workflow B')
  })

  it('leaves an untouched document without a false dirty prompt', async () => {
    const { wrapper, router, app } = await openEditor()
    const confirm = vi.spyOn(app, 'confirm').mockResolvedValue(false)
    await wrapper.get('input[aria-label="工作流名称"]').trigger('blur')
    await router.push('/elsewhere')
    expect(router.currentRoute.value.path).toBe('/elsewhere')
    expect(confirm).not.toHaveBeenCalled()
  })

  it('clears the previous document when navigating to new and guards its unsaved content', async () => {
    const { wrapper, router, app } = await openEditor()
    await router.push('/workflows/new')
    await flushPromises()
    expect(wrapper.get('input[aria-label="工作流名称"]').element.value).toBe('未命名工作流')
    vi.spyOn(app, 'confirm').mockResolvedValue(false)
    await wrapper.get('input[aria-label="工作流名称"]').setValue('New draft')
    await router.push('/elsewhere')
    expect(router.currentRoute.value.path).toBe('/workflows/new')
  })

  it('undoes property edits and dragging while preserving execution results', async () => {
    const { wrapper } = await openEditor('H')
    const canvas = wrapper.findComponent({ name: 'VueFlow' })
    const panel = wrapper.findComponent({ name: 'PropertyPanel' })
    panel.vm.$emit('change', { id: 'h1', data: { config: { template: 'After' } } })
    await flushPromises()
    expect(canvas.props('nodes')[0].data.config.template).toBe('After')
    const undo = wrapper.findAll('button').find(button => button.element.parentElement.getAttribute('content') === '撤销 (Ctrl+Z)')
    expect(undo.attributes('disabled')).toBeUndefined()
    await undo.trigger('click')
    expect(canvas.props('nodes')[0].data.config.template).toBe('Before')
    expect(canvas.props('nodes')[0].data._runtime.output.long_data).toBe('runtime-result')
    canvas.vm.$emit('node-drag-stop', { node: { id: 'h1', position: { x: 300, y: 250 } } })
    await flushPromises()
    await undo.trigger('click')
    expect(canvas.props('nodes')[0].position).toEqual({ x: 100, y: 100 })
  })
})
