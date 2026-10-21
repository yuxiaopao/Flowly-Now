import { writeFileSync } from 'node:fs'
import { McpClient, evalPage, resultText } from './chrome_mcp_client.mjs'

const client = new McpClient()
const checks = []
let workflowId
const report = 'E:/Flowly-now/Docs/verification/personal-center-20261015/editor-results.json'
const evaluate = fn => evalPage(client, fn, 45000)
function check(name, pass, detail) {
  checks.push({ name, pass: Boolean(pass), ...(detail ? { detail } : {}) })
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}`)
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`)
}
async function wait(expression, timeout=15000) {
  return evaluate(`async () => {const end=Date.now()+${timeout};while(Date.now()<end){if(${expression})return true;await new Promise(r=>setTimeout(r,100))}throw new Error('Condition timed out')}`)
}
async function uid(role, text) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(line => line.includes(`${role} "${text}"`))
  if (!line) throw new Error(`Missing ${role} ${text}`)
  return line.match(/uid=(\S+)/)[1]
}
async function go(path, text) {
  await client.tool('navigate_page', { url: `http://localhost:5200${path}` })
  await client.tool('wait_for', { text: [text] })
}
async function api(path, method='GET', data) {
  return evaluate(`async () => {const r=await fetch('/api/v1${path}',{method:${JSON.stringify(method)},headers:{'Content-Type':'application/json',Authorization:'Bearer '+localStorage.getItem('access_token')},${data ? `body:JSON.stringify(${JSON.stringify(data)}),` : ''}});const p=await r.json();return {status:r.status,data:p.data||p}}`)
}
async function setEditorPreferences(value) {
  await go('/settings/preferences', '工作流编辑器')
  for (const key of ['autoSave','snapToGrid','showMinimap']) await evaluate(`() => {const input=document.getElementById('preference-control-${key}');if(input.checked!==${value})document.querySelector('label[for="'+input.id+'"]').click()}`)
  if (await evaluate(`() => ![...document.querySelectorAll('button')].find(button=>button.textContent.trim()==='保存设置').disabled`)) {
    await client.tool('click', { uid: await uid('button','保存设置') })
  }
}
async function nameWorkflow(name) {
  await client.tool('fill', { uid: await uid('textbox','工作流名称'), value:name })
  await evaluate(`() => document.querySelector('.workflow-name-input').blur()`)
}

try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool=>tool.name))
  const pages = resultText(await client.tool('list_pages'))
  const match = [...pages.matchAll(/^(\d+):.*http:\/\/localhost:5200\/(?:settings|workflows)\/.*isolatedContext=isolated-context-\d+/gm)].at(-1)
  if (!match) throw new Error('Missing isolated QA page')
  client.pageId=Number(match[1])
  await client.tool('select_page',{pageId:client.pageId})
  await client.tool('emulate',{viewport:'1440x1000x1'})

  // Verify the page handles a real network failure without clearing the draft.
  await go('/settings/profile','账户资料')
  await evaluate(`() => {const input=document.querySelector('input[autocomplete="given-name"]');input.value='离线保留-'+Date.now();input.dispatchEvent(new Event('input',{bubbles:true}))}`)
  await client.tool('emulate',{viewport:'1440x1000x1',networkConditions:'Offline'})
  await client.tool('click',{uid:await uid('button','保存更改')})
  await wait(`document.querySelector('.profile-section .inline-error')`)
  check('offline save preserves draft and exposes retry',await evaluate(`() => document.querySelector('input[autocomplete="given-name"]').value.startsWith('离线保留-') && ![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='保存更改').disabled`))
  await client.tool('emulate',{viewport:'1440x1000x1'})
  await evaluate(`() => {performance.clearResourceTimings();const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='保存更改');for(let i=0;i<10;i++)button.click()}`)
  await wait(`document.body.innerText.includes('个人资料已更新')`)
  check('ten save clicks send one update',await evaluate(`() => performance.getEntriesByType('resource').filter(entry=>new URL(entry.name).pathname==='/api/v1/auth/user/').length===1`))

  await setEditorPreferences(false)
  const created = await api('/workflows/','POST',{
    name:'Personal center QA',
    nodes:[{id:'qa-start',node_type:'start',name:'开始',position_x:0,position_y:0,config:{}},{id:'qa-end',node_type:'end',name:'结束',position_x:300,position_y:0,config:{}}],
    edges:[{source_node:'qa-start',target_node:'qa-end'}],
  })
  check('temporary workflow created',created.status===201,created.status)
  workflowId=created.data.id
  await go(`/workflows/${workflowId}/edit`,'工作流')
  await wait(`document.querySelectorAll('.vue-flow__node').length===2`)
  check('grid preference reaches Vue Flow',await evaluate(`() => {let c=document.querySelector('.vue-flow').__vueParentComponent;while(c&&c.type?.name!=='VueFlow')c=c.parent;return c?.props.snapToGrid===false}`))
  await client.tool('click',{uid:await uid('button','放大画布')})
  check('disabled minimap stays hidden on zoom',await evaluate(`() => getComputedStyle(document.querySelector('.editor-minimap')).display==='none'`))
  await nameWorkflow('Disabled autosave draft')
  await evaluate(`async () => {await new Promise(r=>setTimeout(r,32000));return true}`)
  check('disabled autosave keeps draft local',(await api(`/workflows/${workflowId}/`)).data.name==='Personal center QA')
  await client.tool('click',{uid:await uid('button','保存工作流')})
  await wait(`!document.querySelector('.unsaved-indicator')`)
  check('manual save works with autosave disabled',(await api(`/workflows/${workflowId}/`)).data.name==='Disabled autosave draft')

  await setEditorPreferences(true)
  await go(`/workflows/${workflowId}/edit`,'工作流')
  await wait(`document.querySelectorAll('.vue-flow__node').length===2`)
  check('enabled grid preference reaches Vue Flow',await evaluate(`() => {let c=document.querySelector('.vue-flow').__vueParentComponent;while(c&&c.type?.name!=='VueFlow')c=c.parent;return c?.props.snapToGrid===true}`))
  check('enabled minimap appears while zooming',await evaluate(`async () => {document.querySelector('button[aria-label="放大画布"]').click();await new Promise(r=>setTimeout(r,200));return getComputedStyle(document.querySelector('.editor-minimap')).display!=='none'}`))
  await nameWorkflow('Enabled autosave saved')
  await evaluate(`async () => {await new Promise(r=>setTimeout(r,32000));return true}`)
  check('enabled autosave persists draft',(await api(`/workflows/${workflowId}/`)).data.name==='Enabled autosave saved')
  check('autosave clears saved draft indicator',await evaluate(`() => !document.querySelector('.unsaved-indicator')`))
  await go('/settings/profile','账户资料')
} catch(error) {
  checks.push({name:'audit error',pass:false,detail:error.message})
  console.error(error.stack)
  process.exitCode=1
} finally {
  try { await client.tool('emulate',{viewport:'1440x1000x1'}) } catch { /* Preserve the original failure if the page closed. */ }
  if(workflowId) {
    try { await api(`/workflows/${workflowId}/`,'DELETE') } catch { /* A 204 response has no JSON body. */ }
  }
  writeFileSync(report,JSON.stringify({checks,passed:checks.filter(c=>c.pass).length,failed:checks.filter(c=>!c.pass).length},null,2))
  client.close()
}
