import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
import { McpClient, evalPage, resultText, delay } from './chrome_mcp_client.mjs'

process.env.CHROME_MCP_BROWSER_URL ||= 'http://127.0.0.1:9223'
const output = path.resolve(import.meta.dirname, '../output/training-monitor')
const client = new McpClient()
const evidence = { tool: 'official chrome-devtools MCP', checks: [] }
const binding = JSON.parse(await fs.readFile(path.join(output, 'workflow-binding.json'), 'utf8'))
const username = process.env.FLOWLY_E2E_USERNAME
const password = process.env.FLOWLY_E2E_PASSWORD
assert(username && password, 'Provide credentials for an existing account')

async function control(label, role = 'button', value) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(row => row.includes(`${role} "${label}"`))
  assert(line, `Missing ${role}: ${label}`)
  const uid = line.match(/uid=(\S+)/)[1]
  await client.tool(value === undefined ? 'click' : 'fill', value === undefined ? { uid } : { uid, value })
}
async function wait(expression) {
  const deadline = Date.now() + 15000
  while (Date.now() < deadline) {
    const value = await evalPage(client, expression)
    if (value) return value
    await delay(300)
  }
  throw new Error(`UI did not settle: ${expression}`)
}
async function signIn() {
  await control('用户名或邮箱', 'textbox', username)
  await control('登录密码', 'textbox', password)
  await evalPage(client, `() => {
    const label = [...document.querySelectorAll('label')].find(el => el.textContent.includes('记住我'));
    if (label && !label.querySelector('input').checked) label.click();
  }`)
  await control('登录')
  await wait(`() => !location.href.includes('/login')`)
  const url = await evalPage(client, `() => location.href.split('#')[0] + '#/workflows/${binding.workflowId}/edit'`)
  await client.tool('navigate_page', { type: 'url', url })
  await wait(`() => Boolean(document.querySelector('[data-testid="yolo-training-details-${binding.nodeId}"]'))`)
  await control('查看训练详情')
  return wait(`async () => {
    try { const data = await window.flowlyDesktop.training.monitor.snapshot();
      return data?.viewer && { viewer: data.viewer, epochs: data.completedEpochs, classes: data.classes.length };
    } catch { return false; }
  }`)
}
async function signOut() {
  await evalPage(client, `() => document.querySelector('.yolo-run-dialog .el-dialog__headerbtn')?.click()`)
  await control('打开账户菜单')
  await control('退出登录', 'menuitem')
  await wait(`() => location.href.includes('/login')`)
}
try {
  await client.initialize()
  const tools = (await client.request('tools/list')).tools
  assert(tools.some(tool => tool.name === 'navigate_page'))
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  const pages = resultText(await client.tool('list_pages'))
  const page = pages.split('\n').find(line => line.includes('/renderer/index.html'))
  assert(page, 'Run against the built Electron app')
  client.pageId = Number(page.match(/^(\d+):/)[1])
  if (await evalPage(client, `() => Boolean(document.querySelector('[aria-label="打开账户菜单"]'))`)) await signOut()
  const loginUrl = await evalPage(client, `() => location.href.split('#')[0] + '#/login'`)
  if (!process.env.FLOWLY_QA_CONFIG_FAILURE_READY) {
    await client.tool('emulate', { networkConditions: 'Offline' })
    await client.tool('navigate_page', { type: 'url', url: loginUrl })
    await client.tool('navigate_page', { type: 'reload', ignoreCache: true })
  }
  await wait(`() => [...document.querySelectorAll('[role=dialog]')].some(el => el.getClientRects().length && el.innerText.includes('注册配置暂时不可用'))`)
  const notice = await evalPage(client, `() => ({
    banner: Boolean(document.querySelector('.auth-portal__panel-inner > .el-alert')),
    bypass: document.body.innerText.includes('无需登录'),
    dialogs: [...document.querySelectorAll('[role=dialog]')].filter(el => el.getClientRects().length).length
  })`)
  assert(!notice.banner && !notice.bypass && notice.dialogs === 1)
  evidence.checks.push('configuration connection failure shows one popup, no banner or login bypass')
  await control('关闭提示')
  await control('注册', 'tab')
  await wait(`() => [...document.querySelectorAll('[role=dialog]')].some(el => el.getClientRects().length)`)
  await client.tool('emulate', {})
  await control('重新加载')
  await wait(`() => [...document.querySelectorAll('[role=dialog]')].every(el => !el.getClientRects().length)`)
  evidence.checks.push('retry after network recovery closes the popup')
  await control('登录', 'tab')
  const denied = await evalPage(client, `async () => {
    const results = {};
    for (const method of ['snapshot', 'start', 'refresh']) {
      try { await window.flowlyDesktop.training.monitor[method](); results[method] = false; }
      catch { results[method] = true; }
    }
    return results;
  }`)
  assert(Object.values(denied).every(Boolean), JSON.stringify(denied))
  await client.tool('navigate_page', { type: 'url', url: loginUrl.split('#')[0] + '#/workflows/' + binding.workflowId + '/edit' })
  await wait(`() => location.href.includes('/login')`)
  evidence.checks.push('unauthenticated route and data IPC reject access')
  evidence.session = await signIn()
  assert.equal(evidence.session.classes, 38)
  assert.equal(evidence.session.epochs, 40)
  await signOut()
  assert(await evalPage(client, `async () => {
    try { await window.flowlyDesktop.training.monitor.snapshot(); return false; } catch { return true; }
  }`))
  evidence.checks.push('existing account logs in; logout clears native data')
  evidence.finalSession = await signIn()
  evidence.checks.push('desktop left logged in with the YOLO node details open inside its workflow')
  evidence.passed = true
} catch (error) {
  evidence.passed = false
  evidence.error = error.stack
  process.exitCode = 1
} finally {
  if (client.pageId !== undefined) await client.tool('emulate', {}).catch(() => {})
  evidence.finishedAt = new Date().toISOString()
  await fs.mkdir(output, { recursive: true })
  await fs.writeFile(path.join(output, 'auth-dialog-verification.json'), JSON.stringify(evidence, null, 2))
  console.log(JSON.stringify(evidence, null, 2))
  client.close()
}
