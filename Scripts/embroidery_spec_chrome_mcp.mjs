import fs from 'node:fs/promises'
import path from 'node:path'
import { McpClient, evalPage, login, delay, FRONTEND_URL, BACKEND_URL } from './chrome_mcp_client.mjs'

const executionPath = path.resolve(process.argv[2])
const saved = JSON.parse(await fs.readFile(executionPath, 'utf8'))
const { workflow_id: workflowId, spec } = saved
let executionId = saved.execution_id
const replay = process.argv.includes('--replay')
const base = executionPath.replace(/-execution\.json$/, '')
const report = { provider: 'chrome-devtools-mcp', workflowId, executionId, checks: [] }
const client = new McpClient()
function check(name, passed, details) {
  report.checks.push({ name, passed: Boolean(passed), details })
  if (!passed) throw new Error(name)
}
async function until(script, accepted) {
  for (let attempt = 0; attempt < 50; attempt++) {
    const result = await evalPage(client, script)
    if (accepted(result)) return result
    await delay(400)
  }
  throw new Error('Browser did not become ready')
}
try {
  const [debug, frontend, backend] = await Promise.all([
    fetch('http://127.0.0.1:9222/json/version').then(r => r.json()),
    fetch(FRONTEND_URL), fetch(`${BACKEND_URL}/admin/`),
  ])
  check('Independent Chrome and local services reachable', debug.webSocketDebuggerUrl.includes('/devtools/browser/') && frontend.ok && backend.ok)
  await client.initialize()
  const schema = await client.request('tools/list')
  client.pageTools = new Set(schema.tools.filter(t => t.inputSchema.required?.includes('pageId')).map(t => t.name))
  check('Chrome DevTools navigate_page available', schema.tools.some(t => t.name === 'navigate_page'))
  await login(client)
  if (replay) {
    const queued = await evalPage(client, `async () => {
      const r=await fetch('${BACKEND_URL}/api/v1/workflows/${workflowId}/execute/',{method:'POST',headers:{Authorization:'Bearer '+localStorage.getItem('access_token'),'Content-Type':'application/json'},body:JSON.stringify({is_async:true,input_data:{}})});
      const b=await r.json();return {http:r.status,row:b.data||b};
    }`)
    check('Native asynchronous workflow queue accepted replay', queued.http === 202 && Boolean(queued.row.execution_id), queued)
    report.originalExecutionId = executionId
    executionId = queued.row.execution_id
    report.executionId = executionId
    const completed = await until(`async () => {
      const r=await fetch('${BACKEND_URL}/api/v1/workflows/executions/${executionId}/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});
      const b=await r.json(),row=b.data||b;return {status:row.status,error:row.errorMessage||row.error_message};
    }`, row => ['completed','failed','cancelled'].includes(row.status))
    check('Celery finished replay successfully', completed.status === 'completed', completed)
  }
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/workflows/${workflowId}/edit`, timeout: 30000 })
  const expected = spec.modules.length === 1 ? 5 : spec.modules.length + 9
  const canvas = await until(`() => ({count:document.querySelectorAll('.vue-flow__node').length,names:[...document.querySelectorAll('.node-name-input')].map(n=>n.value)})`, row => row.count >= expected)
  check('Every native workflow node rendered', canvas.count === expected, canvas)
  check('All configured stitching modules visible', spec.modules.every(m => canvas.names.includes(m.caption)), canvas.names)
  await client.tool('take_screenshot', { filePath: `${base}-canvas.png`, fullPage: false })
  const result = await evalPage(client, `async () => {
    const r=await fetch('${BACKEND_URL}/api/v1/workflows/executions/${executionId}/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});
    const b=await r.json(), row=b.data||b, variables=(row.outputData||row.output_data||{}).variables||{};
    const cached=[];function visit(value){if(!value||typeof value!=='object')return;for(const [key,item] of Object.entries(value)){if(key==='cached_model_output')cached.push(item);else visit(item)}}visit(row.outputData||row.output_data||{});
    return {status:row.status,video: variables.finalVideo||variables.final_video,cached};
  }`)
  check('Execution completed with video output', result.status === 'completed' && Boolean(result.video), result)
  if (replay) check('Replay reused verified AI output without another generation', result.cached.length>0 && result.cached.every(Boolean), result.cached)
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/executions/${executionId}`, timeout: 30000 })
  const filename = new URL(result.video).pathname.split('/').pop()
  const ready = await until(`() => {const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src).includes('${filename}'));return v?{duration:v.duration,width:v.videoWidth,ready:v.readyState,error:v.error?.message}:null}`, v => v?.ready >= 2)
  check('Output decodes at the intended duration and size', Math.abs(ready.duration-spec.seconds)<0.05 && ready.width === spec.encoding.width && !ready.error, ready)
  const playback = await evalPage(client, `async () => {
    const v=[...document.querySelectorAll('video')].find(v=>(v.currentSrc||v.src).includes('${filename}'));
    v.scrollIntoView({block:'center'});v.muted=true;const t=v.currentTime;await v.play();await new Promise(r=>setTimeout(r,700));const advanced=v.currentTime>t;v.pause();
    v.currentTime=Math.max(0,v.duration-0.2);for(let i=0;i<40&&(v.seeking||v.readyState<2);i++)await new Promise(r=>setTimeout(r,100));
    const r=await fetch(v.currentSrc||v.src,{headers:{Range:'bytes=0-1023'}});return {advanced,seeked:!v.seeking,ready:v.readyState,range:r.status,size:(await r.arrayBuffer()).byteLength,error:v.error?.message};
  }`, 15000)
  check('Playback, final frame seeking and ranged download work', playback.advanced && playback.seeked && playback.ready>=2 && playback.range===206 && playback.size===1024 && !playback.error, playback)
  report.status = 'passed'
} catch (error) {
  report.status = 'failed'
  report.error = error.message
  process.exitCode = 1
} finally {
  await fs.writeFile(`${base}-browser-check.json`, JSON.stringify(report, null, 2))
  client.close()
  console.log(JSON.stringify({ status: report.status, checks: report.checks.length, error: report.error }))
}
