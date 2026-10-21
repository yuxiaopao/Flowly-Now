import assert from 'node:assert/strict'
import {readFileSync, writeFileSync} from 'node:fs'
import {McpClient, evalPage, resultText} from './chrome_mcp_client.mjs'
const c=new McpClient()
const output='E:/Flowly-now/Docs/verification/auth-20261019'
const report=JSON.parse(readFileSync(output+'/browser-checks.json','utf8'))
try {
  await c.initialize()
  const {tools}=await c.request('tools/list')
  assert(tools.some(t=>t.name==='navigate_page'))
  c.pageTools=new Set(tools.filter(t=>t.inputSchema?.properties?.pageId).map(t=>t.name))
  await c.tool('new_page',{url:'http://localhost:5200/login'})
  await c.tool('wait_for',{text:['欢迎回来']})
  await evalPage(c, `()=>{const tab=document.querySelector('#auth-login-tab');tab.focus();tab.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));return true}`)
  await c.tool('wait_for',{text:['创建账号']})
  assert.equal(await evalPage(c, `()=>document.activeElement.id==='auth-register-tab'&&document.activeElement.getAttribute('aria-selected')==='true'`),true)
  report.checks.push('方向键切换登录注册并同步键盘焦点')
  for (const theme of ['light','dark','pure-bw','high-contrast']) {
    await evalPage(c, `async()=>{const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme('${theme}');return true}`)
    const colors=await evalPage(c, `()=>{const input=document.querySelector('[aria-label="注册用户名"]');return {foreground:getComputedStyle(input).color,background:getComputedStyle(input.closest('.el-input__wrapper')).backgroundColor,overflow:document.documentElement.scrollWidth>innerWidth}}`)
    assert.notEqual(colors.foreground,colors.background)
    assert.equal(colors.overflow,false)
    await c.tool('take_screenshot',{filePath:output+`/register-${theme}.png`,fullPage:true})
  }
  report.checks.push('四套主题的表单文字和输入背景区分明确且无水平溢出')
  await evalPage(c, `async()=>{const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme('light');return true}`)
  await c.tool('emulate',{viewport:'390x844x1,mobile,touch'})
  await c.tool('wait_for',{text:['创建账号']})
  await c.tool('take_screenshot',{filePath:output+'/register-mobile.png',fullPage:true})
  await c.tool('emulate',{})
  await c.tool('navigate_page',{url:'http://localhost:5200/login'})
  await c.tool('wait_for',{text:['欢迎回来']})
  await c.tool('emulate',{networkConditions:'Offline'})
  await evalPage(c, `()=>{for(const [label,value] of [['用户名或邮箱','authqa_offline'],['登录密码','offline-test-password']]){const input=document.querySelector('[aria-label="'+label+'"]');Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,value);input.dispatchEvent(new Event('input',{bubbles:true}))}document.querySelector('#auth-login-panel button[type="submit"]').click();return true}`)
  await c.tool('wait_for',{text:['登录失败，请检查网络后重试']})
  assert.equal(await evalPage(c, `()=>!document.querySelector('#auth-login-panel button[type="submit"]').disabled`),true)
  assert.equal(await evalPage(c, `()=>document.querySelector('[aria-label="用户名或邮箱"]').value`),'authqa_offline')
  report.checks.push('断网登录保留输入、显示错误并恢复可重试按钮')
  await c.tool('emulate',{})
  await c.tool('navigate_page',{url:'http://localhost:5200/login'})
  await c.tool('wait_for',{text:['欢迎回来']})
  console.log(resultText(await c.tool('list_console_messages',{types:['error']})))
} finally {
  writeFileSync(output+'/browser-checks.json',JSON.stringify(report,null,2))
  c.close()
}
