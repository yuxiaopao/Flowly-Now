import { afterEach, describe, expect, it } from 'vitest'
import api from '@/api/index'
import { applicationsApi } from '@/api/applications'

const originalAdapter = api.defaults.adapter
afterEach(() => { api.defaults.adapter = originalAdapter })

describe('application API data boundary', () => {
  it('adapts metadata while preserving user input, output and draft keys', async () => {
    let submitted
    api.defaults.adapter = async config => {
      submitted = JSON.parse(config.data)
      return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data: {
        id: 'trace-1', application_id: 'app-1', total_tokens: null,
        input_data: submitted.input_data, output_data: { Customer_ID: { result_value: 3 } },
      } } }
    }
    const input = { Customer_ID: 'order-1', mixedCase: { keep_this_key: true } }
    const result = await applicationsApi.test('app-1', input)
    expect(submitted).toEqual({ input_data: input })
    expect(result.applicationId).toBe('app-1')
    expect(result.inputData).toEqual(input)
    expect(result.outputData).toEqual({ Customer_ID: { result_value: 3 } })
    expect(result.totalTokens).toBeNull()

    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config,
      data: { id: 'app-1', draft: { workflow_id: 'source', Custom_Key: 'preserved' }, active_release: { created_at: 'today', configuration: { My_Input: { snake_key: 1 } } } },
    })
    const application = await applicationsApi.get('app-1')
    expect(application.draft).toEqual({ workflow_id: 'source', Custom_Key: 'preserved' })
    expect(application.activeRelease.createdAt).toBe('today')
    expect(application.activeRelease.configuration).toEqual({ My_Input: { snake_key: 1 } })
  })

  it('keeps the failed request trace from an execution error envelope', async () => {
    api.defaults.adapter = async config => {
      const error = new Error('Request failed')
      error.config = config
      error.response = { status: 503, config, data: { code: 503, message: '模型暂时不可用', data: { id: 'failed-1', status: 'failed', error_code: 'upstream_unavailable', input_data: { User_ID: 'u' }, output_data: {}, total_tokens: null } } }
      throw error
    }
    try {
      await applicationsApi.test('app-1', { User_ID: 'u' })
      throw new Error('expected rejection')
    } catch (error) {
      expect(error.message).toBe('模型暂时不可用')
      expect(error.applicationRequest).toMatchObject({ id: 'failed-1', errorCode: 'upstream_unavailable', inputData: { User_ID: 'u' }, totalTokens: null })
    }
  })

  it('maps overview metadata and never replaces unknown usage with zero', async () => {
    api.defaults.adapter = async config => ({ status: 200, statusText: 'OK', headers: {}, config,
      data: { application_count: 2, total_tokens: null, total_cost: null, usage_complete: false },
    })
    expect(await applicationsApi.overview()).toEqual({ applicationCount: 2, totalTokens: null, totalCost: null, usageComplete: false })
  })
})
