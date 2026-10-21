import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5200'
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const USERNAME = process.env.FLOWLY_E2E_USERNAME || 'nlwftest@flowly.test'
const PASSWORD = process.env.FLOWLY_E2E_PASSWORD || 'Test123456!'
const NPX_CMD = process.env.NPX_CMD || 'D:\\nodejs\\npx.cmd'

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

class McpClient {
  constructor() {
    this.nextId = 1
    this.pending = new Map()
    this.buffer = ''
    this.proc = spawn('cmd.exe', ['/d', '/s', '/c', `${NPX_CMD} -y chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222 --no-usage-statistics`], {
      stdio: ['pipe', 'pipe', 'pipe'],
    })
    this.proc.stdout.on('data', (chunk) => this.onData(chunk))
    this.proc.stderr.on('data', (chunk) => {
      const text = String(chunk)
      if (!text.includes('exposes content of the browser')) process.stderr.write(text)
    })
  }

  onData(chunk) {
    this.buffer += String(chunk)
    for (;;) {
      const idx = this.buffer.indexOf('\n')
      if (idx < 0) break
      const line = this.buffer.slice(0, idx).trim()
      this.buffer = this.buffer.slice(idx + 1)
      if (!line || !line.startsWith('{')) continue
      let message
      try {
        message = JSON.parse(line)
      } catch {
        continue
      }
      if (!message.id || !this.pending.has(message.id)) continue
      const { resolve, reject, timeout } = this.pending.get(message.id)
      clearTimeout(timeout)
      this.pending.delete(message.id)
      if (message.error) reject(new Error(JSON.stringify(message.error)))
      else resolve(message.result)
    }
  }

  async initialize() {
    await this.request('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'flowly-workflow-canvas-audit', version: '1.0.0' },
    })
    this.notify('notifications/initialized', {})
  }

  notify(method, params = {}) {
    this.proc.stdin.write(`${JSON.stringify({ jsonrpc: '2.0', method, params })}\n`)
  }

  request(method, params = {}, timeoutMs = 30000) {
    const id = this.nextId++
    const payload = { jsonrpc: '2.0', id, method, params }
    const promise = new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`MCP request timed out: ${method}`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timeout })
    })
    this.proc.stdin.write(`${JSON.stringify(payload)}\n`)
    return promise
  }

  tool(name, args = {}, timeoutMs = 30000) {
    return this.request('tools/call', { name, arguments: args }, timeoutMs)
  }

  close() {
    this.proc.kill()
  }
}

function resultText(result) {
  return (result?.content || [])
    .map((item) => (item.type === 'text' ? item.text : ''))
    .filter(Boolean)
    .join('\n')
}

async function evalPage(client, fn, timeoutMs = 30000) {
  const result = await client.tool('evaluate_script', { function: fn }, timeoutMs)
  const text = resultText(result)
  if (!text) return null
  const fencedJson = text.match(/```json\s*([\s\S]*?)\s*```/)
  const payload = fencedJson ? fencedJson[1] : text
  try {
    return JSON.parse(payload)
  } catch {
    return text
  }
}

async function login(client) {
  await client.tool('new_page', { url: `${FRONTEND_URL}/login`, timeout: 20000 }, 30000)
  await delay(1000)
  const loginResult = await evalPage(client, `async () => {
    const response = await fetch('${BACKEND_URL}/api/v1/auth/login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: '${USERNAME}', password: '${PASSWORD}' })
    });
    const payload = await response.json();
    const data = payload.data || payload;
    if (!response.ok || !data.access) return { ok: false, status: response.status, payload };
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    document.cookie = 'access_token=' + data.access + '; path=/';
    document.cookie = 'refresh_token=' + data.refresh + '; path=/';
    return { ok: true, user: data.user?.username || data.user?.email || null };
  }`, 20000)
  if (!loginResult?.ok) throw new Error(`login failed: ${JSON.stringify(loginResult)}`)
  return loginResult
}

