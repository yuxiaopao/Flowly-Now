import fs from 'node:fs/promises'
import { McpClient, evalPage, login, delay, FRONTEND_URL, BACKEND_URL } from './chrome_mcp_client.mjs'

const output = new URL('../output/butterfly-video/flowly_modular_60/', import.meta.url)
const workflowId = (await fs.readFile(new URL('workflow-id.txt', output), 'utf8')).trim()
const executionId = (await fs.readFile(new URL('execution-id.txt', output), 'utf8')).trim()
const canvasOnly = process.argv.includes('--canvas-only')
const client = new McpClient()
const report = { provider: 'chrome-devtools-mcp', workflowId, executionId, checks: [] }
function check(name, passed, details) {
  report.checks.push({ name, passed: Boolean(passed), details })
  if (!passed) throw new Error(`${name}: ${JSON.stringify(details)}`)
}
async function waitFor(script, predicate) {
  let result
  for (let i = 0; i < 40; i++) {
    result = await evalPage(client, script)
    if (predicate(result)) return result
    await delay(500)
  }
  throw new Error(`UI did not become ready: ${JSON.stringify(result)}`)
}
try {
  const debug = await (await fetch('http://127.0.0.1:9222/json/version')).json()
  check('Independent Chrome browser endpoint', debug.webSocketDebuggerUrl.includes('/devtools/browser/'))
  await client.initialize()
  const schema = await client.request('tools/list')
  client.pageTools = new Set(schema.tools.filter(t => t.inputSchema.required?.includes('pageId')).map(t => t.name))
  check('navigate_page is available', schema.tools.some(t => t.name === 'navigate_page'))
  await login(client)
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/workflows/${workflowId}/edit`, timeout: 30000 })
  const canvas = await waitFor(`() => ({url:location.href,count:document.querySelectorAll('.vue-flow__node').length,text:document.body.innerText.slice(0,6000),names:[...document.querySelectorAll('.node-name-input')].map(n=>n.value)})`, value => value.count >= 18)
  check('All workflow nodes are rendered', canvas.count === 18, canvas)
  check('Distinct sewing modules and garment stage visible', ['中轴起线','菱格转角','凤羽轮廓','蓝线羽片','米白填绣','纹样入衣'].every(label => canvas.names.some(name=>name.includes(label))), canvas.names)
  await evalPage(client, `() => {
    const node=[...document.querySelectorAll('.tool-node')].find(n=>n.querySelector('.node-name-input')?.value.includes('菱格转角'));
    if(!node)throw new Error('Diamond module missing');node.click();return true;
  }`)
  const editable=await waitFor(`() => {
    const node=[...document.querySelectorAll('.tool-node')].find(n=>n.querySelector('.node-name-input')?.value.includes('菱格转角'));
    const text=node?.querySelector('textarea')?.value;if(!text)return null;
    const p=JSON.parse(text);return {module:p.module_id||p.moduleId,seed:p.seed,promptAvailable:typeof p.prompt==='string'&&p.prompt.length>0};
  }`, p=>Boolean(p))
  check('Module prompt and numeric seed are editable on canvas', editable.module==='diamond-travel' && Number.isInteger(editable.seed) && editable.promptAvailable, editable)
  await evalPage(client, `() => {const node=[...document.querySelectorAll('.tool-node')].find(n=>n.querySelector('.node-name-input')?.value.includes('菱格转角'));node.querySelector('.action-btn').click();return true;}`)
  await client.tool('take_screenshot', {filePath: 'E:/Flowly-now/output/butterfly-video/flowly_modular_60/workflow-canvas.png', fullPage: false})
  if (!canvasOnly) {
    const data = await evalPage(client, `async () => {
      const response=await fetch('${BACKEND_URL}/api/v1/workflows/executions/${executionId}/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});
      const body=await response.json();const row=body.data||body;const variables=(row.outputData||row.output_data||{}).variables||{};
      const clips=Object.values(variables.nodeOutputs||variables.node_outputs||{}).filter(v=>v.provider==='ltx_local');
      return {status:row.status,final: variables.finalVideo||variables.final_video, clips:clips.map(c=>({id:c.moduleId||c.module_id,url:c.videoUrl||c.video_url,seconds:c.duration,cached:c.cachedModelOutput??c.cached_model_output,source:c.sourceSha256||c.source_sha256}))};
    }`)
    check('Native workflow execution completed', data.status === 'completed', data)
    check('Nine distinct AI modules total 60 seconds', data.clips.length === 9 && data.clips.reduce((n,c)=>n+c.seconds,0)===60 && new Set(data.clips.map(c=>c.source)).size===9, data.clips)
    check('Original garment style restored', data.clips.some(c=>c.id==='06-garment-map') && data.clips.some(c=>c.id==='08-final'))
    await client.tool('navigate_page', {type:'url',url:`${FRONTEND_URL}/executions/${executionId}`,timeout:30000})
    const filename = new URL(data.final).pathname.split('/').pop()
    const ready = await waitFor(`() => {const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src).includes('${filename}'));return v?{duration:v.duration,ready:v.readyState,width:v.videoWidth,error:v.error?.message}:null}`, v=>v?.duration===60 && v.ready>=2)
    check('Full film playable in execution history', ready.width===1024 && !ready.error, ready)
    const playback = await evalPage(client, `async () => {
      const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src).includes('${filename}'));
      v.scrollIntoView({block:'center'});v.muted=true;const start=v.currentTime;await v.play();await new Promise(r=>setTimeout(r,1200));const advanced=v.currentTime>start;v.pause();v.currentTime=59.5;
      for(let i=0;i<40&&(v.seeking||v.readyState<2);i++)await new Promise(r=>setTimeout(r,100));
      const response=await fetch(v.currentSrc||v.src,{headers:{Range:'bytes=0-1023'}});const bytes=(await response.arrayBuffer()).byteLength;
      return {advanced,time:v.currentTime,seeking:v.seeking,ready:v.readyState,error:v.error?.message,rangeStatus:response.status,bytes};
    }`, 20000)
    check('Playback, final-second seek and byte ranges', playback.advanced && playback.time>=59.4 && !playback.seeking && playback.ready>=2 && !playback.error && playback.rangeStatus===206 && playback.bytes===1024, playback)
    const modules=await waitFor(`() => ${JSON.stringify(data.clips)}.map(c=>{const name=new URL(c.url).pathname.split('/').pop();const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src).includes(name));return {id:c.id,wanted:c.seconds,duration:v?.duration,width:v?.videoWidth,error:v?.error?.message}})`, rows=>rows.every(r=>r.duration===r.wanted && r.width>0))
    check('Every individual module playable', modules.every(m=>!m.error),modules)
    await client.tool('take_screenshot', {filePath:'E:/Flowly-now/output/butterfly-video/flowly_modular_60/final-history.png',fullPage:false})
  }
  report.status='passed'
} catch(error) {
  report.status='failed';report.error=error.message;process.exitCode=1
} finally {
  await fs.writeFile(new URL(canvasOnly?'canvas-check.json':'browser-check.json',output),JSON.stringify(report,null,2))
  console.log(JSON.stringify(report,null,2))
  client.close()
}
