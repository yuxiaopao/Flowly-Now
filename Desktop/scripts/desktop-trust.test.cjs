const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { EventEmitter } = require('node:events');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');

function fixture({ packaged = false } = {}) {
  const filename = path.resolve(__dirname, '../main.js');
  const localRequire = createRequire(filename);
  const handlers = new Map();
  const values = new Map([['apiToken', 'fixture-token'], ['cloudUrl', 'http://cloud.test'], ['agentId', 'fixture-agent']]);
  const sockets = [];
  const external = [];
  const timers = new Map();
  let timerId = 0;
  class Socket extends EventEmitter {
    static OPEN = 1;
    static CONNECTING = 0;
    readyState = 0;
    sent = [];
    constructor(url, options) { super(); this.url = url; this.options = options; sockets.push(this); }
    open() { this.readyState = 1; this.emit('open'); }
    send(data) { this.sent.push(data); }
    close() { this.readyState = 2; }
    terminate() { this.readyState = 3; }
  }
  class Window extends EventEmitter {
    constructor() {
      super();
      this.webContents = new EventEmitter();
      this.webContents.mainFrame = { url: '' };
      this.webContents.send = () => {};
      this.webContents.setWindowOpenHandler = callback => { this.windowOpenHandler = callback; };
      this.webContents.openDevTools = () => {};
    }
    isDestroyed() { return false; }
    show() {}
    focus() {}
    loadURL(url) { this.webContents.mainFrame.url = url; }
    loadFile(file, options) { this.webContents.mainFrame.url = `${pathToFileURL(file).href}#${options.hash}`; }
  }
  const electron = {
    app: { isPackaged: packaged, whenReady: () => ({ then() {} }), on() {}, getVersion: () => 'fixture' },
    BrowserWindow: Window, ipcMain: { handle: (channel, callback) => handlers.set(channel, callback) },
    dialog: { showErrorBox() {} }, shell: { openExternal: async url => { external.push(url); } },
  };
  class Store { get(key) { return values.get(key); } set(key, value) { values.set(key, value); } delete(key) { values.delete(key); } }
  const noop = () => {};
  const logger = { transports: { file: {}, console: {} }, info: noop, debug: noop, warn: noop, error: noop };
  const context = vm.createContext({
    require: name => name === 'electron' ? electron : name === 'electron-store' ? Store : name === 'electron-log' ? logger
      : name === 'ws' ? Socket : name === 'fs' ? { ...fs, existsSync: () => packaged }
      : name === './training-monitor/service' ? {} : localRequire(name),
    __dirname: path.dirname(filename), process: { ...process, env: { ...process.env, FLOWLY_DEV_SERVER_URL: 'http://127.0.0.1:5200' }, argv: ['node', 'main.js'], on: noop },
    Buffer, URL,
    setInterval: () => ++timerId, clearInterval: noop,
    setTimeout: callback => { const id = ++timerId; timers.set(id, callback); return id; }, clearTimeout: id => timers.delete(id),
    fetch: async () => ({ ok: true, json: async () => ({ ok: true }) }),
  });
  vm.runInContext(fs.readFileSync(filename, 'utf8'), context, { filename });
  vm.runInContext('detectGPU = () => ({ available: false }); createWindow(); setupIPC();', context);
  const window = vm.runInContext('mainWindow', context);
  const event = { sender: window.webContents, senderFrame: window.webContents.mainFrame };
  return { context, window, event, handlers, values, sockets, external, timers };
}

test('all main IPC rejects a remote document even when it occupies the real main frame', async () => {
  const f = fixture();
  await f.handlers.get('agent:status')(f.event);
  f.event.senderFrame.url = 'https://untrusted.test/';
  for (const [channel, handler] of f.handlers) {
    await assert.rejects(async () => handler(f.event, {}), /主页面|信任/, channel);
  }
});

test('packaged IPC permits only the exact renderer file, including hash routes', async () => {
  const f = fixture({ packaged: true });
  await f.handlers.get('agent:status')(f.event);
  f.event.senderFrame.url = pathToFileURL(path.resolve(__dirname, '../renderer/other.html')).href;
  await assert.rejects(f.handlers.get('agent:status')(f.event), /主页面|信任/);
});

