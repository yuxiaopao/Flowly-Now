import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { McpClient, evalPage, login, FRONTEND_URL, BACKEND_URL } from './chrome_mcp_client.mjs'

if (process.env.FLOWLY_ISOLATED_QA !== '1') throw new Error('Only run against the explicitly isolated QA backend')
for (const value of [FRONTEND_URL, BACKEND_URL]) {
  if (!['127.0.0.1', 'localhost'].includes(new URL(value).hostname)) throw new Error('QA hosts must be loopback')
}
const output = path.resolve(process.env.FLOWLY_QA_ARTIFACTS || 'Docs/verification/ai-team-20261101')
const adminPassword = process.env.FLOWLY_E2E_ADMIN_PASSWORD || 'FixtureAdmin123!'
const browserUrl = process.env.CHROME_MCP_BROWSER_URL || 'http://127.0.0.1:9222'
const marker = await fetch(`${BACKEND_URL}/api/v1/__isolated-qa__/`).then(response => response.json())
assert.equal(marker.isolated, true, 'Refusing to mutate a backend without its isolated marker')
assert(marker.model_configuration?.gateway?.models?.normal, 'Missing explicit model configuration fixtures')
assert((await fetch(FRONTEND_URL)).ok, 'Frontend service must be reachable before MCP')
assert((await fetch(`${browserUrl}/json/version`)).ok, 'The isolated Chrome debugging port must already be listening')
const fixtures = marker.model_configuration
assert.equal(new URL(fixtures.gateway.base_url).hostname, '127.0.0.1')
const client = new McpClient(), checks = []
const page = fn => evalPage(client, typeof fn === 'string' ? fn : fn.toString(), 60000)
async function check(name, fn) {
  const value = await fn()
  assert.equal(value.ok, true, `${name}: ${JSON.stringify(value)}`)
  checks.push({ name, ...value })
  console.log(JSON.stringify({ name, ...value }))
}
async function initializePage() {
  await page(`() => {
    window.__modelFixtures = ${JSON.stringify(fixtures)};
    window.__modelVisible = node => Boolean(node?.getClientRects().length) && getComputedStyle(node).visibility !== 'hidden';
    window.__modelWait = async (predicate, label = 'model configuration UI') => {
      for (let count = 0; count < 450; count++) { if (await predicate()) return; await new Promise(resolve => setTimeout(resolve, 100)); }
      throw new Error('Timed out waiting for ' + label);
    };
    window.__modelText = node => node.textContent.replace(/\\s+/g, ' ').trim();
    window.__modelButton = (root, text) => [...root.querySelectorAll('button')].find(node => __modelVisible(node) && __modelText(node) === text);
    window.__modelDialog = title => [...document.querySelectorAll('.el-dialog')].findLast(node => __modelVisible(node) && node.querySelector('.el-dialog__title')?.textContent.trim() === title);
    window.__modelField = (root, label) => [...root.querySelectorAll('.el-form-item')].find(node => node.querySelector('.el-form-item__label')?.textContent.trim() === label);
    window.__modelInput = (node, value) => {
      if (!node) throw new Error('Missing real input');
      node.value = value; node.dispatchEvent(new Event('input', { bubbles: true })); node.dispatchEvent(new Event('change', { bubbles: true }));
    };
    window.__modelSelect = async (field, label) => {
      if (!field) throw new Error('Missing select field');
      field.querySelector('.el-select__wrapper').click();
      let option;
      await __modelWait(() => option = [...document.querySelectorAll('.el-select-dropdown__item')].find(node => __modelVisible(node) && __modelText(node) === label), 'actual select option ' + label);
      if (option.classList.contains('is-disabled')) throw new Error('Option is disabled: ' + label);
      option.click();
      await new Promise(resolve => setTimeout(resolve, 50));
    };
    window.__modelCall = async (resource, options = {}) => {
      const response = await fetch('/api/v1/' + resource, { ...options, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + localStorage.getItem('access_token'), ...(options.headers || {}) } });
      const json = await response.json(); return { status: response.status, data: json.data ?? json };
    };
    window.__modelCard = name => [...document.querySelectorAll('.model-card')].find(node => node.querySelector('.model-name')?.textContent.trim() === name);
    window.__modelOpenMenu = async (name, text) => {
      const card = __modelCard(name); if (!card) throw new Error('Missing actual model card ' + name);
      card.querySelector('.model-header button').click();
      let item;
      await __modelWait(() => item = [...document.querySelectorAll('.el-dropdown-menu__item')].find(node => __modelVisible(node) && __modelText(node) === text), 'model menu ' + text);
      return item;
    };
    window.__modelRouter = () => document.querySelector('#app').__vue_app__.config.globalProperties.$router;
    window.__modelRows = result => result.data.results || (Array.isArray(result.data) ? result.data : Object.values(result.data));
    return true;
  }`)
}

