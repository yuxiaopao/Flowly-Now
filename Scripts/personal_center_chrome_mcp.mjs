import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { McpClient, evalPage, resultText } from './chrome_mcp_client.mjs'

const output = 'E:/Flowly-now/Docs/verification/personal-center-20261015'
mkdirSync(output, { recursive: true })
const client = new McpClient()
const resume = Boolean(process.env.PROFILE_QA_RESUME)
const mobileOnly = process.env.PROFILE_QA_RESUME === 'mobile'
const checks = resume ? JSON.parse(readFileSync(`${output}/browser-results.json`, 'utf8')).checks.filter(check => check.pass) : []
async function evaluate(body) { return evalPage(client, body) }
function check(name, pass, detail) {
  checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) })
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}`)
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`)
}
async function wait(expression) {
  return evaluate(`async () => { const end=Date.now()+15000; while(Date.now()<end) { if (${expression}) return true; await new Promise(r=>setTimeout(r,100)); } throw new Error('UI condition timed out'); }`)
}
async function uid(role, name) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(line => line.includes(`${role} "${name}"`) || line.includes(`${role} "*${name}"`))
  if (!line) throw new Error(`Missing ${role}: ${name}`)
  return line.match(/uid=(\S+)/)[1]
}
async function fill(name, value) { await client.tool('fill', { uid: await uid('textbox', name), value }) }
async function click(name) { await client.tool('click', { uid: await uid('button', name) }) }
async function go(path, text) {
  await client.tool('navigate_page', { url: `http://localhost:5200${path}` })
  await client.tool('wait_for', { text: [text] })
  await wait(`document.querySelector('.settings-content') && getComputedStyle(document.querySelector('.settings-content')).opacity === '1'`)
}
async function api(path, method='GET', data) {
  return evaluate(`async () => { const r=await fetch('/api/v1${path}', {method:${JSON.stringify(method)},headers:{Authorization:'Bearer '+localStorage.getItem('access_token'),'Content-Type':'application/json'},${data === undefined ? '' : `body:JSON.stringify(${JSON.stringify(data)}),`}}); const p=await r.json(); return {status:r.status,data:p.data||p,errors:p.errors}; }`)
}

