import http from 'node:http';

const BASE_URL = 'http://127.0.0.1:5200';
const API_BASE = 'http://127.0.0.1:8000/api/v1';

function getJson(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(error);
        }
      });
    }).on('error', reject);
  });
}

async function getPage() {
  const pages = (await getJson('http://127.0.0.1:9222/json/list'))
    .filter((page) => page.type === 'page' && page.webSocketDebuggerUrl);
  const flowly = pages.find((page) => page.url.startsWith(BASE_URL)) || pages[0];
  if (!flowly) {
    throw new Error('No Chrome page target found on port 9222');
  }
  return flowly;
}

function connect(wsUrl) {
  const socket = new WebSocket(wsUrl);
  let seq = 0;
  const pending = new Map();

  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(JSON.stringify(message.error)));
    else resolve(message.result);
  });

  return new Promise((resolve, reject) => {
    socket.addEventListener('open', () => {
      resolve({
        send(method, params = {}) {
          const id = ++seq;
          socket.send(JSON.stringify({ id, method, params }));
          return new Promise((res, rej) => pending.set(id, { resolve: res, reject: rej }));
        },
        close() {
          socket.close();
        },
      });
    });
    socket.addEventListener('error', reject);
  });
}

async function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitFor(send, expression, timeoutMs = 30000) {
  const start = Date.now();
  let last;
  while (Date.now() - start < timeoutMs) {
    const result = await evaluate(send, expression);
    last = result;
    if (result) return result;
    await delay(500);
  }
  throw new Error(`Timed out waiting for expression. Last value: ${JSON.stringify(last)}`);
}

async function evaluate(send, expression) {
  const result = await send('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || 'Runtime evaluation failed');
  }
  return result.result?.value;
}

async function navigate(send, url) {
  await send('Page.navigate', { url });
  await waitFor(send, 'document.readyState === "complete" || document.readyState === "interactive"', 30000);
  await delay(800);
}

const runId = `visible-nl-step-chain-${Date.now()}`;
const prompt = `${runId} 请一步一步创建一个模型训练到识别网站的工作流：训练方式选择 YOLO，基础权重 yolov8n.pt，使用本地 YOLO 数据集，训练后生成 Flask+Vue+Mysql 识别网站，必须包含图片识别、视频识别、事实识别、历史记录、前端搭建、后端搭建、UI 美化、环境配置、自查 QA、代码复查、预览和 Agent 对话节点。`;

const page = await getPage();
const client = await connect(page.webSocketDebuggerUrl);
const { send } = client;

try {
  await send('Runtime.enable');
  await send('Page.enable');

  await navigate(send, `${BASE_URL}/nl-workflow`);
  const auth = await evaluate(send, `(() => {
    const keys = Object.keys(localStorage);
    const tokenKey = keys.find((key) => /access|token/i.test(key));
    return { url: location.href, title: document.title, tokenKey, hasToken: Boolean(tokenKey && localStorage.getItem(tokenKey)) };
  })()`);

  const createResult = await evaluate(send, `fetch('${API_BASE}/nl-workflow/sessions/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('access_token') ? { Authorization: 'Bearer ' + localStorage.getItem('access_token') } : {}),
      ...(localStorage.getItem('token') ? { Authorization: 'Bearer ' + localStorage.getItem('token') } : {}),
    },
    body: JSON.stringify({
      name: '${runId} 模型训练识别网站工作流',
      description: ${JSON.stringify(prompt)},
      mode: 'generate',
      model: 'agnes-2.0-flash',
    }),
  }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }))`);
  if (createResult.status >= 400) {
    throw new Error(`NL create failed: ${JSON.stringify(createResult)}`);
  }
  const sessionId = createResult.body?.session_id || createResult.body?.data?.session_id;
  const workflowJson = createResult.body?.workflow_json || createResult.body?.data?.workflow_json;
  if (!sessionId || !workflowJson) {
    throw new Error(`NL create returned incomplete payload: ${JSON.stringify(createResult)}`);
  }

  await navigate(send, `${BASE_URL}/nl-workflow?session=${sessionId}`);
  await delay(1000);

  const saveResult = await evaluate(send, `fetch('${API_BASE}/nl-workflow/sessions/${sessionId}/confirm/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('access_token') ? { Authorization: 'Bearer ' + localStorage.getItem('access_token') } : {}),
      ...(localStorage.getItem('token') ? { Authorization: 'Bearer ' + localStorage.getItem('token') } : {}),
    },
  }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }))`);
  if (saveResult.status >= 400) {
    throw new Error(`Save failed: ${JSON.stringify(saveResult)}`);
  }
  const workflowId = saveResult.body?.workflow_id || saveResult.body?.data?.workflow_id;
  if (!workflowId) {
    throw new Error(`Save returned no workflow id: ${JSON.stringify(saveResult)}`);
  }

  await navigate(send, `${BASE_URL}/workflows?search=${encodeURIComponent(runId)}`);
  await delay(1000);

  const validateResult = await evaluate(send, `fetch('${API_BASE}/workflows/${workflowId}/validate/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('access_token') ? { Authorization: 'Bearer ' + localStorage.getItem('access_token') } : {}),
      ...(localStorage.getItem('token') ? { Authorization: 'Bearer ' + localStorage.getItem('token') } : {}),
    },
  }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }))`);
  if (validateResult.status >= 400) {
    throw new Error(`Validate request failed: ${JSON.stringify(validateResult)}`);
  }

  const executeResult = await evaluate(send, `fetch('${API_BASE}/workflows/${workflowId}/execute/', {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(localStorage.getItem('access_token') ? { Authorization: 'Bearer ' + localStorage.getItem('access_token') } : {}),
      ...(localStorage.getItem('token') ? { Authorization: 'Bearer ' + localStorage.getItem('token') } : {}),
    },
    body: JSON.stringify({ input_data: {}, trigger_type: 'manual', is_async: false }),
  }).then(async (r) => ({ status: r.status, body: await r.json().catch(() => null) }))`);
  const executionId = executeResult.body?.execution_id || executeResult.body?.id || executeResult.body?.data?.execution_id;
  if (executionId) {
    await navigate(send, `${BASE_URL}/workflows/${workflowId}/execute?execution=${executionId}`);
  }

  const summary = {
    runId,
    auth,
    step1_create: {
      status: createResult.status,
      sessionId,
      mode: createResult.body?.mode || createResult.body?.data?.mode,
      model: createResult.body?.model || createResult.body?.data?.model,
      nodeTypes: (workflowJson.nodes || []).map((node) => node.type),
      nodeCount: (workflowJson.nodes || []).length,
      edgeCount: (workflowJson.edges || []).length,
    },
    step2_save: {
      status: saveResult.status,
      workflowId,
      name: saveResult.body?.workflow?.name || saveResult.body?.name || saveResult.body?.data?.workflow?.name,
    },
    step3_validate: {
      status: validateResult.status,
      valid: validateResult.body?.valid,
      errors: validateResult.body?.errors,
      warnings: validateResult.body?.warnings,
    },
    step4_execute: {
      status: executeResult.status,
      executionId,
      bodyStatus: executeResult.body?.status || executeResult.body?.data?.status,
      error: executeResult.body?.error || executeResult.body?.error_message || executeResult.body?.data?.error,
    },
    finalUrl: await evaluate(send, 'location.href'),
  };
  console.log(JSON.stringify(summary, null, 2));
} finally {
  client.close();
}
