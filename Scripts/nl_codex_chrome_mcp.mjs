import { mkdirSync, writeFileSync } from 'node:fs'
import { McpClient, evalPage, resultText, login } from './chrome_mcp_client.mjs'

const output = 'E:/Flowly-now/Docs/verification/nl-codex-20261019'
mkdirSync(output, { recursive: true })
const client = new McpClient()
const checks = []
const evaluate = fn => evalPage(client, fn)
function check(name, passed, detail) {
  checks.push({ name, passed: Boolean(passed), detail })
  writeFileSync(`${output}/browser-results.json`, JSON.stringify(checks, null, 2))
  console.log(`${passed ? 'PASS' : 'FAIL'} ${name}`, detail ?? '')
  if (!passed) throw new Error(name)
}
async function wait(expression, timeout = 20000) {
  return evaluate(`async () => { const end=Date.now()+${timeout}; while(Date.now()<end) { if (${expression}) return true; await new Promise(r=>setTimeout(r,150)); } throw new Error('Timed out: '+${JSON.stringify(expression)}); }`)
}
async function uid(role, name) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(line => line.includes(`${role} "${name}"`) || line.includes(`${role} "${name} `))
  if (!line) throw new Error(`Missing ${role} ${name}\n${snapshot.slice(-10000)}`)
  return line.match(/uid=(\S+)/)[1]
}
const click = async name => client.tool('click', { uid: await uid('button', name) })
const fill = async (name, value) => client.tool('fill', { uid: await uid('textbox', name), value })
async function go() {
  await client.tool('navigate_page', { url: 'http://localhost:5200/nl-create' })
  await wait(`document.querySelector('.workspace-header') && document.querySelector('#chat-message-input')`)
}
async function shot(name) {
  if (process.env.NL_NO_SCREENSHOTS) return
  await evaluate(`() => window.scrollTo(0,0)`)
  await client.tool('take_screenshot', { filePath: `${output}/${name}.png`, fullPage: false }, 60000)
}
async function viewport(value) {
  await client.tool('emulate', { viewport: value, prefersReducedMotion: 'reduce' })
  // The app's navigation also responds to resize; wait for its reflow before measuring.
  const width = Number(value.split('x')[0])
  await wait(`innerWidth === ${width} && document.documentElement.scrollWidth <= innerWidth && (${width} > 720 || document.querySelector('.nl-creator')?.getBoundingClientRect().left < 40)`)
  await evaluate(`async () => { await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))); }`)
}
const noOverflow = () => evaluate(`() => ({viewport:innerWidth, document:document.documentElement.scrollWidth, body:document.body.scrollWidth, composer:document.querySelector('.chat-input').getBoundingClientRect().toJSON()})`)
try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  if (!tools.some(tool => tool.name === 'navigate_page')) throw new Error('Chrome DevTools navigate_page unavailable')
  await login(client)
  const setup = await evaluate(`async () => {
    const {saveAuthSession,authSession}=await import('/src/utils/authSession.js');
    saveAuthSession({access:localStorage.getItem('access_token'),refresh:localStorage.getItem('refresh_token')});
    const r=await fetch('/api/v1/auth/user/',{headers:{Authorization:'Bearer '+authSession.access}});
    if(!r.ok) throw new Error('Test login failed');
    const p=await r.json(), user=p.data||p;
    if(user.username!=='nlwftest') throw new Error('Refusing to reset non-QA workspace');
    const key='flowly_nl_workspace_v2:'+user.id, previous=localStorage.getItem(key);
    localStorage.removeItem(key); localStorage.setItem('theme','light');
    return {userId:user.id,previous};
  }`)
  writeFileSync(`${output}/qa-workspace-backup.json`, JSON.stringify(setup))
  await go()
  await viewport('1440x1000x1')
  await wait(`!document.querySelector('[data-testid="model-selector"] .is-loading')`)
  check('new conversation has a single header and centered composer', await evaluate(`() => !!document.querySelector('.welcome-state') && !document.querySelector('.tab-bar') && document.querySelectorAll('.starter-item').length===6 && document.querySelector('[data-testid="send-button"]').disabled`))
  check('composer is compact with microphone and send on one row', await evaluate(`() => { const c=document.querySelector('.chat-input').getBoundingClientRect(); const m=document.querySelector('.voice-trigger').getBoundingClientRect(); const s=document.querySelector('[data-testid="send-button"]').getBoundingClientRect(); return c.height<120 && c.width<=720 && Math.abs(m.top-s.top)<5; }`))
  await shot('desktop-start')
  if (!process.env.NL_VOICE_ONLY) {
  await click('数据处理 数据清洗与汇总')
  check('starter fills draft and selects generate mode without sending', await evaluate(`() => document.querySelector('#chat-message-input').value.includes('CSV') && !document.querySelector('.message-user') && document.querySelector('[data-testid="mode-generate"]').getAttribute('aria-pressed')==='true'`))
  await fill('输入工作流描述', '第一份草稿')
  await evaluate(`() => document.querySelector('.new-tab-btn').click()`)
  await fill('输入工作流描述', '第二份草稿')
  await evaluate(`() => document.querySelector('[role="tab"]').click()`)
  check('multiple conversations preserve independent drafts and modes', await evaluate(`() => document.querySelector('#chat-message-input').value==='第一份草稿' && document.querySelector('[data-testid="mode-generate"]').getAttribute('aria-pressed')==='true'`))
  await go()
  check('draft survives reload', await evaluate(`() => document.querySelector('#chat-message-input').value==='第一份草稿'`))
  await click('模型设置')
  check('all models and refresh remain accessible in model settings', (resultText(await client.tool('take_snapshot'))).includes('显示全部模型'))
  await client.tool('press_key', {key:'Escape'})
  await click('对话操作')
  check('conversation menu retains export, sync, rename and close', await evaluate(`() => ['同步会话','导出对话','重命名对话','关闭当前对话'].every(t=>document.body.innerText.includes(t))`))
  await client.tool('press_key', {key:'Escape'})
  await click('历史对话')
  check('history drawer isolates the conversation', await evaluate(`() => document.querySelector('.creator-main').inert && document.querySelector('.history-sidebar').contains(document.activeElement)`))
  await client.tool('press_key', {key:'Escape'})
  check('history escape restores focus', await evaluate(`() => !document.querySelector('.creator-main').inert && document.activeElement.getAttribute('aria-label')==='历史对话'`))
  await click('历史对话')
  await fill('搜索对话', 'NL-QA-20261017 主流程')
  await wait(`document.querySelector('.session-name')?.textContent.includes('主流程')`)
  await evaluate(`() => document.querySelector('.session-item').click()`)
  await wait(`document.querySelectorAll('.vue-flow__node').length===3`)
  check('history restores conversation and interactive workflow preview', await evaluate(`() => document.querySelectorAll('.message-user').length===1 && !!document.querySelector('.mini-workflow-preview')`))
  await shot('desktop-workflow')
  await click('收起工作流预览')
  check('collapsing preview gives the full workspace back to conversation', await evaluate(`() => !document.querySelector('.mini-workflow-preview') && !document.querySelector('.chat-container').classList.contains('has-preview')`))
  await click('工作流')
  await wait(`document.querySelectorAll('.vue-flow__node').length===3`)
  await evaluate(`() => document.querySelector('.vue-flow__node[data-id="code"]').dispatchEvent(new MouseEvent('click',{bubbles:true}))`)
  await wait(`document.querySelector('#node-config-json')`)
  check('preview still exposes node configuration', await evaluate(`() => document.querySelector('#node-config-json').value.includes('customCamelKey')`))
  await fill('节点参数 JSON','{ invalid')
  await click('保存')
  await wait(`document.querySelector('.config-error')?.textContent.includes('JSON')`)
  check('invalid node JSON remains blocked with an inline error',true)
  await click('收起工作流预览')
  for(const theme of ['dark','pure-bw','high-contrast','light']) {
    await evaluate(`async () => { const {useAppStore}=await import('/src/stores/app.js'); useAppStore().setTheme('${theme}'); }`)
    await wait(`document.querySelector('.chat-input')`)
    const dimensions=await noOverflow()
    check(`${theme} has no horizontal overflow`, dimensions.document<=dimensions.viewport, dimensions)
    await shot(`theme-${theme}`)
  }
  await viewport('390x844x1')
  let dimensions=await noOverflow()
  check('mobile conversation has no horizontal overflow',dimensions.document<=dimensions.viewport, dimensions)
  await shot('mobile-conversation')
  await click('工作流')
  await wait(`document.querySelectorAll('.vue-flow__node').length===3`)
  dimensions=await noOverflow()
  check('mobile preview fits viewport and has a reachable close action',dimensions.document<=dimensions.viewport && await evaluate(`() => {const r=document.querySelector('[aria-label="收起工作流预览"]').getBoundingClientRect(); return r.right<=innerWidth && r.top>=0 && r.bottom<innerHeight;}`),dimensions)
  await shot('mobile-preview')
  await click('收起工作流预览')
  await evaluate(`() => document.querySelector('.new-tab-btn').click()`)
  dimensions=await noOverflow()
  check('mobile start keeps templates and composer visible',dimensions.document<=dimensions.viewport && await evaluate(`() => document.querySelector('.chat-input').getBoundingClientRect().bottom<=innerHeight`),dimensions)
  check('mobile textarea has enough height for an unclipped line',await evaluate(`() => {const e=document.querySelector('#chat-message-input'),s=getComputedStyle(e);return e.clientHeight>=parseFloat(s.lineHeight)+parseFloat(s.paddingTop)+parseFloat(s.paddingBottom)-1}`))
  await shot('mobile-start')
  }
  await viewport('1440x1000x1')
  await evaluate(`() => {
    window.__voiceOriginalGetUserMedia=navigator.mediaDevices.getUserMedia;
    window.__voiceContexts=[]; window.__voiceStreams=[];
    navigator.mediaDevices.getUserMedia=async()=>{
      const context=new AudioContext(); await context.resume();
      const oscillator=context.createOscillator(); const gain=context.createGain();
      gain.gain.value=0.03; oscillator.connect(gain);
      const destination=context.createMediaStreamDestination(); gain.connect(destination); oscillator.start();
      window.__voiceContexts.push(context); window.__voiceStreams.push(destination.stream);
      return destination.stream;
    };
  }`)
  await click('开始录音')
  await wait(`document.querySelector('.voice-status')?.textContent.includes('00:01')`)
  check('recording shows elapsed time and disables text send',await evaluate(`() => document.querySelector('[data-testid="send-button"]').disabled && document.querySelector('.voice-trigger').classList.contains('is-recording')`))
  const initialTabCount = await evaluate(`() => document.querySelectorAll('[role="tab"]').length`)
  await evaluate(`() => document.querySelector('.new-tab-btn').click()`)
  check('active recording prevents conversation switches',await evaluate(`() => document.querySelectorAll('[role="tab"]').length`)===initialTabCount)
  await shot('voice-recording')
  await click('结束录音')
  await wait(`document.querySelector('.voice-panel audio')?.readyState>=1`)
  check('native MediaRecorder produces a playable clip and releases all microphone tracks',await evaluate(`() => document.querySelector('.voice-panel audio').readyState>=1 && window.__voiceStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))`))
  await evaluate(`async () => { const a=document.querySelector('.voice-panel audio'); a.volume=0; await a.play(); }`)
  check('recording can be played back',await evaluate(`() => !document.querySelector('.voice-panel audio').paused`))
  await evaluate(`() => document.querySelector('.voice-panel audio').pause()`)
  const download = await evaluate(`() => {const a=document.querySelector('.voice-file a'); return {href:a.href,name:a.download};}`)
  check('download uses recorded blob and correct file extension',download.href.startsWith('blob:') && download.name.endsWith('.webm'),download.name)
  await shot('voice-ready')
  await click('收起录音')
  await evaluate(`() => document.querySelector('.new-tab-btn').click()`)
  check('recordings stay with their own conversation',await evaluate(`() => !document.querySelector('.voice-trigger').classList.contains('has-recording')`))
  await evaluate(`() => {const tabs=[...document.querySelectorAll('[role="tab"]')]; tabs[tabs.length-2].click();}`)
  await click('查看录音')
  await wait(`document.querySelector('.voice-panel audio')?.readyState>=1`)
  check('switching back restores recorded audio',true)
  await viewport('390x844x1')
  check('mobile recording controls and player fit the screen',await evaluate(`() => {const r=document.querySelector('.voice-panel').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight}`))
  await shot('mobile-voice')
  await viewport('1440x1000x1')
  await click('删除录音')
  check('deleting a recording removes its preview',await evaluate(`() => !document.querySelector('.voice-panel audio') && !document.querySelector('.voice-trigger').classList.contains('has-recording')`))
  await click('开始录音')
  await wait(`document.querySelector('.voice-trigger').classList.contains('is-recording')`)
  await click('取消录音')
  check('cancel discards audio and releases microphone',await evaluate(`() => !document.querySelector('.voice-panel') && window.__voiceStreams.every(s=>s.getTracks().every(t=>t.readyState==='ended'))`))
  await evaluate(`() => {navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('test denied','NotAllowedError')};}`)
  await click('开始录音')
  await wait(`document.querySelector('.voice-error')?.textContent.includes('麦克风权限未开启')`)
  check('permission denial shows an actionable retry message',true)
  await shot('voice-permission-error')
  await click('收起录音')
  await evaluate(`async () => {navigator.mediaDevices.getUserMedia=window.__voiceOriginalGetUserMedia; await Promise.all(window.__voiceContexts.map(context=>context.close()));}`)
  const consoleMessages=resultText(await client.tool('list_console_messages',{types:['error','warn']}))
  writeFileSync(`${output}/console.log`,consoleMessages)
  check('no browser errors or warnings',consoleMessages.includes('<no console messages found>'),consoleMessages)
  console.log(`Completed ${checks.length} checks through Chrome DevTools MCP`)
} catch(error) {
  console.error(error)
  writeFileSync(`${output}/failure-snapshot.txt`,resultText(await client.tool('take_snapshot').catch(()=>({}))))
  process.exitCode=1
} finally { client.close() }
