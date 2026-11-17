import assert from 'node:assert/strict'
import { McpClient, evalPage, login, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'

if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('This test requires explicitly isolated QA fixtures')
const client = new McpClient()
const checks = []
async function page(fn) { return evalPage(client, fn.toString(), 45000) }
async function check(name, run) {
  const result = await run()
  assert.equal(result?.ok, true, `${name}: ${JSON.stringify(result)}`)
  checks.push(name)
  console.log(JSON.stringify({ name, ...result }))
}

try {
  await client.initialize()
  assert(client.pageTools.has('navigate_page'))
  await login(client, { entryPath: '/api/health/' })
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/applications?create=1` })
  await delay(700)
  await check('temporarily save a team application draft and open contextual knowledge creation', () => page(async () => {
    const marker = await fetch('/api/v1/__isolated-qa__/').then(response => response.json())
    if (!marker.isolated || !marker.product_fixtures || !marker.application_context?.tenant_id) throw new Error('Refusing a non-fixture or missing-context backend')
    window.__contextWait = async predicate => {
      for (let attempt = 0; attempt < 300; attempt++) {
        if (await predicate()) return
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      throw new Error('Timed out waiting for the real application resource flow')
    }
    await window.__contextWait(() => document.querySelector('#app')?.__vue_app__?.config.globalProperties?.$pinia?._s.get('auth')?.user?.id)
    const auth = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('auth')
    if (!auth.token) throw new Error('The real frontend session did not hydrate')
    window.__contextQa = { tenantId: String(marker.application_context.tenant_id), tenantName: marker.application_context.tenant_name || marker.application_context.name,
      name: `QA 知识交付 ${Date.now()}`, description: '创建知识资源后必须恢复的应用用途说明', token: auth.token }
    window.__contextInput = (selector, value) => {
      const input = document.querySelector(selector)
      if (!input) throw new Error(`Missing field ${selector}`)
      input.value = value
      input.dispatchEvent(new Event(input.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
    }
    window.__contextVisible = element => Boolean(element && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden')
    window.__contextButton = (text, scope = document) => [...scope.querySelectorAll('button')]
      .find(button => window.__contextVisible(button) && button.textContent.replace(/\s+/g, '') === text)
    window.__contextDialog = () => [...document.querySelectorAll('.el-dialog')].find(element => window.__contextVisible(element) && element.textContent.includes('创建文档集合'))
    window.__contextCall = async path => {
      const response = await fetch(`/api/v1/${path}`, { headers: { Authorization: `Bearer ${window.__contextQa.token}` } })
      if (!response.ok) throw new Error('Isolated verification API failed: ' + response.status)
      const result = await response.json()
      return result.data ?? result
    }
    await window.__contextWait(() => [...(document.querySelector('[aria-label="所属空间"]')?.options || [])].some(option => option.value === window.__contextQa.tenantId))
    const available = await window.__contextCall(`applications/resources/?kind=knowledge&tenant_id=${encodeURIComponent(window.__contextQa.tenantId)}`)
    if ((available.results || []).length) throw new Error('The context fixture team must initially have no eligible knowledge resources')
    window.__contextInput('[aria-label="应用名称"]', window.__contextQa.name)
    window.__contextInput('[aria-label="用途说明"]', window.__contextQa.description)
    window.__contextInput('[aria-label="所属空间"]', window.__contextQa.tenantId)
    await window.__contextWait(() => window.__contextButton('先创建知识库'))
    window.__contextButton('先创建知识库').click()
    await window.__contextWait(() => location.pathname === '/knowledge' && window.__contextDialog()?.querySelector('input[placeholder="输入集合名称"]'))
    const parameters = new URLSearchParams(location.search)
    const opaqueUrl = [...parameters.keys()].length === 1
      && /^[0-9a-f]{8}-[0-9a-f-]{27}$/i.test(parameters.get('applicationDraft') || '')
    const dialog = window.__contextDialog()
    const teamSelect = [...dialog.querySelectorAll('.el-form-item')].find(row => row.textContent.includes('所属团队'))?.querySelector('.el-select')
    const disabled = teamSelect?.classList.contains('is-disabled') || teamSelect?.querySelector('.is-disabled, input:disabled, [aria-disabled="true"]')
    const pinned = Boolean(disabled) && dialog.textContent.includes(window.__contextQa.tenantName)
    return { ok: opaqueUrl && pinned && !document.querySelector('.modal-box'), opaqueUrl, teamPinned: Boolean(pinned) }
  }))

  await check('cancel contextual collection creation and recover the unchanged application draft', () => page(async () => {
    const dialog = window.__contextDialog()
    const field = dialog.querySelector('input[placeholder="输入集合名称"]')
    field.value = '取消后不得创建的临时知识库'
    field.dispatchEvent(new Event('input', { bubbles: true }))
    window.__contextButton('取消', dialog).click()
    await window.__contextWait(() => location.pathname === '/applications'
      && document.querySelector('[aria-label="应用名称"]')?.value === window.__contextQa.name
      && document.querySelector('[aria-label="所属空间"]')?.value === window.__contextQa.tenantId)
    const sameDraft = document.querySelector('[aria-label="应用名称"]').value === window.__contextQa.name
      && document.querySelector('[aria-label="用途说明"]').value === window.__contextQa.description
      && document.querySelector('[aria-label="所属空间"]').value === window.__contextQa.tenantId
    const available = await window.__contextCall(`applications/resources/?kind=knowledge&tenant_id=${encodeURIComponent(window.__contextQa.tenantId)}`)
    return { ok: sameDraft && !available.results.length && !document.querySelector('.modal-box'), originalDraftRestored: sameDraft, noCollectionCreated: !available.results.length }
  }))

  await check('create a real same-team collection and bind it on the restored application form', () => page(async () => {
    await window.__contextWait(() => window.__contextButton('先创建知识库'))
    window.__contextButton('先创建知识库').click()
    await window.__contextWait(() => location.pathname === '/knowledge' && window.__contextDialog())
    const dialog = window.__contextDialog()
    const field = dialog.querySelector('input[placeholder="输入集合名称"]')
    field.value = `QA 客户手册 ${Date.now()}`
    field.dispatchEvent(new Event('input', { bubbles: true }))
    window.__contextButton('创建', dialog).click()
    await window.__contextWait(() => location.pathname === '/applications' && document.querySelector('[aria-label="知识库"]')?.value)
    const id = document.querySelector('[aria-label="知识库"]').value
    const collection = await window.__contextCall(`rag/collections/${encodeURIComponent(id)}/`)
    window.__contextQa.collectionId = id
    const restored = document.querySelector('[aria-label="应用名称"]').value === window.__contextQa.name
      && document.querySelector('[aria-label="用途说明"]').value === window.__contextQa.description
      && document.querySelector('[aria-label="所属空间"]').value === window.__contextQa.tenantId
    return { ok: restored && String(collection.tenant) === window.__contextQa.tenantId, originalDraftRestored: restored, sameTeamCollection: String(collection.tenant) === window.__contextQa.tenantId }
  }))

  await check('submit the recovered application through the real form and verify persisted resource ownership', () => page(async () => {
    document.querySelector('[data-testid="application-submit"]').click()
    await window.__contextWait(() => /^\/applications\/[0-9a-f-]+$/.test(location.pathname))
    const id = location.pathname.split('/').at(-1)
    const application = await window.__contextCall(`applications/${encodeURIComponent(id)}/`)
    const sameResource = application.draft.collection_id === window.__contextQa.collectionId
    const sameTeam = String(application.tenant_id) === window.__contextQa.tenantId
    const sameText = application.name === window.__contextQa.name && application.description === window.__contextQa.description
    return { ok: sameResource && sameTeam && sameText, persisted: true, sameResource, sameTeam, sameText }
  }))
  console.log(JSON.stringify({ passed: checks.length, failed: 0, browser: 'chrome-devtools-mcp', scope: 'isolated context resource roundtrip' }))
} finally { client.close() }
