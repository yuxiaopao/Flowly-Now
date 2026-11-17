const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { createRequire } = require('node:module');

function fixture(options = {}) {
  const filename = path.resolve(__dirname, '../main.js');
  const localRequire = createRequire(filename);
  const handlers = new Map();
  const values = new Map([['apiToken', 'fixture-access'], ['cloudUrl', 'http://cloud.test'], ['agentId', 'fixture-agent']]);
  const calls = [];
  const webContents = { mainFrame: { url: 'http://127.0.0.1:5200/home' }, send() {} };
  const window = { webContents, isDestroyed: () => false };
  const noop = () => {};
  const fileSystem = { ...fs };
  const childProcess = { ...localRequire('child_process'), execFileSync: command => options.version?.(command) || 'Python 3.12.10',
    spawn: () => { throw new Error('unexpected subprocess start'); } };
  const electron = { app: { whenReady: () => ({ then: noop }), on: noop, getVersion: () => 'test' },
    ipcMain: { handle: (name, callback) => handlers.set(name, callback) },
    BrowserWindow: class {}, dialog: {}, shell: {} };
  class Store { get(key) { return values.get(key); } set(key, value) { values.set(key, value); } delete(key) { values.delete(key); } }
  const logger = { transports: { file: {}, console: {} }, info: noop, debug: noop, warn: noop, error: noop };
  const context = vm.createContext({
    require: name => name === 'electron' ? electron : name === 'electron-store' ? Store :
      name === 'electron-log' ? logger : name === 'fs' ? fileSystem : name === 'child_process' ? childProcess :
        name === './training-monitor/service' ? {} : localRequire(name),
    __dirname: path.dirname(filename), process: { ...process, on: noop }, Buffer, URL,
    setInterval: () => 1, clearInterval: noop, setTimeout: () => 1, clearTimeout: noop,
    fetch: async (url, options) => { calls.push({ url, options }); return { ok: true, json: async () => ({ ok: true }) }; },
    windowFixture: window,
  });
  vm.runInContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  if (fs.existsSync(path.resolve(__dirname, '../trusted-renderer.js'))) {
    localRequire('./trusted-renderer').registerTrustedRenderer(window, { mode: 'url', url: 'http://127.0.0.1:5200' });
  }
  vm.runInContext('mainWindow = windowFixture; detectGPU = () => ({ available: false }); setupIPC();', context);
  return { context, handlers, values, calls, fileSystem, event: { sender: webContents, senderFrame: webContents.mainFrame } };
}

test('cloud registration and heartbeat carry the current login credential', async () => {
  const f = fixture();
  await vm.runInContext('registerAgentViaRest("http://cloud.test", "fixture-agent")', f.context);
  await vm.runInContext('sendHeartbeat()', f.context);
  assert.equal(f.calls.length, 2);
  for (const call of f.calls) assert.equal(call.options.headers.Authorization, 'Bearer fixture-access');
});

test('logged-out cloud registration does not send an anonymous request', async () => {
  const f = fixture();
  f.values.delete('apiToken');
  await assert.rejects(vm.runInContext('registerAgentViaRest("http://cloud.test", "fixture-agent")', f.context), /登录/);
  assert.equal(f.calls.length, 0);
});

test('every main IPC rejects a different window or a subframe before doing work', async () => {
  const f = fixture();
  for (const [channel, handler] of f.handlers) {
    await assert.rejects(async () => handler({ ...f.event, sender: {} }), /主页面/, channel);
    await assert.rejects(async () => handler({ ...f.event, senderFrame: {} }), /主页面/, channel);
  }
});

test('logout disconnects cloud credentials as well as its socket', async () => {
  const f = fixture();
  await f.handlers.get('agent:disconnect')(f.event);
  assert.equal(f.values.get('apiToken'), null);
});

test('legacy or differently owned agent identity is replaced without claiming it', async () => {
  const f = fixture();
  const ids = [];
  f.context.fetch = async (_url, options) => {
    ids.push(JSON.parse(options.body).agent_id);
    return ids.length === 1
      ? { ok: false, status: 409, json: async () => ({ code: 409, data: null, errors: { code: 'agent_identity_conflict' } }) }
      : { ok: true, json: async () => ({ data: { ok: true } }) };
  };
  vm.runInContext('connectToCloud = () => {};', f.context);
  await f.handlers.get('agent:connect')(f.event, { cloudUrl: 'http://cloud.test', agentId: 'fixture-agent', apiToken: 'fixture-access' });
  assert.equal(ids.length, 2);
  assert.equal(ids[0], 'fixture-agent');
  assert.notEqual(ids[1], ids[0]);
  assert.equal(f.values.get('agentId'), ids[1]);
});