async function runScenario(client) {
  const source = String.raw`
async () => {
  const FRONTEND_URL = '__FRONTEND_URL__';
  const BACKEND_URL = '__BACKEND_URL__';
  const token = localStorage.getItem('access_token');
  const runId = 'canvas-audit-' + Date.now();
  const report = { runId, steps: [], cleanup: [] };
  const created = { workflows: [] };

  const add = (step, ok, details = {}) => report.steps.push({ step, ok, ...details });
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const unwrap = (payload) => payload && typeof payload === 'object' && 'code' in payload && 'data' in payload ? payload.data : payload;
  const round2 = (value) => Number(Number(value).toFixed(2));
  const closeTo = (actual, expected) => Math.abs(Number(actual) - Number(expected)) < 0.02;

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Authorization', 'Bearer ' + token);
    const init = { method: options.method || 'GET', headers, credentials: 'include' };
    if (options.body !== undefined) {
      headers.set('Content-Type', 'application/json');
      init.body = JSON.stringify(options.body);
    }
    const response = await fetch(BACKEND_URL + '/api/v1' + path, init);
    const contentType = response.headers.get('content-type') || '';
    let payload = null;
    if (response.status === 204) payload = null;
    else if (contentType.includes('application/json')) payload = unwrap(await response.json());
    else payload = await response.text();
    return { ok: response.ok, status: response.status, payload };
  }

  async function expectOk(step, promise) {
    const result = await promise;
    add(step, result.ok, { status: result.status, payload: result.ok ? undefined : result.payload });
    assert(result.ok, step + ' failed: ' + result.status + ' ' + JSON.stringify(result.payload).slice(0, 500));
    return result.payload;
  }

  function findNode(workflow, type) {
    return (workflow.nodes || []).find((node) => (node.nodeType || node.node_type) === type);
  }

  try {
    assert(token, 'missing access token');
    const createPayload = {
      name: runId,
      description: 'Chrome DevTools MCP workflow canvas audit',
      status: 'draft',
      config: { source: runId },
      nodes: [
        { id: 'audit-start', type: 'start', position: { x: 0, y: 0 }, data: { label: 'Start', config: {} } },
        { id: 'audit-llm', type: 'llm', position: { x: 360.25, y: 124.75 }, data: { label: 'LLM', config: { prompt: 'hello' } } },
        { id: 'audit-end', type: 'end', position: { x: 720.5, y: 124.75 }, data: { label: 'End', config: {} } },
      ],
      edges: [
        { source: 'audit-start', target: 'audit-llm', label: 'next' },
        { source: 'audit-llm', target: 'audit-end', label: 'done' },
      ],
    };
    const createdWorkflow = await expectOk('create workflow with decimal positions', api('/workflows/', { method: 'POST', body: createPayload }));
    created.workflows.push(createdWorkflow.id);
    assert(createdWorkflow.id, 'workflow id missing');

    const detailBefore = await expectOk('fetch workflow before editor save', api('/workflows/' + createdWorkflow.id + '/'));
    const beforeStart = findNode(detailBefore, 'start');
    const beforeLlm = findNode(detailBefore, 'llm');
    assert(beforeStart && closeTo(beforeStart.positionX ?? beforeStart.position_x, 0), 'origin x was not preserved before editor');
    assert(beforeStart && closeTo(beforeStart.positionY ?? beforeStart.position_y, 0), 'origin y was not preserved before editor');
    assert(beforeLlm && closeTo(beforeLlm.positionX ?? beforeLlm.position_x, 360.25), 'decimal x was not persisted before editor');
    assert(beforeLlm && closeTo(beforeLlm.positionY ?? beforeLlm.position_y, 124.75), 'decimal y was not persisted before editor');
    add('backend preserved origin and decimal positions before editor', true);

    history.pushState({}, '', '/workflows/' + createdWorkflow.id + '/edit');
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 3500));
    const editorState = {
      path: location.pathname,
      nodeCount: document.querySelectorAll('.vue-flow__node').length,
      hasCanvas: Boolean(document.querySelector('.vue-flow')),
      visibleText: document.body.innerText.replace(/\s+/g, ' ').slice(0, 400),
    };
    add('editor route renders real Vue Flow canvas', editorState.hasCanvas && editorState.nodeCount >= 3, editorState);
    assert(editorState.hasCanvas && editorState.nodeCount >= 3, 'editor canvas did not render expected nodes');

    const saveButton = [...document.querySelectorAll('button')]
      .find((button) => (button.innerText || '').includes('\u4fdd\u5b58') && !button.disabled);
    assert(saveButton, 'editor save button not found');
    saveButton.click();
    await new Promise((resolve) => setTimeout(resolve, 4500));
    const detailAfter = await expectOk('fetch workflow after save', api('/workflows/' + createdWorkflow.id + '/'));
    const afterStart = findNode(detailAfter, 'start');
    const afterLlm = findNode(detailAfter, 'llm');
    assert(afterStart && closeTo(afterStart.positionX ?? afterStart.position_x, 0), 'origin x moved after save');
    assert(afterStart && closeTo(afterStart.positionY ?? afterStart.position_y, 0), 'origin y moved after save');
    const actualLlmX = afterLlm?.positionX ?? afterLlm?.position_x;
    const actualLlmY = afterLlm?.positionY ?? afterLlm?.position_y;
    assert(afterLlm && closeTo(actualLlmX, 360.25), 'decimal x moved after editor save: ' + actualLlmX);
    assert(afterLlm && closeTo(actualLlmY, 124.75), 'decimal y moved after editor save: ' + actualLlmY);
    const preview = detailAfter.canvasPreview || detailAfter.canvas_preview || detailAfter.config?.canvasPreview || detailAfter.config?.canvas_preview;
    assert(typeof preview === 'string' && preview.startsWith('data:image'), 'canvas preview was not stored');
    assert(preview.length > 1000, 'canvas preview is too small to be a real captured screenshot');
    add('editor save preserved positions and captured real screenshot data URL', true, {
      llmPosition: { x: round2(afterLlm.positionX ?? afterLlm.position_x), y: round2(afterLlm.positionY ?? afterLlm.position_y) },
      previewPrefix: preview.slice(0, 32),
      previewLength: preview.length,
    });

    history.pushState({}, '', '/workflows?search=' + encodeURIComponent(runId));
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 2500));
    const cardState = {
      path: location.pathname + location.search,
      screenshotCount: document.querySelectorAll('.workflow-card-preview img.preview-screenshot').length,
      miniPreviewCount: document.querySelectorAll('.mini-workflow-preview, .preview-fallback').length,
      body: document.body.innerText.replace(/\s+/g, ' ').slice(0, 500),
    };
    add('workflow list card uses stored editor screenshot', cardState.screenshotCount >= 1 && cardState.miniPreviewCount === 0, cardState);
    assert(cardState.screenshotCount >= 1, 'workflow card did not render screenshot image');
    assert(cardState.miniPreviewCount === 0, 'workflow card still rendered generated mini preview');

    return report;
  } finally {
    for (const id of created.workflows.reverse()) {
      const result = await api('/workflows/' + id + '/', { method: 'DELETE' });
      report.cleanup.push({ label: 'workflow', id, ok: result.ok || result.status === 404, status: result.status });
    }
  }
}`

  return evalPage(
    client,
    source
      .replaceAll('__FRONTEND_URL__', FRONTEND_URL)
      .replaceAll('__BACKEND_URL__', BACKEND_URL),
    70000,
  )
}

async function main() {
  const client = new McpClient()
  try {
    await client.initialize()
    await login(client)
    const report = await runScenario(client)
    await fs.mkdir('test-results', { recursive: true })
    await fs.writeFile('test-results/chrome-mcp-workflow-canvas-audit.json', JSON.stringify(report, null, 2), 'utf8')
    if (!report || typeof report !== 'object' || !Array.isArray(report.steps)) {
      throw new Error(`Unexpected audit report: ${JSON.stringify(report)}`)
    }
    const failed = (report.steps || []).filter((step) => !step.ok)
    const cleanupFailed = (report.cleanup || []).filter((item) => !item.ok)
    console.log(JSON.stringify({ steps: report.steps.length, failed: failed.length, cleanupFailed: cleanupFailed.length }, null, 2))
    if (failed.length || cleanupFailed.length) {
      process.exitCode = 1
    }
  } finally {
    client.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
