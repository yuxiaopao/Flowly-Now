const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const { createRequire } = require('node:module');
const { TrainingMonitorReader, parseHistory, parseBatch, safePath, contained } = require('../training-monitor/reader');
const { createMonitorSession, AUTH_SETTINGS } = require('../training-monitor/auth');

const HEADER = 'epoch,time,train/loss,metrics/accuracy_top1,metrics/accuracy_top5,val/loss,lr/pg0';
const BINDING = {
  jobId: '00000000-0000-4000-8000-000000000001',
  nodeId: '00000000-0000-4000-8000-000000000002',
  workflowId: '00000000-0000-4000-8000-000000000003',
};

function fixture(context, options = {}) {
  const base = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(base, 'flowly-monitor-test-'));
  context.after(() => {
    const resolved = fs.realpathSync(root);
    assert(contained(base, resolved) && path.basename(resolved).startsWith('flowly-monitor-test-'));
    fs.rmSync(resolved, { recursive: true });
  });
  const write = (relative, value) => {
    const target = safePath(root, relative);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, typeof value === 'string' ? value : JSON.stringify(value));
  };
  write('training/config.json', { training: { name: 'test-run', epochs: 40, batch: 32 }, acceptance: {} });
  write('training/status.json', { pid: process.pid, stage: 'training', started_at: Date.now() / 1000 - 250,
    updated_at: Date.now() / 1000 - 10, epoch: 1, epochs: 40, ...options });
  write('datasets/plantvillage/dataset-report.json', {
    images: 100, classes: ['Apple___healthy'], per_class: { Apple___healthy: { train: 70, val: 10, test: 20 } },
    counts: { train: 70, val: 10, test: 20 }, cross_split_leaf_overlap: 0, cross_split_sha256_overlap: 0,
  });
  write('training/labels.json', [{ key: 'Apple___healthy', crop: '苹果', disease: '健康', label: '苹果健康', healthy: true }]);
  write('runs/classify/test-run/results.csv', `${HEADER}\n1,200,0.9,0.8,0.95,0.5,0.0005\n`);
  write('.logs/training/bootstrap.out.log', '\u001b[K 2/40 1.50G 0.420 32 224: 50% ━━━━━ 591/1182 8.0it/s\n');
  return { root, write, reader: new TrainingMonitorReader(root, { gpu: false }) };
}

test('CSV parser tolerates a partial last write, deduplicates resumed epochs and rejects NaN', () => {
  const rows = parseHistory(`${HEADER}\n1,200,0.9,0.8,0.95,0.5,0.0005\n1,202,0.8,0.82,0.95,0.4,0.0005\n2,400,NaN,0.9,1,0.1,0.0004\n3,600,`);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].top1, 0.82);
  assert.equal(rows[0].seconds, 202);
});

test('batch parser reads real Ultralytics output rather than inventing progress', () => {
  assert.deepEqual(parseBatch(' 3/40 1.96G 0.123 32 224: 10% ━ 118/1182 8.2it/s'), {
    epoch: 3, epochs: 40, gpuMemoryGb: 1.96, loss: 0.123, batch: 118, batches: 1182,
  });
  assert.equal(parseBatch('validation summary only'), null);
});

test('snapshot combines live batch, history and Chinese class meanings without a GPU dependency', async context => {
  const { reader } = fixture(context);
  const snapshot = await reader.snapshot();
  assert.equal(snapshot.completedEpochs, 1);
  assert.equal(snapshot.activeBatch.epoch, 2);
  assert.equal(snapshot.progress, 3.75);
  assert.equal(snapshot.classes[0].crop, '苹果');
  assert.equal(snapshot.classes[0].counts.test, 20);
  assert.equal(snapshot.test, null);
  assert.equal(snapshot.manifest, null);
  assert.equal(snapshot.processAlive, true);
  assert(snapshot.host.totalMemory > 0);
  assert(snapshot.host.memoryUsedRatio >= 0 && snapshot.host.memoryUsedRatio <= 1);
  assert.equal(snapshot.artifacts.find(item => item.id === 'onnx').exists, false);
  assert.throws(() => reader.artifact('../secret'), /尚未生成/);
});

