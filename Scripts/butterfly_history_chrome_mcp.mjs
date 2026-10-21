import fs from 'node:fs/promises'
import { McpClient, evalPage, login, delay, resultText, FRONTEND_URL, BACKEND_URL } from './chrome_mcp_client.mjs'
const reportDirectory = new URL('../test-reports/butterfly-30s/', import.meta.url)
const isEffects = process.argv.includes('--effect-images')
const outputDirectory = new URL(isEffects ? '../output/butterfly-video/embroidery/' : '../output/butterfly-video/combination/', import.meta.url)
const phase = isEffects ? 'effects' : process.argv.includes('--final') ? 'final' : 'running'
const executionId = (await fs.readFile(new URL('execution-id.txt', outputDirectory), 'utf8')).trim()
const client = new McpClient()
const report = { provider: 'chrome-devtools-mcp', phase, executionId, checks: [] }
function check(name, condition, details) {
  report.checks.push({ name, passed: Boolean(condition), details })
  if (!condition) throw new Error(`${name}: ${JSON.stringify(details)}`)
}
async function waitFor(fn, predicate) {
  let value
  for (let attempt = 0; attempt < 20; attempt++) {
    value = await evalPage(client, fn)
    if (predicate(value)) return value
    await delay(750)
  }
  throw new Error(`Page did not become ready: ${JSON.stringify(value)}`)
}
try {
  await client.initialize()
  const tools = await client.request('tools/list')
  client.pageTools = new Set(tools.tools.filter(tool=>tool.inputSchema.required?.includes('pageId')).map(tool=>tool.name))
  await fs.writeFile(new URL('chrome-tool-schemas.json', reportDirectory), JSON.stringify(tools.tools, null, 2))
  check('navigate_page available', tools.tools.some(tool => tool.name === 'navigate_page'))
  const version = await (await fetch('http://127.0.0.1:9222/json/version')).json()
  check('browser debugging endpoint', version.webSocketDebuggerUrl.includes('/devtools/browser/'))
  report.login = await login(client)
  const records = await evalPage(client, `async () => {
    const response = await fetch('${BACKEND_URL}/api/v1/workflows/executions/?workflow=65df2ae5-3d69-4f06-a645-3272a198aa6a', {headers: {Authorization: 'Bearer ' + localStorage.getItem('access_token')}})
    const payload = await response.json(); const data = payload.data || payload;
    return {status:response.status, records:(data.results || data).map(row => ({id:row.id,status:row.status,source:row.trigger_source,images:row.output_data?.images?.length || 0,video:row.output_data?.video_url || null,partial:row.artifact_outputs?.length || 0}))};
  }`)
  check('history API owner access', records.status === 200, records)
  check('both archived films visible', records.records.filter(row => row.source?.method === 'archive' && row.status === 'completed' && row.images >= 2).length === 2, records)
  check('cloud failure preserved with artifacts', records.records.some(row => row.status === 'failed' && row.partial > 0), records)
  await client.tool('navigate_page', {type:'url',url:FRONTEND_URL + '/executions',timeout:30000})
  const history = await waitFor(`() => ({text:document.body.innerText, rows:[...document.querySelectorAll('.el-table__row')].map(row=>row.innerText)})`, value => value.rows.some(row => row.includes(executionId)))
  const statistics = await waitFor(`() => ({values:[...document.querySelectorAll('.stat-value')].map(element=>element.innerText)})`, value=>Number(value.values[0])>0)
  check('history statistics show actual totals', Number(statistics.values[0])>0 && Number(statistics.values[1])>0,statistics)
  check('history list shows current and archive labels', history.text.includes('本地成片') && history.text.includes('历史成片归档'), {rows:history.rows.filter(row=>row.includes('蝶羽'))})
  if (isEffects) check('image generation source label', history.text.includes('效果图生成'))
  await client.tool('take_screenshot', {filePath:new URL('history-' + phase + '.png', reportDirectory).pathname.replace(/^\//,'') ,fullPage:true})
  const clicked = await evalPage(client, `() => {const row=[...document.querySelectorAll('.el-table__row')].find(row=>row.innerText.includes('${executionId}')); const button=[...row.querySelectorAll('button')].find(button=>button.innerText.trim()==='详情'); button.click();return true}`)
  check('history detail button click', clicked)
  const detail = await waitFor(`() => ({url:location.href,text:document.body.innerText,videos:[...document.querySelectorAll('video')].map(video=>({src:video.currentSrc||video.src,duration:video.duration,error:video.error?.message||null})),images:document.querySelectorAll('.artifact-image').length,artifacts:document.querySelectorAll('.artifact-card').length,graph:document.querySelectorAll('.execution-workflow-graph').length})`, value => value.text.includes('独立媒体任务') && (phase !== 'final' || value.videos.length > 0))
  check('detail route opens selected record', detail.url.includes(executionId), detail)
  check('media source explanation visible', detail.text.includes('独立媒体任务'), detail)
  check('media job offers no native retry', !detail.text.split('\n').some(line=>line.trim()==='重试'), detail)
  if (isEffects) {
    const images = await waitFor(`() => ({count:document.querySelectorAll('.artifact-image').length,loaded:[...document.querySelectorAll('.artifact-image')].filter(image=>image.complete&&image.naturalWidth>0).length})`,value=>value.loaded===2)
    check('both effect images load without fake document previews', images.count===2 && images.loaded===2,images)
    const documents = await evalPage(client, `() => ({files:[...document.querySelectorAll('.grid-file .artifact-card')].length})`)
    check('prompts and provenance files classified correctly',documents.files===3,documents)
  }
  if (phase === 'final') {
    check('all generated media shown', detail.videos.length >= 1 && detail.images >= 3, detail)
    const visible = await evalPage(client, `() => { const video=document.querySelector('video');const box=video.getBoundingClientRect();let clipped=false;for(let parent=video.parentElement;parent;parent=parent.parentElement){const style=getComputedStyle(parent);if(/auto|scroll|hidden/.test(style.overflowY)){const bounds=parent.getBoundingClientRect();if(box.top>=bounds.bottom||box.bottom<=bounds.top)clipped=true}}return {top:box.top,bottom:box.bottom,height:box.height,clipped,viewport:innerHeight}; }`)
    check('video visible on first screen', visible.height>0 && visible.top<visible.viewport && !visible.clipped,visible)
    await delay(2000)
    await evalPage(client, `() => { const video=document.querySelector('video');video.scrollIntoView({block:'center'});video.preload='auto';video.load();return {src:video.src,connected:video.isConnected}; }`)
    await waitFor(`() => {const video=document.querySelector('video');return {duration:video?.duration,readyState:video?.readyState,src:video?.src,error:video?.error?.message||null}}`,value=>value.readyState>=3 && value.duration===30)
    const media = await evalPage(client, `async () => {
      const video=document.querySelector('video');video.muted=true; const playResult=await Promise.race([video.play().then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),6000))]); const start=video.currentTime;await new Promise(resolve=>setTimeout(resolve,1200)); const advanced=video.currentTime>start; video.pause();
      for(let i=0;i<40 && video.readyState<4;i++) await new Promise(resolve=>setTimeout(resolve,250));
      const before={readyState:video.readyState,buffered:video.buffered.length?video.buffered.end(video.buffered.length-1):0};
      video.currentTime=29.5;for(let i=0;i<40 && (video.seeking||video.currentTime<29.4);i++) await new Promise(resolve=>setTimeout(resolve,250));
      return {duration:video.duration,width:video.videoWidth,height:video.videoHeight,playResult,advanced,currentTime:video.currentTime,before,seeking:video.seeking,connected:video.isConnected,error:video.error?.message||null};
    }`)
    check('30 second video plays and seeks', media.duration === 30 && media.width === 1280 && media.height === 720 && media.advanced && media.currentTime >= 29.4 && !media.error, media)
    const failedId = records.records.find(row => row.status === 'failed' && row.partial > 0).id
    await client.tool('navigate_page', {type:'url',url:FRONTEND_URL + '/executions/' + failedId,timeout:30000})
    const failed = await waitFor(`() => ({text:document.body.innerText,images:[...document.querySelectorAll('.artifact-image')].filter(image=>image.complete&&image.naturalWidth>0).length})`, value => value.images >= 3)
    check('failed run still shows intermediate images', failed.images >= 3, failed)
    await client.tool('take_screenshot', {filePath:new URL('failed-detail.png', reportDirectory).pathname.replace(/^\//,''),fullPage:true})
    await client.tool('navigate_page', {type:'url',url:FRONTEND_URL + '/executions/' + executionId,timeout:30000})
    await waitFor(`() => ({videos:document.querySelectorAll('video').length})`, value=>value.videos>0)
  }
  await client.tool('take_screenshot', {filePath:new URL('detail-' + phase + '.png', reportDirectory).pathname.replace(/^\//,''),fullPage:true})
  if (phase === 'final') {
    await client.tool('emulate', {viewport:'390x844x1,mobile,touch'})
    await delay(1000)
    const mobile = await evalPage(client, `() => {const video=document.querySelector('video');const box=video.getBoundingClientRect();return {left:box.left,right:box.right,width:box.width,viewport:innerWidth,document:document.documentElement.scrollWidth};}`)
    check('video fits narrow viewport', mobile.width>0 && mobile.left>=0 && mobile.right<=mobile.viewport,mobile)
    await client.tool('take_screenshot', {filePath:new URL('detail-mobile.png',reportDirectory).pathname.replace(/^\//,''),fullPage:false})
    await client.tool('emulate', {viewport:'1440x932x1'})
  }
  report.status = 'passed'
} catch (error) {
  report.status = 'failed'
  report.error = error.message
  process.exitCode = 1
} finally {
  await fs.writeFile(new URL('chrome-' + phase + '.json',reportDirectory),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
  client.close()
}

