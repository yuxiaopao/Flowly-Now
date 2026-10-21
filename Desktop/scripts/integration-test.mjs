/**
 * Desktop Agent integration test (REST register + WebSocket handshake).
 *
 * Usage:
 *   FLOWLY_CLOUD_URL=http://127.0.0.1:8000 node scripts/integration-test.mjs
 */
import WebSocket from 'ws';
import crypto from 'crypto';
import os from 'os';

const cloudUrl = (process.env.FLOWLY_CLOUD_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
const agentId = process.env.FLOWLY_AGENT_ID
  || `agent-test-${crypto.randomBytes(4).toString('hex')}`;

const apiBase = `${cloudUrl}/api/v1/agents/desktop`;

function fail(message) {
  console.error(`[FAIL] ${message}`);
  process.exit(1);
}

function pass(message) {
  console.log(`[PASS] ${message}`);
}

async function parseApiResponse(response) {
  const payload = await response.json();
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'data')) {
    if (!response.ok || (payload.code && payload.code >= 400)) {
      fail(payload.message || `API error ${payload.code || response.status}`);
    }
    return payload.data;
  }
  if (!response.ok) {
    fail(`HTTP ${response.status}: ${JSON.stringify(payload).slice(0, 200)}`);
  }
  return payload;
}

async function registerAgent() {
  const payload = {
    agent_id: agentId,
    display_name: `Integration Test (${os.hostname()})`,
    hostname: os.hostname(),
    platform: process.platform,
    gpu_info: { available: true, name: 'integration-test-gpu', deviceCount: 1 },
    gpu_available: true,
    gpu_name: 'integration-test-gpu',
    capabilities: ['yolo_training'],
    supports_yolo_training: true,
    cloud_url: cloudUrl,
  };

  const response = await fetch(`${apiBase}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await parseApiResponse(response);
  if (data.agent_id !== agentId) {
    fail(`register returned unexpected agent_id: ${data.agent_id}`);
  }
  pass(`register agent ${agentId}`);
  return data;
}

async function heartbeat() {
  const response = await fetch(`${apiBase}/heartbeat/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
    const ws = new WebSocket(wsUrl);
    const timer = setTimeout(() => {
      ws.terminate();
      reject(new Error(`WS timeout after ${timeoutMs}ms`));
    }, timeoutMs);

    ws.on('open', () => {
      ws.send(JSON.stringify({
        type: 'agent_registered',
        agentId,
        hostname: os.hostname(),
        platform: process.platform,
        gpu: { available: false },
        capabilities: ['yolo_training'],
      }));
    });

    ws.on('message', (raw) => {
      const msg = JSON.parse(raw.toString());
      if (msg.type === 'connected') {
        clearTimeout(timer);
        pass('websocket connected');
        ws.close();
        resolve(msg);
      } else if (msg.type === 'agent_registered_ack') {
        pass('agent_registered_ack received');
      }
    });

    ws.on('error', (err) => {
      clearTimeout(timer);
      reject(err);
    });

    ws.on('close', () => {
      clearTimeout(timer);
    });
  });
}

async function checkAvailableAgents() {
  const token = process.env.FLOWLY_API_TOKEN;
  if (!token) {
    pass('available endpoint skipped (set FLOWLY_API_TOKEN to verify listing)');
    return;
  }

  const response = await fetch(`${apiBase}/available/`, {
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });

  const agents = await parseApiResponse(response);
  const found = Array.isArray(agents) && agents.some((item) => item.agent_id === agentId);
  if (!found) {
    fail('registered agent not listed in /available/');
  }
  pass('agent visible in /available/');
}

async function main() {
  console.log(`Cloud URL: ${cloudUrl}`);
  console.log(`Agent ID:  ${agentId}`);

  await registerAgent();
  await heartbeat();
  await connectWebSocket();
  await checkAvailableAgents();

  console.log('\nAll desktop integration checks passed.');
}

main().catch((err) => fail(err.message));