test('external navigation and popup protocols cannot replace the trusted renderer', async () => {
  const f = fixture();
  let prevented = false;
  f.window.webContents.emit('will-navigate', { preventDefault: () => { prevented = true; } }, 'https://docs.example.test/');
  assert.equal(prevented, true);
  assert.deepEqual(f.external, ['https://docs.example.test/']);
  assert.equal(f.window.windowOpenHandler({ url: 'javascript:alert(1)' }).action, 'deny');
  assert.equal(f.window.windowOpenHandler({ url: 'file:///C:/untrusted.html' }).action, 'deny');
  assert.equal(f.external.length, 1);
  prevented = false;
  f.window.webContents.emit('will-redirect', { preventDefault: () => { prevented = true; } }, 'https://redirect.example.test/');
  assert.equal(prevented, true);
  assert.equal(f.external.length, 1);
  prevented = false;
  f.window.webContents.emit('will-navigate', { preventDefault: () => { prevented = true; } }, 'http://127.0.0.1:5200/workflows/A/edit');
  assert.equal(prevented, false);
});

test('retired socket callbacks cannot mutate the next session or dispatch old training commands', async () => {
  const f = fixture();
  vm.runInContext('connectToCloud();', f.context);
  const oldSocket = f.sockets[0];
  oldSocket.open();
  const oldClose = oldSocket.listeners('close')[0];
  const oldMessage = oldSocket.listeners('message')[0];
  const oldOpen = oldSocket.listeners('open')[0];
  await f.handlers.get('agent:connect')(f.event, { cloudUrl: 'http://cloud.test', agentId: 'fixture-agent', apiToken: 'rotated-token' });
  const newSocket = f.sockets[1];
  newSocket.open();
  vm.runInContext('auditMessages = []; handleCloudMessage = message => auditMessages.push(message);', f.context);
  oldClose();
  oldMessage(Buffer.from(JSON.stringify({ type: 'training_command', payload: { command: 'start' } })));
  oldOpen();
  assert.equal(vm.runInContext('wsConnected', f.context), true);
  assert.equal(vm.runInContext('auditMessages.length', f.context), 0);
  assert.equal(f.timers.size, 0);
  assert.equal(oldSocket.listenerCount('message'), 0);
});

test('logout invalidates callbacks already captured by the socket event loop', async () => {
  const f = fixture();
  vm.runInContext('connectToCloud();', f.context);
  const socket = f.sockets[0];
  socket.open();
  const onMessage = socket.listeners('message')[0];
  const onOpen = socket.listeners('open')[0];
  await f.handlers.get('agent:disconnect')(f.event);
  vm.runInContext('auditMessages = []; handleCloudMessage = message => auditMessages.push(message);', f.context);
  onMessage(Buffer.from(JSON.stringify({ type: 'training_command', payload: { command: 'start' } })));
  onOpen();
  assert.equal(vm.runInContext('auditMessages.length', f.context), 0);
  assert.equal(vm.runInContext('wsConnected', f.context), false);
});

test('duplicate connect attempts share an in-flight socket', () => {
  const f = fixture();
  vm.runInContext('connectToCloud(); connectToCloud();', f.context);
  assert.equal(f.sockets.length, 1);
});

test('logout overtaking REST registration cannot establish a new socket', async () => {
  const f = fixture();
  let finishRegistration;
  f.context.fetch = () => new Promise(resolve => { finishRegistration = resolve; });
  const connecting = f.handlers.get('agent:connect')(f.event, { cloudUrl: 'http://cloud.test', agentId: 'fixture-agent', apiToken: 'fixture-token' });
  await f.handlers.get('agent:disconnect')(f.event);
  finishRegistration({ ok: true, json: async () => ({ data: { ok: true } }) });
  await connecting;
  assert.equal(f.values.get('apiToken'), null);
  assert.equal(f.sockets.length, 0);
});

test('same-credential explicit reconnect creates a transport for the new session revision', async () => {
  const f = fixture();
  vm.runInContext('connectToCloud();', f.context);
  f.sockets[0].open();
  await f.handlers.get('agent:connect')(f.event, { cloudUrl: 'http://cloud.test', agentId: 'fixture-agent', apiToken: 'fixture-token' });
  assert.equal(f.sockets.length, 2);
  f.sockets[1].open();
  assert.equal(vm.runInContext('wsConnected', f.context), true);
  assert.equal(f.sockets[1].sent.length, 1);
});
