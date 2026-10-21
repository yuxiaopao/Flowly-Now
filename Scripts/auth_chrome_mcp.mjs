import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { McpClient, evalPage, resultText } from './chrome_mcp_client.mjs'

const origin = process.env.FRONTEND_URL || 'http://localhost:5200'
const output = 'E:/Flowly-now/Docs/verification/auth-20261019'
const resume = process.env.FLOWLY_AUTH_RESUME === '1'
const username = resume ? readFileSync('E:/Flowly-now/.cache/auth-qa-username.txt','utf8').trim() : `authqa_${Date.now()}`
const password = 'Cobalt!48219'
const nextPassword = 'Violet!68391'
const checks = resume ? JSON.parse(readFileSync(output + '/browser-checks.json','utf8')).checks : []
const client = new McpClient()
mkdirSync(output, { recursive: true })
writeFileSync('E:/Flowly-now/.cache/auth-qa-username.txt', username)
async function snapshot() { return resultText(await client.tool('take_snapshot')) }
async function uid(role, label) {
  const text = await snapshot()
  const line = text.split('\n').find(line => line.includes(`${role} "${label}"`))
  assert(line, `Missing ${role}: ${label}\n${text}`)
  return line.match(/uid=([^ ]+)/)[1]
}
async function click(role, label) {
  await uid(role, label)
  for (let attempt=0; attempt<60; attempt++) {
    const enabled=await evalPage(client, `()=>[...document.querySelectorAll(${JSON.stringify(role === 'button' ? 'button:not([role=tab])' : `[role="${role}"]`)})].some(e=>e.textContent.trim()===${JSON.stringify(label)}&&e.getClientRects().length&&!e.disabled)`)
    if (enabled) break
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  await evalPage(client, `()=>{
    const role=${JSON.stringify(role)},label=${JSON.stringify(label)};
    const elements=[...document.querySelectorAll(role==='button'?'button:not([role=tab])':'[role="'+role+'"]')];
    const element=elements.find(e=>e.textContent.trim()===label && e.getClientRects().length);
    if(!element)throw Error('Visible control missing: '+label);
    element.scrollIntoView({block:'center'});element.click();return true;
  }`)
}
async function fill(label, value) {
  await uid('textbox', label)
  // Set and dispatch in one browser task so Element Plus observes the edit.
  await evalPage(client, `()=>{const input=[...document.querySelectorAll('input')].find(e=>e.getAttribute('aria-label')===${JSON.stringify(label)});input.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(value)});input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));input.blur();return true}`)
}
async function wait(text) {
  await client.tool('wait_for', { text: [text], timeout: 10000 })
  for (let attempt = 0; attempt < 60; attempt++) {
    if (await evalPage(client, `()=>document.body.innerText.includes(${JSON.stringify(text)})`)) return
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`Visible text did not appear: ${text}`)
}
async function check(name, fn) { await fn(); checks.push(name); console.log(`PASS ${name}`) }
async function waitPath(path) {
  for (let attempt=0; attempt<80; attempt++) {
    if (await evalPage(client, `()=>location.pathname===${JSON.stringify(path)}`)) return
    await new Promise(resolve=>setTimeout(resolve,200))
  }
  throw Error(`Navigation did not reach ${path}`)
}
async function navigate(path) { await client.tool('navigate_page', { url: origin + path }) }

try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  assert(tools.some(tool => tool.name === 'navigate_page'))
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  await client.tool('new_page', { url: origin + '/login' })
  if (!resume) {
  await evalPage(client, `async()=>{ const {clearAuthSession}=await import('/src/utils/authSession.js');clearAuthSession();return true }`)
  await navigate('/login?redirect=%2Fworkflows%3Fauthqa%3D1')
  await wait('欢迎回来')

  await check('空登录表单显示字段校验', async () => {
    await fill('用户名或邮箱', '')
    await fill('登录密码', '')
    await click('button', '登录')
    await wait('请输入用户名或邮箱')
    await wait('请输入密码')
  })
  await click('tab', '注册')
  await wait('创建账号')
  await check('注册邮箱和确认密码校验', async () => {
    await fill('注册用户名', username)
    await fill('注册邮箱', 'invalid-email')
    await fill('注册密码', password)
    await fill('确认注册密码', 'different')
    await click('button', '创建账号')
    await wait('请输入有效的邮箱地址')
    await wait('两次输入的密码不一致')
  })
  await fill('注册邮箱', `${username}@example.invalid`)
  await fill('确认注册密码', password)
  await check('未同意条款时给出明确提示', async () => {
    await click('button', '创建账号')
    await wait('请先阅读并同意服务条款与隐私政策')
  })
  await check('服务条款可阅读且不自动勾选同意', async () => {
    await click('button', '服务条款')
    assert((await snapshot()).includes('dialog'))
    assert.equal(await evalPage(client, `()=>document.querySelector('.form-terms input').checked`), false)
    await evalPage(client, `()=>{document.querySelector('.el-dialog__headerbtn').click();return true}`)
  })
  await evalPage(client, `()=>{document.querySelector('.form-terms .el-checkbox').click();return true}`)
  await check('真实注册成功后带回用户名并清空密码', async () => {
    await click('button', '创建账号')
    await wait('欢迎回来')
    const values = await evalPage(client, `()=>({username:document.querySelector('[aria-label="用户名或邮箱"]').value,emptyPassword:document.querySelector('[aria-label="登录密码"]').value===''})`)
    assert.equal(values.username, username)
    assert.equal(values.emptyPassword, true)
  })
  await check('错误密码显示接口具体错误', async () => {
    await fill('用户名或邮箱', username)
    await fill('登录密码', 'wrong-password')
    await click('button', '登录')
    await wait('用户名或密码错误')
  })
  await check('登录返回受保护目标并遵守未记住登录选择', async () => {
    await fill('登录密码', password)
    await click('button', '登录')
    await waitPath('/workflows')
    await wait('工作流')
    const state = await evalPage(client, `()=>({path:location.pathname,query:location.search,local:!!localStorage.getItem('access_token'),session:!!sessionStorage.getItem('access_token'),sid:!!JSON.parse(atob(sessionStorage.getItem('access_token').split('.')[1])).sid})`)
    assert.equal(state.path, '/workflows')
    assert(state.query.includes('authqa=1'))
    assert.equal(state.local, false)
    assert.equal(state.session, true)
    assert.equal(state.sid, true)
  })
  await check('刷新页面保留有效登录态', async () => {
    await navigate('/workflows')
    await wait('工作流')
    assert.equal(await evalPage(client, '()=>location.pathname'), '/workflows')
  })
  } else {
    await navigate('/login?redirect=/workflows')
    if (await evalPage(client, `()=>location.pathname==='/login'`)) {
      await wait('欢迎回来')
      await fill('用户名或邮箱', username)
      await fill('登录密码', password)
      await click('button', '登录')
      await waitPath('/workflows')
    }
    await navigate('/workflows')
    await waitPath('/workflows')
    await wait('工作流')
  }
  await evalPage(client, `async()=>{const {authSession}=await import('/src/utils/authSession.js');window.__authQaOldToken=authSession.access;return true}`)
  console.log('AUTHENTICATED_SNAPSHOT\n' + await snapshot())
  await client.tool('take_screenshot', { filePath: output + '/authenticated.png', fullPage: true })

  // The UI and native menu are exercised through the DevTools MCP DOM surface.
  await evalPage(client, `()=>{document.querySelector('[aria-label="打开账户菜单"]').click();return true}`)
  await wait('退出登录')
  await check('退出按钮返回登录页且撤销服务器凭证', async () => {
    await click('menuitem', '退出登录')
    await wait('欢迎回来')
    const state = await evalPage(client, `async()=>{const r=await fetch('/api/v1/auth/user/',{headers:{Authorization:'Bearer '+window.__authQaOldToken}});return {status:r.status,local:!!localStorage.getItem('access_token'),session:!!sessionStorage.getItem('access_token')}}`)
    assert.equal(state.status, 401)
    assert.equal(state.local, false)
    assert.equal(state.session, false)
  })
  await check('忘记密码表单真实提交并保留中性反馈', async () => {
    await navigate('/forgot-password')
    await wait('发送重置链接')
    await fill('注册邮箱', 'absent-authqa@example.invalid')
    await click('button', '发送重置链接')
    for (let attempt=0; attempt<60; attempt++) {
      if(await evalPage(client, `()=>/如果邮箱存在|当前为本地测试环境/.test(document.body.innerText)`)) return
      await new Promise(resolve=>setTimeout(resolve,200))
    }
    throw Error('Missing neutral delivery feedback')
  })
  await check('无效重置链接提供重新申请入口', async () => {
    await navigate('/reset-password')
    await wait('重置链接无效或缺少参数')
    assert((await snapshot()).includes('重新申请重置链接'))
  })
  const reset = JSON.parse(execFileSync('E:/Flowly-now/.venv/Scripts/python.exe', ['E:/Flowly-now/Scripts/auth_e2e_fixture.py', username], { encoding: 'utf8', windowsHide: true }).trim())
  await check('真实重置密码后可以用新密码登录', async () => {
    await navigate(`/reset-password?uid=${reset.uid}&token=${reset.token}`)
    await wait('更新密码')
    await fill('新密码', nextPassword)
    await fill('确认新密码', nextPassword)
    await click('button', '更新密码')
    await wait('欢迎回来')
    await fill('用户名或邮箱', `${username}@example.invalid`.toUpperCase())
    await fill('登录密码', nextPassword)
    await evalPage(client, `()=>{document.querySelector('.form-options .el-checkbox').click();return true}`)
    await click('button', '登录')
    await waitPath('/home')
    await wait('工作台')
    assert.equal(await evalPage(client, `()=>!!localStorage.getItem('refresh_token')`), true)
  })
  await check('已登录仍可打开重置链接且旧链接不能重复使用', async () => {
    await navigate(`/reset-password?uid=${reset.uid}&token=${reset.token}`)
    await wait('更新密码')
    await fill('新密码', password)
    await fill('确认新密码', password)
    await click('button', '更新密码')
    await wait('重置链接已过期')
  })
  await evalPage(client, `async()=>{const {useAuthStore}=await import('/src/stores/auth.js');await useAuthStore().logout();return true}`)
  await navigate('/login?tab=register')
  await wait('创建账号')
  await client.tool('emulate', { viewport: '390x844x1,mobile,touch' })
  await wait('创建账号')
  await check('移动端无水平溢出且注册提交入口可滚动到达', async () => {
    const layout = await evalPage(client, `()=>({overflow:document.documentElement.scrollWidth>innerWidth,submit:!![...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='创建账号')})`)
    assert.equal(layout.overflow, false)
    assert.equal(layout.submit, true)
  })
  await client.tool('take_screenshot', { filePath: output + '/register-mobile.png', fullPage: true })
  await client.tool('emulate', {})
  await wait('创建账号')
  await client.tool('take_screenshot', { filePath: output + '/register-desktop.png', fullPage: true })
} catch (error) {
  console.log(await snapshot())
  console.log(resultText(await client.tool('list_console_messages', { types: ['error'] })))
  throw error
} finally {
  writeFileSync(output + '/browser-checks.json', JSON.stringify({ tool: 'chrome-devtools-mcp', username, checks }, null, 2))
  if (!process.env.FLOWLY_AUTH_KEEP_ACCOUNT) {
    execFileSync('E:/Flowly-now/.venv/Scripts/python.exe', ['E:/Flowly-now/Scripts/auth_e2e_fixture.py', username, '--cleanup'], { windowsHide: true })
  }
  client.close()
}
