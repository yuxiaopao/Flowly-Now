import fs from 'node:fs/promises'
import { McpClient, evalPage, login, delay, FRONTEND_URL, BACKEND_URL } from './chrome_mcp_client.mjs'

const output = new URL('../output/butterfly-video/ai_60/', import.meta.url)
const reports = new URL('../test-reports/butterfly-30s/', import.meta.url)
const executionId = (await fs.readFile(new URL('ltx-execution-id.txt', output), 'utf8')).trim()
const workflowId = (await fs.readFile(new URL('ltx-workflow-id.txt', output), 'utf8')).trim()
const client = new McpClient()
const report = { provider: 'chrome-devtools-mcp', executionId, workflowId, checks: [] }
function check(name, passed, details) {
  report.checks.push({ name, passed: Boolean(passed), details })
  if (!passed) throw new Error(`${name}: ${JSON.stringify(details)}`)
}
async function waitFor(script, predicate) {
  let result
  for (let attempt = 0; attempt < 30; attempt++) {
    result = await evalPage(client, script)
    if (predicate(result)) return result
    await delay(500)
  }
  throw new Error(`Browser content did not become ready: ${JSON.stringify(result)}`)
}
try {
  const debug = await (await fetch('http://127.0.0.1:9222/json/version')).json()
  check('Independent Chrome debug endpoint listening', debug.webSocketDebuggerUrl.includes('/devtools/browser/'))
  await client.initialize()
  const schema = await client.request('tools/list')
  client.pageTools = new Set(schema.tools.filter(tool => tool.inputSchema.required?.includes('pageId')).map(tool => tool.name))
  check('navigate_page available', schema.tools.some(tool => tool.name === 'navigate_page'))
  await login(client)
  const execution = await evalPage(client, `async () => {
    const response = await fetch('${BACKEND_URL}/api/v1/workflows/executions/${executionId}/', {headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});
    const payload=await response.json();const data=payload.data||payload;const output=data.outputData||data.output_data||{};
    const variables=output.variables||{};const nodes=Object.values(variables.nodeOutputs||variables.node_outputs||{});
    const clips=nodes.filter(node=>node.provider==='ltx_local'||node.provider==='ltx_public');
    return {status:response.status,executionStatus:data.status,finalVideo:variables.finalVideo||variables.final_video,
      clips:clips.map(node=>({provider:node.provider,model:node.model,duration:node.duration,videoUrl:node.videoUrl||node.video_url,cached:node.cachedModelOutput??node.cached_model_output}))};
  }`)
  check('Native execution completed', execution.status === 200 && execution.executionStatus === 'completed', execution)
  check('Eight real model outputs recorded honestly', execution.clips.length === 8 && execution.clips.every(clip => clip.model.startsWith('Lightricks/') && clip.duration === 7.5 && clip.cached === true), execution.clips)
  check('Final media URL returned', Boolean(execution.finalVideo))
  const filename = new URL(execution.finalVideo).pathname.split('/').pop()
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/executions/${executionId}`, timeout: 30000 })
  const mediaScript = `() => {const video=[...document.querySelectorAll('video')].find(item=>(item.currentSrc||item.src).includes('${filename}'));return video?{duration:video.duration,readyState:video.readyState,width:video.videoWidth,height:video.videoHeight,error:video.error?.message||null}:null}`
  const initial = await waitFor(mediaScript, media => media?.duration === 60 && media.readyState >= 2)
  check('Completed 60-second film renders in execution history', initial.duration === 60 && initial.width > 0 && !initial.error, initial)
  const clipFilenames=execution.clips.map(clip=>new URL(clip.videoUrl).pathname.split('/').pop())
  const clips=await waitFor(`() => ${JSON.stringify(clipFilenames)}.map(filename=>{
    const video=[...document.querySelectorAll('video')].find(item=>(item.currentSrc||item.src).includes(filename));
    return {filename,duration:video?.duration,width:video?.videoWidth,readyState:video?.readyState,error:video?.error?.message||null};
  })`,items=>items.every(item=>item.duration===7.5&&item.readyState>=2))
  check('All eight independent AI clips play in browser-compatible encodings',clips.length===8&&clips.every(item=>item.width>0&&!item.error),clips)
  const playback = await evalPage(client, `async () => {
    const video=[...document.querySelectorAll('video')].find(item=>(item.currentSrc||item.src).includes('${filename}'));
    video.scrollIntoView({block:'center'});video.muted=true;const start=video.currentTime;
    const played=await Promise.race([video.play().then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),5000))]);
    await new Promise(resolve=>setTimeout(resolve,1200));const advanced=video.currentTime>start;video.pause();
    video.currentTime=59.5;for(let i=0;i<40&&(video.seeking||video.readyState<2);i++)await new Promise(resolve=>setTimeout(resolve,200));
    const nearEnd={time:video.currentTime,seeking:video.seeking,readyState:video.readyState};
    video.currentTime=57;for(let i=0;i<30&&video.seeking;i++)await new Promise(resolve=>setTimeout(resolve,100));
    const response=await fetch(video.currentSrc||video.src,{headers:{Range:'bytes=0-1023'}});const rangeBytes=(await response.arrayBuffer()).byteLength;
    return {played,advanced,nearEnd,duration:video.duration,error:video.error?.message||null,rangeStatus:response.status,rangeBytes};
  }`, 25000)
  check('Video plays and seeks to its final second', playback.played && playback.advanced && playback.nearEnd.time >= 59.4 && !playback.nearEnd.seeking && playback.nearEnd.readyState >= 2 && !playback.error, playback)
  check('Media byte ranges support seeking', playback.rangeStatus === 206 && playback.rangeBytes === 1024, playback)
  await client.tool('take_screenshot', { filePath: 'E:/Flowly-now/test-reports/butterfly-30s/ltx-final-history.png', fullPage: false })
  report.status = 'passed'
} catch (error) {
  report.status = 'failed'; report.error = error.message; process.exitCode = 1
} finally {
  await fs.writeFile(new URL('ltx-final-browser.json', reports), JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report, null, 2))
  client.close()
}
