import { spawn } from 'node:child_process'
const NPX_CMD = process.env.NPX_CMD || 'D:\\nodejs\\npx.cmd'
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:5200'
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000'
const USERNAME = process.env.FLOWLY_E2E_USERNAME || 'nlwftest@flowly.test'
const PASSWORD = process.env.FLOWLY_E2E_PASSWORD || 'Test123456!'
function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)) }
class McpClient {
  constructor() {
    this.nextId = 1
    this.pending = new Map()
    this.buffer = ''
    const entry = process.env.CHROME_MCP_ENTRY
    const browserUrl = process.env.CHROME_MCP_BROWSER_URL || 'http://127.0.0.1:9222'
    const workspace = process.env.CHROME_MCP_WORKSPACE || 'E:/Flowly-now'
    const flags = [`--browserUrl=${browserUrl}`, '--no-usage-statistics', '--no-performance-crux', `--workspace=${workspace}`]
    this.proc = spawn(entry ? process.execPath : 'cmd.exe', entry ? [entry, ...flags] : ['/d', '/s', '/c', `${NPX_CMD} -y chrome-devtools-mcp@latest ${flags.join(' ')}`], {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
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

  async tool(name, args = {}, timeoutMs = 30000) {
    const params = this.pageTools?.has(name) ? { pageId: this.pageId, ...args } : args
    const result = await this.request('tools/call', { name, arguments: params }, timeoutMs)
    if (result.isError) throw new Error(resultText(result))
    if (name === 'new_page') {
      const pages = await this.request('tools/call', {name:'list_pages',arguments:{}})
      const text = resultText(pages)
      const matches = [...text.matchAll(/^(\d+):\s+(.+)$/gm)]
      const selected = matches.find(match=>match[2].includes('[selected]')) || matches.findLast(match=>match[2].includes(args.url))
      if (!selected) throw new Error(`Cannot select page: ${text}`)
      this.pageId = Number(selected[1])
    }
    return result
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
  const result = await client.tool('evaluate_script', { function: fn, waitForStableDom: false }, timeoutMs)
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


export { McpClient, evalPage, login, delay, resultText, FRONTEND_URL, BACKEND_URL }
