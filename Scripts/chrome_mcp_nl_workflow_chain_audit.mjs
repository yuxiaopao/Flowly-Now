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
      clientInfo: { name: 'flowly-nl-workflow-chain-audit', version: '1.0.0' },
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

function chainScenarioSource() {
  return String.raw`
async () => {
  const BACKEND_URL = '__BACKEND_URL__';
  const runId = 'nl-chain-' + Date.now();
  const token = localStorage.getItem('access_token');
  const report = { runId, steps: [], cleanup: [] };
  const created = { sessionId: null, workflowId: null };

  const add = (step, ok, details = {}) => report.steps.push({ step, ok, ...details });
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const unwrap = (payload) => payload && typeof payload === 'object' && 'code' in payload && 'data' in payload ? payload.data : payload;
  const textOf = () => (document.body.innerText || '').replace(/\s+/g, ' ').trim();

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
    assert(result.ok, step + ' failed: ' + result.status + ' ' + JSON.stringify(result.payload).slice(0, 600));
    return result.payload;
  }

  function nodePosition(node) {
    return {
      x: Number(node.positionX ?? node.position_x ?? node.position?.x ?? 0),
      y: Number(node.positionY ?? node.position_y ?? node.position?.y ?? 0),
    };
  }

  function hasDuplicatePositions(nodes) {
    const seen = new Set();
    for (const node of nodes || []) {
      const pos = nodePosition(node);
      const key = Math.round(pos.x) + ':' + Math.round(pos.y);
      if (seen.has(key)) return true;
      seen.add(key);
    }
    return false;
  }

  function canvasPreviewFromWorkflow(workflow) {
    return workflow?.canvasPreview
      || workflow?.canvas_preview
      || workflow?.config?.canvasPreview
      || workflow?.config?.canvas_preview
      || '';
  }

  try {
    assert(token, 'missing access token');

    history.pushState({}, '', '/nl-create');
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 1800));
    const nlPageState = {
      path: location.pathname,
      hasMainText: /NL|自然语言|工作流|创建|create/i.test(textOf()),
      bodyPreview: textOf().slice(0, 300),
    };
    add('open NL create page in Chrome', nlPageState.path === '/nl-create' && nlPageState.hasMainText, nlPageState);
    assert(nlPageState.path === '/nl-create' && nlPageState.hasMainText, 'NL create page did not render');

    const prompt = [
      'Create a production workflow for customer review intelligence.',
      'It should receive review text, call an LLM for sentiment and issue extraction,',
      'route negative cases to email notification, store the structured summary,',
      'and finish with a clear output node. Use explicit node positions.'
    ].join(' ');

    const session = await expectOk('create NL session through backend from Chrome context', api('/nl-workflow/sessions/', {
      method: 'POST',
      body: { name: runId, description: prompt, mode: 'generate', temperature: 0.2 }
    }));
    created.sessionId = session.session_id || session.id;
    const workflowJson = session.workflow_json || session.workflow;
    assert(created.sessionId, 'NL session id missing');
    assert(workflowJson?.nodes?.length >= 2, 'NL did not produce workflow nodes');
    const generationMode = workflowJson._generation_mode || 'unknown';
    add('NL generation used non-template intelligence path', generationMode === 'llm', {
      generationMode,
      model: workflowJson._llm_model || null,
      nodeCount: workflowJson.nodes.length,
      edgeCount: (workflowJson.edges || []).length,
    });
    assert(generationMode === 'llm', 'NL generation did not use LLM path: ' + generationMode);

    const confirmed = await expectOk('confirm NL session into saved workflow', api('/nl-workflow/sessions/' + created.sessionId + '/confirm/', { method: 'POST' }));
    created.workflowId = confirmed.workflow_id;
    assert(created.workflowId, 'confirmed workflow id missing');

    await expectOk('tag confirmed workflow with audit name for list lookup', api('/workflows/' + created.workflowId + '/', {
      method: 'PATCH',
      body: { name: runId + ' confirmed workflow' }
    }));

    const detailAfterConfirm = await expectOk('fetch confirmed workflow detail', api('/workflows/' + created.workflowId + '/'));
    const savedNodes = detailAfterConfirm.nodes || [];
    const savedEdges = detailAfterConfirm.edges || [];
    add('confirmed workflow has stable non-overlapping node coordinates', savedNodes.length >= 2 && !hasDuplicatePositions(savedNodes), {
      nodeCount: savedNodes.length,
      edgeCount: savedEdges.length,
      positions: savedNodes.map((node) => ({ id: node.id, type: node.nodeType || node.node_type, ...nodePosition(node) })).slice(0, 12),
    });
    assert(savedNodes.length >= 2, 'saved workflow missing nodes');
    assert(!hasDuplicatePositions(savedNodes), 'saved workflow has duplicate node positions');

    history.pushState({}, '', '/workflows/' + created.workflowId + '/edit');
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 4500));
    const editorState = {
      path: location.pathname,
      hasCanvas: Boolean(document.querySelector('.vue-flow')),
      nodeCount: document.querySelectorAll('.vue-flow__node').length,
      edgeCount: document.querySelectorAll('.vue-flow__edge').length,
      bodyPreview: textOf().slice(0, 300),
    };
    add('open generated workflow in editor and render canvas', editorState.hasCanvas && editorState.nodeCount >= savedNodes.length, editorState);
    assert(editorState.hasCanvas, 'workflow editor canvas missing');
    assert(editorState.nodeCount >= savedNodes.length, 'editor rendered fewer nodes than backend detail');

    const saveButton = [...document.querySelectorAll('button')]
      .find((button) => (button.innerText || '').includes('保存') && !button.disabled);
    assert(saveButton, 'editor save button not found');
    saveButton.click();
    await new Promise((resolve) => setTimeout(resolve, 5000));

    const detailAfterSave = await expectOk('fetch workflow after editor save', api('/workflows/' + created.workflowId + '/'));
    const afterSaveNodes = detailAfterSave.nodes || [];
    const preview = canvasPreviewFromWorkflow(detailAfterSave);
    add('editor save keeps positions and stores real canvas screenshot preview', typeof preview === 'string' && preview.startsWith('data:image') && preview.length > 1000 && !hasDuplicatePositions(afterSaveNodes), {
      previewPrefix: typeof preview === 'string' ? preview.slice(0, 32) : '',
      previewLength: typeof preview === 'string' ? preview.length : 0,
      positions: afterSaveNodes.map((node) => ({ id: node.id, ...nodePosition(node) })).slice(0, 12),
    });
    assert(typeof preview === 'string' && preview.startsWith('data:image'), 'workflow screenshot preview missing');
    assert(preview.length > 1000, 'workflow screenshot preview is too small');
    assert(!hasDuplicatePositions(afterSaveNodes), 'editor save created duplicate positions');

    const validation = await api('/workflows/' + created.workflowId + '/validate/', { method: 'POST' });
    add('workflow validation endpoint responds for NL-created workflow', validation.ok || validation.status === 400, {
      status: validation.status,
      payload: validation.payload,
    });
    assert(validation.ok || validation.status === 400, 'workflow validation endpoint failed unexpectedly');

    const execution = await api('/workflows/' + created.workflowId + '/execute/', {
      method: 'POST',
      body: {
        input_data: {
          audit: runId,
          review_text: 'The onboarding flow is useful, but export failed twice and support needs to follow up.',
        },
        trigger_type: 'manual',
        is_async: false,
      }
    });
    add('workflow execution endpoint accepts NL-created workflow', execution.ok, {
      status: execution.status,
      payload: execution.payload,
    });
    assert(execution.ok, 'workflow execution endpoint rejected NL-created workflow');

    history.pushState({}, '', '/workflows?search=' + encodeURIComponent(runId));
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 3000));
    const listApi = await expectOk('fetch workflow list filtered by run id', api('/workflows/?search=' + encodeURIComponent(runId)));
    const apiItems = Array.isArray(listApi?.results) ? listApi.results : (Array.isArray(listApi) ? listApi : []);
    const apiTarget = apiItems.find((item) => String(item.id) === String(created.workflowId) || (item.name || '').includes(runId));
    const apiPreview = canvasPreviewFromWorkflow(apiTarget);
    const workflowCards = [...document.querySelectorAll('.workflow-card')];
    const targetCard = workflowCards.find((card) => (card.innerText || '').includes(runId));
    const listState = {
      path: location.pathname + location.search,
      cardCount: workflowCards.length,
      targetCardFound: Boolean(targetCard),
      screenshotCount: targetCard ? targetCard.querySelectorAll('.workflow-card-preview img.preview-screenshot').length : 0,
      pendingCount: targetCard ? [...targetCard.querySelectorAll('.workflow-card-preview')].filter((el) => /保存后生成|空工作流/.test(el.innerText || '')).length : 0,
      apiTargetFound: Boolean(apiTarget),
      apiPreviewLength: typeof apiPreview === 'string' ? apiPreview.length : 0,
      bodyPreview: textOf().slice(0, 400),
    };
    add('workflow card preview uses captured editor screenshot', listState.apiTargetFound && listState.apiPreviewLength > 1000 && (!listState.targetCardFound || (listState.screenshotCount >= 1 && listState.pendingCount === 0)), listState);
    assert(listState.apiTargetFound, 'created workflow was not returned by filtered workflow list API');
    assert(listState.apiPreviewLength > 1000, 'filtered workflow list API did not include screenshot preview');
    if (listState.targetCardFound) {
      assert(listState.screenshotCount >= 1, 'target workflow card did not show screenshot preview');
      assert(listState.pendingCount === 0, 'target workflow card still showed placeholder preview');
    }

    return report;
  } finally {
    if (created.workflowId) {
      const result = await api('/workflows/' + created.workflowId + '/', { method: 'DELETE' });
      report.cleanup.push({ label: 'workflow', id: created.workflowId, ok: result.ok || result.status === 404, status: result.status });
    }
    if (created.sessionId) {
      const result = await api('/nl-workflow/sessions/' + created.sessionId + '/', { method: 'DELETE' });
      report.cleanup.push({ label: 'nl-session', id: created.sessionId, ok: result.ok || result.status === 404, status: result.status });
    }
  }
}
`.replaceAll('__BACKEND_URL__', BACKEND_URL)
}

