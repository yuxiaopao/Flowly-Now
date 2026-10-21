import { mkdirSync, writeFileSync, readFileSync } from 'node:fs'
import { McpClient, evalPage, resultText } from './chrome_mcp_client.mjs'

const output = 'E:/Flowly-now/Docs/verification/personal-center-layout-20261015'
const username = 'profile_layout_qa_20261015'
const password = 'Layout-QA-7xV!'
const client = new McpClient()
const resume = Boolean(process.env.PROFILE_LAYOUT_RESUME)
const finalPass = process.env.PROFILE_LAYOUT_RESUME === 'final'
const checks = resume ? JSON.parse(readFileSync(`${output}/browser-results.json`, 'utf8')).checks.filter(check=>check.pass) : []
mkdirSync(output, { recursive: true })
const evaluate = fn => evalPage(client, fn, 45000)
const callTool = client.tool.bind(client)
client.tool = (name, args = {}, timeout = 45000) => callTool(name, args, timeout)
function check(name, pass, detail) {
  checks.push({ name, pass: Boolean(pass), ...(detail === undefined ? {} : { detail }) })
  console.log(`${pass ? 'PASS' : 'FAIL'} ${name}`)
  if (!pass) throw new Error(`${name}: ${JSON.stringify(detail)}`)
}
async function wait(expression) {
  return evaluate(`async () => {const end=Date.now()+15000;while(Date.now()<end){if(${expression})return true;await new Promise(r=>setTimeout(r,100))}throw new Error('UI condition timed out')}`)
}
async function uid(role, label) {
  const snapshot = resultText(await client.tool('take_snapshot'))
  const line = snapshot.split('\n').find(line => line.includes(`${role} "${label}"`) || line.includes(`${role} "*${label}"`))
  if (!line) throw new Error(`Missing ${role}: ${label}`)
  return line.match(/uid=(\S+)/)[1]
}
async function click(label) { await client.tool('click', { uid: await uid('button', label) }) }
async function fill(label, value) { await client.tool('fill', { uid: await uid('textbox', label), value }) }
async function go(path, text) {
  await client.tool('navigate_page', { url: `http://localhost:5200${path}` })
  await client.tool('wait_for', { text: [text] })
  await wait(`document.querySelector('.settings-content') && getComputedStyle(document.querySelector('.main-content__page')).opacity==='1'`)
}
async function user() {
  return evaluate(`async () => {const r=await fetch('/api/v1/auth/user/',{headers:{Authorization:'Bearer '+localStorage.getItem('access_token')}});const p=await r.json();return p.data||p}`)
}
async function dimensions() {
  return evaluate(`() => {
    const page=document.querySelector('.settings-page'), content=document.querySelector('.settings-content'), section=document.querySelector('.profile-section'), footer=document.querySelector('.profile-section .form-footer');
    return { viewport:innerWidth, overflow:document.documentElement.scrollWidth>innerWidth, contentWidth:Math.round(content.getBoundingClientRect().width), pageWidth:Math.round(page.getBoundingClientRect().width), footerBottom:Math.round(footer.getBoundingClientRect().bottom), profileColumns:getComputedStyle(document.querySelector('.profile-columns')).gridTemplateColumns.split(' ').length, fieldColumns:getComputedStyle(document.querySelector('.profile-fields')).gridTemplateColumns.split(' ').length, navVisible:getComputedStyle(document.querySelector('.settings-nav')).display!=='none', fieldsFit:[...section.querySelectorAll('.el-input,.el-textarea')].every(e=>e.getBoundingClientRect().right<=section.getBoundingClientRect().right)};
  }`)
}

