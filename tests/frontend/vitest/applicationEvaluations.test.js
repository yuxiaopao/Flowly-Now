import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useAppStore } from '@/stores/app'
import api from '@/api/index'
import { applicationEvaluationsApi } from '@/api/applicationEvaluations'
import { APPLICATION_EVALUATIONS, parseEvaluationCase } from '@/config/applicationEvaluations'
import ApplicationEvaluations from '@/views/applications/ApplicationEvaluations.vue'

const originalAdapter = api.defaults.adapter
const input = { Customer_ID: 'keep', foo_bar: 1, fooBar: 2, nested: [{ Very_Custom: true }] }
const assertion = { type: 'json_equals', path: '/Customer_ID', expected: { foo_bar: 1, fooBar: 2, Customer_ID: 'keep' } }
const application = { id: 'app-1', kind: 'workflow', name: 'Fixture application', canEdit: true, canPublish: true, requiredEvaluationSuiteId: null, evaluationGate: { required: false, ready: true } }
let wrapper, calls, suites, cases, runs, startMode, suitesFail, detailStatus, comparison, pagedCases, resultAssertions, runDetailFail
const suiteRow = () => ({ id: 'suite-1', name: 'Smoke suite', description: 'Real regression', revision: 3, case_count: cases.length, enabled_case_count: cases.filter(row => row.enabled).length })
const runRow = (id = 'run-1', status = 'completed') => ({ id, application_id: 'app-1', suite_id: 'suite-1', suite_name: 'Smoke suite', suite_revision: 3, target: 'draft', status, total: 2, passed: status === 'completed' ? 1 : 0, failed: status === 'completed' ? 1 : 0, errors: 0, skipped: 0, pass_rate: status === 'completed' ? 0.5 : null, runner_mode: 'celery', is_stale: false, corpus_changed: false, created_at: '2026-11-01T10:00:00Z' })
beforeEach(() => {
  calls = []; startMode = 'completed'; suitesFail = false; detailStatus = null
  pagedCases = false
  resultAssertions = [{ ...assertion, passed: false, actual: '{"Customer_ID":"observed"}' }]
  runDetailFail = false
  cases = [{ id: 'case-1', suite_id: 'suite-1', name: 'Existing case', input_data: input, assertions: [assertion], enabled: true, position: 0 }]
  suites = [suiteRow()]; runs = []
  comparison = { baseline_id: 'base', current_id: 'current', corpus_matches: false, warning: '知识内容发生变化，不能直接归因。', results: [{ case_id: 'case-1', name: 'Existing case', baseline_status: 'passed', current_status: 'failed', change: 'inconclusive' }] }
  api.defaults.adapter = async config => {
    const data = typeof config.data === 'string' ? JSON.parse(config.data) : config.data
    calls.push({ url: config.url, method: config.method, data, params: config.params, key: config.headers.get('Idempotency-Key') })
    let result
    if (config.url === '/applications/app-1/test-suites/' && config.method === 'get') {
      if (suitesFail) return failure(config, 503, 'Fixture suite service offline')
      result = { count: suites.length, next: null, results: suites }
    } else if (config.url === '/applications/app-1/test-suites/' && config.method === 'post') {
      result = { ...suiteRow(), ...data, id: 'suite-new', revision: 1, case_count: 0, enabled_case_count: 0 }; suites.push(result)
    } else if (/\/test-suites\/[^/]+\/cases\/$/.test(config.url) && config.method === 'get') result = { count: cases.length, next: pagedCases && config.params.page === 1 ? 'next-page' : null, results: pagedCases ? config.params.page === 1 ? cases.slice(0, 1) : cases.slice(1) : cases }
    else if (/\/test-suites\/[^/]+\/cases\/$/.test(config.url) && config.method === 'post') {
      result = { id: 'case-new', suite_id: 'suite-1', ...data, input_data: data.from_request_id ? input : data.input_data }; delete result.from_request_id; cases.push(result); suites[0] = suiteRow()
    } else if (/\/test-suites\/[^/]+\/cases\/[^/]+\/$/.test(config.url) && config.method === 'patch') {
      result = { ...cases[0], ...data }; cases[0] = result; suites[0] = suiteRow()
    } else if (config.url.endsWith('/releases/')) result = { count: 1, next: null, results: [{ id: 'release-1', version: 1 }] }
    else if (config.url.endsWith('/evaluation-runs/') && config.method === 'get') result = { count: runs.length, next: null, results: runs }
    else if (config.url.endsWith('/evaluation-runs/') && config.method === 'post') {
      const run = runs.find(row => row.id === 'run-1') || runRow('run-1', startMode === 'completed' ? 'completed' : startMode === 'queue-failed' ? 'failed' : 'queued')
      if (!runs.some(row => row.id === run.id)) runs.push(run)
      if (startMode === 'network-first') { startMode = 'queued'; const error = new Error('Network Error'); error.config = config; throw error }
      if (startMode === 'queue-failed') {
        Object.assign(run, { error_code: 'queue_unavailable', error_message: 'Fixture worker queue unavailable' })
        const error = new Error('Queue unavailable'); error.config = config; error.response = { status: 503, config, data: { message: 'Fixture worker queue unavailable', data: run } }; throw error
      }
      result = run
    } else if (/\/evaluation-runs\/[^/]+\/cancel\/$/.test(config.url)) { runs[0].status = 'cancelling'; result = runs[0] }
    else if (/\/evaluation-runs\/[^/]+\/compare\/$/.test(config.url)) result = comparison
    else if (/\/evaluation-runs\/[^/]+\/$/.test(config.url)) {
      if (runDetailFail) return failure(config, 503, 'Fixture run detail offline')
      const id = config.url.split('/').at(-2), run = runs.find(row => row.id === id) || runRow(id)
      result = { ...run, status: detailStatus || run.status, results: [{ id: 'result-1', case_id_snapshot: 'case-1', case_name: 'Existing case', status: 'failed', request_id: 'request-1', latency_ms: 17, assertion_results: resultAssertions }] }
    } else if (config.url.endsWith('/test-suites-import/')) { cases = data.cases.map((row, index) => ({ ...row, id: `imported-case-${index}`, suite_id: 'imported' })); result = { ...suiteRow(), name: data.suite.name, id: 'imported' }; suites.push(result) }
    else if (config.url.endsWith('/export/')) result = new Blob([JSON.stringify({ type: 'flowly_application_test_suite', schema_version: 1, suite: { name: 'Smoke suite' }, cases: [{ input_data: input, assertions: [assertion] }] })], { type: 'application/json' })
    else if (config.url === '/applications/app-1/' && config.method === 'patch') result = { ...application, required_evaluation_suite_id: data.required_evaluation_suite_id }
    else if (config.url === '/applications/app-1/') result = { ...application, evaluation_gate: { required: false, ready: true } }
    else throw new Error(`Unexpected fixture route: ${config.method} ${config.url}`)
    return { status: 200, statusText: 'OK', headers: {}, config, data: config.responseType === 'blob' ? result : { code: 200, data: structuredClone(result) } }
  }
})
function failure(config, status, message) { const error = new Error(message); error.config = config; error.response = { status, config, data: { message } }; throw error }
afterEach(() => { wrapper?.unmount(); wrapper = null; api.defaults.adapter = originalAdapter; vi.restoreAllMocks(); vi.useRealTimers() })
async function open(extra = {}) {
  const pinia = createPinia(); setActivePinia(pinia)
  wrapper = mount(ApplicationEvaluations, { attachTo: document.body, props: { application: { ...application }, ...extra }, global: { plugins: [pinia] } })
  await flushPromises()
  return wrapper
}
const button = text => wrapper.findAll('button').find(item => item.text().trim() === text)