test('subsequent snapshots expose newly completed epochs and final exports', async context => {
  const { reader, write } = fixture(context);
  await reader.snapshot();
  write('runs/classify/test-run/results.csv', `${HEADER}\n1,200,0.9,0.8,0.95,0.5,0.0005\n2,380,0.4,0.94,1,0.2,0.0004\n`);
  let snapshot = await reader.snapshot();
  assert.equal(snapshot.completedEpochs, 2);
  assert.equal(snapshot.activeBatch, null);
  assert.equal(snapshot.best.top1, 0.94);
  assert.equal(snapshot.averageEpochSeconds, 180);
  write('runs/classify/test-run/training-complete.json', { completed_at: Date.now() / 1000 });
  write('models/candidates/test-run/manifest.json', { task: 'classify', validation_passed: true, classes: [] });
  write('models/candidates/test-run/model.onnx', 'fixture model');
  write('training/status.json', { stage: 'ready_for_system_test', pid: process.pid, epoch: 2, epochs: 40,
    started_at: 1000, updated_at: 1380 });
  snapshot = await reader.snapshot();
  assert.equal(snapshot.trainingFinished, true);
  assert.equal(snapshot.etaSeconds, null);
  assert.equal(snapshot.elapsedSeconds, 380);
  assert.equal(snapshot.manifest.validation_passed, true);
  assert.equal(snapshot.artifacts.find(item => item.id === 'onnx').exists, true);
  assert.equal(snapshot.terminal, true);
});

test('malformed JSON is reported instead of showing fabricated training results', async context => {
  const { reader, write } = fixture(context);
  write('training/status.json', '{unfinished');
  await assert.rejects(reader.snapshot(), SyntaxError);
});

test('failed workflow preserves the actual error and never marks a candidate completed', async context => {
  const { reader } = fixture(context, { stage: 'failed', error: 'CUDA out of memory' });
  const snapshot = await reader.snapshot();
  assert.equal(snapshot.error, 'CUDA out of memory');
  assert.equal(snapshot.running, false);
  assert.equal(snapshot.trainingFinished, false);
});

test('project traversal and unsafe run names cannot expose unrelated files', context => {
  const { root, write } = fixture(context);
  assert.throws(() => safePath(root, '../private.json'), /超出/);
  write('training/config.json', { training: { name: '../../secrets' } });
  assert.throws(() => new TrainingMonitorReader(root), /名称无效/);
});

function serviceFixture(context) {
  const { root } = fixture(context);
  const handlers = new Map();
  const timers = new Set();
  const messages = [];
  const webContents = { mainFrame: {}, send: (...message) => messages.push(message) };
  const window = { webContents, isDestroyed: () => false };
  const servicePath = path.resolve(__dirname, '../training-monitor/service.js');
  const localRequire = createRequire(servicePath);
  const module = { exports: {} };
  const electron = {
    ipcMain: { handle: (name, handler) => handlers.set(name, handler) },
    dialog: { showOpenDialog: async () => ({ canceled: true }), showSaveDialog: async () => ({ canceled: true }) },
    shell: { showItemInFolder: () => {} },
  };
  vm.runInNewContext(fs.readFileSync(servicePath, 'utf8'), {
    module,
    require: name => name === 'electron' ? electron : name === './reader' ? {
      ...localRequire(name),
      TrainingMonitorReader: class extends TrainingMonitorReader {
        constructor(project) { super(project, { gpu: false }); }
      },
    } : localRequire(name),
    setInterval: callback => { timers.add(callback); return callback; },
    clearInterval: timer => timers.delete(timer),
  });
  const session = createMonitorSession(() => 'http://flowly.test', async (url, options) => ({
    ok: options.headers.Authorization === 'Bearer valid',
    json: async () => ({ data: url.endsWith(AUTH_SETTINGS.profilePath) ? { id: 1, username: 'existing-user' } : {
      id: BINDING.jobId, node: BINDING.nodeId, workflow: BINDING.workflowId,
      config: { local_monitor: { project_root: root, run_name: 'test-run' } },
    } }),
  }));
  const service = module.exports.installTrainingMonitor({
    store: { get: () => root, set: () => {} }, getWindow: () => window, session,
  });
  context.after(() => service.stop());
  const event = { sender: webContents, senderFrame: webContents.mainFrame };
  return { handlers, timers, messages, event, service };
}

test('main-page IPC subscribes, reports actual data, cancels dialogs and stops polling without stopping training', async context => {
  const { handlers, timers, messages, event } = serviceFixture(context);
  const initial = await handlers.get('monitor:start')(event, 'valid', BINDING);
  assert.equal(initial.snapshot.viewer.username, 'existing-user');
  assert.equal(initial.snapshot.completedEpochs, 1);
  assert.equal(timers.size, 1);
  assert(messages.some(([channel, payload]) => channel === 'monitor:update' && payload.snapshot.classes.length === 1));
  assert.equal((await handlers.get('monitor:export')(event, 'json')).cancelled, true);
  await assert.rejects(handlers.get('monitor:export')(event, 'exe'), /不支持/);
  await assert.rejects(handlers.get('monitor:reveal')(event, '../secret'), /尚未生成/);
  handlers.get('monitor:stop')(event);
  assert.equal(timers.size, 0);
  assert.equal(process.kill(process.pid, 0), true);
});

