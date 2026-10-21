import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'

const FRONTEND_URL = process.env.FRONTEND_URL || 'http://127.0.0.1:5200'
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const USERNAME = process.env.FLOWLY_E2E_USERNAME || 'nlwftest@flowly.test'
const PASSWORD = process.env.FLOWLY_E2E_PASSWORD || 'Test123456!'
const NPX_CMD = process.env.NPX_CMD || 'D:\\nodejs\\npx.cmd'
const MAX_CLICKS_PER_ROUTE = Number(process.env.FLOWLY_AUDIT_MAX_CLICKS || 45)
const CLICK_TIMEOUT_MS = Number(process.env.FLOWLY_AUDIT_CLICK_TIMEOUT_MS || 45000)

const DEFAULT_ROUTES = [
  '/home',
  '/nl-create',
  '/workflows',
  '/workflows/new',
  '/agents',
  '/agents/new',
  '/agents/collaborate',
  '/agents/marketplace',
  '/knowledge',
  '/dataset-recommend',
  '/datasets',
  '/augmentations',
  '/prompts',
  '/models',
  '/vector-stores',
  '/team',
  '/team/join',
  '/monitoring',
  '/analytics',
  '/codegraph',
  '/api-explorer',
  '/marketplace',
  '/my-templates',
  '/executions',
  '/workflows/diff',
  '/settings/profile',
  '/settings/api-doc',
  '/settings/notifications',
  '/settings/preferences',
  '/settings/billing',
  '/settings/data-export',
  '/settings/branding',
  '/settings/credentials',
  '/settings/integrations',
  '/settings/desktop-agent',
]

const ROUTES = process.env.FLOWLY_AUDIT_ROUTES
  ? process.env.FLOWLY_AUDIT_ROUTES.split(',').map((route) => route.trim()).filter(Boolean)
  : DEFAULT_ROUTES