try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  check('Chrome DevTools navigate_page available', tools.some(tool=>tool.name==='navigate_page'))
  client.pageTools = new Set(tools.filter(tool=>tool.inputSchema?.properties?.pageId).map(tool=>tool.name))
  if (!resume) {
  await client.tool('new_page', { url:'http://localhost:5200/src/config/personalCenter.js', isolatedContext:'profile-layout-20261015', timeout:20000 })
  check('isolated test account login', await evaluate(`async () => {const r=await fetch('/api/v1/auth/login/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:${JSON.stringify(username)},password:${JSON.stringify(password)}})});const p=await r.json(),d=p.data||p;if(!d.access)return false;localStorage.setItem('access_token',d.access);localStorage.setItem('refresh_token',d.refresh);document.cookie='access_token='+d.access+'; path=/';document.cookie='refresh_token='+d.refresh+'; path=/';return true}`))
  await go('/settings/profile','修改密码')
  await client.tool('emulate',{viewport:'1440x900x1'})
  const desktop = await dimensions()
  check('full content width restored', desktop.contentWidth===desktop.pageWidth, desktop)
  check('save actions visible in desktop first screen', desktop.footerBottom<=900, desktop.footerBottom)
  check('desktop grouped navigation shows all ten destinations', await evaluate(`() => document.querySelectorAll('.settings-nav a').length===10 && document.querySelectorAll('.settings-nav [aria-current="page"]').length===1 && !document.querySelector('.settings-sidebar')`))
  check('password form initially collapsed', await evaluate(`() => getComputedStyle(document.querySelector('.password-details')).display==='none'`))
  await fill('名','布局验证')
  await click('保存更改')
  await wait(`document.body.innerText.includes('个人资料已更新')`)
  check('profile form still saves', (await user()).first_name==='布局验证')
  await go('/settings/profile','修改密码')
  check('saved names still render', await evaluate(`() => document.querySelector('input[autocomplete="given-name"]').value==='布局验证'`))
  await fill('邮箱','invalid')
  await click('保存更改')
  await wait(`document.querySelector('.el-form-item__error')?.textContent.includes('有效的邮箱')`)
  check('validation retained', (await user()).email==='profile-layout@example.test')
  await click('撤销更改')
  await fill('名','长'.repeat(150))
  check('long field values stay inside layout', (await dimensions()).fieldsFit)
  await click('撤销更改')
  await click('修改密码')
  check('expand focuses current password input', await evaluate(`() => document.activeElement?.autocomplete==='current-password' && document.querySelector('.security-section [aria-controls]').getAttribute('aria-expanded')==='true'`))
  await fill('当前密码','Wrong-password')
  await fill('新密码','Layout-next-9x!')
  await fill('确认新密码','different')
  await click('更新密码')
  await wait(`document.querySelector('.security-section')?.innerText.includes('两次输入的密码不一致')`)
  check('expanded password form validates confirmation', true)
  await fill('确认新密码','Layout-next-9x!')
  await click('更新密码')
  await wait(`document.querySelector('.security-section')?.innerText.includes('原密码错误')`)
  check('password field error remains inline', await evaluate(`() => [...document.querySelectorAll('.security-section .el-form-item__error')].some(e=>e.textContent.includes('原密码错误'))`))
  await click('收起密码表单')
  await click('修改密码')
  check('collapse preserves unfinished password input', await evaluate(`() => document.querySelector('input[autocomplete="current-password"]').value==='Wrong-password'`))
  await fill('当前密码',password)
  await click('更新密码')
  await wait(`document.body.innerText.includes('密码修改成功')`)
  check('successful password change collapses and returns focus', await evaluate(`() => getComputedStyle(document.querySelector('.password-details')).display==='none' && document.activeElement===document.querySelector('.security-section [aria-controls]') && [...document.querySelectorAll('.security-section input')].every(input=>!input.value)`))

  await client.tool('upload_file',{uid:await uid('button','更换头像'),filePaths:['E:/Flowly-now/.cache/profile-avatar-test.png']})
  await wait(`document.body.innerText.includes('头像已更新')`)
  check('moved avatar action still uploads', Boolean((await user()).avatar))
  await click('移除头像')
  await wait(`document.body.innerText.includes('头像已移除')`)
  check('avatar removal retained', !(await user()).avatar)
  } else {
    await client.tool('new_page',{url:'http://localhost:5200/src/config/personalCenter.js',isolatedContext:'profile-layout-final',timeout:20000})
    check('final verification account login',await evaluate(`async () => {const r=await fetch('/api/v1/auth/login/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:${JSON.stringify(username)},password:'Layout-next-9x!'})});const p=await r.json(),d=p.data||p;if(!d.access)return false;localStorage.setItem('access_token',d.access);localStorage.setItem('refresh_token',d.refresh);document.cookie='access_token='+d.access+'; path=/';document.cookie='refresh_token='+d.refresh+'; path=/';return true}`))
    await go('/settings/profile','修改密码')
  }
  await evaluate(`async () => {const {useAppStore}=await import('/src/stores/app.js');const store=useAppStore();[...store.toasts].forEach(toast=>store.removeToast(toast.id))}`)

  for (const width of finalPass ? [390,320] : [1920,1440,1280,1024,768,390,320]) {
    await client.tool('emulate',{viewport:`${width}x900x1`})
    await evaluate(`async () => {await new Promise(resolve=>setTimeout(resolve,350));return true}`)
    const metrics=await dimensions()
    check(`layout fits ${width}px`, !metrics.overflow && metrics.fieldsFit && metrics.contentWidth===metrics.pageWidth, metrics)
    if(width>=1280) check(`desktop nav fits ${width}px`,metrics.navVisible && await evaluate(`() => [...document.querySelectorAll('.settings-nav a')].every(e=>e.getBoundingClientRect().right<=document.querySelector('.settings-page').getBoundingClientRect().right)`))
    if(width<=1024) check(`narrow layout stacks ${width}px`,!metrics.navVisible && metrics.profileColumns===1)
    await client.tool('take_screenshot',{filePath:`${output}/profile-${width}.png`})
  }
  if(!finalPass) {
  await fill('名','保留草稿')
  await client.tool('fill',{uid:await uid('combobox','个人中心设置'),value:'偏好设置'})
  await wait(`document.body.innerText.includes('继续编辑')`)
  await click('继续编辑')
  check('cancelled mobile navigation restores selection and draft',await evaluate(`() => location.pathname.endsWith('/profile') && document.querySelector('.settings-mobile-nav').value==='/settings/profile' && document.querySelector('input[autocomplete="given-name"]').value==='保留草稿'`))
  await click('撤销更改')
  await wait(`document.querySelector('.profile-section .save-status').textContent==='资料已同步'`)
  }
  await wait(`document.querySelector('.profile-section .save-status').textContent==='资料已同步'`)
  await client.tool('fill',{uid:await uid('combobox','个人中心设置'),value:'偏好设置'})
  await wait(`location.pathname.endsWith('/preferences')`)
  check('mobile navigation works',true)

  await client.tool('emulate',{viewport:'1440x900x1'})
  for(const [path,text] of [['profile','修改密码'],['preferences','工作流编辑器'],['notifications','系统默认 SMTP'],['credentials','添加凭证'],['integrations','第三方集成'],['api-doc','API 文档'],['desktop-agent','桌面'],['billing','订阅管理'],['data-export','数据管理'],['branding','品牌']]) {
    await go(`/settings/${path}`,text)
    check(`destination ${path}`,await evaluate(`() => document.querySelectorAll('.settings-nav [aria-current="page"]').length===1 && document.querySelector('.settings-nav [aria-current="page"]').getAttribute('href')===${JSON.stringify('/settings/'+path)} && document.querySelector('.settings-content').getBoundingClientRect().width===document.querySelector('.settings-page').getBoundingClientRect().width && document.documentElement.scrollWidth<=innerWidth`))
  }
  await go('/settings/profile','修改密码')
  for(const theme of ['dark','light','pure-bw','high-contrast']) {
    await evaluate(`async () => {const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme(${JSON.stringify(theme)})}`)
    await client.tool('take_screenshot',{filePath:`${output}/profile-${theme}.png`})
    check(`${theme} theme preserves layout`,!(await dimensions()).overflow)
  }
  await evaluate(`async () => {const {useAppStore}=await import('/src/stores/app.js');useAppStore().setTheme('dark')}`)
  await client.tool('take_screenshot',{filePath:`${output}/profile-final.png`})
} catch(error) {
  checks.push({name:'audit error',pass:false,detail:error.message})
  console.error(error.stack)
  process.exitCode=1
} finally {
  const uniqueChecks=[...new Map(checks.map(check=>[check.name,check])).values()]
  writeFileSync(`${output}/browser-results.json`,JSON.stringify({checks:uniqueChecks,passed:uniqueChecks.filter(c=>c.pass).length,failed:uniqueChecks.filter(c=>!c.pass).length},null,2))
  client.close()
}
