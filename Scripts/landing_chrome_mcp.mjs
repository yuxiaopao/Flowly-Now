import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { McpClient, evalPage, delay, FRONTEND_URL } from './chrome_mcp_client.mjs'

const target = new URL(FRONTEND_URL)
assert(['localhost', '127.0.0.1'].includes(target.hostname), 'Landing QA must use the isolated local frontend')
const output = path.resolve('Docs/verification/ai-team-20261031')
await mkdir(output, { recursive: true })
for (const url of [target.origin, 'http://127.0.0.1:9222/json/version']) {
  const response = await fetch(url, { signal: AbortSignal.timeout(8000) })
  assert.equal(response.ok, true, `Required QA service unavailable: ${url}`)
}

const client = new McpClient()
const checks = []
const screenshots = []
async function check(name, run) {
  try {
    const evidence = await run()
    checks.push({ name, passed: true, evidence })
    console.log(JSON.stringify({ check: name, passed: true, evidence }))
  } catch (error) {
    checks.push({ name, passed: false, error: error.message })
    console.log(JSON.stringify({ check: name, passed: false, error: error.message }))
  }
}
async function screenshot(name, fullPage = true) {
  const filePath = path.join(output, `${name}.png`)
  await client.tool('take_screenshot', { filePath, fullPage })
  screenshots.push(filePath)
}
async function waitForLanding() {
  for (let attempt = 0; attempt < 80; attempt++) {
    const ready = await evalPage(client, `() => Boolean(document.querySelector('.landing-page #hero-title'))`)
    if (ready) return
    await delay(100)
  }
  throw new Error('Landing did not render on the anonymous QA page')
}
async function tabState() {
  return evalPage(client, `() => {
    const tabs = [...document.querySelectorAll('.stage-tabs [role="tab"]')];
    const panels = [...document.querySelectorAll('.stage-panel[role="tabpanel"]')];
    return { tabs: tabs.map(tab => ({id:tab.id, selected:tab.getAttribute('aria-selected'), tabindex:tab.tabIndex, controls:tab.getAttribute('aria-controls')})),
      panels: panels.map(panel => ({id:panel.id, label:panel.getAttribute('aria-labelledby'), visible:getComputedStyle(panel).display !== 'none'})),
      focused: document.activeElement.id };
  }`)
}
async function assertTab(index, focused = true) {
  const state = await tabState()
  assert.equal(state.tabs.length, 4)
  assert.equal(state.panels.length, 4)
  state.tabs.forEach((tab, item) => {
    assert.equal(tab.selected, String(item === index))
    assert.equal(tab.tabindex, item === index ? 0 : -1)
    assert.equal(tab.controls, state.panels[item].id)
    assert.equal(state.panels[item].label, tab.id)
    assert.equal(state.panels[item].visible, item === index)
  })
  if (focused) assert.equal(state.focused, `delivery-tab-${index}`)
  return state
}
async function boundary(width) {
  const result = await evalPage(client, `() => ({width:innerWidth, documentWidth:document.documentElement.scrollWidth,
    bodyWidth:document.body.scrollWidth, horizontalOverflow:document.documentElement.scrollWidth > innerWidth + 1,
    heading:document.querySelector('#hero-title')?.textContent.trim(),
    primaryLinks:[...document.querySelectorAll('.landing-page a.primary')].map(link => ({text:link.textContent.trim(),path:new URL(link.href).pathname,visible:link.getBoundingClientRect().width > 0})),
    navigationLinks:[...document.querySelectorAll('.landing-page .nav-links a')].map(link=>({href:link.getAttribute('href'),targetExists:Boolean(document.querySelector(link.getAttribute('href')))}))})`)
  assert.equal(result.width, width)
  assert.equal(result.horizontalOverflow, false, JSON.stringify(result))
  assert.equal(result.primaryLinks.length, 2)
  assert(result.primaryLinks.every(link => link.visible && link.path === '/applications'))
  assert(result.navigationLinks.every(link => link.targetExists))
  return result
}