const INIT_SCRIPT = String.raw`
(() => {
  window.__flowlyAudit = { console: [], runtime: [], network: [] };
  const push = (bucket, payload) => {
    try { window.__flowlyAudit[bucket].push({ ts: Date.now(), ...payload }); } catch (_) {}
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
  const OriginalXHR = window.XMLHttpRequest;
  window.XMLHttpRequest = function() {
    const xhr = new OriginalXHR();
    let method = '';
    let url = '';
    const originalOpen = xhr.open;
    xhr.open = function(nextMethod, nextUrl, ...rest) {
      method = nextMethod;
      url = nextUrl;
      return originalOpen.call(xhr, nextMethod, nextUrl, ...rest);
    };
    xhr.addEventListener('loadend', () => {
      if (xhr.status >= 400) push('network', { transport: 'xhr', method, status: xhr.status, url: String(url || '') });
    });
    xhr.addEventListener('error', () => push('network', { transport: 'xhr', method, status: 0, url: String(url || '') }));
    return xhr;
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
      clientInfo: { name: 'flowly-click-audit', version: '1.0.0' },
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

async function auditRoute(client, route) {
  const url = `${FRONTEND_URL}${route}`
  const item = { route, url, pageOk: false, clicked: [], skipped: [], errors: [], warnings: [], networkErrors: [] }
  await client.tool('navigate_page', { type: 'url', url, initScript: INIT_SCRIPT, timeout: 25000 }, 35000)
  await delay(2200)
  const initial = await evalPage(client, `async () => {
    const visible = (el) => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 2 && rect.height > 2;
    };
    const selectors = 'button, [role="button"], a[href], input[type="button"], input[type="submit"], .el-dropdown-link, .el-switch, .el-tabs__item, .el-menu-item';
    const elements = [...document.querySelectorAll(selectors)].filter(visible).slice(0, 80);
    return {
      title: document.title,
      path: location.pathname + location.search,
      bodyText: document.body.innerText.slice(0, 500),
      clickableCount: elements.length,
      controls: elements.map((el, index) => ({
        index,
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        text: (el.innerText || el.value || el.getAttribute('aria-label') || el.title || el.href || '').replace(/\s+/g, ' ').trim().slice(0, 80),
        disabled: Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true'),
        href: el.href || '',
        classes: el.className || ''
      })),
      audit: window.__flowlyAudit || null,
    };
  }`)
  item.initial = initial
  item.pageOk = Boolean(initial?.bodyText) && !/404|页面不存在|Page Not Found/i.test(initial.bodyText)

  const clickResult = await evalPage(client, `async () => {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const visible = (el) => {
      const style = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 2 && rect.height > 2;
    };
    const closeOverlays = async () => {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      await sleep(120);
      for (const el of [...document.querySelectorAll('.el-dialog__close, .el-drawer__close-btn, .el-message-box__close')].filter(visible).slice(0, 4)) {
        el.click();
        await sleep(120);
      }
      for (const el of [...document.querySelectorAll('.el-message-box .el-button, .el-dialog .el-button')].filter(visible)) {
        const text = (el.innerText || '').trim();
        if (/取消|关闭|Cancel|Close/i.test(text)) {
          el.click();
          await sleep(120);
          break;
        }
      }
    };
    const selectors = 'button, [role="button"], a[href], input[type="button"], input[type="submit"], .el-dropdown-link, .el-switch, .el-tabs__item, .el-menu-item';
    const destructive = /删除|移除|退出|注销|登出|清空|重置|解绑|停用|禁用|Delete|Remove|Logout|Sign out|Reset|Disable/i;
    const submitLike = /保存|提交|创建|新建|导入|导出|上传|发送|执行|运行|发布|购买|邀请|复制|Save|Submit|Create|Import|Export|Upload|Send|Run|Execute|Publish|Invite|Duplicate/i;
    const clicked = [];
    const skipped = [];
    const originalUrl = location.href;
    let elements = [...document.querySelectorAll(selectors)].filter(visible);
    for (let i = 0; i < Math.min(elements.length, ${MAX_CLICKS_PER_ROUTE}); i++) {
      elements = [...document.querySelectorAll(selectors)].filter(visible);
      const el = elements[i];
      if (!el) continue;
      const label = (el.innerText || el.value || el.getAttribute('aria-label') || el.title || el.href || '').replace(/\s+/g, ' ').trim().slice(0, 80) || el.tagName;
      if (el.disabled || el.getAttribute('aria-disabled') === 'true') {
        skipped.push({ label, reason: 'disabled' });
        continue;
      }
      if (destructive.test(label)) {
        skipped.push({ label, reason: 'destructive' });
        continue;
      }
      if (submitLike.test(label) && !/新建对话|新增对话|查看|详情|筛选|搜索|展开|收起|更多|设置|编辑|预览|Test|测试|复制|Copy/i.test(label)) {
        skipped.push({ label, reason: 'mutating-submit' });
        continue;
      }
      const beforePath = location.pathname + location.search + location.hash;
      const beforeDialogs = [...document.querySelectorAll('.el-dialog, .el-message-box, .el-drawer')].filter(visible).length;
      try {
        el.scrollIntoView({ block: 'center', inline: 'center' });
        await sleep(80);
        el.click();
        await sleep(450);
        const afterPath = location.pathname + location.search + location.hash;
        const overlays = [...document.querySelectorAll('.el-dialog, .el-message-box, .el-drawer, .el-popper')].filter(visible).map((node) => (node.innerText || node.className || '').replace(/\s+/g, ' ').trim().slice(0, 80));
        clicked.push({ label, beforePath, afterPath, openedOverlay: overlays.length > beforeDialogs, overlays: overlays.slice(0, 3) });
        await closeOverlays();
        if (location.href !== originalUrl && history.length > 1) {
          history.back();
          await sleep(600);
        }
      } catch (error) {
        skipped.push({ label, reason: 'click-error', message: error?.message || String(error) });
        await closeOverlays();
      }
    }
    return { clicked, skipped, audit: window.__flowlyAudit || null, finalPath: location.pathname + location.search };
  }`, CLICK_TIMEOUT_MS)

  item.clicked = clickResult?.clicked || []
  item.skipped = clickResult?.skipped || []
  const audit = clickResult?.audit || initial?.audit || {}
  item.errors = [...(audit.runtime || []), ...(audit.console || []).filter((entry) => entry.level === 'error')]
  item.warnings = (audit.console || []).filter((entry) => entry.level === 'warn')
  item.networkErrors = audit.network || []
  return item
}

async function main() {
  const client = new McpClient()
  try {
    await client.initialize()
    await login(client)
    const results = []
    for (const route of ROUTES) {
      try {
        const result = await auditRoute(client, route)
        results.push(result)
        const status = result.pageOk && result.errors.length === 0 && result.networkErrors.length === 0 ? 'OK' : 'CHECK'
        console.log(`${status} ${route} controls=${result.initial?.clickableCount || 0} clicked=${result.clicked.length} skipped=${result.skipped.length} errors=${result.errors.length} net=${result.networkErrors.length}`)
      } catch (error) {
        results.push({ route, pageOk: false, fatal: error.message, clicked: [], skipped: [], errors: [{ message: error.message }], warnings: [], networkErrors: [] })
        console.log(`FAIL ${route} ${error.message}`)
      }
    }
    const summary = {
      generatedAt: new Date().toISOString(),
      frontendUrl: FRONTEND_URL,
      backendUrl: BACKEND_URL,
      routeCount: results.length,
      totalClicked: results.reduce((sum, item) => sum + item.clicked.length, 0),
      totalSkipped: results.reduce((sum, item) => sum + item.skipped.length, 0),
      routesWithErrors: results.filter((item) => !item.pageOk || item.fatal || item.errors.length || item.networkErrors.length).map((item) => item.route),
      results,
    }
    await fs.mkdir('test-results', { recursive: true })
    await fs.writeFile('test-results/chrome-mcp-click-audit.json', `${JSON.stringify(summary, null, 2)}\n`, 'utf8')
    console.log(JSON.stringify({
      routeCount: summary.routeCount,
      totalClicked: summary.totalClicked,
      totalSkipped: summary.totalSkipped,
      routesWithErrors: summary.routesWithErrors,
      report: 'test-results/chrome-mcp-click-audit.json',
    }, null, 2))
  } finally {
    client.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
