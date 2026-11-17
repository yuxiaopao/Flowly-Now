import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import api, { request } from '@/api/index'
import { workflowApi, importWorkflow, exportWorkflow, streamExecuteWorkflow, streamExecuteSSE } from '@/api/workflow'
import { saveAuthSession, clearAuthSession } from '@/utils/authSession'

const originalAdapter = api.defaults.adapter
const raw = { user_snake_key: 'snake', userCamelKey: 'camel', Customer_ID: 'kept',
  nested_items: [{ literal_id: '11111111-1111-4111-8111-111111111111', nodeAlias: "node_outputs['11111111-1111-4111-8111-111111111111']", both_keys: { foo_bar: 1, fooBar: 2 } }] }
const metadata = { id: 'w', created_at: 'today', node_type: 'code', position_x: 100, config: raw,
  input_data: raw, output_data: raw, input_schema: raw, output_schema: raw, fallback_value: raw, variables: raw, style: raw }
let calls
beforeEach(() => {
  calls = []
  api.defaults.adapter = async config => {
    calls.push(config)
    return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data: structuredClone(metadata) } }
  }
})
afterEach(() => { api.defaults.adapter = originalAdapter; vi.unstubAllGlobals(); clearAuthSession() })

describe('workflow API opaque JSON subtrees', () => {
  it('keeps scoped opaque subtrees in both directions while adapting surrounding metadata', async () => {
    const sent = { nodeType: 'code', positionX: 150, config: raw, inputData: raw, outputData: raw,
      inputSchema: raw, outputSchema: raw, fallbackValue: raw, variables: raw, style: raw }
    const response = await workflowApi.update('w', sent)
    const payload = JSON.parse(calls[0].data)
    expect(payload.node_type).toBe('code')
    expect(payload.position_x).toBe(150)
    for (const key of ['config', 'input_data', 'output_data', 'input_schema', 'output_schema', 'fallback_value', 'variables', 'style']) expect(payload[key]).toEqual(raw)
    expect(response.createdAt).toBe('today')
    expect(response.nodeType).toBe('code')
    for (const key of ['config', 'inputData', 'outputData', 'inputSchema', 'outputSchema', 'fallbackValue', 'variables', 'style']) expect(response[key]).toEqual(raw)
    expect(sent.config).toEqual(raw)
  })

  it.each([
    ['create', () => workflowApi.create({ name: 'new', nodes: [{ nodeType: 'code', config: raw }] })],
    ['createNode', () => workflowApi.createNode('w', { nodeType: 'code', name: 'node', config: raw })],
    ['updateNode', () => workflowApi.updateNode('n', { config: raw })],
    ['batchCreateNodes', () => workflowApi.batchCreateNodes('w', [{ nodeType: 'code', config: raw }])],
    ['optimize', () => workflowApi.optimize({ nodes: [{ nodeType: 'code', config: raw }] })],
  ])('preserves node configuration in %s', async (_name, run) => {
    await run()
    const payload = JSON.parse(calls[0].data)
    expect(payload.nodes?.[0]?.config ?? payload.config).toEqual(raw)
    if (payload.nodes) expect(payload.nodes[0].node_type).toBe('code')
  })

  it('preserves Vue Flow data/config and free schema property names inside arrays', async () => {
    await workflowApi.create({ nodes: [{ type: 'code', position: { x: 12, y: 24 }, data: { label: 'Original', config: raw, custom_value: raw } }] })
    expect(JSON.parse(calls[0].data).nodes[0].data.config).toEqual(raw)
    expect(JSON.parse(calls[0].data).nodes[0].data.custom_value).toEqual(raw)
  })

  it.each([
    ['execute', () => workflowApi.execute('w', raw)],
    ['executeAsync', () => workflowApi.executeAsync('w', raw)],
    ['retryExecution', () => workflowApi.retryExecution('e', { inputData: raw })],
    ['continueExecution', () => workflowApi.continueExecution('e', { inputData: raw })],
  ])('does not rewrite invocation input in %s', async (_name, run) => {
    const response = await run()
    expect(JSON.parse(calls[0].data).input_data).toEqual(raw)
    expect(response.outputData).toEqual(raw)
  })

  it.each(['getById', 'getNodes', 'getExecution', 'getExecutionStatus', 'getExecutionTimeline', 'getExecutionOutput', 'getExecutionLogs', 'getExecutionNodeDetail'])('preserves payloads when reading %s', async name => {
    const run = name === 'getExecutionNodeDetail' ? () => workflowApi.getExecutionNodeDetail('e', 'n') : () => workflowApi[name]('w')
    const response = await run()
    expect(response.config).toEqual(raw)
    expect(response.outputData).toEqual(raw)
  })

  it('imports plain JSON with a JSON content type and keeps n8n artifacts unchanged', async () => {
    await importWorkflow({ name: 'Flowly', nodes: [{ nodeType: 'code', config: raw }] })
    expect(calls[0].headers.get('Content-Type')).toContain('application/json')
    expect(JSON.parse(calls[0].data).nodes[0]).toEqual({ node_type: 'code', config: raw })
    const n8n = { name: 'n8n', nodes: [{ type: 'n8n-nodes-base.code', typeVersion: 2, parameters: raw }], connections: { 'A_B': { main: [[{ node: 'A_B' }]] } } }
    await importWorkflow(n8n)
    expect(JSON.parse(calls[1].data)).toEqual(n8n)
  })

  it('lets multipart set its boundary and keeps imported file bytes untouched', async () => {
    const form = new FormData()
    const file = new File([JSON.stringify({ nodes: [{ config: raw }] })], 'workflow.json', { type: 'application/json' })
    form.append('workflow_json', file)
    await importWorkflow(form)
    expect(calls[0].data).toBe(form)
    expect(calls[0].headers.get('Content-Type')).not.toBe('multipart/form-data')
    expect(calls[0].data.get('workflow_json')).toBe(file)
  })

  it('exports a lossless canonical artifact for reimport rather than converting its keys', async () => {
    const artifact = await exportWorkflow('w')
    expect(artifact.node_type).toBe('code')
    expect(artifact.config).toEqual(raw)
    await importWorkflow(artifact)
    expect(JSON.parse(calls[1].data).config).toEqual(raw)
  })

  it('keeps template artifacts and flattens real query parameters', async () => {
    await workflowApi.getTemplates({ category: 'rag', page: 2 })
    expect(calls[0].params).toEqual({ category: 'rag', page: 2 })
    await workflowApi.createTemplate({ name: 'T', workflowData: { nodes: [{ node_type: 'code', config: raw }], Custom_Input: raw }, variablesSchema: raw })
    const body = JSON.parse(calls[1].data)
    expect(body.workflow_data).toEqual({ nodes: [{ node_type: 'code', config: raw }], Custom_Input: raw })
    expect(body.variables_schema).toEqual(raw)
  })

  it('does not change default key conversion for other resources', async () => {
    const response = await request.post('/unrelated/', { someValue: { nestedKey: 1 } })
    expect(JSON.parse(calls[0].data)).toEqual({ some_value: { nested_key: 1 } })
    expect(response.config.userSnakeKey).toBe('snake')
  })

  it('supports explicit per-call opaque keys without globally disabling metadata conversion', async () => {
    api.defaults.adapter = async config => {
      expect(JSON.parse(config.data)).toEqual({ created_at: 'today', user_payload: raw })
      return { status: 200, statusText: 'OK', headers: {}, config, data: { created_at: 'today', user_payload: raw } }
    }
    expect(await request.post('/custom/', { createdAt: 'today', userPayload: raw }, { opaqueKeys: ['user_payload'] })).toEqual({ createdAt: 'today', userPayload: raw })
  })

  it.each([streamExecuteWorkflow, streamExecuteSSE])('uses actual POST fetch, signal and untouched input for the stream helper', async run => {
    saveAuthSession({ access: 'workflow-transport-test-token', refresh: 'workflow-transport-test-refresh' })
    const response = new Response('data: {"type":"execution_complete"}\n\n', { headers: { 'Content-Type': 'text/event-stream' } })
    const fetch = vi.fn().mockResolvedValue(response)
    vi.stubGlobal('fetch', fetch)
    const controller = new AbortController()
    expect(await run('w', raw, { signal: controller.signal, opaqueKeys: ['custom_extra'] })).toBe(response)
    const [url, config] = fetch.mock.calls[0]
    expect(url).toContain('/workflows/w/stream_execute/')
    expect(url).not.toContain('token=')
    expect(config.method).toBe('POST')
    expect(config.signal).toBe(controller.signal)
    expect(config.headers.Authorization).toBe('Bearer workflow-transport-test-token')
    expect(JSON.parse(config.body)).toEqual({ input_data: raw })
  })
})