describe('application regression workspace with the actual HTTP adapter boundary', () => {
  it('keeps case input, expected values and assertion results opaque', async () => {
    const saved = await applicationEvaluationsApi.createCase('app-1', 'suite-1', { name: 'New case', input_data: input, assertions: [assertion], enabled: true })
    expect(calls[0].data.input_data).toEqual(input)
    expect(calls[0].data.assertions[0].expected).toEqual(assertion.expected)
    expect(saved.inputData).toEqual(input)
    expect(saved.assertions[0].expected).toEqual(assertion.expected)
    runs = [runRow()]
    const detail = await applicationEvaluationsApi.run('app-1', 'run-1')
    expect(detail.results[0].requestId).toBe('request-1')
    expect(detail.results[0].assertionResults[0].expected).toEqual(assertion.expected)
    expect(detail.results[0].assertionResults[0].actual).toBe('{"Customer_ID":"observed"}')
  })

  it('saves seed input as a persistent case and acknowledges only the same input', async () => {
    await open({ seedRequest: { id: 'request-seed', inputData: input } })
    await button('将此输入保存为用例').trigger('click')
    await wrapper.get('[data-testid="evaluation-case-name"]').setValue('Saved request')
    await wrapper.get('[data-testid="evaluation-assertion-expected"]').setValue(JSON.stringify(assertion.expected))
    await wrapper.get('form[aria-label="编辑回归用例"]').trigger('submit')
    await flushPromises()
    const posted = calls.find(call => call.method === 'post' && call.url.endsWith('/cases/'))
    expect(posted.data.from_request_id).toBe('request-seed')
    expect(posted.data).not.toHaveProperty('input_data')
    expect(wrapper.emitted('case-saved')?.[0]?.[0]).toEqual(input)
    expect(wrapper.text()).toContain('Saved request')
  })

  it('does not acknowledge the original playground input when a saved seed case was changed', async () => {
    await open({ seedRequest: { id: 'request-seed', inputData: input } })
    await button('将此输入保存为用例').trigger('click')
    await wrapper.get('[data-testid="evaluation-case-name"]').setValue('Changed request')
    const edited = { ...input, Customer_ID: 'edited' }
    await wrapper.get('[data-testid="evaluation-case-input"]').setValue(JSON.stringify(edited))
    await wrapper.get('form[aria-label="编辑回归用例"]').trigger('submit')
    await flushPromises()
    const posted = calls.find(call => call.method === 'post' && call.url.endsWith('/cases/'))
    expect(posted.data.input_data).toEqual(edited)
    expect(posted.data).not.toHaveProperty('from_request_id')
    expect(wrapper.emitted('case-saved')).toBeUndefined()
  })

  it('loads every server case page before presenting the complete suite', async () => {
    pagedCases = true
    cases.push({ ...cases[0], id: 'case-2', name: 'Second server page' })
    await open()
    expect(calls.filter(call => call.url.endsWith('/cases/') && call.method === 'get').map(call => call.params.page)).toEqual([1, 2])
    expect(wrapper.text()).toContain('Second server page')
  })

  it.each(['suites', 'cases'])('does not enable or submit a run while the %s response is still loading', async resource => {
    const fixtureAdapter = api.defaults.adapter
    let completeLoading
    const loading = new Promise(resolve => { completeLoading = resolve })
    api.defaults.adapter = async config => {
      const response = await fixtureAdapter(config)
      const isTarget = resource === 'suites' ? config.url === '/applications/app-1/test-suites/' : config.url.endsWith('/cases/')
      if (config.method === 'get' && isTarget) await loading
      return response
    }
    await open()
    expect(wrapper.get('[data-testid="evaluation-start"]').element.disabled).toBe(true)
    expect(wrapper.text()).toContain('正在加载测试集与用例')
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(calls.some(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))).toBe(false)
    expect(wrapper.text()).not.toContain('请先保存并启用至少一条用例')
    completeLoading()
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-start"]').element.disabled).toBe(false)
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(calls.filter(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))).toHaveLength(1)
  })

  it.each(['empty', 'disabled'])('disables an %s suite with an actionable explanation', async kind => {
    cases = kind === 'empty' ? [] : cases.map(row => ({ ...row, enabled: false }))
    await open()
    expect(wrapper.get('[data-testid="evaluation-start"]').element.disabled).toBe(true)
    expect(wrapper.text()).toContain('当前测试集没有启用用例，请新增或启用至少一条用例后运行')
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    expect(calls.some(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))).toBe(false)
  })

  it('keeps a confirmed case save disabled until its list refresh has finished', async () => {
    await open()
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([false])
    await wrapper.get('[data-testid="evaluation-new-case"]').trigger('click')
    await wrapper.get('[data-testid="evaluation-case-name"]').setValue('Single save')
    const fixtureAdapter = api.defaults.adapter
    let completeRefresh, saved = false
    const pendingRefresh = new Promise(resolve => { completeRefresh = resolve })
    api.defaults.adapter = async config => {
      const response = await fixtureAdapter(config)
      if (config.method === 'post' && config.url.endsWith('/cases/')) saved = true
      if (saved && config.method === 'get' && config.url.endsWith('/cases/')) await pendingRefresh
      return response
    }
    await wrapper.get('form[aria-label="编辑回归用例"]').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-case-save"]').element.disabled).toBe(true)
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([true])
    expect(wrapper.emitted('dirty')?.at(-1)).toEqual([true])
    await wrapper.get('form[aria-label="编辑回归用例"]').trigger('submit')
    await flushPromises()
    expect(calls.filter(call => call.method === 'post' && call.url.endsWith('/cases/'))).toHaveLength(1)
    completeRefresh()
    await flushPromises()
    expect(wrapper.find('form[aria-label="编辑回归用例"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Single save')
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([false])
    expect(wrapper.emitted('dirty')?.at(-1)).toEqual([false])
  })

  it('clears the parent busy and dirty signals when an in-flight editor is unmounted', async () => {
    await open()
    await wrapper.get('[data-testid="evaluation-new-case"]').trigger('click')
    await wrapper.get('[data-testid="evaluation-case-name"]').setValue('Pending save')
    const fixtureAdapter = api.defaults.adapter
    let completeWrite
    const pendingWrite = new Promise(resolve => { completeWrite = resolve })
    api.defaults.adapter = async config => {
      const response = await fixtureAdapter(config)
      if (config.method === 'post' && config.url.endsWith('/cases/')) await pendingWrite
      return response
    }
    await wrapper.get('form[aria-label="编辑回归用例"]').trigger('submit')
    await flushPromises()
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([true])
    wrapper.unmount()
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([false])
    expect(wrapper.emitted('dirty')?.at(-1)).toEqual([false])
    completeWrite()
    await flushPromises()
    expect(wrapper.emitted('busy')?.at(-1)).toEqual([false])
    wrapper = null
  })

  it('imports the actual JSON artifact and downloads lossless JSON bytes through the API', async () => {
    await open()
    const artifact = { type: 'flowly_application_test_suite', schema_version: 1, suite: { name: 'Imported suite' }, cases: [{ name: 'Imported case', input_data: input, assertions: [assertion], enabled: true, position: 0 }] }
    await button('导入测试集 JSON').trigger('click')
    await wrapper.get('textarea[aria-label="测试集导入 JSON"]').setValue(JSON.stringify(artifact))
    await wrapper.get('form[aria-label="导入测试集"]').trigger('submit')
    await flushPromises()
    expect(calls.find(call => call.url.endsWith('/test-suites-import/')).data).toEqual(artifact)
    expect(wrapper.get('[data-testid="evaluation-suite"]').element.value).toBe('imported')
    expect(wrapper.text()).toContain('Imported case')
    const blob = await applicationEvaluationsApi.exportSuite('app-1', 'imported')
    expect(blob).toBeInstanceOf(Blob)
    const text = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsText(blob) })
    expect(JSON.parse(text).cases[0].input_data).toEqual(input)
    expect(JSON.parse(text).cases[0].assertions[0].expected).toEqual(assertion.expected)
  })

  it('discards a confirmed unsaved gate selection before opening another editor', async () => {
    await open()
    const confirm = vi.spyOn(useAppStore(), 'confirm').mockResolvedValue(true)
    await wrapper.get('select[aria-label="发布要求的测试集"]').setValue('suite-1')
    await wrapper.get('[data-testid="evaluation-new-case"]').trigger('click')
    await flushPromises()
    expect(confirm).toHaveBeenCalledTimes(1)
    expect(wrapper.get('select[aria-label="发布要求的测试集"]').element.value).toBe('')
  })

  it('submits one durable batch and shows real per-case request evidence', async () => {
    await open()
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(calls.filter(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))).toHaveLength(1)
    expect(wrapper.get('[data-testid="evaluation-run-status"]').text()).toBe('已完成')
    expect(wrapper.text()).toContain('50%')
    expect(wrapper.text()).toContain('断言未通过')
    await button('查看真实请求').trigger('click')
    expect(wrapper.emitted('request')?.[0]).toEqual(['request-1'])
  })

  it('recovers an ambiguous start with the same idempotency key', async () => {
    startMode = 'network-first'
    await open()
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-start"]').text()).toContain('恢复同一启动请求')
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    const starts = calls.filter(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))
    expect(starts).toHaveLength(2)
    expect(starts[0].key).toBe(starts[1].key)
    expect(starts[0].data).toEqual(starts[1].data)
    expect(runs).toHaveLength(1)
  })

  it('displays the server-truncated expected value instead of a misleading null', async () => {
    resultAssertions = [{ type: 'json_equals', path: '/Customer_ID', expected: null, expected_display: '{"Customer_ID":"server bounded preview…', expected_truncated: true, passed: false, actual: '"observed"' }]
    runs = [runRow()]
    await open()
    await wrapper.get('[data-testid="evaluation-history-run-1"]').findAll('button')[0].trigger('click')
    await flushPromises()
    const assertionResult = wrapper.get('.evaluation-assertion-results')
    expect(assertionResult.text()).toContain('预期值过长，已截断')
    expect(assertionResult.findAll('pre')[0].text()).toBe(resultAssertions[0].expected_display)
    expect(assertionResult.findAll('pre')[1].text()).toBe('"observed"')
  })

  it('can retry a selected historical run when its first detail request fails', async () => {
    runs = [runRow()]
    await open()
    runDetailFail = true
    await wrapper.get('[data-testid="evaluation-history-run-1"]').findAll('button')[0].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Fixture run detail offline')
    runDetailFail = false
    await button('重新读取批次').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-run-status"]').text()).toBe('已完成')
    expect(calls.filter(call => call.url === '/applications/app-1/evaluation-runs/run-1/')).toHaveLength(2)
  })

  it('runs a real selected release and blocks an unsaved draft target', async () => {
    await open({ dirty: true })
    expect(wrapper.get('[data-testid="evaluation-start"]').element.disabled).toBe(true)
    await wrapper.get('select[aria-label="评测运行目标"]').setValue('release')
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(calls.find(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/')).data).toEqual({ suite_id: 'suite-1', target: 'release', release_id: 'release-1' })
  })

  it('shows a persisted queue failure without pretending that a worker started or offering ambiguous recovery', async () => {
    startMode = 'queue-failed'
    await open()
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-run-status"]').text()).toBe(APPLICATION_EVALUATIONS.runStatuses.failed)
    expect(wrapper.text()).toContain('queue_unavailable')
    expect(wrapper.text()).toContain('Fixture worker queue unavailable')
    expect(wrapper.text()).not.toContain('恢复同一启动请求')
    expect(calls.filter(call => call.method === 'post' && call.url.endsWith('/evaluation-runs/'))).toHaveLength(1)
  })

  it('ignores an old application run response after switching applications', async () => {
    runs = [runRow()]
    await open()
    const fixtureAdapter = api.defaults.adapter
    let completeOldDetail
    const oldDetail = new Promise(resolve => { completeOldDetail = resolve })
    api.defaults.adapter = async config => {
      if (config.url.includes('/applications/app-2/')) {
        return { status: 200, statusText: 'OK', headers: {}, config, data: { code: 200, data: { count: 0, next: null, results: [] } } }
      }
      const response = await fixtureAdapter(config)
      if (config.url === '/applications/app-1/evaluation-runs/run-1/') await oldDetail
      return response
    }
    await wrapper.get('[data-testid="evaluation-history-run-1"]').findAll('button')[0].trigger('click')
    await flushPromises()
    await wrapper.setProps({ application: { ...application, id: 'app-2' } })
    await flushPromises()
    completeOldDetail()
    await flushPromises()
    expect(wrapper.find('[data-testid="evaluation-run-status"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Existing case')
    expect(wrapper.emitted('updated')).toBeUndefined()
    expect(wrapper.text()).toContain('尚无测试集')
  })

  it('retains cancelling until the server reports the terminal cancellation', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    startMode = 'queued'
    await open()
    await wrapper.get('[data-testid="evaluation-start"]').trigger('click')
    await flushPromises()
    runs[0].status = 'running'
    await vi.advanceTimersByTimeAsync(APPLICATION_EVALUATIONS.pollMs)
    await flushPromises()
    await wrapper.get('[data-testid="evaluation-cancel"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-run-status"]').text()).toBe('正在取消')
    expect(wrapper.text()).toContain('外部副作用无法撤回')
    detailStatus = 'cancelled'
    await vi.advanceTimersByTimeAsync(APPLICATION_EVALUATIONS.pollMs)
    await flushPromises()
    expect(wrapper.get('[data-testid="evaluation-run-status"]').text()).toBe('已取消')
  })

  it('shows server comparison classifications and does not label corpus changes as regression', async () => {
    runs = [runRow('current'), runRow('base')]
    await open()
    await wrapper.get('[data-testid="evaluation-history-current"]').findAll('button')[0].trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="evaluation-history-base"]').findAll('button')[1].trigger('click')
    await wrapper.get('[data-testid="evaluation-compare"]').trigger('click')
    await flushPromises()
    expect(calls.find(call => call.url.endsWith('/compare/')).params).toEqual({ baseline_id: 'base' })
    expect(wrapper.text()).toContain('不可归因')
    expect(wrapper.text()).toContain('知识内容发生变化')
  })

  it('shows actionable load errors and preserves read-only permissions', async () => {
    suitesFail = true
    await open({ application: { ...application, canEdit: false, canPublish: false } })
    expect(wrapper.text()).toContain('Fixture suite service offline')
    expect(wrapper.find('[data-testid="evaluation-new-suite"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="evaluation-start"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="evaluation-save-gate"]').exists()).toBe(false)
    suitesFail = false
    await button('重试测试集').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Existing case')
  })

  it('stores a publisher-selected gate and emits authoritative application metadata', async () => {
    await open()
    await wrapper.get('select[aria-label="发布要求的测试集"]').setValue('suite-1')
    await wrapper.get('[data-testid="evaluation-save-gate"]').trigger('click')
    await flushPromises()
    expect(calls.find(call => call.method === 'patch').data).toEqual({ required_evaluation_suite_id: 'suite-1' })
    expect(wrapper.emitted('updated')?.at(-1)?.[0].requiredEvaluationSuiteId).toBe('suite-1')
  })
})

