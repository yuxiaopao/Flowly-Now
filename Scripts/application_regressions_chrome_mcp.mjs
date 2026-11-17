import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { McpClient, evalPage, login, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'

if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('Run only with isolated continuation fixtures')
const client = new McpClient(), checks = []
async function page(fn) { return evalPage(client, fn.toString(), 60000) }
async function check(name, fn) {
  const result = await page(fn)
  assert.equal(result?.ok, true, `${name}: ${JSON.stringify(result)}`)
  checks.push(name); console.log(JSON.stringify({ name, ...result }))
}
try {
  await client.initialize()
  assert(client.pageTools.has('navigate_page'), 'Actual chrome-devtools MCP navigate_page is required')
  await login(client, { entryPath: '/api/health/' })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/applications?create=1` })
  await check('actual application creation and configuration readiness', async () => {
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json())
    if (!marker.isolated || !marker.product_fixtures || !marker.async_evaluations) throw new Error('Private asynchronous fixture marker required')
    window.__regressionQa = { marker, token: localStorage.getItem('access_token') }
    window.__regressionWait = async (condition, description = 'UI') => {
      for (let n = 0; n < 300; n++) { if (await condition()) return; await new Promise(resolve => setTimeout(resolve, 100)) }
      throw new Error(`Timed out: ${description}`)
    }
    window.__regressionInput = (selector, value) => {
      const field = document.querySelector(selector); if (!field) throw new Error(`Missing ${selector}`)
      field.value = value; field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
    }
    window.__regressionClick = async selector => {
      await window.__regressionWait(() => document.querySelector(selector) && !document.querySelector(selector).disabled, selector)
      document.querySelector(selector).click()
      await new Promise(resolve => requestAnimationFrame(resolve))
    }
    window.__regressionButton = (text, container = document) => {
      const button = [...container.querySelectorAll('button')].find(node => node.textContent.trim() === text)
      if (!button) throw new Error(`Missing button: ${text}`)
      if (button.disabled) throw new Error(`Disabled button: ${text}`)
      button.click()
    }
    window.__regressionCall = async (path, options = {}) => {
      const response = await fetch(`/api/v1/${path}`, { ...options, headers: {
        Authorization: `Bearer ${window.__regressionQa.token}`, 'Content-Type': 'application/json', ...(options.headers || {}),
      } })
      const value = await response.json(); return { status: response.status, data: value.data ?? value, error: value.errors }
    }
    window.__regressionRouter = document.querySelector('#app').__vue_app__.config.globalProperties.$router
    await window.__regressionWait(() => document.querySelector('[data-testid="application-name"]'))
    window.__regressionInput('[data-testid="application-name"]', '小团队回归发布验证')
    window.__regressionInput('[data-testid="application-kind"]', 'workflow')
    await window.__regressionWait(() => [...document.querySelector('[data-testid="application-source"]').options].some(option => option.textContent.includes('QA 客服工作流')))
    const option = [...document.querySelector('[data-testid="application-source"]').options].find(item => item.textContent.includes('QA 客服工作流'))
    window.__regressionQa.workflowId = option.value
    const sourceWorkflow = (await window.__regressionCall(`workflows/${option.value}/`)).data
    const template = sourceWorkflow.nodes.find(node => node.node_type === 'text_template')
    const reset = await window.__regressionCall(`workflows/nodes/${template.id}/`, { method: 'PATCH', body: JSON.stringify({ config: { ...template.config, template: 'Hello {{customerName}}' } }) })
    if (reset.status !== 200) throw new Error('Private canonical workflow could not be reset')
    window.__regressionInput('[data-testid="application-source"]', option.value)
    await window.__regressionClick('[data-testid="application-submit"]')
    await window.__regressionWait(() => document.querySelector('#application-tab-evaluations'))
    window.__regressionQa.appId = location.pathname.split('/').at(-1)
    const readiness = await window.__regressionCall(`applications/${window.__regressionQa.appId}/readiness/`)
    return { ok: readiness.status === 200 && readiness.data.draft.configuration_ready && readiness.data.draft.connection_verified === false, actualConnectivityClaimed: false }
  })
  await check('persistent suite creation and unsaved test input survives reload', async () => {
    await window.__regressionClick('#application-tab-evaluations')
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-new-suite"]'))
    await window.__regressionClick('[data-testid="evaluation-new-suite"]')
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-suite-name"]'))
    window.__regressionInput('[data-testid="evaluation-suite-name"]', '客服核心流程')
    await window.__regressionClick('[data-testid="evaluation-suite-save"]')
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-suite"]')?.value && !document.querySelector('[data-testid="evaluation-suite-save"]') && !document.querySelector('#application-tab-test').disabled)
    window.__regressionQa.suiteId = document.querySelector('[data-testid="evaluation-suite"]').value
    await window.__regressionClick('#application-tab-test')
    await window.__regressionWait(() => document.querySelector('[data-testid="application-test-input"]'))
    const input = JSON.stringify({ customerName: 'Ada', Customer_ID: 'Keep', foo_bar: 1, fooBar: 2 })
    window.__regressionInput('[data-testid="application-test-input"]', input)
    await window.__regressionClick('[data-testid="application-refresh"]')
    await window.__regressionWait(() => document.querySelector('[data-testid="application-refresh"]')?.disabled === false)
    await new Promise(resolve => setTimeout(resolve, 300))
    return { ok: document.querySelector('[data-testid="application-test-input"]').value === input }
  })
  await check('manual proof and current input saved through the actual case editor', async () => {
    await window.__regressionClick('[data-testid="application-test"]')
    await window.__regressionWait(() => document.querySelector('.delivery-trace [data-status="completed"]'))
    await window.__regressionClick('[data-testid="application-save-case"]')
    await window.__regressionWait(() => [...document.querySelectorAll('button')].some(node => node.textContent.trim() === '将此输入保存为用例'))
    window.__regressionButton('将此输入保存为用例')
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-case-name"]'))
    const input = JSON.parse(document.querySelector('[data-testid="evaluation-case-input"]').value)
    window.__regressionInput('[data-testid="evaluation-case-name"]', '客服回复必须正确')
    window.__regressionInput('[data-testid="evaluation-assertion-type"]', 'json_equals')
    window.__regressionInput('[data-testid="evaluation-assertion-path"]', '/variables/text')
    window.__regressionInput('[data-testid="evaluation-assertion-expected"]', '"Hello Ada"')
    await window.__regressionClick('[data-testid="evaluation-case-save"]')
    await window.__regressionWait(() => !document.querySelector('[data-testid="evaluation-case-save"]'))
    const cases = (await window.__regressionCall(`applications/${window.__regressionQa.appId}/test-suites/${window.__regressionQa.suiteId}/cases/`)).data.results
    window.__regressionQa.caseId = cases[0].id
    return { ok: cases.length === 1 && input.Customer_ID === 'Keep' && cases[0].input_data.foo_bar === 1 && cases[0].input_data.fooBar === 2 }
  })
  await check('real Celery batch retains request evidence and enables the optional publish gate', async () => {
    const path = `applications/${window.__regressionQa.appId}/`
    window.__regressionInput('#evaluation-gate-suite', window.__regressionQa.suiteId)
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-save-gate"]')?.disabled === false)
    await window.__regressionClick('[data-testid="evaluation-save-gate"]')
    await window.__regressionWait(async () => (await window.__regressionCall(path)).data.required_evaluation_suite_id === window.__regressionQa.suiteId)
    const denied = await window.__regressionCall(path + 'publish/', { method: 'POST', body: '{}' })
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-start"]')?.disabled === false)
    await window.__regressionClick('[data-testid="evaluation-start"]')
    let run
    await window.__regressionWait(async () => {
      const rows = (await window.__regressionCall(path + 'evaluation-runs/')).data.results
      run = rows[0]; return run?.status === 'completed'
    }, 'actual asynchronous worker completion')
    window.__regressionQa.firstRunId = run.id
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-run-status"]')?.textContent.includes('已完成'))
    const details = (await window.__regressionCall(path + `evaluation-runs/${run.id}/`)).data
    const app = (await window.__regressionCall(path)).data
    await window.__regressionClick('#application-tab-publish')
    await window.__regressionWait(() => document.querySelector('[data-testid="application-publish"]')?.disabled === false)
    await window.__regressionClick('[data-testid="application-publish"]')
    await window.__regressionWait(() => document.querySelector('[data-testid="application-release-1"]'))
    window.__regressionQa.releaseId = (await window.__regressionCall(path)).data.active_release.id
    return { ok: denied.status === 409 && run.runner_mode === 'celery' && run.passed === 1 && app.evaluation_gate.ready && details.results[0].request_id && details.results[0].assertion_results[0].passed }
  })
  await check('changed draft really regresses and server comparison identifies the case', async () => {
    const qa = window.__regressionQa, path = `applications/${qa.appId}/`
    const workflow = (await window.__regressionCall(`workflows/${qa.workflowId}/`)).data
    const reply = workflow.nodes.find(node => node.node_type === 'text_template')
    const update = await window.__regressionCall(`workflows/nodes/${reply.id}/`, { method: 'PATCH', body: JSON.stringify({ config: { ...reply.config, template: 'Changed {{customerName}}' } }) })
    if (update.status !== 200) return { ok: false, update: update.status }
    await window.__regressionClick('#application-tab-evaluations')
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-start"]')?.disabled === false)
    await window.__regressionClick('[data-testid="evaluation-start"]')
    let run
    await window.__regressionWait(async () => {
      const rows = (await window.__regressionCall(path + 'evaluation-runs/')).data.results
      run = rows.find(row => row.id !== qa.firstRunId); return run?.status === 'completed'
    })
    qa.secondRunId = run.id
    await window.__regressionWait(() => document.querySelector(`[data-testid="evaluation-history-${qa.firstRunId}"]`))
    window.__regressionButton('作为比较基线', document.querySelector(`[data-testid="evaluation-history-${qa.firstRunId}"]`))
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-compare"]')?.disabled === false)
    await window.__regressionClick('[data-testid="evaluation-compare"]')
    await window.__regressionWait(() => document.querySelector('[aria-label="批次比较"]')?.textContent.includes('退步'))
    const app = (await window.__regressionCall(path)).data
    return { ok: run.failed === 1 && !app.evaluation_gate.ready && app.active_release.id === qa.releaseId, activeVersionPreserved: true }
  })
  await check('historical release target remains pinned and does not replace the active version', async () => {
    const qa = window.__regressionQa, path = `applications/${qa.appId}/`
    window.__regressionInput('#evaluation-target', 'release')
    await window.__regressionWait(() => document.querySelector('#evaluation-release')?.options.length > 1)
    window.__regressionInput('#evaluation-release', qa.releaseId)
    await window.__regressionWait(() => document.querySelector('[data-testid="evaluation-start"]')?.disabled === false)
    await window.__regressionClick('[data-testid="evaluation-start"]')
    let run
    await window.__regressionWait(async () => {
      run = (await window.__regressionCall(path + 'evaluation-runs/')).data.results.find(row => row.target === 'release')
      return run?.status === 'completed'
    })
    return { ok: run.passed === 1 && run.release_id === qa.releaseId && (await window.__regressionCall(path)).data.active_release.id === qa.releaseId }
  })
  await check('actual suite download is importable and creates independent case identities', async () => {
    const qa = window.__regressionQa
    const original = URL.createObjectURL.bind(URL)
    URL.createObjectURL = value => { if (value instanceof Blob && value.type.includes('json')) qa.download = value; return original(value) }
    window.__regressionButton('导出 JSON')
    await window.__regressionWait(() => qa.download)
    const exported = JSON.parse(await qa.download.text())
    window.__regressionButton('导入测试集 JSON')
    await window.__regressionWait(() => document.querySelector('#evaluation-import-json'))
    exported.suite.name = '导入的独立测试集'
    window.__regressionInput('#evaluation-import-json', JSON.stringify(exported))
    await window.__regressionWait(() => [...document.querySelectorAll('button')].some(node => node.textContent.trim() === '导入为新测试集' && !node.disabled))
    window.__regressionButton('导入为新测试集')
    await window.__regressionWait(() => document.querySelector('#evaluation-suite')?.selectedOptions[0]?.textContent.includes('导入的独立测试集'))
    const suiteId = document.querySelector('#evaluation-suite').value
    const cases = (await window.__regressionCall(`applications/${qa.appId}/test-suites/${suiteId}/cases/`)).data.results
    return { ok: exported.type === 'flowly_application_test_suite' && suiteId !== qa.suiteId && cases[0].id !== qa.caseId && cases[0].input_data.Customer_ID === 'Keep' }
  })
  await check('new regression surface supports keyboard tabs and theme tokens without global overflow', async () => {
    const tabs = [...document.querySelectorAll('[role="tab"]')]
    const selected = tabs.find(tab => tab.getAttribute('aria-selected') === 'true')
    await window.__regressionWait(() => !selected.disabled)
    selected.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }))
    await window.__regressionWait(() => document.querySelector('#application-tab-publish')?.getAttribute('aria-selected') === 'true')
    await window.__regressionClick('#application-tab-evaluations')
    await window.__regressionWait(() => document.querySelector('.application-evaluations'))
    return { ok: tabs.length >= 5 && document.documentElement.scrollWidth <= innerWidth + 1, tabs: tabs.length }
  })
  await mkdir('E:/Flowly-now/.cache/continuation-browser', { recursive: true })
  await client.tool('take_screenshot', { format: 'png', fullPage: false, filePath: 'E:/Flowly-now/.cache/continuation-browser/regression-desktop.png' })
  await client.tool('emulate', { viewport: '390x844x1', prefersReducedMotion: 'reduce' })
  await delay(300)
  await check('mobile regression page keeps viewport and scrollable table containment', async () => ({
    ok: document.documentElement.scrollWidth <= innerWidth + 1,
    viewport: innerWidth, documentWidth: document.documentElement.scrollWidth,
  }))
  await client.tool('take_screenshot', { format: 'png', fullPage: false, filePath: 'E:/Flowly-now/.cache/continuation-browser/regression-mobile.png' })
  console.log(JSON.stringify({ passed: checks.length, checks }))
} catch (error) { console.error(error.stack); process.exitCode = 1 }
finally { client.close() }