test('environment preparation requires local process permission first', async () => {
  const f = fixture();
  f.fileSystem.existsSync = () => true;
  vm.runInContext(`
    ensureRuntimePermission = async () => { throw new Error('permission denied'); };
    ensureSiteEnv = async () => { throw new Error('should not install'); };
  `, f.context);
  const result = await f.handlers.get('runtime:prepareEnv')(f.event, { outputDir: 'fixture-project' });
  assert.equal(result.success, false);
  assert.equal(result.error, 'permission denied');
});

test('site startup stops on environment failure without starting system Python', async () => {
  const f = fixture();
  f.fileSystem.existsSync = () => true;
  f.fileSystem.accessSync = () => {};
  vm.runInContext(`
    ensureRuntimePermission = async () => ({});
    ensureSiteEnv = async () => ({ error: 'environment install failed', pythonExecutable: 'fixture-python' });
  `, f.context);
  const result = await f.handlers.get('runtime:startSite')(f.event, { outputDir: 'fixture-project', port: 54321 });
  assert.equal(result.success, false);
  assert.equal(result.error, 'environment install failed');
});

test('environment installation failures never return a system interpreter fallback', async () => {
  const f = fixture();
  f.fileSystem.existsSync = () => false;
  vm.runInContext(`
    resolvePythonExecutable = () => 'fixture-python';
    runCommand = async () => { throw new Error('venv creation failed'); };
  `, f.context);
  const result = await vm.runInContext('ensureSiteEnv("fixture-backend")', f.context);
  assert.equal(result.error, 'venv creation failed');
  assert.equal(result.pythonExecutable, undefined);
});

test('changing requirements invalidates the environment marker', async () => {
  const f = fixture();
  let requirements = 'flask==3.0.0';
  let marker = '{}';
  let installations = 0;
  f.context.installation = () => { installations++; };
  f.fileSystem.existsSync = () => true;
  f.fileSystem.readFileSync = target => target.endsWith('requirements.txt') ? requirements : marker;
  f.fileSystem.writeFileSync = (_target, data) => { marker = data; };
  vm.runInContext(`resolvePythonExecutable = () => 'fixture-python'; runCommand = async () => installation();`, f.context);
  await vm.runInContext('ensureSiteEnv("fixture-backend")', f.context);
  assert.equal(installations, 1);
  await vm.runInContext('ensureSiteEnv("fixture-backend")', f.context);
  assert.equal(installations, 1);
  requirements = 'flask==3.1.0';
  await vm.runInContext('ensureSiteEnv("fixture-backend")', f.context);
  assert.equal(installations, 2);
});

test('an old virtual environment cannot be marked ready for a different Python version', async () => {
  const f = fixture({ version: command => command === 'fixture-python' ? 'Python 3.13.0' : 'Python 3.12.10' });
  f.fileSystem.existsSync = () => true;
  vm.runInContext(`resolvePythonExecutable = () => 'fixture-python';`, f.context);
  const result = await vm.runInContext('ensureSiteEnv("fixture-backend")', f.context);
  assert.match(result.error, /现有虚拟环境/);
  assert.equal(result.pythonExecutable, undefined);
});

test('cancelling a queued cloud job acknowledges it without stopping another local job', () => {
  const f = fixture();
  const messages = [];
  f.context.captureMessage = message => messages.push(message);
  vm.runInContext(`
    sendToCloud = message => captureMessage(message);
    stopTraining = () => { throw new Error('must not stop another job'); };
    trainingState.running = true;
    trainingState.jobId = 'current-job';
    handleCloudMessage({type:'training_command',payload:{command:'stop',jobId:'queued-target'}});
  `, f.context);
  assert.equal(messages.length, 1);
  assert.equal(messages[0].type, 'training_cancelled');
  assert.equal(messages[0].jobId, 'queued-target');
});
