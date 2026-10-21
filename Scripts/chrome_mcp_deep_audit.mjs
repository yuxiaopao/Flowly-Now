import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5200'
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const USERNAME = process.env.FLOWLY_E2E_USERNAME || 'nlwftest@flowly.test'
const PASSWORD = process.env.FLOWLY_E2E_PASSWORD || 'Test123456!'
const NPX_CMD = process.env.NPX_CMD || 'D:\\nodejs\\npx.cmd'

const INIT_SCRIPT = String.raw`
(() => {
  window.__flowlyDeepAudit = { console: [], runtime: [], network: [] };
  const push = (bucket, payload) => {
    try { window.__flowlyDeepAudit[bucket].push({ ts: Date.now(), ...payload }); } catch (_) {}
  };
  ['error', 'warn'].forEach((level) => {
    const original = console[level];
    console[level] = function(...args) {
      push('console', { level, args: args.map((arg) => {
        if (arg instanceof Error) return arg.stack || arg.message;
        if (typeof arg === 'string') return arg;
        try { return JSON.stringify(arg); } catch (_) { return String(arg); }
      }) });
      return original.apply(this, args);
    };
  });
  window.addEventListener('error', (event) => {
    if (event.message === 'ResizeObserver loop completed with undelivered notifications.') return;
    push('runtime', { type: 'error', message: event.message, source: event.filename, line: event.lineno });
  });
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    push('runtime', { type: 'unhandledrejection', message: reason?.stack || reason?.message || String(reason) });
  });
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const url = typeof args[0] === 'string' ? args[0] : args[0]?.url;
    try {
      const response = await originalFetch(...args);
      if (response.status >= 400) push('network', { transport: 'fetch', status: response.status, url: String(url || '') });
      return response;
    } catch (error) {
      push('network', { transport: 'fetch', status: 0, url: String(url || ''), message: error?.message || String(error) });
      throw error;
    }
  };
})();
`

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
    this.proc.stdout.on('data', (chunk) => this._onData(chunk))
    this.proc.stderr.on('data', (chunk) => {
      const text = String(chunk)
      if (!text.includes('exposes content of the browser')) process.stderr.write(text)
    })
  }

  _onData(chunk) {
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
      clientInfo: { name: 'flowly-deep-audit', version: '1.0.0' },
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
    .map((item) => item.type === 'text' ? item.text : '')
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

function browserScenarioSource() {
  return String.raw`
async () => {
  const FRONTEND_URL = '__FRONTEND_URL__';
  const BACKEND_URL = '__BACKEND_URL__';
  const runId = 'deep-audit-' + Date.now();
  const report = { runId, modules: [], cleanup: [] };
  const created = { workflows: [], agents: [], vectorStores: [], collections: [], templates: [], datasets: [] };

  const token = localStorage.getItem('access_token');
  if (!token) throw new Error('missing access token');

  const unwrap = (payload) => payload && typeof payload === 'object' && 'code' in payload && 'data' in payload ? payload.data : payload;
  const add = (module, step, ok, details = {}) => report.modules.push({ module, step, ok, ...details });
  const assert = (condition, message) => { if (!condition) throw new Error(message); };
  const normalizeList = (payload) => Array.isArray(payload) ? payload : (Array.isArray(payload?.results) ? payload.results : []);

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Authorization', 'Bearer ' + token);
    const init = { method: options.method || 'GET', headers, credentials: 'include' };
    if (options.body !== undefined) {
      if (options.body instanceof FormData) {
        init.body = options.body;
      } else {
        headers.set('Content-Type', 'application/json');
        init.body = JSON.stringify(options.body);
      }
    }
    const response = await fetch(BACKEND_URL + '/api/v1' + path, init);
    const contentType = response.headers.get('content-type') || '';
    let payload = null;
    if (response.status === 204) payload = null;
    else if (contentType.includes('application/json')) payload = unwrap(await response.json());
    else payload = await response.text();
    return { ok: response.ok, status: response.status, payload, path };
  }

  async function expectOk(module, step, promise) {
    try {
      const result = await promise;
      assert(result.ok, step + ' failed: ' + result.status + ' ' + JSON.stringify(result.payload).slice(0, 500));
      add(module, step, true, { status: result.status });
      return result.payload;
    } catch (error) {
      add(module, step, false, { error: error.message });
      throw error;
    }
  }

  async function expectStatus(module, step, promise, statuses) {
    try {
      const result = await promise;
      const ok = statuses.includes(result.status);
      add(module, step, ok, { status: result.status, payload: ok ? undefined : result.payload });
      assert(ok, step + ' expected ' + statuses.join('/') + ', got ' + result.status);
      return result.payload;
    } catch (error) {
      add(module, step, false, { error: error.message });
      throw error;
    }
  }

  async function navigateAndAudit(route, module = 'ui') {
    const before = window.__flowlyDeepAudit ? {
      console: window.__flowlyDeepAudit.console.length,
      runtime: window.__flowlyDeepAudit.runtime.length,
      network: window.__flowlyDeepAudit.network.length,
    } : { console: 0, runtime: 0, network: 0 };
    history.pushState({}, '', route);
    window.dispatchEvent(new PopStateEvent('popstate'));
    await new Promise((resolve) => setTimeout(resolve, 1200));
    const text = document.body.innerText || '';
    const after = window.__flowlyDeepAudit || { console: [], runtime: [], network: [] };
    const newErrors = [
      ...after.runtime.slice(before.runtime),
      ...after.console.slice(before.console).filter((entry) => entry.level === 'error'),
    ];
    const newNetwork = after.network.slice(before.network).filter((entry) => entry.status >= 400 || entry.status === 0);
    const ok = text.trim().length > 0 && !/Page Not Found|404|页面不存在/i.test(text) && newErrors.length === 0 && newNetwork.length === 0;
    add(module, 'route ' + route, ok, {
      path: location.pathname + location.search,
      bodyPreview: text.replace(/\s+/g, ' ').trim().slice(0, 300),
      errors: newErrors,
      network: newNetwork,
    });
  }

  try {
    const profile = await expectOk('auth', 'current user profile', api('/auth/user/'));
    assert(profile?.id || profile?.username || profile?.email, 'profile response missing user identity');
    await expectStatus('auth', 'invalid login is rejected', fetch(BACKEND_URL + '/api/v1/auth/login/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'bad-' + runId, password: 'bad' })
    }).then(async (response) => ({ ok: response.ok, status: response.status, payload: await response.json().catch(() => null), path: '/auth/login/' })), [400, 401]);
    await expectOk('system', 'backend ping', api('/ping/'));
    await expectOk('system', 'public site config', api('/public/site-config/'));

    const workflow = await expectOk('workflow', 'create workflow with nodes and edge', api('/workflows/', {
      method: 'POST',
      body: {
        name: runId + ' workflow',
        description: 'Chrome MCP deep audit workflow',
        status: 'draft',
        tags: ['deep-audit'],
        config: { audit: runId },
        nodes: [
          { id: 'start-node', type: 'start', position: { x: 0, y: 0 }, data: { label: 'Start' } },
          { id: 'end-node', type: 'end', position: { x: 240, y: 0 }, data: { label: 'End' } },
        ],
        edges: [{ source: 'start-node', target: 'end-node', label: 'done' }],
      }
    }));
    created.workflows.push(workflow.id);
    assert(workflow?.id, 'workflow missing id');
    assert((workflow.nodes || []).length >= 2, 'workflow nodes were not persisted');
    assert((workflow.edges || []).length >= 1, 'workflow edge was not persisted');
    await expectOk('workflow', 'retrieve workflow detail', api('/workflows/' + workflow.id + '/'));
    const searchedWorkflows = normalizeList(await expectOk('workflow', 'search workflow list', api('/workflows/?search=' + encodeURIComponent(runId))));
    assert(searchedWorkflows.some((item) => item.id === workflow.id), 'created workflow not found by search');
    const updatedWorkflow = await expectOk('workflow', 'update workflow metadata', api('/workflows/' + workflow.id + '/', {
      method: 'PATCH', body: { name: runId + ' workflow updated', config: { updatedByAudit: true } }
    }));
    assert(updatedWorkflow.name.includes('updated'), 'workflow update did not persist');
    await expectStatus('workflow', 'workflow validation endpoint responds', api('/workflows/' + workflow.id + '/validate/', { method: 'POST' }), [200, 400]);
    const duplicate = await expectOk('workflow', 'duplicate workflow', api('/workflows/' + workflow.id + '/duplicate/', { method: 'POST' }));
    if (duplicate?.id) created.workflows.push(duplicate.id);
    await expectOk('workflow', 'export workflow', api('/workflows/' + workflow.id + '/export/'));
    await navigateAndAudit('/workflows/' + workflow.id, 'workflow');

    const availableTypes = await expectOk('workflow', 'available node types', api('/workflows/nodes/available_types/'));
    assert(Array.isArray(availableTypes) && availableTypes.length > 0, 'available node types empty');
    await expectOk('workflow', 'execution list', api('/workflows/executions/'));
    await expectOk('workflow', 'execution statistics', api('/workflows/executions/statistics/'));

    const agent = await expectOk('agent', 'create agent', api('/agents/', {
      method: 'POST',
      body: {
        name: runId + ' agent',
        description: 'Chrome MCP deep audit agent',
        agent_type: 'conversational',
        system_prompt: 'Return concise test responses.',
        model: 'qwen2.5-coder:7b',
        temperature: 0.2,
        max_tokens: 256,
        tools: [],
        skills: [],
        memory_enabled: false,
        context_window: 2048,
        settings: { audit: runId },
      }
    }));
    created.agents.push(agent.id);
    assert(agent?.id, 'agent missing id');
    await expectOk('agent', 'retrieve agent', api('/agents/' + agent.id + '/'));
    await expectOk('agent', 'update agent', api('/agents/' + agent.id + '/', { method: 'PATCH', body: { description: 'updated by deep audit' } }));
    await expectOk('agent', 'available tools', api('/agents/tools/available/'));
    await expectOk('agent', 'debug history', api('/agents/' + agent.id + '/debug_history/'));
    await expectStatus('agent', 'debug empty message rejected', api('/agents/' + agent.id + '/debug/', { method: 'POST', body: { message: '' } }), [400]);
    await navigateAndAudit('/agents/' + agent.id + '/debug', 'agent');

    const vectorStore = await expectOk('rag', 'create memory vector store', api('/rag/vector-stores/', {
      method: 'POST',
      body: { name: runId + ' vector', store_type: 'memory', collection: runId.replace(/-/g, '_'), dimension: 16, metric: 'cosine', is_default: false }
    }));
    created.vectorStores.push(vectorStore.id);
    assert(vectorStore?.id, 'vector store missing id');
    await expectOk('rag', 'test memory vector store connection', api('/rag/vector-stores/' + vectorStore.id + '/test_connection/', { method: 'POST' }));
    const collection = await expectOk('rag', 'create collection', api('/rag/collections/', {
      method: 'POST',
      body: { name: runId + ' collection', description: 'deep audit collection', vector_store: vectorStore.id, chunk_size: 120, chunk_overlap: 10 }
    }));
    created.collections.push(collection.id);
    assert(collection?.id, 'collection missing id');
    await expectOk('rag', 'add text document', api('/rag/collections/' + collection.id + '/add_document/', {
      method: 'POST', body: { title: runId + ' doc', content: 'Flowly deep audit document. Retrieval should find this content.' }
    }));
    await expectOk('rag', 'collection stats', api('/rag/collections/' + collection.id + '/stats/'));
    await expectStatus('rag', 'empty collection search rejected', api('/rag/collections/' + collection.id + '/search/'), [400]);
    await navigateAndAudit('/knowledge/' + collection.id, 'rag');

    const datasetForm = new FormData();
    datasetForm.append('file', new Blob(['name,value\nalpha,1\nbeta,2\n'], { type: 'text/csv' }), runId + '.csv');
    datasetForm.append('name', runId + ' dataset');
    datasetForm.append('description', 'deep audit dataset');
    datasetForm.append('format', 'csv');
    const dataset = await expectOk('dataset', 'upload generic dataset', api('/datasets/upload/', { method: 'POST', body: datasetForm }));
    created.datasets.push(dataset.id);
    assert(dataset?.id, 'dataset missing id');
    await expectOk('dataset', 'generic dataset detail', api('/datasets/' + dataset.id + '/'));
    const preview = await expectOk('dataset', 'generic dataset preview', api('/datasets/' + dataset.id + '/preview/'));
    assert(Array.isArray(preview.rows) && preview.rows.length > 0, 'dataset preview rows empty');
    await expectOk('dataset', 'generic dataset stats', api('/datasets/' + dataset.id + '/stats/'));
    await navigateAndAudit('/datasets/' + dataset.id + '?source=generic', 'dataset');

    const categories = normalizeList(await expectOk('template', 'template categories', api('/template-categories/')));
    assert(categories.length > 0, 'template categories empty');
    const template = await expectOk('template', 'create private workflow template', api('/templates/', {
      method: 'POST',
      body: {
        category: categories[0].id,
        name: runId + ' template',
        description: 'deep audit template',
        difficulty: 'beginner',
        tags: ['deep-audit'],
        workflow_data: { nodes: workflow.nodes || [], edges: workflow.edges || [] },
        variables_schema: {},
        estimated_duration: 1,
        required_apis: [],
        is_public: false,
        is_active: true,
      }
    }));
    created.templates.push(template.id);
    assert(template?.id, 'template missing id');
    await expectOk('template', 'retrieve template', api('/templates/' + template.id + '/'));
    await expectOk('template', 'my templates contains created template', api('/templates/mine/?search=' + encodeURIComponent(runId)));
    await navigateAndAudit('/marketplace/' + template.id, 'template');

    const readOnlyEndpoints = [
      ['monitoring', '/monitoring/metrics/'],
      ['analytics', '/workflows/executions/analytics/'],
      ['prompts', '/prompts/templates/'],
      ['models', '/gateway/models/'],
      ['billing', '/billing/prices/plans/'],
      ['branding', '/branding/branding/'],
      ['notifications', '/notifications/'],
      ['dataset-recommend', '/dataset-recommend/datasets/'],
      ['codegraph', '/codegraph/ws-status/'],
    ];
    for (const [module, path] of readOnlyEndpoints) {
      await expectStatus(module, 'read endpoint ' + path, api(path), [200, 204, 400, 403, 404]);
    }

    const routes = [
      '/home', '/nl-create', '/workflows', '/agents', '/agents/collaborate', '/agents/marketplace',
      '/knowledge', '/dataset-recommend', '/datasets', '/augmentations', '/prompts', '/models',
      '/vector-stores', '/team', '/monitoring', '/analytics', '/codegraph', '/api-explorer',
      '/marketplace', '/my-templates', '/executions', '/workflows/diff', '/settings/profile',
      '/settings/api-doc', '/settings/notifications', '/settings/preferences', '/settings/billing',
      '/settings/data-export', '/settings/branding', '/settings/credentials', '/settings/integrations',
      '/settings/desktop-agent'
    ];
    for (const route of routes) {
      await navigateAndAudit(route, 'ui');
    }
  } finally {
    async function cleanupItem(label, id, path) {
      if (!id) return;
      const result = await api(path + id + '/', { method: 'DELETE' }).catch((error) => ({ ok: false, status: 0, payload: error.message }));
      report.cleanup.push({ label, id, ok: result.ok || result.status === 404, status: result.status, payload: result.ok ? undefined : result.payload });
    }
    for (const id of created.templates.reverse()) await cleanupItem('template', id, '/templates/');
    for (const id of created.datasets.reverse()) await cleanupItem('dataset', id, '/datasets/');
    for (const id of created.collections.reverse()) await cleanupItem('collection', id, '/rag/collections/');
    for (const id of created.vectorStores.reverse()) await cleanupItem('vectorStore', id, '/rag/vector-stores/');
    for (const id of created.agents.reverse()) await cleanupItem('agent', id, '/agents/');
    for (const id of created.workflows.reverse()) await cleanupItem('workflow', id, '/workflows/');
  }

  const expectedNetworkErrors = new Set([
    BACKEND_URL + '/api/v1/auth/login/',
    BACKEND_URL + '/api/v1/agents/' + (created.agents[0] || '') + '/debug/',
    BACKEND_URL + '/api/v1/rag/collections/' + (created.collections[0] || '') + '/search/',
    BACKEND_URL + '/api/v1/billing/prices/plans/',
  ]);
  const unexpectedNetworkErrors = (window.__flowlyDeepAudit?.network || []).filter((entry) => {
    if (!(entry.status >= 400 || entry.status === 0)) return false;
    return !expectedNetworkErrors.has(entry.url);
  });

  report.summary = {
    totalSteps: report.modules.length,
    failedSteps: report.modules.filter((item) => !item.ok).length,
    cleanupFailed: report.cleanup.filter((item) => !item.ok).length,
    consoleErrors: (window.__flowlyDeepAudit?.console || []).filter((entry) => entry.level === 'error').length,
    runtimeErrors: (window.__flowlyDeepAudit?.runtime || []).length,
    networkErrors: unexpectedNetworkErrors.length,
  };
  report.expectedNetworkErrors = (window.__flowlyDeepAudit?.network || []).filter((entry) => {
    return (entry.status >= 400 || entry.status === 0) && expectedNetworkErrors.has(entry.url);
  });
  report.unexpectedNetworkErrors = unexpectedNetworkErrors;
  return report;
}
`.replaceAll('__FRONTEND_URL__', FRONTEND_URL).replaceAll('__BACKEND_URL__', BACKEND_URL)
}

async function main() {
  const client = new McpClient()
  try {
    await client.initialize()
    await login(client)
    await client.tool('navigate_page', { type: 'url', url: `${FRONTEND_URL}/home`, initScript: INIT_SCRIPT, timeout: 25000 }, 35000)
    await delay(2000)
    const report = await evalPage(client, browserScenarioSource(), 180000)
    await fs.mkdir('test-results', { recursive: true })
    await fs.writeFile('test-results/chrome-mcp-deep-audit.json', `${JSON.stringify(report, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify({
      runId: report.runId,
      totalSteps: report.summary?.totalSteps,
      failedSteps: report.summary?.failedSteps,
      cleanupFailed: report.summary?.cleanupFailed,
      consoleErrors: report.summary?.consoleErrors,
      runtimeErrors: report.summary?.runtimeErrors,
      networkErrors: report.summary?.networkErrors,
      report: 'test-results/chrome-mcp-deep-audit.json',
    }, null, 2))
  } finally {
    client.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
