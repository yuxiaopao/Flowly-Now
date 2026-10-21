const { ipcMain, dialog, shell } = require('electron');
const fs = require('node:fs');
const { TrainingMonitorReader, SETTINGS } = require('./reader');
const { createMonitorSession } = require('./auth');

function installTrainingMonitor({ store, getWindow, session = createMonitorSession(() => store.get('cloudUrl')) }) {
  let reader = null;
  let timer = null;
  let busy = false;
  let snapshot = null;
  let enabled = false;
  let generation = 0;
  let subscription = 0;
  let binding = null;

  function logout() {
    broadcast({ snapshot: null, error: '请先登录 Flowly 后查看训练数据', authRequired: true });
    stop();
    session.clear();
    reader = null;
    snapshot = null;
    binding = null;
  }

  async function requireLogin(token) {
    const version = generation;
    try { return await session.requireSession(token); }
    catch (error) { if (version === generation) logout(); throw error; }
  }

  function authorize(event) {
    const window = getWindow();
    if (!window || event.sender !== window.webContents || event.senderFrame !== window.webContents.mainFrame) {
      throw new Error('该操作仅供 Flowly 桌面端主页面使用');
    }
    return window;
  }

  function broadcast(payload) {
    const window = getWindow();
    if (enabled && window && !window.isDestroyed()) {
      window.webContents.send('monitor:update', payload);
    }
  }

  async function refresh() {
    if (busy || !reader || !enabled) return;
    busy = true;
    const source = reader;
    const version = generation;
    try {
      const viewer = await requireLogin();
      const context = await session.getRun(binding);
      const next = await source.snapshot();
      if (source === reader && version === generation) {
        snapshot = { ...next, viewer, context };
        broadcast({ snapshot, error: null });
      }
    } catch (error) {
      if (source === reader && version === generation) {
        snapshot = null;
        broadcast({ snapshot: null, error: error.message });
      }
    } finally {
      busy = false;
    }
  }

  async function attach(context) {
    const viewer = await requireLogin();
    const version = generation;
    const candidate = new TrainingMonitorReader(context.projectRoot);
    if (candidate.config.training.name !== context.runName) throw new Error('节点绑定的训练名称与本地记录不一致');
    const initial = await candidate.snapshot();
    if (version !== generation) return;
    reader = candidate;
    snapshot = { ...initial, viewer, context };
    generation++;
    broadcast({ snapshot, error: null });
  }

  function stop() {
    enabled = false;
    subscription++;
    generation++;
    clearInterval(timer);
    timer = null;
  }

  ipcMain.handle('monitor:start', async (event, token, requestedBinding) => {
    authorize(event);
    stop();
    reader = null;
    snapshot = null;
    const currentSubscription = subscription;
    await requireLogin(token || '');
    const context = await session.getRun(requestedBinding);
    if (subscription !== currentSubscription) return { snapshot: null, error: null };
    binding = requestedBinding;
    enabled = true;
    let error = null;
    try { await attach(context); } catch (failure) { error = failure.message; }
    if (enabled && subscription === currentSubscription) {
      timer = setInterval(refresh, SETTINGS.refreshMs);
      await refresh();
    }
    return { snapshot, error };
  });
  ipcMain.handle('monitor:stop', event => { authorize(event); stop(); });
  ipcMain.handle('monitor:logout', event => { authorize(event); logout(); });
  ipcMain.handle('monitor:snapshot', async event => { authorize(event); await requireLogin(); await session.getRun(binding); return snapshot; });
  ipcMain.handle('monitor:refresh', async event => { authorize(event); await requireLogin(); await refresh(); });
  ipcMain.handle('monitor:reveal', async (event, id) => {
    authorize(event);
    await requireLogin();
    await session.getRun(binding);
    if (!reader) throw new Error('请先选择训练项目');
    shell.showItemInFolder(reader.artifact(id));
    return { success: true };
  });
  ipcMain.handle('monitor:export', async (event, format) => {
    const window = authorize(event);
    await requireLogin();
    await session.getRun(binding);
    const version = generation;
    if (!reader || !snapshot) throw new Error('还没有可导出的训练记录');
    if (!['json', 'csv'].includes(format)) throw new Error('不支持的导出格式');
    const selected = await dialog.showSaveDialog(window, {
      title: '保存当前训练快照', defaultPath: `${snapshot.name}-training.${format}`,
      filters: [{ name: format.toUpperCase(), extensions: [format] }],
    });
    if (selected.canceled || !selected.filePath) return { cancelled: true };
    await requireLogin();
    await session.getRun(binding);
    if (!snapshot || version !== generation) throw new Error('节点已切换，请从当前节点重新导出');
    const text = format === 'json' ? JSON.stringify(snapshot, null, 2)
      : ['epoch,elapsed_seconds,train_loss,val_loss,top1,top5,learning_rate',
        ...snapshot.history.map(row => [row.epoch, row.seconds, row.trainLoss, row.valLoss,
          row.top1, row.top5, row.learningRate].join(','))].join('\n');
    await fs.promises.writeFile(selected.filePath, text, 'utf8');
    return { success: true, path: selected.filePath };
  });
  return { stop };
}

module.exports = { installTrainingMonitor };