test('IPC rejects another window and subframes, and rapid page remounts keep only one poller', async context => {
  const { handlers, timers, event } = serviceFixture(context);
  await assert.rejects(handlers.get('monitor:start')({ ...event, sender: {} }), /主页面/);
  await assert.rejects(handlers.get('monitor:snapshot')({ ...event, senderFrame: {} }), /主页面/);
  const first = handlers.get('monitor:start')(event, 'valid', BINDING);
  handlers.get('monitor:stop')(event);
  const second = handlers.get('monitor:start')(event, 'valid', BINDING);
  await Promise.all([first, second]);
  assert.equal(timers.size, 1);
});

test('every data IPC rejects unauthenticated calls and logout clears data and polling', async context => {
  const { handlers, timers, event, messages } = serviceFixture(context);
  for (const channel of ['snapshot', 'refresh', 'reveal', 'export']) {
    await assert.rejects(handlers.get(`monitor:${channel}`)(event), /登录/);
  }
  await assert.rejects(handlers.get('monitor:start')(event), /登录/);
  await assert.rejects(handlers.get('monitor:start')(event, 'invalid'), /登录/);
  await handlers.get('monitor:start')(event, 'valid', BINDING);
  handlers.get('monitor:logout')(event);
  assert.equal(timers.size, 0);
  assert(messages.some(([, payload]) => payload.authRequired && payload.snapshot === null));
  await assert.rejects(handlers.get('monitor:snapshot')(event), /登录/);
});

test('backend validates credentials, clears revoked sessions and never includes tokens in the profile', async () => {
  let calls = 0;
  let success = true;
  const session = createMonitorSession(() => 'http://flowly.test', async (url, options) => {
    calls++;
    assert.equal(url, 'http://flowly.test' + AUTH_SETTINGS.profilePath);
    assert.equal(options.headers.Authorization, 'Bearer valid');
    return { ok: success, json: async () => ({ data: { id: 42, username: 'existing', access: 'private' } }) };
  });
  assert.deepEqual(await session.requireSession('valid'), { id: 42, username: 'existing' });
  await session.requireSession();
  assert.equal(calls, 1);
  session.clear();
  success = false;
  await assert.rejects(session.requireSession('valid'), /登录/);
  await assert.rejects(session.requireSession(), /登录/);
});

test('an authentication request completing after logout cannot restore the session', async () => {
  let respond;
  const session = createMonitorSession(() => 'http://flowly.test', () => new Promise(resolve => { respond = resolve; }));
  const request = session.requireSession('valid');
  session.clear();
  respond({ ok: true, json: async () => ({ id: 1, username: 'existing' }) });
  await assert.rejects(request, /登录/);
  await assert.rejects(session.requireSession(), /登录/);
});

test('completed epochs use persisted CSV and cannot exceed the configured maximum', async context => {
  const { reader } = fixture(context, { epoch: 41, epochs: 40, stage: 'ready_for_system_test' });
  const snapshot = await reader.snapshot();
  assert.equal(snapshot.completedEpochs, 1);
  assert(snapshot.completedEpochs <= snapshot.totalEpochs);
});

test('a valid login still cannot open an unbound or mismatched workflow node', async context => {
  const { handlers, event } = serviceFixture(context);
  await assert.rejects(handlers.get('monitor:start')(event, 'valid'), /YOLO/);
  await assert.rejects(handlers.get('monitor:start')(event, 'valid', { ...BINDING, nodeId: BINDING.jobId }), /不匹配/);
  const result = await handlers.get('monitor:start')(event, 'valid', BINDING);
  assert.equal(result.snapshot.context.nodeId, BINDING.nodeId);
});

test('cached identity is rechecked after its short validity period', async context => {
  let valid = true;
  const session = createMonitorSession(() => 'http://flowly.test', async () => ({
    ok: valid, json: async () => ({ id: 1, username: 'existing' }),
  }));
  await session.requireSession('valid');
  valid = false;
  const later = Date.now() + AUTH_SETTINGS.cacheMs + 1;
  context.mock.method(Date, 'now', () => later);
  await assert.rejects(session.requireSession(), /登录/);
});
