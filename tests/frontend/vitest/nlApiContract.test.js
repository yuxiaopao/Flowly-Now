import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../../Frontend/src/router', () => ({ default: { currentRoute: { value: { path: '/nl-create' } }, push: vi.fn() } }))

import { api } from '../../../Frontend/src/api/index'
import { nlWorkflowApi } from '../../../Frontend/src/api/nl-workflow'

const originalAdapter = api.defaults.adapter
afterEach(() => { api.defaults.adapter = originalAdapter })

describe('NL API transport contract', () => {
  it('blocks draft writes against a backend that has not loaded the new contract', async () => {
    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config, data: { session_id: 's' } })
    await expect(nlWorkflowApi.ensureWorkspaceVersion('s')).rejects.toThrow('更新或重启服务')
    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config, data: { session_id: 's', workspace_version: 1 } })
    expect((await nlWorkflowApi.ensureWorkspaceVersion('s')).workspaceVersion).toBe(1)
  })
  it('sends model scope, task ID and history pagination as flat query parameters', async () => {
    const requests = []
    api.defaults.adapter = async config => {
      requests.push(config)
      return { status: 200, statusText: 'OK', headers: {}, config, data: {} }
    }
    await nlWorkflowApi.getModels(true)
    await nlWorkflowApi.getSessions({ paginated: true, page: 2, search: '历史' })
    await nlWorkflowApi.getTaskStatus('session', { task_id: 'task' })
    expect(requests.map(request => request.params)).toEqual([
      { include_all: true }, { paginated: true, page: 2, search: '历史' }, { task_id: 'task' }
    ])
  })
  it('normalizes API envelope while preserving executable JSON and guidance keys', async () => {
    const workflow = { nodes: [{ config: { customCamelKey: 1, api_key: 'test', nested: { Keep_CASE: true } } }], _node_guidance: [{ node_type: 'llm' }] }
    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config, data: { session_id: 's', workflow_json: workflow, messages: [{ node_guidance: workflow._node_guidance }] } })
    const result = await nlWorkflowApi.getSession('s')
    expect(result.sessionId).toBe('s')
    expect(result.workflowJson).toEqual(workflow)
    expect(result.messages[0].node_guidance).toEqual(workflow._node_guidance)
  })
  it('submits the selected snapshot unchanged through request normalization', async () => {
    let payload
    api.defaults.adapter = async config => {
      payload = JSON.parse(config.data)
      return { status: 200, statusText: 'OK', headers: {}, config, data: {} }
    }
    const workflow = { nodes: [{ config: { customCamelKey: 'preserved', API_TOKEN: 'test' } }] }
    await nlWorkflowApi.confirmWorkflow('s', workflow)
    expect(JSON.parse(payload.workflow_json)).toEqual(workflow)
  })
})
