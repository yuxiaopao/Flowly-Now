import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { McpClient, evalPage, resultText, login } from './chrome_mcp_client.mjs'

const output = 'E:/Flowly-now/Docs/verification/nl-creator-20261017'
mkdirSync(output, { recursive: true })
const client = new McpClient()
const fixture = JSON.parse(readFileSync(`${output}/fixture.json`, 'utf8'))
const checks = []
const evaluate = fn => evalPage(client, fn)
async function wait(expression, timeout = 20000) {
  return evaluate(`async () => { const end=Date.now()+${timeout}; while(Date.now()<end) { if (${expression}) return true; await new Promise(r=>setTimeout(r,150)); } throw new Error('Timed out: '+${JSON.stringify(expression)}); }`)
}
function check(name, passed, detail) {
  checks.push({ name, passed: Boolean(passed), detail })
  console.log(`${passed ? 'PASS' : 'FAIL'} ${name}`)
  writeFileSync(`${output}/browser-results.json`, JSON.stringify(checks, null, 2))
  if (!passed) throw new Error(`${name}: ${JSON.stringify(detail)}`)
}
async function uid(role, name) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(line => line.includes(`${role} "${name}"`) || line.includes(`${role} "${name} `))
  if (!line) throw new Error(`Missing ${role} ${name}\n${snapshot.slice(-12000)}`)
  return line.match(/uid=(\S+)/)[1]
}
async function click(name) { await client.tool('click', { uid: await uid('button', name) }) }
async function fill(name, value) { await client.tool('fill', { uid: await uid('textbox', name), value }) }
async function api(path) {
  return evaluate(`async () => { const r=await fetch('/api/v1${path}', {headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}}); const p=await r.json(); return {status:r.status,data:p.data||p}; }`)
}
async function go() {
  await client.tool('navigate_page', { url: 'http://localhost:5200/nl-create' })
  await client.tool('wait_for', { text: ['语创工作台'], timeout: 20000 })
  await wait(`document.querySelector('[role="tab"]')`)
}
try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  if (!tools.some(tool => tool.name === 'navigate_page')) throw new Error('navigate_page unavailable')
  await login(client)
  await evaluate(`() => { localStorage.removeItem('flowly_nl_workspace_v2:${fixture.userId}'); localStorage.setItem('theme','light'); }`)
  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await go()
  check('workspace initializes without waiting for model discovery', await evaluate(`() => Boolean(document.querySelector('[role="tab"]'))`))
  await click('数据处理 数据清洗与汇总')
  check('starter fills editable draft without sending', await evaluate(`() => document.querySelector('#chat-message-input').value.includes('CSV') && document.querySelectorAll('.message-user').length===0 && document.querySelector('[data-testid="mode-generate"]').getAttribute('aria-pressed')==='true'`))
  await fill('输入工作流描述', '第一个标签的草稿')
  await click('新标签')
  await fill('输入工作流描述', '第二个标签的草稿')
  await evaluate(`() => document.querySelector('[role="tab"]').click()`)
  check('tab drafts and modes remain independent', await evaluate(`() => document.querySelector('#chat-message-input').value==='第一个标签的草稿' && document.querySelector('[data-testid="mode-generate"]').getAttribute('aria-pressed')==='true'`))
  await go()
  check('draft survives reload', await evaluate(`() => document.querySelector('#chat-message-input').value==='第一个标签的草稿'`))
  await client.tool('take_screenshot', { filePath: `${output}/desktop-start.png`, fullPage: true })
  if (!process.env.NL_UI_ONLY) {
  await click('历史对话')
  await fill('搜索对话', 'NL-QA-20261017')
  await wait(`document.querySelectorAll('.session-item').length===30`)
  check('history first page has 30 records', true)
  await click('加载更多对话')
  await wait(`document.querySelectorAll('.session-item').length===33`)
  check('history loads records beyond the former 20-record limit', true)
  await click('失败')
  await wait(`document.querySelectorAll('.session-item').length===1`)
  check('history status filter matches backend failed status', await evaluate(`() => document.querySelector('.session-name').textContent.includes('历史 00')`))
  await click('全部')
  await fill('搜索对话', 'NL-QA-20261017 主流程')
  await wait(`document.querySelector('.session-name')?.textContent.includes('主流程')`)
  await click('NL-QA-20261017 主流程 已完成 验证完整语创操作链 刚刚 3 节点').catch(async () => {
    await evaluate(`() => document.querySelector('.session-item').click()`)
  })
  await wait(`document.querySelectorAll('.vue-flow__node').length===3`)
  check('history restores exactly one original user message', await evaluate(`() => document.querySelectorAll('.message-user').length===1`))
  await evaluate(`() => document.querySelector('.vue-flow__node[data-id="code"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`)
  await wait(`document.querySelector('#node-config-json')`)
  check('node form reads exact configuration keys', await evaluate(`() => document.querySelector('#node-config-json').value.includes('customCamelKey') && document.querySelector('#node-config-json').value.includes('Keep_CASE')`))
  await fill('节点参数 JSON', '{ invalid')
  await click('保存')
  await wait(`document.querySelector('.config-error')?.textContent.includes('JSON')`)
  check('invalid JSON blocks persistence with inline feedback', true)
  await fill('节点名称', '整理输入（已编辑）')
  const config = { language: 'python', code: 'result = {"message": "ok"}', customCamelKey: { Keep_CASE: true }, verificationValue: '真实保存' }
  await fill('节点参数 JSON', JSON.stringify(config, null, 2))
  await click('保存')
  await wait(`document.body.innerText.includes('节点配置已保存到会话草稿')`)
  const restored = await api(`/nl-workflow/sessions/${fixture.sessionId}/`)
  check('node edit persists name and arbitrary nested keys', restored.data.workflow_json.nodes[1].name==='整理输入（已编辑）' && restored.data.workflow_json.nodes[1].config.verificationValue==='真实保存', restored.status)
  await click('同步会话')
  await wait(`document.querySelector('.vue-flow__node[data-id="code"]')?.textContent.includes('已编辑')`)
  check('server draft reload reflects edited node', true)
  await client.tool('take_screenshot', { filePath: `${output}/desktop-workflow.png`, fullPage: true })
  await click('保存并打开编辑器')
  await wait(`location.pathname.includes('/workflows/') && !location.pathname.includes('nl-create')`)
  const savedSession = await api(`/nl-workflow/sessions/${fixture.sessionId}/`)
  const savedWorkflow = await api(`/workflows/${savedSession.data.workflow_id}/`)
  check('saved workflow opens editor and keeps edited configuration', savedWorkflow.data.nodes.some(node=>node.name==='整理输入（已编辑）' && node.config.verificationValue==='真实保存'))
  } else {
    await evaluate(`async () => { const r=await fetch('/api/v1/nl-workflow/sessions/${fixture.sessionId}/', {method:'PATCH',headers:{Authorization:'Bearer '+localStorage.getItem('access_token'),'Content-Type':'application/json'},body:JSON.stringify({name:'NL-QA-20261017 主流程'})}); if(!r.ok) throw new Error('QA fixture refresh failed'); }`)
    await go()
    await click('历史对话')
    await fill('搜索对话', 'NL-QA-20261017 主流程')
    await wait(`document.querySelector('.session-name')?.textContent.includes('主流程')`)
    await evaluate(`() => document.querySelector('.session-item').click()`)
    await wait(`document.querySelectorAll('.vue-flow__node').length===3`)
    check('existing backend workflow restores with exact node config', await evaluate(`() => document.querySelectorAll('.message-user').length===1`))
    await evaluate(`() => document.querySelector('.vue-flow__node[data-id="code"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`)
    await wait(`document.querySelector('#node-config-json')`)
    check('node form preserves arbitrary key casing', await evaluate(`() => document.querySelector('#node-config-json').value.includes('customCamelKey') && document.querySelector('#node-config-json').value.includes('Keep_CASE')`))
    await fill('节点参数 JSON', '{invalid')
    await click('保存')
    await wait(`document.querySelector('.config-error')?.textContent.includes('JSON')`)
    check('invalid node config is rejected before network mutation', true)
    await fill('节点参数 JSON', '{"language":"python","code":"result = 1","shouldNotPersist":true}')
    await click('保存')
    await wait(`document.querySelector('.config-error')?.textContent.includes('更新或重启服务')`)
    const unchanged = await api(`/nl-workflow/sessions/${fixture.sessionId}/`)
    check('old backend is detected before attempting draft mutation', !unchanged.data.workflow_json.nodes[1].config.shouldNotPersist)
    await click('取消')
    await client.tool('take_screenshot', { filePath: `${output}/desktop-workflow.png`, fullPage: true })
  }
  await go()
  for (const theme of ['light', 'dark', 'pure-bw', 'high-contrast']) {
    await evaluate(`() => { localStorage.setItem('theme',${JSON.stringify(theme)}); }`)
    await go()
    check(`${theme} theme has no horizontal overflow`, await evaluate(`() => document.documentElement.scrollWidth <= innerWidth`))
    await client.tool('take_screenshot', { filePath: `${output}/theme-${theme}.png`, fullPage: true })
  }
  await client.tool('emulate', { viewport: '390x844x1,mobile,touch', prefersReducedMotion: 'reduce' })
  await evaluate(`() => localStorage.setItem('theme','light')`)
  await go()
  check('390px mobile has no horizontal overflow', await evaluate(`() => document.documentElement.scrollWidth <= innerWidth`), await evaluate(`() => ({width:innerWidth,scroll:document.documentElement.scrollWidth})`))
  await client.tool('take_screenshot', { filePath: `${output}/mobile.png`, fullPage: true })
  console.log(resultText(await client.tool('list_console_messages', { types: ['error', 'warn'] })))
} catch (error) {
  console.error(error.stack)
  writeFileSync(`${output}/failure-snapshot.txt`, resultText(await client.tool('take_snapshot').catch(()=>({}))))
  await client.tool('take_screenshot', { filePath: `${output}/failure.png`, fullPage: true }).catch(()=>{})
  process.exitCode = 1
} finally { client.close() }

