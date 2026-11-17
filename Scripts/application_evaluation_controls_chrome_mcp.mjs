import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { McpClient, evalPage, login, FRONTEND_URL } from './chrome_mcp_client.mjs'

if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('An explicitly isolated QA backend is required')
const client = new McpClient(), checks = []
async function check(name, run) {
  const value = await evalPage(client, run.toString(), 60000)
  assert.equal(value?.ok, true, `${name}: ${JSON.stringify(value)}`)
  checks.push(name); console.log(JSON.stringify({ name, ...value }))
}
try {
  await client.initialize(); assert(client.pageTools.has('navigate_page'))
  await login(client, { entryPath: '/api/health/' })
  const setup = await evalPage(client, `async () => {
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json());
    if (!marker.isolated || !marker.async_evaluations) throw new Error('Private worker fixture required');
    window.__controlToken = localStorage.getItem('access_token');
    window.__controlCall = async (path, options = {}) => {
      const response = await fetch('/api/v1/'+path, {...options, headers: {Authorization: 'Bearer '+window.__controlToken, 'Content-Type':'application/json', ...(options.headers || {})}});
      const payload = await response.json(); return {status:response.status, data:payload.data ?? payload};
    };
    const apps = (await window.__controlCall('applications/?page_size=100')).data.results;
    const app = apps.find(row => row.name === '小团队回归发布验证' && row.kind === 'workflow' && row.tenant_id === null);
    if (!app) throw new Error('Run application_regressions_chrome_mcp first');
    return {id:app.id};
  }`)
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/applications/${setup.id}?tab=evaluations` })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await check('cancel a real running worker batch and never start its second case', async () => {
    const token = localStorage.getItem('access_token')
    window.__controlCall = async (path, options = {}) => {
      const response = await fetch('/api/v1/'+path, { ...options, headers: { Authorization: 'Bearer '+token, 'Content-Type': 'application/json', ...(options.headers || {}) } })
      const payload = await response.json(); return { status: response.status, data: payload.data ?? payload }
    }
    window.__controlWait = async predicate => {
      for (let n = 0; n < 300; n++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)) }
      throw new Error('Actual worker or UI did not settle')
    }
    window.__controlInput = async (selector, value) => {
      const field = document.querySelector(selector); if (!field) throw new Error('Missing '+selector)
      field.value = value; field.dispatchEvent(new Event(field.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
      await new Promise(resolve => requestAnimationFrame(resolve))
    }
    window.__controlClick = async selector => {
      await window.__controlWait(() => document.querySelector(selector) && !document.querySelector(selector).disabled)
      document.querySelector(selector).click(); await new Promise(resolve => requestAnimationFrame(resolve))
    }
    const id = location.pathname.split('/').at(-1), base = `applications/${id}/`
    const app = (await window.__controlCall(base)).data
    const workflow = (await window.__controlCall(`workflows/${app.draft.workflow_id}/`)).data
    const node = workflow.nodes.find(row => row.node_type === 'text_template')
    const suites = (await window.__controlCall(base+'test-suites/')).data.results
    const suite = suites.find(row => row.name === '客服核心流程')
    if (!node || !suite) throw new Error('Canonical regression fixture missing')
    const extra = await window.__controlCall(base+`test-suites/${suite.id}/cases/`, { method: 'POST', body: JSON.stringify({ name: 'Must never start after cancellation',
      input_data: {}, assertions: [{ type: 'json_exists', path: '', expected: true }], position: 100 }) })
    if (extra.status !== 201) throw new Error('Could not persist the second actual case')
    window.__controlQa = { id, base, workflow, node, suite, releaseId: app.active_release.id }
    try {
      const update = await window.__controlCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ node_type: 'delay', config: { duration: 8, unit: 'seconds' } }) })
      if (update.status !== 200) throw new Error('Could not configure the actual delay')
      await window.__controlWait(() => document.querySelector('#evaluation-suite'))
      await window.__controlInput('#evaluation-suite', suite.id)
      await window.__controlInput('#evaluation-target', 'draft')
      const refresh = [...document.querySelectorAll('button')].find(button => button.textContent.trim() === '刷新用例')
      await window.__controlWait(() => !refresh.disabled)
      refresh.click()
      await window.__controlWait(() => document.querySelector(`[data-testid="evaluation-case-${extra.data.id}"]`))
      await window.__controlClick('[data-testid="evaluation-start"]')
      let batch
      await window.__controlWait(async () => {
        const runs = (await window.__controlCall(base+'evaluation-runs/')).data.results
        const current = runs.find(row => row.suite_id === suite.id && row.status === 'running')
        if (!current) return false
        batch = (await window.__controlCall(base+`evaluation-runs/${current.id}/`)).data
        const requestId = batch.results[0]?.request_id
        if (!requestId) return false
        const record = (await window.__controlCall(base+`requests/${requestId}/`)).data
        if (!record.workflow_execution_id) return false
        const execution = (await window.__controlCall(base+`requests/${requestId}/execution/`)).data
        return execution.status === 'running' && execution.nodes.some(row => row.status === 'running')
      })
      await window.__controlClick('[data-testid="evaluation-cancel"]')
      await window.__controlWait(async () => { batch = (await window.__controlCall(base+`evaluation-runs/${batch.id}/`)).data; return batch.status === 'cancelled' })
      await window.__controlWait(() => document.querySelector('[data-testid="evaluation-run-status"]')?.textContent.includes('已取消'))
      const requests = batch.results.filter(row => row.request_id)
      const actual = (await window.__controlCall(base+`requests/${requests[0].request_id}/`)).data
      const requestButton = [...document.querySelectorAll(`[data-testid="evaluation-result-${batch.results[0].case_id_snapshot}"] button`)]
        .find(button => button.textContent.trim() === '查看真实请求')
      if (!requestButton) throw new Error('Missing actual request trace entry')
      requestButton.click()
      await window.__controlClick('[data-testid="application-workflow-trace-toggle"]')
      await window.__controlWait(() => document.querySelector('[aria-label="主流程节点状态"]'))
      const visibleTrace = document.querySelector('[data-testid="application-workflow-trace-status"]')?.textContent.includes('取消')
      return { ok: requests.length === 1 && actual.status === 'failed' && actual.error_code === 'evaluation_cancelled'
        && batch.results.at(-1).status === 'cancelled' && batch.results.at(-1).request_id === null && visibleTrace,
      actualRunningExecutionObserved: true, actualScopedTraceOpened: visibleTrace, requestsStarted: requests.length, totalCases: batch.total }
    } finally {
      await window.__controlCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ node_type: node.node_type, config: node.config }) })
      await window.__controlCall(base+`test-suites/${suite.id}/cases/${extra.data.id}/`, { method: 'DELETE' }).catch(() => {})
    }
  })
  await check('four actual themes keep the regression interface contained and readable', async () => {
    await document.querySelector('#app').__vue_app__.config.globalProperties.$router.replace({ query: { tab: 'evaluations' } })
    await window.__controlWait(() => document.querySelector('.application-evaluations h2'))
    const app = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('app')
    const results = []
    for (const theme of ['dark', 'light', 'pure-bw', 'high-contrast']) {
      app.setTheme(theme)
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
      const heading = document.querySelector('.application-evaluations h2')
      const text = getComputedStyle(heading).color
      results.push({ theme, text, applied: document.documentElement.dataset.theme === theme,
        contained: document.documentElement.scrollWidth <= innerWidth + 1 })
    }
    app.setTheme('dark')
    return { ok: results.every(row => row.applied && row.contained && row.text !== 'rgba(0, 0, 0, 0)'), themes: results }
  })
  await check('an unimplemented model deployment cannot become a tested or published application', async () => {
    const qa = window.__controlQa, node = qa.node
    try {
      const update = await window.__controlCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ node_type: 'model_deployment', config: { platform: 'local', modelPath: 'unprovisioned-fixture-model' } }) })
      if (update.status !== 200) throw new Error('Private configuration setup failed')
      const router = document.querySelector('#app').__vue_app__.config.globalProperties.$router
      await router.push(`/workflows/${qa.workflow.id}/edit`)
      await window.__controlWait(() => document.querySelector(`[data-id="${node.id}"]`))
      document.querySelector(`[data-id="${node.id}"]`).click()
      await window.__controlWait(() => document.body.textContent.includes('此节点尚未接入真实模型服务部署'))
      await router.push(`/applications/${qa.id}?tab=build`)
      await window.__controlWait(() => document.querySelector('[data-testid="application-readiness"]')?.textContent.includes('尚未接入'))
      const readiness = (await window.__controlCall(qa.base+'readiness/')).data
      await window.__controlClick('#application-tab-test')
      await window.__controlClick('[data-testid="application-test"]')
      await window.__controlWait(() => document.querySelector('.delivery-trace [data-status="failed"]'))
      const record = (await window.__controlCall(qa.base+'requests/')).data.results[0]
      await window.__controlClick('#application-tab-publish')
      await window.__controlWait(() => document.querySelector('[data-testid="application-publish"]'))
      const active = (await window.__controlCall(qa.base)).data.active_release
      return { ok: record.error_code === 'workflow_validation' && record.workflow_execution_id === null && record.output_data === null
        && !readiness.draft.configuration_ready && readiness.active_release.configuration_ready
        && document.querySelector('[data-testid="application-publish"]').disabled && active.id === qa.releaseId,
      falseDeploymentSuccessBlocked: true, existingReleasePreserved: true }
    } finally {
      await window.__controlCall(`workflows/nodes/${node.id}/`, { method: 'PATCH', body: JSON.stringify({ node_type: node.node_type, config: node.config }) })
    }
  })
  await mkdir('E:/Flowly-now/.cache/continuation-browser', { recursive: true })
  await client.tool('take_screenshot', { format: 'png', fullPage: false, filePath: 'E:/Flowly-now/.cache/continuation-browser/publish-gate.png' })
  console.log(JSON.stringify({ passed: checks.length, checks }))
} catch (error) { console.error(error.stack); process.exitCode = 1 }
finally { client.close() }