let failure = null
try {
  await client.initialize()
  const { tools } = await client.request('tools/list')
  assert(tools.some(tool => tool.name === 'navigate_page'), 'chrome-devtools navigate_page must be available')
  await client.tool('new_page', { url: 'about:blank' })
  // This QA origin must be anonymous; never read or print any existing credential.
  await client.tool('navigate_page', { type: 'url', url: `${target.origin}/`, timeout: 30000, initScript: `
    for (const key of ['access_token','refresh_token']) {
      localStorage.removeItem(key); sessionStorage.removeItem(key);
      document.cookie = key + '=; Max-Age=0; path=/';
    }
  ` })
  await waitForLanding()
  await client.tool('emulate', { viewport: '1440x1000x1' })
  await check('desktop boundary and navigation targets', () => boundary(1440))
  await screenshot('landing-desktop')

  await check('four-step tab roles, selection, keyboard and wraparound', async () => {
    await assertTab(0, false)
    await evalPage(client, `() => document.getElementById('delivery-tab-0').focus()`)
    const keys = [['ArrowRight', 1], ['ArrowRight', 2], ['End', 3], ['ArrowRight', 0], ['ArrowLeft', 3], ['Home', 0], ['End', 3]]
    for (const [key, index] of keys) {
      await client.tool('press_key', { key })
      await assertTab(index)
    }
    return { count: 4, keys: keys.map(([key, selected]) => ({ key, selected })) }
  })

  await check('native FAQ details support keyboard open and close', async () => {
    const count = await evalPage(client, `() => document.querySelectorAll('#faq details').length`)
    assert.equal(count, 6)
    for (let index = 0; index < count; index++) {
      await evalPage(client, `() => document.querySelectorAll('#faq summary')[${index}].focus()`)
      await client.tool('press_key', { key: 'Enter' })
      assert.equal(await evalPage(client, `() => document.querySelectorAll('#faq details')[${index}].open`), true)
      await client.tool('press_key', { key: 'Enter' })
      assert.equal(await evalPage(client, `() => document.querySelectorAll('#faq details')[${index}].open`), false)
    }
    return { count, keyboard: 'Enter toggles each native details element' }
  })

  await client.tool('emulate', { viewport: '390x844x1,mobile,touch' })
  await evalPage(client, `() => scrollTo(0,0)`)
  await check('390px mobile boundary and CTA visibility', () => boundary(390))
  await screenshot('landing-mobile')
  await screenshot('landing-mobile-viewport', false)

  await client.tool('emulate', { viewport: '1440x1000x1', prefersReducedMotion: 'reduce' })
  await evalPage(client, `() => scrollTo(0,0)`)
  await check('prefers-reduced-motion disables the primary transition', async () => {
    const result = await evalPage(client, `() => ({reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,
      deliveryTransition:getComputedStyle(document.documentElement).getPropertyValue('--delivery-transition').trim(),
      primaryDuration:getComputedStyle(document.querySelector('a.primary')).transitionDuration,
      runningAnimations:document.getAnimations().filter(animation=>animation.playState==='running' && animation.effect?.target?.closest?.('.landing-page')).length})`)
    assert.equal(result.reduced, true)
    assert.equal(result.deliveryTransition, '0ms')
    assert(result.primaryDuration.split(',').every(value => Number.parseFloat(value) === 0), JSON.stringify(result))
    assert.equal(result.runningAnimations, 0)
    return result
  })
  await screenshot('landing-reduced-motion', false)

  await check('primary CTA follows the real authentication route', async () => {
    await evalPage(client, `() => document.querySelector('a.primary').focus()`)
    await client.tool('press_key', { key: 'Enter' })
    let route
    for (let attempt = 0; attempt < 80; attempt++) {
      route = await evalPage(client, `() => ({path:location.pathname,redirect:new URL(location.href).searchParams.get('redirect'),loginForm:Boolean(document.querySelector('input[type="password"]'))})`)
      if (route.path === '/login' && route.loginForm) break
      await delay(100)
    }
    assert.equal(route.path, '/login', JSON.stringify(route))
    assert.equal(route.redirect, '/applications', JSON.stringify(route))
    assert.equal(route.loginForm, true)
    return route
  })

  await client.tool('emulate', { viewport: '1440x1000x1' })
  await client.tool('navigate_page', { type: 'url', url: `${target.origin}/`, timeout: 30000 })
  await waitForLanding()
  const failed = checks.filter(item => !item.passed)
  if (failed.length) failure = new Error(failed.map(item => `${item.name}: ${item.error}`).join('\n'))
} catch (error) {
  failure = error
  try { await screenshot('landing-failure', false) } catch { /* Preserve the original failure. */ }
} finally {
  const report = { browser: 'chrome-devtools-mcp', target: target.origin, timestamp: new Date().toISOString(),
    passed: failure === null, checks, screenshots, error: failure?.message || null }
  await writeFile(path.join(output, 'landing-results.json'), `${JSON.stringify(report, null, 2)}\n`)
  client.close()
}
if (failure) throw failure
console.log(JSON.stringify({ browser: 'chrome-devtools-mcp', passed: true, checks: checks.length, screenshots }))
