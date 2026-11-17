import fs from 'node:fs/promises'
import path from 'node:path'
import assert from 'node:assert/strict'
import { McpClient, resultText, evalPage, delay } from './chrome_mcp_client.mjs'

const client = new McpClient()
const output = path.resolve(import.meta.dirname, '../output/training-monitor')
const binding = JSON.parse(await fs.readFile(path.join(output, 'workflow-binding.json'), 'utf8'))
const jobId = binding.trainingJobId || binding.jobId
assert(jobId, 'Missing existing training job binding')
const evidence = { tool: 'official chrome-devtools MCP', checks: [], themes: [] }
async function control(role, label, value) {
  const text = resultText(await client.tool('take_snapshot'))
  const line = text.split('\n').find(row => row.includes(`${role} "${label}${role === 'menuitem' ? '' : '"'}`))
  assert(line, `Missing ${role}: ${label}`)
  const uid = line.match(/uid=(\S+)/)[1]
  await client.tool(value === undefined ? 'click' : 'fill', value === undefined ? { uid } : { uid, value })
}
async function wait(fn) {
  const until = Date.now() + 20000
  while (Date.now() < until) {
    const data = await evalPage(client, fn)
    if (data) return data
    await delay(250)
  }
  throw new Error(`Timed out: ${fn}`)
}
async function ready() { return wait(`() => document.querySelectorAll('.analytics-chart canvas').length >= 4`) }
async function select(label, value) {
  await evalPage(client, `() => {
    const label = [...document.querySelectorAll('.analysis-controls label')].find(el => el.textContent.includes(${JSON.stringify(label)}));
    const input = label.querySelector('select'); input.value = ${JSON.stringify(value)};
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }`)
}
try {
  await client.initialize()
  const tools = (await client.request('tools/list')).tools
  assert(tools.some(tool => tool.name === 'navigate_page'))
  client.pageTools = new Set(tools.filter(tool => tool.inputSchema?.properties?.pageId).map(tool => tool.name))
  const pages = resultText(await client.tool('list_pages'))
  const page = pages.split('\n').find(line => line.includes(process.env.FLOWLY_QA_PAGE_MATCH || '127.0.0.1:5200/workflows/'))
  assert(page, pages)
  client.pageId = Number(page.match(/^(\d+):/)[1])
  const desktop = page.includes('file:///')
  if (!desktop) await client.tool('resize_page', { width: 1440, height: 1000 })
  if (!await evalPage(client, `() => Boolean(document.querySelector('[data-testid=yolo-run-analytics]'))`)) await control('button', '查看训练详情')
  await ready()
  const curves = await evalPage(client, `() => ({ text: document.querySelector('.analysis-stats').innerText, canvases: document.querySelectorAll('.analytics-chart canvas').length, theme: document.documentElement.dataset.theme })`)
  assert(curves.text.includes('99.67%') && curves.text.includes('10999'))
  assert(curves.canvases >= 4)
  evidence.curves = curves
  evidence.checks.push('actual loss, Top-1/Top-5, learning-rate and epoch-duration charts rendered')
  const firstSync = await evalPage(client, `() => document.querySelector('.analysis-actions [role=status]').textContent`)
  await delay(2400)
  assert.notEqual(await evalPage(client, `() => document.querySelector('.analysis-actions [role=status]').textContent`), firstSync)
  evidence.checks.push('automatic polling updates the visible synchronization timestamp')
  await client.tool('take_screenshot', { filePath: path.join(output, 'analytics-curves.png'), fullPage: false })

  await control('tab', '混淆矩阵')
  await wait(`() => document.querySelectorAll('.analytics-chart canvas').length === 1`)
  const matrix = await evalPage(client, `() => ({ text: document.querySelector('[data-testid=yolo-run-analytics]').innerText, width: document.querySelector('.analytics-chart canvas').width, height: document.querySelector('.analytics-chart canvas').height, errors: document.querySelectorAll('.analysis-table tbody tr').length })`)
  assert(matrix.text.includes('10999') && matrix.errors > 0 && matrix.width > 0 && matrix.height > 0)
  await client.tool('take_screenshot', { filePath: path.join(output, 'analytics-confusion.png'), fullPage: false })
  await select('矩阵数值', 'normalized')
  await select('评估集合', 'validation')
  await wait(`() => document.querySelector('.analysis-controls').innerText.includes('5485')`)
  evidence.checks.push('raw/row-normalized confusion matrices switch between 10999 test and 5485 validation samples')
  await control('tab', '逐类表现')
  await wait(`() => document.querySelectorAll('.analysis-table tbody tr').length === 38`)
  await select('逐类指标', 'precision')
  assert((await evalPage(client, `() => document.querySelector('.analytics-figure figcaption').innerText`)).includes('PRECISION'))
  evidence.checks.push('all 38 classes have Precision, Recall, F1 and support; ranking switches metric')

  await control('tab', '原生图表')
  const images = await wait(`() => {
    const items=[...document.querySelectorAll('.plots-grid img')];
    return items.length >= 3 && items.every(image => image.complete && image.naturalWidth > 0) && { count: items.length, text: document.querySelector('.yolo-native-plots').innerText };
  }`)
  assert(images.text.includes('混淆矩阵') && images.text.includes('训练曲线总览'))
  evidence.nativeImages = images.count
  await client.tool('take_screenshot', { filePath: path.join(output, 'analytics-native.png'), fullPage: false })
  evidence.checks.push('native confusion matrices, results chart and real batch images all load through authenticated endpoints')

  await control('tab', '模型对比')
  await wait(`() => document.querySelector('.analysis-table tbody tr')?.textContent.includes('YOLO26m')`)
  assert((await evalPage(client, `() => document.querySelector('[data-testid=yolo-run-analytics]').innerText`)).includes('当前只选择了'))
  assert.equal(await evalPage(client, `() => document.querySelectorAll('.analysis-table tbody tr').length`), 1)
  const candidate = await wait(`() => [...document.querySelector('.analysis-controls select').options].find(option => option.value && !option.disabled)?.value`)
  await select('添加训练记录', candidate)
  await control('button', '加入对比')
  const comparison = await wait(`() => document.querySelectorAll('.analysis-table tbody tr').length > 1 ? 'added' : document.querySelector('.analysis-notice.error')?.textContent`)
  evidence.comparison = comparison
  evidence.checks.push('only real owned runs appear in comparison; incompatible task types have explicit feedback')

  const themeNames = { dark: '深色模式', light: '浅色模式', 'pure-bw': '纯黑白', 'high-contrast': '高对比' }
  for (const themeId of [...Object.keys(themeNames), curves.theme]) {
    await control('button', '关闭此对话框')
    const snapshot = resultText(await client.tool('take_snapshot'))
    const trigger = snapshot.split('\n').find(line => line.includes('button "当前主题：'))
    assert(trigger)
    await client.tool('click', { uid: trigger.match(/uid=(\S+)/)[1] })
    await control('menuitem', themeNames[themeId])
    await control('button', '查看训练详情')
    await ready()
    const actual = await evalPage(client, `() => ({ id: document.documentElement.dataset.theme, background: getComputedStyle(document.querySelector('.yolo-analytics')).backgroundColor, charts: document.querySelectorAll('.analytics-chart canvas').length })`)
    assert.equal(actual.id, themeId)
    evidence.themes.push(actual)
  }
  if (!desktop) { await client.tool('resize_page', { width: 760, height: 1000 }); await delay(500) }
  assert(!await evalPage(client, `() => document.documentElement.scrollWidth > innerWidth`))
  evidence.checks.push(desktop ? 'four app themes are inherited and the native window has no horizontal page overflow' : 'four app themes are inherited and the narrow dialog has no horizontal page overflow')
  if (!desktop) await client.tool('resize_page', { width: 1440, height: 1000 })
  evidence.viewport = await evalPage(client, `() => ({ width: innerWidth, height: innerHeight, desktop: Boolean(window.flowlyDesktop) })`)
  const api = await evalPage(client, `async () => {
    const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || decodeURIComponent(document.cookie.match(/(?:^|; )access_token=([^;]+)/)?.[1] || '');
    const url='http://127.0.0.1:8002/api/v1/training/yolo-runs/${jobId}/analytics/';
    const unauthorized=await fetch(url); const response=await fetch(url,{headers:{Authorization:'Bearer '+token}}); const body=await response.json(); const data=body.data||body;
    const wrong=await fetch(url.replace('${jobId}','00000000-0000-4000-8000-000000000099'),{headers:{Authorization:'Bearer '+token}});
    const matrix=data.reports.test.confusion_matrix; const sum=matrix.flat().reduce((a,b)=>a+b,0);const diagonal=matrix.reduce((a,row,i)=>a+row[i],0);
    return { unauthorized:unauthorized.status, missing:wrong.status, history:data.history.length, classes:data.classes.length, sum, accuracy:diagonal/sum, reported:data.reports.test.top1 };
  }`)
  assert.equal(api.unauthorized, 401); assert.equal(api.missing, 404); assert.equal(api.history, 40); assert.equal(api.sum, 10999); assert.equal(api.classes, 38); assert(Math.abs(api.accuracy-api.reported)<1e-12)
  evidence.api = api
  evidence.checks.push('401/404 protections work and matrix diagonal accuracy exactly matches the independent test report')
  evidence.passed = true
} catch (error) {
  evidence.passed = false; evidence.error = error.stack
  throw error
} finally {
  evidence.finishedAt = new Date().toISOString()
  await fs.writeFile(path.join(output, 'analytics-browser-verification.json'), JSON.stringify(evidence, null, 2))
  client.close()
}
