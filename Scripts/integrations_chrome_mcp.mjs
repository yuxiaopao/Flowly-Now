import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { McpClient, evalPage, resultText, login } from './chrome_mcp_client.mjs'

// Requires a disposable QA user, an isolated backend with explicit loopback allowlist,
// and a controlled receiver supporting /accept (200) and /reject (403).
const ROOT = path.resolve(import.meta.dirname, '..')
const OUTPUT = path.join(ROOT, 'Docs/verification/integrations-20261019')
const QA_API = process.env.INTEGRATIONS_QA_API || 'http://127.0.0.1:8001/api/v1'
const RECEIVER = process.env.INTEGRATIONS_QA_RECEIVER || 'http://127.0.0.1:8766'
const QA_SETTINGS = process.env.INTEGRATIONS_QA_SETTINGS || 'tests.integrations_e2e_settings'
const username = process.env.FLOWLY_E2E_USERNAME
assert.ok(username?.startsWith('integrations_qa_'), 'Use a disposable integrations_qa_ user')
fs.mkdirSync(OUTPUT, { recursive: true })
const c = new McpClient(), checks = []
function pass(name, evidence = true) { checks.push({ name, evidence }); console.log(`PASS ${name}`) }
async function snapshot() { return resultText(await c.tool('take_snapshot')) }
async function uid(role, name, last = false) {
  const lines = (await snapshot()).split('\n').filter(line => line.includes(`${role} "${name}"`) || line.includes(`${role} "*${name}"`))
  const line = last ? lines.at(-1) : lines[0]
  assert.ok(line, `${role} ${name} not found`)
  return line.match(/uid=(\S+)/)[1]
}
async function click(name, last = false) { await c.tool('click', { uid: await uid('button', name, last) }) }
async function fill(name, value) { await c.tool('fill', { uid: await uid('textbox', name), value }) }
async function waitFor(expression) {
  const ok = await evalPage(c, `async()=>{const end=Date.now()+20000;while(Date.now()<end){if(${expression})return true;await new Promise(r=>setTimeout(r,100))}return false}`, 25000)
  assert.equal(ok, true, expression)
}
async function api(expression) {
  return evalPage(c, `async()=>{const {api}=await import('/src/api/index.js');api.defaults.baseURL=${JSON.stringify(QA_API)};${expression}}`)
}
async function records() { return api(`const r=await api.get('/integrations/integrations/');return r.results||r`) }
async function capture(name) {
  console.log(`SCREENSHOT ${name}`)
  await c.tool('take_screenshot', { filePath: path.join(OUTPUT, `${name}.png`), fullPage: !name.includes('drawer') && !['verified','rejected'].includes(name) })
}
try {
  await c.initialize()
  const { tools } = await c.request('tools/list')
  assert.ok(tools.some(t => t.name === 'navigate_page'))
  c.pageTools = new Set(tools.filter(t => t.inputSchema?.properties?.pageId).map(t => t.name))
  await login(c)
  await c.tool('navigate_page', { url: 'http://localhost:5200/settings/integrations' })
  await c.tool('wait_for', { text: ['配置连接'] })
  await api(`const r=await api.get('/integrations/integrations/');for(const row of r.results||r)await api.delete('/integrations/integrations/'+row.id+'/');return true`)
  await click('刷新')
  await waitFor("document.querySelectorAll('.service-card').length===18")
  const logos = await evalPage(c, `()=>[...document.querySelectorAll('.integration-logo img')].map(i=>({name:i.alt,loaded:i.complete&&i.naturalWidth>0}))`)
  assert.equal(logos.length, 17); assert.ok(logos.every(i => i.loaded))
  pass('18 services and 17 original brand logos', logos)
  await fill('搜索服务、能力或关键词', 'GitHub'); await waitFor("document.querySelectorAll('.service-card').length===1")
  await fill('搜索服务、能力或关键词', 'no-service-matches'); await c.tool('wait_for', { text: ['没有匹配的集成'] })
  await click('清除筛选'); await waitFor("document.querySelectorAll('.service-card').length===18")
  await c.tool('click', { uid: await uid('tab', '存储 1') }); await waitFor("document.querySelectorAll('.service-card').length===1")
  await c.tool('click', { uid: await uid('tab', '全部 18') }); pass('Search, empty results and category filters')
  await click('配置连接 自定义 Webhook')
  await click('保存并测试'); await c.tool('wait_for', { text: ['请填写Webhook 地址'] }); pass('Required field prevents empty save')
  await fill('连接名称', '集成自动化验收')
  await fill('Webhook 地址', `${RECEIVER}/accept`)
  await fill('签名密钥 (选填)', 'integration-test-signing')
  await c.tool('click', { uid: await uid('checkbox', '工作流执行成功') }).catch(async () => {
    // Element Plus visually hides its native checkbox; activate its visible label.
    await evalPage(c, `()=>{const input=[...document.querySelectorAll('.el-drawer input[type=checkbox]')].find(i=>i.value==='execution.completed');input.closest('label').click();return input.checked}`)
  })
  await click('保存配置'); await c.tool('wait_for', { text: ['配置已保存，请测试连接。'] })
  let rows = await records(); assert.equal(rows.length, 1); assert.equal(rows[0].verificationStatus, 'untested')
  assert.ok(!JSON.stringify(rows).includes('integration-test-signing'))
  assert.equal(await evalPage(c, `()=>document.querySelector('#integration-webhook_url').value`), '')
  pass('Save persists unverified config and never echoes credentials')
  await click('测试连接'); await c.tool('wait_for', { text: ['目标服务已确认本次请求。'] })
  rows = await records(); assert.equal(rows[0].verificationStatus, 'success'); assert.equal(rows[0].isConnected, true)
  await capture('verified'); pass('Real HTTP delivery succeeds with visible evidence')
  const eventOutput = execFileSync(path.join(ROOT, '.venv/Scripts/python.exe'), ['-c', `import os,json;os.environ['DJANGO_SETTINGS_MODULE']=${JSON.stringify(QA_SETTINGS)};import django;django.setup();from django.contrib.auth import get_user_model;from workflows.models import Workflow,WorkflowExecution;from integrations.models import IntegrationDelivery;u=get_user_model().objects.get(username=${JSON.stringify(username)});w=Workflow.objects.create(owner=u,name='集成事件验收');e=WorkflowExecution.objects.create(workflow=w,version=1,status='pending');e.mark_completed({'private':'must-not-leak'});e.save();logs=list(IntegrationDelivery.objects.filter(integration__user=u,event='execution.completed').values('status','payload'));print(json.dumps(logs));w.delete()`], { cwd: path.join(ROOT, 'Backend'), env: { ...process.env, PYTHONPATH: `${ROOT};${path.join(ROOT,'Backend')}` }, encoding: 'utf8', windowsHide: true })
  assert.ok(eventOutput.includes('"status": "success"')); assert.ok(!eventOutput.includes('must-not-leak'))
  pass('Workflow completion dispatches exactly one real event without workflow output')
  await click('关闭'); await click('刷新'); await click('管理连接 自定义 Webhook')
  assert.ok((await snapshot()).includes('工作流执行成功'))
  await fill('Webhook 地址', `${RECEIVER}/reject`); await click('保存并测试')
  await waitFor("document.querySelector('.verification-section')?.innerText.includes('验证失败')")
  rows = await records(); assert.equal(rows[0].isConnected, false); assert.equal(rows[0].verificationStatus, 'failed')
  await capture('rejected'); pass('HTTP 403 produces failed status and delivery evidence')
  await fill('Webhook 地址', `${RECEIVER}/accept`); await click('保存并测试')
  await waitFor("document.querySelector('.verification-section')?.innerText.includes('已验证')")
  await click('断开连接'); await waitFor("document.querySelector('.verification-section')?.innerText.includes('已断开')")
  rows = await records(); assert.equal(rows[0].isActive, false); assert.equal(rows[0].isConnected, false)
  await click('关闭'); await click('刷新'); await click('管理连接 自定义 Webhook')
  assert.ok((await snapshot()).includes('已断开')); pass('Disconnect survives refresh')
  await click('新建另一条连接'); await fill('连接名称', '第二条连接'); await fill('Webhook 地址', `${RECEIVER}/accept`)
  await click('保存配置'); await waitFor("document.querySelectorAll('.connection-picker').length===1")
  rows = await records(); assert.equal(rows.length, 2); pass('Multiple independent connections for one provider')
  await click('删除连接'); await click('删除连接', true)
  await waitFor("!document.querySelector('.el-message-box')")
  await click('删除连接'); await click('删除连接', true)
  await waitFor("!document.querySelector('.connection-picker')")
  rows = await records(); assert.equal(rows.length, 0); pass('Deletion removes only the selected connection')
  await click('关闭')
  await click('配置连接 GitHub'); await fill('访问令牌', 'integrations-qa-token'); await click('保存并测试')
  await waitFor("document.querySelector('.verification-section')?.innerText.includes('已验证')")
  await click('读取数据'); await c.tool('wait_for', { text: ['flowly/connector-verification'] })
  rows = await records(); assert.equal(rows[0].lastResult.items[0].name, 'flowly/connector-verification')
  await capture('api-read-drawer'); pass('Read-only API resource appears in UI through real controlled HTTP')
  await fill('访问令牌', 'invalid-test-token'); await click('保存并测试')
  await waitFor("document.querySelector('.verification-section')?.innerText.includes('验证失败')")
  rows = await records(); assert.equal(rows[0].isConnected, false)
  await click('删除连接'); await click('删除连接', true); await waitFor("!document.querySelector('.connection-picker')")
  await click('关闭'); pass('Invalid API token is rejected and old data cleared')
  await c.tool('emulate', { networkConditions: 'Offline' }); await click('刷新')
  await c.tool('wait_for', { text: ['集成加载失败，请检查网络后重试。'] }); pass('Offline failure offers retry')
  await c.tool('emulate', {}); await click('重新加载'); await waitFor("document.querySelectorAll('.service-card').length===18")
  pass('Retry recovers the complete catalog')
  for (const theme of ['light', 'dark', 'pure-bw', 'high-contrast']) {
    await evalPage(c, `async()=>{const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme(${JSON.stringify(theme)});return true}`)
    await capture(theme)
  }
  await c.tool('emulate', { viewport: '390x844x1,mobile,touch' })
  await c.tool('wait_for', { text: ['配置连接 飞书', '配置连接'] })
  await waitFor("document.querySelectorAll('.service-card').length===18")
  await evalPage(c, `async()=>{const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme('light');return true}`)
  await capture('mobile')
  assert.equal(await evalPage(c, `()=>document.documentElement.scrollWidth<=innerWidth`), true)
  await click('配置连接 飞书'); await capture('mobile-drawer')
  assert.equal(await evalPage(c, `()=>document.querySelector('.el-drawer').scrollWidth<=innerWidth`), true)
  await click('关闭'); pass('Four themes and mobile catalog/drawer have no horizontal overflow')
  await c.tool('emulate', {})
  const consoleErrors = resultText(await c.tool('list_console_messages', { types: ['error'] }))
  fs.writeFileSync(path.join(OUTPUT, 'browser-console.txt'), consoleErrors)
  fs.writeFileSync(path.join(OUTPUT, 'checks.json'), JSON.stringify({ transport: 'chrome-devtools MCP', checks }, null, 2))
} catch (error) {
  fs.writeFileSync(path.join(OUTPUT, 'failure-snapshot.txt'), await snapshot().catch(() => 'unavailable'))
  console.error(error.stack); process.exitCode = 1
} finally { c.close() }
