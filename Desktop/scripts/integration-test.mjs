/**
 * Desktop Agent integration test (REST register + WebSocket handshake).
 *
 * Usage:
 *   FLOWLY_ISOLATED_QA=1 FLOWLY_CLOUD_URL=http://127.0.0.1:8000
 *   FLOWLY_API_TOKEN=<isolated-user-jwt> node scripts/integration-test.mjs
 * Or supply FLOWLY_E2E_USERNAME / FLOWLY_E2E_PASSWORD for the isolated login.
 */
import WebSocket from 'ws';
import crypto from 'crypto';
import os from 'os';

const cloudUrl = (process.env.FLOWLY_CLOUD_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
const agentId = process.env.FLOWLY_AGENT_ID
  || `agent-test-${crypto.randomBytes(4).toString('hex')}`;

const apiBase = `${cloudUrl}/api/v1/agents/desktop`;
let token = process.env.FLOWLY_API_TOKEN?.trim() || '';
let registeredId;

function fail(message) {
  throw new Error(String(message).replaceAll(token || '\0', '[redacted]'));
}

function pass(message) {
  console.log(`[PASS] ${message}`);
}

async function parseApiResponse(response) {
  const payload = await response.json();
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'data')) {
    if (!response.ok || (payload.code && payload.code >= 400)) {
      fail(`API ${response.status}: ${payload.message || 'request rejected'}`);
    }
    return payload.data;
  }
  if (!response.ok) {
    fail(`HTTP ${response.status}: request rejected`);
  }
  return payload;
}

function authHeaders() {
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

async function requireIsolatedBackend() {
  const url = new URL(cloudUrl);
  if (process.env.FLOWLY_ISOLATED_QA !== '1' || !['127.0.0.1', 'localhost'].includes(url.hostname)
      || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    fail('Integration writes require FLOWLY_ISOLATED_QA=1 and an explicit loopback QA backend');
  }
  const response = await fetch(`${cloudUrl}/api/v1/__isolated-qa__/`);
  const marker = response.ok ? await response.json() : null;
  if (marker?.isolated !== true) fail('Refusing writes without the backend isolated-fixture marker');
  pass('isolated backend marker confirmed');
}

async function authenticate() {
  if (!token) {
    const username = process.env.FLOWLY_E2E_USERNAME, password = process.env.FLOWLY_E2E_PASSWORD;
    if (!username || !password) fail('Provide an isolated FLOWLY_API_TOKEN or FLOWLY_E2E_USERNAME / FLOWLY_E2E_PASSWORD');
    const response = await fetch(`${cloudUrl}/api/v1/auth/login/`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }),
    });
    const data = await parseApiResponse(response);
    if (!data.access) fail('Isolated login did not return an access token');
    token = data.access;
  }
  pass('isolated authentication available (token omitted)');
}

async function checkAnonymousDenied() {
  const response = await fetch(`${apiBase}/register/`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ agent_id: agentId }),
  });
  if (![401, 403].includes(response.status)) fail('Unauthenticated agent registration was not rejected');
  pass(`anonymous registration denied (${response.status})`);
}

async function registerAgent() {
  const payload = {
    agent_id: agentId,
    display_name: `Integration Test (${os.hostname()})`,
    hostname: os.hostname(),
    platform: process.platform,
    gpu_info: { available: false, deviceCount: 0 },
    gpu_available: false,
    gpu_name: '',
    capabilities: [],
    supports_yolo_training: false,
    cloud_url: cloudUrl,
  };

  const response = await fetch(`${apiBase}/register/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });

  const data = await parseApiResponse(response);
  if (data.agent_id !== agentId) {
    fail(`register returned unexpected agent_id: ${data.agent_id}`);
  }
  registeredId = data.id;
  pass(`register agent ${agentId}`);
  return data;
}

async function heartbeat() {
  const response = await fetch(`${apiBase}/heartbeat/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ agent_id: agentId, status: 'online' }),
  });

  const heartbeatData = await parseApiResponse(response);
  if (!heartbeatData?.ok) {
    fail('heartbeat did not return ok');
  }
  pass('heartbeat');
}

function connectWebSocket(timeoutMs = 10000) {
  return new Promise((resolve, reject) => {
    const wsUrl = `${cloudUrl.replace('http://', 'ws://').replace('https://', 'wss://')}/ws/agent/${agentId}/`;
    const ws = new WebSocket(wsUrl, { headers: { Authorization: `Bearer ${token}` } });
    let connected = false, acknowledged = false, finished = false;
    function finish(error) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (ws.readyState === WebSocket.OPEN) ws.close();
      else if (ws.readyState !== WebSocket.CLOSED) ws.terminate();
      if (error) reject(error);
      else resolve({ connected, acknowledged });
    }
    const timer = setTimeout(() => finish(new Error(`WS timeout after ${timeoutMs}ms`)), timeoutMs);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        type: 'agent_registered',
        agentId,
        hostname: os.hostname(),
        platform: process.platform,
        gpu: { available: false },
        capabilities: [],
      }));
    });

    ws.on('message', (raw) => {
      let msg;
      try { msg = JSON.parse(raw.toString()); }
      catch { finish(new Error('WebSocket returned malformed JSON')); return; }
      if (msg.type === 'connected') {
        if (msg.agent_id !== agentId) { finish(new Error('WebSocket connected to an unexpected agent identity')); return; }
        connected = true;
        pass('websocket connected');
      } else if (msg.type === 'agent_registered_ack') {
        if (msg.agent_id !== agentId) { finish(new Error('WebSocket acknowledged an unexpected agent identity')); return; }
        acknowledged = true;
        pass('agent_registered_ack received');
      }
      if (connected && acknowledged) finish();
    });

    ws.on('error', (err) => {
      finish(new Error(`Authenticated WebSocket failed: ${err.message.replaceAll(token, '[redacted]')}`));
    });

    ws.on('close', code => {
      if (!finished) finish(new Error(`WebSocket closed before the authenticated handshake completed (${code})`));
    });
  });
}

async function checkAvailableAgents() {
  const listing = await parseApiResponse(await fetch(`${apiBase}/?page_size=100`, { headers: authHeaders() }));
  const rows = Array.isArray(listing) ? listing : listing.results;
  if (!rows?.some(item => item.id === registeredId && item.agent_id === agentId)) fail('Owned device is missing from the authenticated listing');
  const response = await fetch(`${apiBase}/available/`, {
    headers: authHeaders(),
  });

  const agents = await parseApiResponse(response);
  const found = Array.isArray(agents) && agents.some((item) => item.agent_id === agentId);
  if (found) fail('The no-GPU fixture was incorrectly advertised as training-available');
  pass('owned device listed; no-GPU fixture correctly excluded from training availability');
}

async function main() {
  console.log(`Cloud URL: ${cloudUrl}`);
  console.log(`Agent ID:  ${agentId}`);

  await requireIsolatedBackend();
  await authenticate();
  await checkAnonymousDenied();
  try {
    await registerAgent();
    await heartbeat();
    await connectWebSocket();
    await checkAvailableAgents();
  } finally {
    if (registeredId) {
      const response = await fetch(`${apiBase}/${encodeURIComponent(registeredId)}/`, { method: 'DELETE', headers: authHeaders() });
      if (!response.ok) fail(`Could not clean up the owned fixture device (${response.status})`);
      pass('owned fixture device removed');
    }
  }

  console.log('\nAll desktop integration checks passed.');
}

main().catch(err => {
  console.error(`[FAIL] ${String(err.message).replaceAll(token || '\0', '[redacted]')}`);
  process.exitCode = 1;
});
