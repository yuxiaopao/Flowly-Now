import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { McpClient, evalPage, login, resultText, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'

const client = new McpClient()
const contextName = `flowly-codegraph-${process.pid}`
const callTool = client.tool.bind(client)
client.tool = async (name, args = {}, timeout = 45000) => {
  if (name !== 'new_page') return callTool(name, args, timeout)
  const result = await client.request('tools/call', { name, arguments: { ...args, isolatedContext: contextName } }, timeout)
  if (result.isError) throw new Error(resultText(result))
  const listing = resultText(await client.request('tools/call', { name: 'list_pages', arguments: {} }))
  const page = listing.split('\n').findLast(line => /^\d+:/.test(line) && line.includes(contextName))
  if (!page) throw new Error(`Isolated test page missing: ${listing}`)
  client.pageId = Number(page.match(/^(\d+):/)[1])
  return result
}
const output = fileURLToPath(new URL('../Docs/verification/codegraph-20261015/', import.meta.url))
const results = []
const mode = process.argv[2] || 'test'
const storeExpr = `document.querySelector('#app').__vue_app__.config.globalProperties.$pinia._s.get('codegraph')`
async function evaluate(body) { return evalPage(client, `async () => { ${body} }`, 45000) }
async function waitFor(body, timeout = 45000) {
  const end = Date.now() + timeout
  while (Date.now() < end) {
    const value = await evaluate(body)
    if (value) return value
    await delay(250)
  }
  throw new Error(`Condition timed out: ${body}`)
}
async function snapshot() { return resultText(await client.tool('take_snapshot', {})) }
async function uid(role, label) {
  let text = ''
  for (let attempt = 0; attempt < 12; attempt++) {
    text = await snapshot()
    const line = text.split('\n').find(line => line.includes(`${role} "${label}"`))
    if (line) return line.match(/uid=([^\s]+)/)[1]
    await delay(150)
  }
  throw new Error(`Cannot find ${role} ${label}: ${text.slice(-7000)}`)
}
async function click(role, label) {
  if (role === 'option') {
    // Chrome's compact accessibility snapshot omits ElSelect options; select the visible role=option through DevTools.
    const value = await evaluate(`const option=[...document.querySelectorAll('[role="listbox"]')].filter(el=>el.getClientRects().length).flatMap(el=>[...el.querySelectorAll('[role="option"]')]).find(el=>el.textContent.trim()===${JSON.stringify(label)}); if(!option) return false; option.scrollIntoView({block:'nearest'}); option.click(); return true`)
    assert(value, `Visible option unavailable: ${label}`)
    return
  }
  await client.tool('click', { uid: await uid(role, label) })
}
async function fill(label, value) { await client.tool('fill', { uid: await uid('textbox', label), value }) }
async function step(name, action) {
  const started = Date.now()
  try { const detail = await action(); results.push({ name, passed: true, ms: Date.now() - started, detail }); console.log(`PASS ${name} ${JSON.stringify(detail ?? '')}`) }
  catch (error) { results.push({ name, passed: false, error: error.message }); throw error }
}
async function screenshot(name) { await client.tool('take_screenshot', { filePath: path.join(output, `${name}.png`) }) }
async function ready() { return waitFor(`const s = ${storeExpr}; return s && !s.loading && !s.analyzing && s.nodes.length && !document.querySelector('.loading-overlay') && {files: s.allFiles.length, edges: s.edges.length, project: s.currentProject.id}`) }
async function captureApi() {
  await evaluate(`const source=await (await fetch('/src/api/codegraph.js')).text(); const url=source.match(/import api from "([^"]+)"/)[1]; window.__cgApi=(await import(url)).default; return true`)
}
async function afterEmulation() {
  await client.tool('wait_for',{text:['三维星云'],timeout:30000})
  await ready()
  await captureApi()
}
async function verifyRefresh() {
  await evaluate(`
    const api=window.__cgApi; const {default:axios}=await import('/node_modules/.vite/deps/axios.js');
    window.__cgAdapter=api.defaults.adapter; const adapter=axios.getAdapter(api.defaults.adapter); window.__cgCalls=[];
    api.defaults.adapter=async config=>{if(config.url.includes('/codegraph/')) window.__cgCalls.push({url:config.url,method:config.method});return adapter(config)};
    window.__cgSuccessSeen=false;
    window.__cgToastObserver=new MutationObserver(()=>{if(document.body.innerText.includes('代码图谱已更新'))window.__cgSuccessSeen=true});
    window.__cgToastObserver.observe(document.body,{childList:true,subtree:true,characterData:true});
    return true;
  `)
  try {
    await click('button','重新分析')
    await ready()
    const detail=await evaluate(`return {calls:window.__cgCalls,successFeedback:window.__cgSuccessSeen}`)
    assert.equal(detail.calls.filter(call=>call.url.endsWith('/analyze/')).length,1)
    assert.equal(detail.calls.filter(call=>call.url.endsWith('/graph/')).length,0)
    assert(detail.successFeedback,JSON.stringify(detail))
    return detail
  } finally {
    await evaluate(`window.__cgApi.defaults.adapter=window.__cgAdapter; window.__cgToastObserver.disconnect(); return true`)
  }
}

try {
  await fs.mkdir(output, { recursive: true })
  await client.initialize()
  const { tools } = await client.request('tools/list')
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  assert(tools.some(tool => tool.name === 'navigate_page'))
  await login(client)
  await client.tool('emulate', { viewport: '1600x1000x1' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/codegraph?project=1` })
  await client.tool('wait_for', { text: ['三维星云'], timeout: 30000 })
  if (mode === 'schemas') {
    console.log(JSON.stringify(tools.filter(tool => ['click', 'fill', 'wait_for', 'emulate', 'press_key'].includes(tool.name)), null, 2))
  } else if (mode === 'refresh') {
    const previous=JSON.parse(await fs.readFile(path.join(output,'browser-results.json'),'utf8'))
    results.push(...previous.results.filter(result=>result.passed))
    await ready()
    await captureApi()
    await step('重新分析一次请求并刷新结果',verifyRefresh)
    await screenshot('desktop-final-3d')
    console.log(resultText(await client.tool('list_console_messages',{types:['error'],pageSize:30})))
  } else if (mode === 'inspect') {
    await ready()
    console.log(await snapshot())
    console.log(await evaluate(`return {shell:document.querySelector('.codegraph-shell').getBoundingClientRect().toJSON(),canvas:document.querySelector('.chart-container').getBoundingClientRect().toJSON(),height:innerHeight}`))
    await screenshot('inspection')
  } else if (mode === 'inspect-select') {
    await ready()
    await click('combobox', '按模块筛选')
    console.log(await evaluate(`return [...document.querySelectorAll('.el-select-dropdown')].map(el=>({html:el.outerHTML.slice(0,5000),visible:!!el.getClientRects().length}))`))
    console.log(await snapshot())
  } else {
    await step('真实项目加载、WebGL 渲染与画布高度', async () => {
      const data = await ready()
      await captureApi()
      assert(data.files > 0)
      const metrics = await evaluate(`const r = document.querySelector('.codegraph-shell').getBoundingClientRect(); return { bottom:r.bottom, height:innerHeight, webgl:!!document.querySelector('.graph-3d-host canvas') }`)
      assert(metrics.webgl)
      assert(metrics.bottom <= metrics.height + 1, JSON.stringify(metrics))
      await screenshot('desktop-3d')
      return { ...data, ...metrics }
    })
    for (const layout of ['力导向', '树形', '层次']) {
      await step(`${layout}布局及完整文件节点`, async () => {
        await click('radio', layout)
        return waitFor(`const s = ${storeExpr}; return document.querySelectorAll('.node-group').length === s.allFiles.length && { nodes: s.allFiles.length, paths: document.querySelectorAll('.edge-path').length }`)
      })
    }
    await step('全量连线开关', async () => {
      await click('StaticText', '全部连线')
      const detail = await waitFor(`const s = ${storeExpr}; const ids = new Set(s.allFiles.map(n=>n.id)); const count=s.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).length; return document.querySelectorAll('.edge-path').length===count && {drawn:count}`)
      await click('StaticText', '全部连线')
      return detail
    })
    await step('连续搜索、结果选择、二维定位和依赖明细', async () => {
      await fill('搜索图谱文件', 'does-not-exist-flowly-graph')
      await client.tool('wait_for', { text: ['未找到匹配的文件'], timeout: 15000 })
      await fill('搜索图谱文件', 'stores/codeGraph')
      await fill('搜索图谱文件', 'codeGraph')
      await waitFor(`return document.querySelectorAll('.result-item').length > 0`)
      const detail = await evaluate(`const s=${storeExpr}; return {query:s.searchQuery,paths:s.searchResults.map(n=>n.path)}`)
      assert.equal(detail.query, 'codeGraph')
      const resultUid = (await snapshot()).split('\n').find(line=>line.includes('button "codeGraph.js') && line.includes('stores'))?.match(/uid=([^\s]+)/)?.[1]
      assert(resultUid)
      await client.tool('click', { uid: resultUid })
      await waitFor(`const s=${storeExpr}; return s.selectedNode?.name==='codeGraph.js' && !!document.querySelector('.node-group.selected')`)
      await waitFor(`return [...document.querySelectorAll('.section-title')].some(el=>el.textContent.includes('导入 ('))`)
      const selected = await evaluate(`const s=${storeExpr}; return {path:s.selectedNode.path, dependencies:[...s.relationships.relationships.get(s.selectedNode.id).imports].length, transform:document.querySelector('.main-group').getAttribute('transform')}`)
      assert(selected.dependencies > 0)
      await screenshot('desktop-detail')
      return selected
    })
    await step('源码预览与关闭', async () => {
      await click('button', '查看源码')
      await waitFor(`return [...document.querySelectorAll('.code-line')].some(el=>el.textContent.includes('defineStore'))`)
      const lines = await evaluate(`return document.querySelectorAll('.code-line').length`)
      await screenshot('source-preview')
      const dialogSnapshot = await snapshot()
      const close = dialogSnapshot.split('\n').find(line=>line.includes('button "Close this dialog"')) || dialogSnapshot.split('\n').find(line=>line.includes('button "关闭此对话框"'))
      if (close) await client.tool('click', { uid: close.match(/uid=([^\s]+)/)[1] })
      else await client.tool('press_key', { key: 'Escape' })
      return {lines}
    })
    await step('模块及类型筛选、清除筛选', async () => {
      await click('combobox', '按模块筛选')
      await click('option', 'stores')
      await waitFor(`const s=${storeExpr}; return s.filters.module==='stores' && s.filteredNodes.length<s.nodes.length && document.querySelectorAll('.node-group').length===s.filteredNodes.filter(n=>n.type!=='function').length`)
      await click('combobox', '按文件类型筛选')
      await click('option', '.vue')
      await waitFor(`const s=${storeExpr}; return s.filteredNodes.length===0 && !document.querySelector('.node-group')`)
      await click('button', '清除筛选')
      return ready()
    })
    await step('同规模数据替换立即更新画布', async () => {
      const detail=await evaluate(`const s=${storeExpr}; const original=s.nodes; const id=original[0].id; s.nodes=original.map((n,i)=>i===0?{...n,name:'same-size-refresh-check.js'}:n); await new Promise(r=>setTimeout(r,500)); const label=[...document.querySelectorAll('.node-group')].find(el=>el.getAttribute('data-id')===id)?.__data__?.name; s.nodes=original; return {label}`)
      assert.equal(detail.label, 'same-size-refresh-check.js')
      return detail
    })
    await step('搜索旧响应、清空搜索和错误后恢复', async () => {
      const detail = await evaluate(`
        const api=window.__cgApi; const s=${storeExpr};
        const original=api.defaults.adapter; const response=(config,data)=>({data,status:200,statusText:'OK',headers:{},config});
        api.defaults.adapter=async config=>{
          if(!config.url.endsWith('/search/')) return (await import('/node_modules/.vite/deps/axios.js')).default.getAdapter(original)(config);
          await new Promise(resolve=>setTimeout(resolve,config.params.q==='old'?220:20));
          return response(config,{results:[{id:config.params.q,name:config.params.q,path:config.params.q}]});
        };
        try {
          const old=s.search('old'); await new Promise(resolve=>setTimeout(resolve,10)); await s.search('new'); await old;
          const latest=s.searchResults[0]?.id; const searchError=s.searchError; const currentQuery=s.searchQuery;
          const pending=s.search('old'); s.clearSearch(); await pending;
          return {latest,searchError,currentQuery,cleared:s.searchResults.length,loading:s.searchLoading};
        } finally {api.defaults.adapter=original; s.clearSearch()}
      `)
      assert.equal(detail.latest,'new',JSON.stringify(detail))
      assert.equal(detail.cleared,0)
      assert.equal(detail.loading,false)
      return detail
    })
    await step('项目快速切换不会串入旧图或重建已断开的连接', async () => {
      const detail = await evaluate(`
        const api=window.__cgApi; const {default:axios}=await import('/node_modules/.vite/deps/axios.js');
        const s=${storeExpr}; const original=api.defaults.adapter; const adapter=axios.getAdapter(original); const NativeSocket=window.WebSocket; let sockets=0;
        window.WebSocket=class extends NativeSocket {constructor(...args){super(...args);sockets++}};
        api.defaults.adapter=async config=>{
          if(!/\\/codegraph\\/projects\\/[12]\\/graph\\/$/.test(config.url)) return adapter(config);
          const project=config.url.includes('/projects/1/')?1:2;
          await new Promise(resolve=>setTimeout(resolve,project===1?220:20));
          return {data:{nodes:[{id:'fixture-'+project,name:'fixture.js',type:'js',module:'root'}],edges:[],stats:{},cycles:[],hotspots:[]},status:200,statusText:'OK',headers:{},config};
        };
        let detail;
        try {
          const first=s.selectProject(1); await new Promise(resolve=>setTimeout(resolve,10)); await s.selectProject(2); await first;
          detail={project:s.currentProject.id,node:s.nodes[0]?.id};
          s.disconnectWebSocket(); const before=sockets; await new Promise(resolve=>setTimeout(resolve,5500)); detail.reopened=sockets-before;
        } finally {api.defaults.adapter=original;window.WebSocket=NativeSocket;await s.selectProject(1)}
        return detail;
      `)
      assert.equal(detail.project,2)
      assert.equal(detail.node,'fixture-2')
      assert.equal(detail.reopened,0)
      await ready()
      return detail
    })
    await step('取图错误可见且重试后恢复', async () => {
      const detail = await evaluate(`
        const api=window.__cgApi; const s=${storeExpr}; const original=api.defaults.adapter;
        api.defaults.adapter=async config=>{const error=new Error('CodeGraph regression: retry');error.config=config;error.response={status:503,data:{error:error.message},config};throw error};
        try {await s.fetchGraphData(1); await new Promise(resolve=>setTimeout(resolve,30)); return {error:s.error,visible:document.querySelector('.el-alert')?.innerText.includes('CodeGraph regression: retry')}}
        finally {api.defaults.adapter=original}
      `)
      assert(detail.visible)
      await click('button','重试')
      await ready()
      assert.equal(await evaluate(`return ${storeExpr}.error`),null)
      return detail
    })
    await step('手机文件入口、选中详情与源码入口', async () => {
      await client.tool('emulate', {viewport:'390x844x1,mobile,touch'})
      await afterEmulation()
      await click('button', '文件与筛选')
      await fill('搜索图谱文件', 'codeGraph')
      await waitFor(`return document.querySelectorAll('.result-item').length>0`)
      const line=(await snapshot()).split('\n').find(line=>line.includes('button "codeGraph.js') && line.includes('stores'))
      assert(line)
      await client.tool('click',{uid:line.match(/uid=([^\s]+)/)[1]})
      const detail=await evaluate(`return {details:getComputedStyle(document.querySelector('.detail-sidebar')).display, bodyWidth:document.documentElement.scrollWidth,viewport:innerWidth,shellBottom:document.querySelector('.codegraph-shell').getBoundingClientRect().bottom,height:innerHeight}`)
      assert.notEqual(detail.details,'none')
      assert(detail.bodyWidth<=detail.viewport+1)
      assert(detail.shellBottom<=detail.height+1)
      await screenshot('mobile-detail')
      await click('button','关闭项目洞察')
      await screenshot('mobile-graph')
      return detail
    })
    await client.tool('emulate', {viewport:'1600x1000x1'})
    await afterEmulation()
    await step('重新分析一次请求并刷新结果',verifyRefresh)
    await screenshot('desktop-final')
    if (await evaluate(`return Boolean(${storeExpr}.selectedNode)`)) await click('button','关闭文件详情')
    await click('radio','三维星云')
    await waitFor(`return !!document.querySelector('.graph-3d-host canvas') && !document.querySelector('.loading-overlay')`)
    await delay(1600)
    await screenshot('desktop-final-3d')
    console.log(resultText(await client.tool('list_console_messages',{types:['error'],pageSize:30})))
  }
} catch (error) {
  console.error(error.stack)
  await screenshot('failure').catch(()=>{})
  process.exitCode=1
} finally {
  await fs.writeFile(path.join(output,'browser-results.json'),JSON.stringify({results},null,2))
  if (client.pageId != null) await client.tool('close_page',{pageId:client.pageId}).catch(()=>{})
  client.close()
}