async function waitForBrowserState(client, label, isDone, timeoutMs = 360000, intervalMs = 5000) {
  const startedAt = Date.now()
  for (;;) {
    const state = await evalPage(client, 'async () => window.__flowlyNlChain || null', 10000)
    if (state?.error) throw new Error(`${label}: ${state.error}`)
    if (isDone(state)) return state
    if (Date.now() - startedAt > timeoutMs) {
      throw new Error(`${label} timed out after ${timeoutMs}ms`)
    }
    await delay(intervalMs)
  }
}

async function runSegmentedScenario(client) {
  await evalPage(client, `async () => {
    const runId = 'nl-chain-' + Date.now();
    window.__flowlyNlChain = { runId, backendUrl: '${BACKEND_URL}', steps: [], cleanup: [], created: {}, error: null };
    window.__flowlyNlAdd = (step, ok, details = {}) => window.__flowlyNlChain.steps.push({ step, ok, ...details });
    window.__flowlyNlAssert = (condition, message) => { if (!condition) throw new Error(message); };
    window.__flowlyNlUnwrap = (payload) => payload && typeof payload === 'object' && 'code' in payload && 'data' in payload ? payload.data : payload;
    window.__flowlyNlApi = async (path, options = {}) => {
      const token = localStorage.getItem('access_token');
      const headers = new Headers(options.headers || {});
      headers.set('Authorization', 'Bearer ' + token);
      const init = { method: options.method || 'GET', headers, credentials: 'include' };
      if (options.body !== undefined) {
        headers.set('Content-Type', 'application/json');
        init.body = JSON.stringify(options.body);
      }
      const response = await fetch(window.__flowlyNlChain.backendUrl + '/api/v1' + path, init);
      const contentType = response.headers.get('content-type') || '';
      let payload = null;
      if (response.status === 204) payload = null;
      else if (contentType.includes('application/json')) payload = window.__flowlyNlUnwrap(await response.json());
      else payload = await response.text();
      return { ok: response.ok, status: response.status, payload };
    };
    window.__flowlyNlExpectOk = async (step, promise) => {
      const result = await promise;
      window.__flowlyNlAdd(step, result.ok, { status: result.status, payload: result.ok ? undefined : result.payload });
      window.__flowlyNlAssert(result.ok, step + ' failed: ' + result.status + ' ' + JSON.stringify(result.payload).slice(0, 600));
      return result.payload;
    };
    window.__flowlyNlNodePosition = (node) => ({
      x: Number(node.positionX ?? node.position_x ?? node.position?.x ?? 0),
      y: Number(node.positionY ?? node.position_y ?? node.position?.y ?? 0),
    });
    window.__flowlyNlHasDuplicatePositions = (nodes) => {
      const seen = new Set();
      for (const node of nodes || []) {
        const pos = window.__flowlyNlNodePosition(node);
        const key = Math.round(pos.x) + ':' + Math.round(pos.y);
        if (seen.has(key)) return true;
        seen.add(key);
      }
      return false;
    };
    window.__flowlyNlPreview = (workflow) => workflow?.canvasPreview || workflow?.canvas_preview || workflow?.config?.canvasPreview || workflow?.config?.canvas_preview || '';
    return { runId };
  }`, 10000)

  const pageState = await evalPage(client, `async () => {
    history.pushState({}, '', '/nl-create');
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 1800));
    const text = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
    const ok = location.pathname === '/nl-create' && /NL|自然语言|工作流|创建|create/i.test(text);
    window.__flowlyNlAdd('open NL create page in Chrome', ok, { path: location.pathname, bodyPreview: text.slice(0, 300) });
    window.__flowlyNlAssert(ok, 'NL create page did not render');
    return window.__flowlyNlChain;
  }`, 20000)
  if (pageState?.error) throw new Error(pageState.error)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    const prompt = [
      'Create a production workflow for customer review intelligence.',
      'It should receive review_text, call an LLM for sentiment and issue extraction,',
      'route negative cases to email notification, store the structured summary,',
      'and finish with a clear output node. Use explicit node positions.'
    ].join(' ');
    s.generation = { started: true, done: false };
    s.generationPromise = (async () => {
      const session = await window.__flowlyNlExpectOk('create NL session through backend from Chrome context', window.__flowlyNlApi('/nl-workflow/sessions/', {
        method: 'POST',
        body: { name: s.runId, description: prompt, mode: 'generate', temperature: 0.2 }
      }));
      s.created.sessionId = session.session_id || session.id;
      const workflowJson = session.workflow_json || session.workflow;
      window.__flowlyNlAssert(s.created.sessionId, 'NL session id missing');
      window.__flowlyNlAssert(workflowJson?.nodes?.length >= 2, 'NL did not produce workflow nodes');
      const generationMode = workflowJson._generation_mode || 'unknown';
      window.__flowlyNlAdd('NL generation used non-template intelligence path', generationMode === 'llm', {
        generationMode,
        model: workflowJson._llm_model || null,
        nodeCount: workflowJson.nodes.length,
        edgeCount: (workflowJson.edges || []).length,
      });
      window.__flowlyNlAssert(generationMode === 'llm', 'NL generation did not use LLM path: ' + generationMode);
      s.generation.done = true;
    })().catch((error) => { s.error = error?.message || String(error); s.generation.done = true; });
    return { started: true, runId: s.runId };
  }`, 10000)

  await waitForBrowserState(client, 'NL generation', (state) => state?.generation?.done, 420000, 6000)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    const confirmed = await window.__flowlyNlExpectOk('confirm NL session into saved workflow', window.__flowlyNlApi('/nl-workflow/sessions/' + s.created.sessionId + '/confirm/', { method: 'POST' }));
    s.created.workflowId = confirmed.workflow_id;
    window.__flowlyNlAssert(s.created.workflowId, 'confirmed workflow id missing');
    await window.__flowlyNlExpectOk('tag confirmed workflow with audit name for list lookup', window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/', {
      method: 'PATCH',
      body: { name: s.runId + ' confirmed workflow' }
    }));
    const detail = await window.__flowlyNlExpectOk('fetch confirmed workflow detail', window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/'));
    const nodes = detail.nodes || [];
    const edges = detail.edges || [];
    const ok = nodes.length >= 2 && !window.__flowlyNlHasDuplicatePositions(nodes);
    window.__flowlyNlAdd('confirmed workflow has stable non-overlapping node coordinates', ok, {
      nodeCount: nodes.length,
      edgeCount: edges.length,
      positions: nodes.map((node) => ({ id: node.id, type: node.nodeType || node.node_type, ...window.__flowlyNlNodePosition(node) })).slice(0, 12),
    });
    window.__flowlyNlAssert(ok, 'saved workflow has missing or duplicate node positions');
    return s;
  }`, 30000)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    history.pushState({}, '', '/workflows/' + s.created.workflowId + '/edit');
    window.dispatchEvent(new PopStateEvent('popstate'));
    return { path: location.pathname };
  }`, 10000)
  await delay(6000)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    const text = (document.body.innerText || '').replace(/\s+/g, ' ').trim();
    const state = {
      path: location.pathname,
      hasCanvas: Boolean(document.querySelector('.vue-flow')),
      nodeCount: document.querySelectorAll('.vue-flow__node').length,
      edgeCount: document.querySelectorAll('.vue-flow__edge').length,
      bodyPreview: text.slice(0, 300),
    };
    const ok = state.hasCanvas && state.nodeCount >= 2;
    window.__flowlyNlAdd('open generated workflow in editor and render canvas', ok, state);
    window.__flowlyNlAssert(ok, 'workflow editor canvas missing or empty');
    const saveButton = [...document.querySelectorAll('button')].find((button) => (button.innerText || '').includes('保存') && !button.disabled);
    window.__flowlyNlAssert(saveButton, 'editor save button not found');
    saveButton.click();
    return s;
  }`, 20000)
  await delay(9000)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    const detail = await window.__flowlyNlExpectOk('fetch workflow after editor save', window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/'));
    const nodes = detail.nodes || [];
    const preview = window.__flowlyNlPreview(detail);
    const ok = typeof preview === 'string' && preview.startsWith('data:image') && preview.length > 1000 && !window.__flowlyNlHasDuplicatePositions(nodes);
    window.__flowlyNlAdd('editor save keeps positions and stores real canvas screenshot preview', ok, {
      previewPrefix: typeof preview === 'string' ? preview.slice(0, 32) : '',
      previewLength: typeof preview === 'string' ? preview.length : 0,
      positions: nodes.map((node) => ({ id: node.id, ...window.__flowlyNlNodePosition(node) })).slice(0, 12),
    });
    window.__flowlyNlAssert(ok, 'workflow screenshot preview missing or positions duplicated');
    const validation = await window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/validate/', { method: 'POST' });
    window.__flowlyNlAdd('workflow validation endpoint responds for NL-created workflow', validation.ok || validation.status === 400, { status: validation.status, payload: validation.payload });
    window.__flowlyNlAssert(validation.ok || validation.status === 400, 'workflow validation endpoint failed unexpectedly');
    const execution = await window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/execute/', {
      method: 'POST',
      body: {
        input_data: { audit: s.runId, review_text: 'The onboarding flow is useful, but export failed twice and support needs to follow up.' },
        trigger_type: 'manual',
        is_async: true,
      }
    });
    window.__flowlyNlAdd('workflow execution endpoint accepts NL-created workflow', execution.ok, { status: execution.status, payload: execution.payload });
    window.__flowlyNlAssert(execution.ok, 'workflow execution endpoint rejected NL-created workflow');
    return s;
  }`, 30000)

  await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    history.pushState({}, '', '/workflows?search=' + encodeURIComponent(s.runId));
    window.dispatchEvent(new PopStateEvent('popstate'));
    return s;
  }`, 10000)
  await delay(4000)

  const finalState = await evalPage(client, `async () => {
    const s = window.__flowlyNlChain;
    const listApi = await window.__flowlyNlExpectOk('fetch workflow list filtered by run id', window.__flowlyNlApi('/workflows/?search=' + encodeURIComponent(s.runId)));
    const apiItems = Array.isArray(listApi?.results) ? listApi.results : (Array.isArray(listApi) ? listApi : []);
    const apiTarget = apiItems.find((item) => String(item.id) === String(s.created.workflowId) || (item.name || '').includes(s.runId));
    const apiPreview = window.__flowlyNlPreview(apiTarget);
    const workflowCards = [...document.querySelectorAll('.workflow-card')];
    const targetCard = workflowCards.find((card) => (card.innerText || '').includes(s.runId));
    const listState = {
      path: location.pathname + location.search,
      cardCount: workflowCards.length,
      targetCardFound: Boolean(targetCard),
      screenshotCount: targetCard ? targetCard.querySelectorAll('.workflow-card-preview img.preview-screenshot').length : 0,
      pendingCount: targetCard ? [...targetCard.querySelectorAll('.workflow-card-preview')].filter((el) => /保存后生成|空工作流/.test(el.innerText || '')).length : 0,
      apiTargetFound: Boolean(apiTarget),
      apiPreviewLength: typeof apiPreview === 'string' ? apiPreview.length : 0,
      bodyPreview: (document.body.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 400),
    };
    const ok = listState.apiTargetFound && listState.apiPreviewLength > 1000 && (!listState.targetCardFound || (listState.screenshotCount >= 1 && listState.pendingCount === 0));
    window.__flowlyNlAdd('workflow card preview uses captured editor screenshot', ok, listState);
    window.__flowlyNlAssert(ok, 'workflow list did not expose the captured screenshot preview');
    return s;
  }`, 30000)

  try {
    await evalPage(client, `async () => {
      const s = window.__flowlyNlChain;
      if (s?.created?.workflowId) {
        const result = await window.__flowlyNlApi('/workflows/' + s.created.workflowId + '/', { method: 'DELETE' });
        s.cleanup.push({ label: 'workflow', id: s.created.workflowId, ok: result.ok || result.status === 404, status: result.status });
      }
      if (s?.created?.sessionId) {
        const result = await window.__flowlyNlApi('/nl-workflow/sessions/' + s.created.sessionId + '/', { method: 'DELETE' });
        s.cleanup.push({ label: 'nl-session', id: s.created.sessionId, ok: result.ok || result.status === 404, status: result.status });
      }
      return s;
    }`, 30000)
  } catch (cleanupError) {
    finalState.cleanup.push({ label: 'cleanup', ok: false, status: 0, payload: cleanupError.message })
  }

  const report = await evalPage(client, 'async () => window.__flowlyNlChain', 10000)
  return {
    runId: report.runId,
    steps: report.steps,
    cleanup: report.cleanup,
  }
}

async function main() {
  const client = new McpClient()
  try {
    await client.initialize()
    await login(client)
    await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/nl-create`, timeout: 25000 }, 35000)
    await delay(1000)
    const report = await runSegmentedScenario(client)
    await fs.mkdir('test-results', { recursive: true })
    await fs.writeFile('test-results/chrome-mcp-nl-workflow-chain-audit.json', `${JSON.stringify(report, null, 2)}\n`, 'utf8')
    if (!report || !Array.isArray(report.steps)) {
      throw new Error(`Unexpected NL chain report: ${JSON.stringify(report)}`)
    }
    const failed = report.steps.filter((step) => !step.ok)
    const cleanupFailed = (report.cleanup || []).filter((item) => !item.ok)
    console.log(JSON.stringify({
      runId: report.runId,
      steps: report.steps.length,
      failed: failed.length,
      cleanupFailed: cleanupFailed.length,
      report: 'test-results/chrome-mcp-nl-workflow-chain-audit.json',
    }, null, 2))
    if (failed.length || cleanupFailed.length) process.exitCode = 1
  } finally {
    client.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