try {
  await client.initialize()
  const inventory = await client.request('tools/list')
  assert(inventory.tools.some(tool => tool.name === 'navigate_page'), 'chrome-devtools navigate_page must be available')
  await login(client, { entryPath: '/api/health/' })
  await client.tool('emulate', { viewport: '1440x1050x1', prefersReducedMotion: 'reduce' })
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/models` })
  await initializePage()
  await check('ordinary user adds a real masked personal model credential through the form', () => page(async () => {
    await __modelWait(() => __modelButton(document, '添加 API Key'))
    window.__modelQa = { secret: 'qa-dom-' + crypto.randomUUID(), keyName: 'QA DOM credential ' + Date.now() }
    __modelButton(document, '添加 API Key').click()
    await __modelWait(() => __modelDialog('添加 API Key'))
    const dialog = __modelDialog('添加 API Key')
    __modelInput(__modelField(dialog, '名称').querySelector('input'), __modelQa.keyName)
    await __modelSelect(__modelField(dialog, '服务商'), '自定义')
    __modelInput(__modelField(dialog, 'API Key').querySelector('input'), __modelQa.secret)
    __modelInput(__modelField(dialog, 'API Endpoint').querySelector('input'), __modelFixtures.gateway.base_url)
    __modelInput(__modelField(dialog, '验证模型（选填）').querySelector('input'), __modelFixtures.gateway.model_ids.normal)
    __modelButton(dialog, '保存').click()
    await __modelWait(() => !__modelDialog('添加 API Key'))
    let key
    await __modelWait(async () => key = __modelRows(await __modelCall('gateway/api-keys/?page_size=100')).find(row => row.name === __modelQa.keyName))
    __modelQa.keyId = key.id
    const card = [...document.querySelectorAll('.api-key-card')].find(node => node.querySelector('.key-name')?.textContent === __modelQa.keyName)
    return { ok: Boolean(card) && card.querySelector('code').textContent === key.masked_key && !JSON.stringify(key).includes(__modelQa.secret) && !Object.hasOwn(key, 'api_key'), serverMaskOnly: true }
  }))
  await check('editing with a blank secret preserves the stored credential and explicit model probe succeeds', () => page(async () => {
    let card = [...document.querySelectorAll('.api-key-card')].find(node => node.querySelector('.key-name')?.textContent === __modelQa.keyName)
    const before = (await __modelCall(`gateway/api-keys/${__modelQa.keyId}/`)).data
    __modelButton(card, '编辑').click()
    await __modelWait(() => __modelDialog('编辑 API Key'))
    const dialog = __modelDialog('编辑 API Key'), secret = __modelField(dialog, 'API Key').querySelector('input')
    if (secret.value !== '') return { ok: false, stage: 'edit secret must be empty' }
    __modelQa.keyName += ' edited'
    __modelInput(__modelField(dialog, '名称').querySelector('input'), __modelQa.keyName)
    __modelButton(dialog, '保存').click()
    await __modelWait(() => !__modelDialog('编辑 API Key'))
    await __modelWait(() => card = [...document.querySelectorAll('.api-key-card')].find(node => node.querySelector('.key-name')?.textContent === __modelQa.keyName))
    __modelButton(card, '验证').click()
    let after
    await __modelWait(async () => { after = (await __modelCall(`gateway/api-keys/${__modelQa.keyId}/`)).data; return after.last_used_at })
    return { ok: before.masked_key === after.masked_key && after.model === __modelFixtures.gateway.model_ids.normal && !JSON.stringify(after).includes(__modelQa.secret), explicitModel: after.model, blankSecretPreserved: true }
  }))
  await check('model metadata is searchable and an ordinary user cannot change catalog defaults', () => page(async () => {
    document.querySelector('#tab-models').click()
    await __modelWait(() => __modelCard('QA Normal Model'))
    const card = __modelCard('QA Normal Model')
    const item = await __modelOpenMenu('QA Normal Model', '设为目录默认')
    const disabled = item.getAttribute('aria-disabled') === 'true' || item.classList.contains('is-disabled')
    document.body.click()
    const forbidden = await __modelCall(`gateway/models/${__modelFixtures.gateway.models.normal}/set_default/`, { method: 'POST', body: JSON.stringify({ is_default: true }) })
    return { ok: disabled && forbidden.status === 403 && card.textContent.includes(__modelFixtures.gateway.model_ids.normal) && document.body.innerText.includes('目录默认'), uiDisabled: disabled, serverStatus: forbidden.status }
  }))
  for (const [kind, name, expected] of [
    ['normal', 'QA Normal Model', 'Isolated provider connection confirmed.'],
    ['empty', 'QA Empty Model', '错误:'],
    ['error', 'QA Error Model', 'Isolated provider fixture error'],
  ]) {
    await check(`real model dialog reports ${kind} HTTP-provider result honestly`, () => page(`async () => {
      const item = await __modelOpenMenu(${JSON.stringify(name)}, '测试连接'); item.click();
      await __modelWait(() => __modelDialog('测试模型'));
      const dialog = __modelDialog('测试模型');
      __modelInput(dialog.querySelector('textarea'), 'Isolated browser transport probe');
      __modelButton(dialog, '发送测试').click();
      await __modelWait(() => dialog.querySelector('.result-content')?.textContent.includes(${JSON.stringify(expected)}), 'actual provider result');
      const text = dialog.querySelector('.result-content').textContent.trim();
      const ok = text.includes(${JSON.stringify(expected)}) && !text.includes(__modelQa.secret);
      __modelButton(dialog, '关闭').click(); await __modelWait(() => !__modelDialog('测试模型'));
      return { ok, kind: ${JSON.stringify(kind)}, containsSecret: false };
    }`))
  }
  await mkdir(output, { recursive: true })
  await client.tool('take_screenshot', { filePath: path.join(output, 'models-ordinary.png'), fullPage: true })

  await check('actual Editor replaces legacy model and training-dataset references with registered resources', () => page(async () => {
    await __modelRouter().push(`/workflows/${__modelFixtures.evaluation.workflow_id}/edit`)
    const selector = `.vue-flow__node[data-id="${__modelFixtures.evaluation.node_id}"]`
    await __modelWait(() => document.querySelector(selector))
    document.querySelector(selector).click()
    window.__modelEvaluationForm = () => [...document.querySelectorAll('.model-evaluation-config-form')].findLast(__modelVisible)
    await __modelWait(() => __modelEvaluationForm())
    await __modelSelect(__modelField(__modelEvaluationForm(), '模型来源'), '已完成的训练记录')
    await __modelSelect(__modelField(__modelEvaluationForm(), '训练记录'), 'QA Fixed CPU Classifier')
    await __modelSelect(__modelField(__modelEvaluationForm(), '测试数据来源'), '训练数据集')
    await __modelSelect(__modelField(__modelEvaluationForm(), '测试数据集'), 'QA Training-Domain Zero F1')
    window.__modelSaveEvaluation = async () => {
      const button = document.querySelector('button[aria-label="保存工作流"]')
      await __modelWait(() => button && !button.disabled); button.click()
      let config
      await __modelWait(async () => {
        const workflow = (await __modelCall(`workflows/${__modelFixtures.evaluation.workflow_id}/`)).data
        config = workflow.nodes.find(row => row.id === __modelFixtures.evaluation.node_id).config
        return config.evaluationModelSource === 'registered' && config.trainingJobId === __modelFixtures.evaluation.training_job_id
      }, 'persisted Editor configuration')
      return config
    }
    const config = await __modelSaveEvaluation()
    return { ok: config.modelPath === '' && !Object.hasOwn(config, 'trainingRunId') && config.testDataset === '' && config.datasetId === '' && config.trainingDatasetId === __modelFixtures.evaluation.training_dataset_id, legacyCleared: true, domain: 'training' }
  }))
  await check('actual Editor switches to the generic dataset domain and persists the mutually exclusive selection', () => page(async () => {
    await __modelSelect(__modelField(__modelEvaluationForm(), '测试数据来源'), '通用数据集')
    await __modelSelect(__modelField(__modelEvaluationForm(), '测试数据集'), 'QA Generic-Domain Zero F1')
    const button = document.querySelector('button[aria-label="保存工作流"]'); button.click()
    let config
    await __modelWait(async () => {
      config = (await __modelCall(`workflows/${__modelFixtures.evaluation.workflow_id}/`)).data.nodes.find(row => row.id === __modelFixtures.evaluation.node_id).config
      return config.datasetId === __modelFixtures.evaluation.generic_dataset_id
    }, 'persisted generic dataset selection')
    return { ok: config.trainingDatasetId === '' && config.testDataset === '' && config.evaluationDatasetSource === 'generic', domain: 'generic' }
  }))
  await check('a real workflow evaluation returns and displays F1 equal to zero', () => page(async () => {
    const before = __modelRows(await __modelCall(`workflows/executions/?workflow=${__modelFixtures.evaluation.workflow_id}&page_size=100`)).map(row => row.id)
    document.querySelector('button[aria-label="运行工作流"]').click()
    let execution
    await __modelWait(async () => {
      execution = __modelRows(await __modelCall(`workflows/executions/?workflow=${__modelFixtures.evaluation.workflow_id}&page_size=100`)).find(row => !before.includes(row.id))
      return execution && ['completed', 'failed'].includes(execution.status)
    }, 'actual CPU model evaluation')
    const rows = __modelRows(await __modelCall('evaluations/?page_size=100'))
    const measured = rows.find(row => row.workflow_id === __modelFixtures.evaluation.workflow_id && row.execution_id === execution.id)
    const node = document.querySelector(`.vue-flow__node[data-id="${__modelFixtures.evaluation.node_id}"]`)
    await __modelWait(() => [...node.querySelectorAll('.metric-row')].some(row => row.querySelector('.metric-label')?.textContent.trim() === 'F1' && row.querySelector('.metric-value')?.textContent.trim() === '0.0%'), 'actual F1 result on node')
    return { ok: execution.status === 'completed' && measured?.metrics?.f1 === 0 && measured.metrics.sample_count === 4 && measured.verification_status === 'verified', measuredF1: measured?.metrics?.f1, samples: measured?.metrics?.sample_count, syntheticCpuOnly: true }
  }))
  await page(async () => {
    document.querySelector('.execution-bottom-panel .exec-header-right button:last-child')?.click()
    document.querySelector('button[aria-label="适应窗口"]')?.click()
    await __modelWait(() => {
      const node = document.querySelector(`.vue-flow__node[data-id="${__modelFixtures.evaluation.node_id}"]`)
      const row = [...(node?.querySelectorAll('.metric-row') || [])].find(item => item.querySelector('.metric-label')?.textContent.trim() === 'F1')
      const metric = row?.querySelector('.metric-value'), rect = metric?.getBoundingClientRect()
      return rect?.top > 0 && rect.bottom < innerHeight && metric.contains(document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2))
    }, 'unobscured F1 screenshot evidence')
    return { ok: true }
  })
  await client.tool('take_screenshot', { filePath: path.join(output, 'model-evaluation-zero-f1.png'), fullPage: true })

  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/api/health/` })
  await page(`async () => {
    const response = await fetch(${JSON.stringify(`${BACKEND_URL}/api/v1/auth/login/`)}, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: ${JSON.stringify(fixtures.admin_username)}, password: ${JSON.stringify(adminPassword)} }) });
    const payload = await response.json(), data = payload.data || payload;
    if (!response.ok || !data.access) throw new Error('Isolated catalog admin login failed');
    localStorage.setItem('access_token', data.access); localStorage.setItem('refresh_token', data.refresh);
    document.cookie = 'access_token=' + data.access + '; path=/'; document.cookie = 'refresh_token=' + data.refresh + '; path=/';
    return { ok: true };
  }`)
  await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/models` })
  await initializePage()
  await check('catalog admin sets, replaces, and removes the real chat default without altering the embedding default', () => page(async () => {
    await __modelWait(() => document.querySelector('#tab-models'))
    document.querySelector('#tab-models').click()
    await __modelWait(() => __modelCard('QA Normal Model'))
    for (const name of ['QA Normal Model', 'QA Alternate Model']) {
      const item = await __modelOpenMenu(name, '设为目录默认')
      if (item.getAttribute('aria-disabled') === 'true') return { ok: false, stage: 'admin unexpectedly disabled' }
      item.click()
      await __modelWait(() => [...__modelCard(name).querySelectorAll('.el-tag')].some(tag => tag.textContent.trim() === '默认'))
    }
    const defaults = __modelRows(await __modelCall('gateway/models/default_models/'))
    const chats = defaults.filter(row => row.model_type === 'chat')
    const embeddingKept = defaults.some(row => row.id === __modelFixtures.gateway.models.embedding)
    const item = await __modelOpenMenu('QA Alternate Model', '取消目录默认'); item.click()
    await __modelWait(() => ![...__modelCard('QA Alternate Model').querySelectorAll('.el-tag')].some(tag => tag.textContent.trim() === '默认'))
    const after = __modelRows(await __modelCall('gateway/models/default_models/'))
    return { ok: chats.length === 1 && chats[0].id === __modelFixtures.gateway.models.alternate && embeddingKept && !after.some(row => row.model_type === 'chat') && after.some(row => row.id === __modelFixtures.gateway.models.embedding), adminMutualExclusion: true, otherTypeUnchanged: true }
  }))
  await client.tool('take_screenshot', { filePath: path.join(output, 'models-admin.png'), fullPage: true })
  await writeFile(path.join(output, 'model-configuration-results.json'), JSON.stringify({ tool: 'chrome-devtools MCP', checks, boundary: fixtures.scope }, null, 2))
  console.log(JSON.stringify({ passed: checks.length, failed: 0, scope: fixtures.scope }))
} finally {
  client.close()
}