describe('deterministic assertion editor validation', () => {
  it.each([
    ['json_equals', { Customer_ID: 'kept' }], ['json_contains', { foo_bar: 1, fooBar: 2 }], ['json_exists', true], ['json_type', 'object'],
    ['response_contains', 'answer'], ['grounded', false], ['sources_min', 2], ['latency_max', 120.5], ['error_code', 'no_evidence']
  ])('supports the server %s assertion contract', (type, expected) => {
    const result = parseEvaluationCase({ name: 'Case', inputText: JSON.stringify(input), enabled: true, position: 0, assertions: [{ type, path: type.startsWith('json_') ? '/Customer_ID' : '', expectedText: JSON.stringify(expected) }] })
    expect(result.input_data).toEqual(input)
    expect(result.assertions[0].expected).toEqual(expected)
  })
  it('rejects non-finite, invalid JSONPointer and wrong expected types before transport', () => {
    const form = { name: 'Case', inputText: '{}', enabled: true, assertions: [{ type: 'json_exists', path: '/value', expectedText: '1' }] }
    expect(() => parseEvaluationCase(form)).toThrow('true 或 false')
    expect(() => parseEvaluationCase({ ...form, inputText: '{"amount":1e999}' })).toThrow('有限')
    expect(() => parseEvaluationCase({ ...form, assertions: [{ type: 'json_equals', path: '/bad~2key', expectedText: '{}' }] })).toThrow('JSON Pointer')
  })
})
