import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
import { McpClient, evalPage, resultText, delay } from './chrome_mcp_client.mjs'

const root = path.resolve(import.meta.dirname, '..')
const output = path.join(root, 'output/training-monitor')
process.env.CHROME_MCP_BROWSER_URL ||= 'http://127.0.0.1:9223'
const client = new McpClient()
const evidence = { tool: 'official chrome-devtools MCP', startedAt: new Date().toISOString(), checks: [] }
const binding = JSON.parse(await fs.readFile(path.join(output, 'workflow-binding.json'), 'utf8'))

async function clickText(label) {
  let line
  const deadline = Date.now() + 15000
  while (!line && Date.now() < deadline) {
    const snapshot = resultText(await client.tool('take_snapshot', {}))
    line = snapshot.split('\n').find(row => row.includes(`"${label}"`) && (row.includes('button') || row.includes('tab ')))
    if (!line) await delay(300)
  }
  assert(line, `UI control not found: ${label}`)
  const uid = line.match(/uid=(\S+)/)?.[1]
  assert(uid)
  await client.tool('click', { uid })
}

async function main() {
  await fs.mkdir(output, { recursive: true })
  await client.initialize()
  const tools = (await client.request('tools/list')).tools
  assert(tools.some(tool => tool.name === 'navigate_page'))
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  const pages = resultText(await client.tool('list_pages', {}))
  const page = pages.split('\n').find(line => line.includes('/renderer/index.html') || line.includes(':5200/'))
  assert(page, `Training monitor window not found: ${pages}`)
  client.pageId = Number(page.match(/^(\d+):/)[1])
  const editorUrl = await evalPage(client, `() => location.href.split('#')[0] + '#/workflows/${binding.workflowId}/edit'`)
  await client.tool('navigate_page', { type: 'url', url: editorUrl, timeout: 20000 })
  await delay(1800)
  await clickText('查看训练详情')
  await delay(1200)
  const first = await evalPage(client, `async () => {
    const data = await window.flowlyDesktop.training.monitor.snapshot();
    return { title: document.title, epoch: data.completedEpochs, batch: data.activeBatch?.batch,
      stage: data.stage, observedAt: data.observedAt, classes: data.classes.length, viewer: data.viewer,
      history: data.history.length, parameters: data.transfer.total_parameters,
      chartCount: document.querySelector('[data-testid=training-live]').shadowRoot.querySelectorAll('.chart svg').length,
      visible: !document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('workspace').hidden,
      error: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('error').hidden ? null : document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('error').textContent,
      connection: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('connection').textContent };
  }`)
  assert(first.visible && first.chartCount === 2 && first.classes === 38 && !first.error, JSON.stringify(first))
  assert(first.viewer?.username && first.epoch === 40)
  const navigation = await evalPage(client, `() => ({
    path: location.hash || location.pathname,
    editor: Boolean(document.querySelector('.vue-flow')),
    standaloneLink: Boolean(document.querySelector('a[href$="/training/live"]')),
    nodeDialog: document.querySelector('.yolo-run-dialog')?.getAttribute('aria-label')
  })`)
  assert(navigation.editor && navigation.path.includes(binding.workflowId) && !navigation.standaloneLink)
  evidence.navigation = navigation
  evidence.checks.push('monitor opens from the bound YOLO workflow node with no separate menu page')
  evidence.first = first
  evidence.checks.push('real training state, 38 classes and two metric charts visible')
  await delay(6500)
  const second = await evalPage(client, `async () => {
    const data = await window.flowlyDesktop.training.monitor.snapshot();
    return { epoch: data.completedEpochs, batch: data.activeBatch?.batch,
      observedAt: data.observedAt, connection: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('connection').textContent };
  }`)
  assert(second.observedAt > first.observedAt, 'Snapshot did not refresh')
  evidence.second = second
  evidence.checks.push('automatic snapshot refresh observed across multiple polling intervals')
  await clickText('网络与参数')
  const network = await evalPage(client, `() => ({
    rows: document.querySelector('[data-testid=training-live]').shadowRoot.querySelectorAll('#network-table tbody tr').length,
    text: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('network-summary').innerText,
    active: !document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('network').hidden
  })`)
  assert(network.active && network.rows === 12)
  evidence.network = network
  evidence.checks.push('actual 12-block network and parameter inventory visible')
  await clickText('分类与数据')
  let snapshot = resultText(await client.tool('take_snapshot', {}))
  const cropLine = snapshot.split('\n').find(line => line.includes('combobox') && line.includes('作物'))
  assert(cropLine)
  await client.tool('fill', { uid: cropLine.match(/uid=(\S+)/)[1], value: '苹果' })
  const filtered = await evalPage(client, `() => ({
    rows: document.querySelector('[data-testid=training-live]').shadowRoot.querySelectorAll('#class-table tbody tr').length,
    content: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('class-table').innerText,
    count: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('class-count').textContent
  })`)
  assert.equal(filtered.rows, 4)
  assert(filtered.content.includes('苹果健康') && filtered.content.includes('黑星病'))
  evidence.checks.push('crop filtering shows four correct Apple classes with sample counts')
  snapshot = resultText(await client.tool('take_snapshot', {}))
  const searchLine = snapshot.split('\n').find(line => /textbox|searchbox/.test(line) && line.includes('搜索类别'))
  assert(searchLine)
  await client.tool('fill', { uid: searchLine.match(/uid=(\S+)/)[1], value: '不存在的类别' })
  const empty = await evalPage(client, `() => document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('class-table').innerText`)
  assert(empty.includes('没有符合筛选条件'))
  await client.tool('fill', { uid: searchLine.match(/uid=(\S+)/)[1], value: '' })
  evidence.checks.push('class search and empty state work')
  await clickText('评估与导出')
  const exports = await evalPage(client, `() => ({
    files: document.querySelector('[data-testid=training-live]').shadowRoot.querySelectorAll('.artifact').length,
    disabled: document.querySelector('[data-testid=training-live]').shadowRoot.querySelectorAll('[data-artifact][disabled]').length,
    content: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('evaluation-summary').innerText
  })`)
  assert.equal(exports.files, 9)
  evidence.exports = exports
  assert.equal(exports.disabled, 0)
  evidence.checks.push('final model, ONNX and complete evaluation artifacts are available')
  await clickText('实时日志')
  const logs = await evalPage(client, `() => ({
    content: document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('log-output').textContent,
    visible: !document.querySelector('[data-testid=training-live]').shadowRoot.getElementById('logs').hidden
  })`)
  assert(logs.visible && logs.content.length > 30)
  evidence.checks.push('real live training log visible')
  await clickText('实时概览')
  const theme = await evalPage(client, `() => {
    const host = document.querySelector('[data-testid=training-live]');
    return { panel: host.dataset.theme, system: document.documentElement.dataset.theme,
      background: getComputedStyle(host).backgroundColor,
      globalBackground: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim(),
      independentSwitch: Boolean(host.shadowRoot.getElementById('theme')) };
  }`)
  assert.equal(theme.panel, theme.system)
  assert(!theme.independentSwitch)
  evidence.theme = theme
  evidence.themes = []
  const themes = { dark: '深色模式', light: '浅色模式', 'pure-bw': '纯黑白', 'high-contrast': '高对比' }
  for (const themeId of [...Object.keys(themes), theme.system]) {
    await evalPage(client, `() => document.querySelector('.yolo-run-dialog .el-dialog__headerbtn').click()`)
    await delay(300)
    let snapshot = resultText(await client.tool('take_snapshot'))
    const trigger = snapshot.split('\n').find(row => row.includes('button "当前主题：'))
    assert(trigger)
    await client.tool('click', { uid: trigger.match(/uid=(\S+)/)[1] })
    snapshot = resultText(await client.tool('take_snapshot'))
    const item = snapshot.split('\n').find(row => row.includes(`menuitem "${themes[themeId]}`))
    assert(item, `Missing application theme: ${themeId}`)
    await client.tool('click', { uid: item.match(/uid=(\S+)/)[1] })
    await clickText('查看训练详情')
    await delay(800)
    const actual = await evalPage(client, `() => {
      const host = document.querySelector('[data-testid=training-live]');
      return { panel: host.dataset.theme, system: document.documentElement.dataset.theme,
        background: getComputedStyle(host).backgroundColor,
        text: getComputedStyle(host).color,
        globalBackground: getComputedStyle(document.documentElement).getPropertyValue('--bg-primary').trim() };
    }`)
    assert.equal(actual.system, themeId)
    assert.equal(actual.panel, themeId)
    evidence.themes.push(actual)
  }
  assert(new Set(evidence.themes.map(item => item.background)).size > 1)
  evidence.checks.push('node monitor inherits the application theme and has no independent theme switch')
  const overflow = await evalPage(client, `() => document.documentElement.scrollWidth > window.innerWidth`)
  assert(!overflow, 'Unexpected horizontal page overflow')
  const consoleMessages = resultText(await client.tool('list_console_messages', { types: ['error', 'warn'], includePreservedMessages: false }))
  evidence.consoleMessages = consoleMessages
  assert(consoleMessages.includes('no console messages'), consoleMessages)
  evidence.checks.push('no console errors or warnings and no horizontal overflow')
  await fs.writeFile(path.join(output, 'latest-snapshot.txt'), resultText(await client.tool('take_snapshot', {})))
  try {
    await client.tool('take_screenshot', { filePath: path.join(output, 'overview.png'), fullPage: false }, 25000)
    evidence.screenshot = 'overview.png'
  } catch (error) {
    evidence.screenshotError = error.message
  }
  evidence.passed = true
  evidence.finishedAt = new Date().toISOString()
  await fs.writeFile(path.join(output, 'browser-verification.json'), JSON.stringify(evidence, null, 2))
  console.log(JSON.stringify(evidence, null, 2))
}

try {
  await main()
} catch (error) {
  evidence.passed = false
  evidence.error = error.stack
  await fs.mkdir(output, { recursive: true })
  await fs.writeFile(path.join(output, 'browser-verification.json'), JSON.stringify(evidence, null, 2))
  console.error(error)
  process.exitCode = 1
} finally {
  client.close()
}