try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  check('Chrome DevTools navigate_page available', tools.some(tool => tool.name === 'navigate_page'))
  if (!resume) {
  await client.tool('new_page', { url: 'http://localhost:5200/login', isolatedContext: 'personal-center-20261015' })
  const login = await evaluate(`async () => {
    const r=await fetch('/api/v1/auth/login/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'profile_qa_20261015',password:'Profile-QA-7xV!'})});
    const p=await r.json(), d=p.data||p;
    if(!d.access) return false;
    localStorage.setItem('access_token',d.access); localStorage.setItem('refresh_token',d.refresh);
    document.cookie='access_token='+d.access+'; path=/'; document.cookie='refresh_token='+d.refresh+'; path=/';
    localStorage.setItem('user_preferences', JSON.stringify({notifyOnError:false,notifyOnComplete:false}));
    return true;
  }`)
  check('isolated QA account login', login)
  await go('/settings/profile', '账户资料')
  check('all destinations preserved', await evaluate(`() => document.querySelectorAll('.settings-nav a').length === 10`))
  check('clean form save disabled', await evaluate(`() => [...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='保存更改').disabled`))
  await fill('邮箱', 'qa-profile@example.test')
  await fill('姓', '陈')
  await fill('名', '小流')
  await fill('个人简介', '个人中心端到端验证')
  await click('保存更改')
  await wait(`document.body.innerText.includes('个人资料已更新')`)
  const profile = await api('/auth/user/')
  check('profile save persists names and biography', profile.data.first_name === '小流' && profile.data.last_name === '陈' && profile.data.bio === '个人中心端到端验证')
  await go('/settings/profile', '账户资料')
  check('name round trip renders', await evaluate(`() => document.querySelector('input[autocomplete="given-name"]').value === '小流'`))
  await fill('名', '待撤销')
  await click('撤销更改')
  check('reset restores saved values', await evaluate(`() => document.querySelector('input[autocomplete="given-name"]').value === '小流'`))
  await fill('邮箱', 'invalid')
  await click('保存更改')
  await wait(`document.querySelector('.el-form-item__error')?.textContent.includes('有效的邮箱')`)
  check('invalid email blocked inline', (await api('/auth/user/')).data.email === 'qa-profile@example.test')
  await click('撤销更改')
  await fill('名', '未保存')
  await evaluate(`() => document.querySelector('a[href="/settings/preferences"]').click()`)
  await wait(`document.body.innerText.includes('继续编辑')`)
  await click('继续编辑')
  check('route guard preserves unsaved input', await evaluate(`() => location.pathname.endsWith('/profile') && document.querySelector('input[autocomplete="given-name"]').value==='未保存'`))
  await click('撤销更改')

  await fill('当前密码', 'Wrong-password')
  await fill('新密码', 'Next-profile-9x!')
  await fill('确认新密码', 'Next-profile-9x!')
  await click('更新密码')
  await wait(`document.querySelector('.security-section')?.innerText.includes('原密码错误')`)
  check('wrong password error stays beside field', await evaluate(`() => [...document.querySelectorAll('.security-section .el-form-item__error')].some(e=>e.textContent.includes('原密码错误'))`))
  await fill('当前密码', 'Profile-QA-7xV!')
  await fill('确认新密码', 'Mismatch-9x!')
  await click('更新密码')
  await wait(`document.querySelector('.security-section')?.innerText.includes('两次输入的密码不一致')`)
  check('password confirmation validation', true)
  await fill('确认新密码', 'Next-profile-9x!')
  await click('更新密码')
  await wait(`document.body.innerText.includes('密码修改成功')`)
  check('successful password update clears inputs', await evaluate(`() => [...document.querySelectorAll('.security-section input')].every(input=>!input.value)`))
  check('new password authenticates', await evaluate(`async () => { const r=await fetch('/api/v1/auth/login/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'profile_qa_20261015',password:'Next-profile-9x!'})});const p=await r.json();return Boolean((p.data||p).access); }`))

  await client.tool('upload_file', { uid: await uid('button','更换头像'), filePaths: ['E:/Flowly-now/.cache/profile-avatar-test.png'] })
  await wait(`document.body.innerText.includes('头像已更新')`)
  const avatar = await api('/auth/user/')
  check('avatar upload persisted and displayed', Boolean(avatar.data.avatar) && await evaluate(`() => Boolean(document.querySelector('.profile-identity img')?.complete && document.querySelector('.profile-identity img')?.naturalWidth)`))
  await client.tool('upload_file', { uid: await uid('button','更换头像'), filePaths: ['E:/Flowly-now/.cache/profile-avatar-oversize.png'] })
  await wait(`document.querySelector('.profile-identity')?.innerText.includes('大小不能超过')`)
  check('oversized avatar rejected', (await api('/auth/user/')).data.avatar === avatar.data.avatar)
  await client.tool('upload_file', { uid: await uid('button','更换头像'), filePaths: ['E:/Flowly-now/.cache/profile-avatar-invalid.png'] })
  await wait(`document.querySelector('.profile-identity')?.innerText.includes('有效的 JPG')`)
  check('fake image rejected without losing avatar', (await api('/auth/user/')).data.avatar === avatar.data.avatar)
  await click('移除头像')
  await wait(`document.body.innerText.includes('头像已移除')`)
  check('avatar removal persisted', !(await api('/auth/user/')).data.avatar)
  } else {
    const pages = resultText(await client.tool('list_pages'))
    const match = [...pages.matchAll(/^(\d+):.*http:\/\/localhost:5200\/settings\/(?:preferences|profile).*isolatedContext=isolated-context-\d+/gm)].at(-1)
    if (!match) throw new Error('Cannot find isolated QA context to resume')
    client.pageId = Number(match[1])
    await client.tool('select_page', { pageId: client.pageId })
  }

  if (!mobileOnly) {
  await go('/settings/preferences', '工作流编辑器')
  for (const [key,label] of [['autoSave','自动保存'],['snapToGrid','对齐网格'],['showMinimap','显示迷你地图']]) {
    check(`${label} accessible name`, Boolean(await uid('switch', label)))
    await evaluate(`() => { const input=document.getElementById(${JSON.stringify('preference-control-'+key)}); if(input.checked) document.querySelector('label[for="'+input.id+'"]').click(); }`)
  }
  await click('保存设置')
  check('preferences persist without replacing notifications', await evaluate(`() => {const p=JSON.parse(localStorage.getItem('user_preferences')); return p.autoSave===false&&p.snapToGrid===false&&p.showMinimap===false&&p.notifyOnError===false;}`))
  await go('/settings/preferences', '工作流编辑器')
  check('preferences restored on reload', await evaluate(`() => [...document.querySelectorAll('.preferences-settings [role="switch"]')].every(e=>e.getAttribute('aria-checked')==='false')`))
  for (const [theme, label] of [['dark','深色模式'],['light','浅色模式'],['pure-bw','纯黑白'],['high-contrast','高对比']]) {
    await evaluate(`async () => { const {useAppStore}=await import('/src/stores/app.js'); useAppStore().setTheme(${JSON.stringify(theme)}); }`)
    await wait(`document.documentElement.dataset.theme===${JSON.stringify(theme)}`)
    check(`${label} render`, await evaluate(`() => { const e=document.querySelector('.settings-content'); const s=getComputedStyle(e); return s.backgroundColor!=='rgba(0, 0, 0, 0)' && document.querySelector('h1').textContent==='偏好设置'; }`))
    await client.tool('take_screenshot', { filePath: `${output}/preferences-${theme}.png` })
  }
  await click('恢复默认')
  check('reset restores editor and theme defaults', await evaluate(`() => {const p=JSON.parse(localStorage.getItem('user_preferences'));return p.autoSave&&p.snapToGrid&&p.showMinimap&&p.notifyOnError===false&&document.documentElement.dataset.theme==='dark';}`))

  for (const [path,text] of [['credentials','添加凭证'],['integrations','第三方集成'],['api-doc','API 文档'],['desktop-agent','桌面'],['billing','订阅管理'],['data-export','数据管理'],['branding','品牌']]) {
    await go(`/settings/${path}`, text)
    check(`navigation /settings/${path}`, await evaluate(`() => location.pathname===${JSON.stringify('/settings/'+path)} && document.querySelectorAll('.settings-nav [aria-current="page"]').length===1 && Boolean(document.querySelector('.settings-content').innerText.trim())`))
  }
  await go('/settings/notifications','系统默认 SMTP')
  await evaluate(`() => localStorage.setItem('user_preferences','broken')`)
  await click('保存设置')
  check('notification save recovers corrupt storage', await evaluate(`() => {try{return typeof JSON.parse(localStorage.getItem('user_preferences')).notifyOnError==='boolean'}catch{return false}}`))
  }
  await go('/settings/profile','账户资料')
  for (const width of [1440, 1024, 768, 390]) {
    await client.tool('emulate', { viewport: `${width}x1000x1` })
    check(`profile layout ${width}px`, await evaluate(`() => {const r=document.querySelector('.settings-content').getBoundingClientRect();return r.right<=innerWidth+1 && r.width>0 && document.documentElement.scrollWidth<=innerWidth;}`))
    await client.tool('take_screenshot', { filePath: `${output}/profile-${width}.png` })
  }
  check('mobile exposes every destination', await evaluate(`() => getComputedStyle(document.querySelector('.settings-mobile-nav')).display!=='none' && document.querySelectorAll('.settings-mobile-nav option').length===10`))
  await client.tool('fill', { uid: await uid('combobox','个人中心设置'), value: '偏好设置' })
  await wait(`location.pathname.endsWith('/preferences')`)
  check('mobile navigation changes route', true)
  await client.tool('emulate', { viewport: '1440x1000x1' })
  await go('/settings/profile', '账户资料')
  await client.tool('take_screenshot', { filePath: `${output}/profile-final.png` })
} catch (error) {
  checks.push({ name: 'audit error', pass: false, detail: error.message })
  console.error(error.stack)
  process.exitCode = 1
} finally {
  writeFileSync(`${output}/browser-results.json`, JSON.stringify({ checks, passed: checks.filter(c=>c.pass).length, failed: checks.filter(c=>!c.pass).length }, null, 2))
  client.close()
}
