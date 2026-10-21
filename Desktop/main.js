/**
 * Flowly Agent — Electron Main Process
 *
 * Responsibilities:
 * - Spawn GPU training subprocesses (YOLO training)
 * - Maintain WebSocket connection to Flowly cloud server
 * - Broadcast training progress back to cloud via WS
 * - Expose IPC API to renderer
 * - GPU detection and health monitoring
 *
 * IPC Channels (renderer ↔ main):
 *   agent:connect       → connect to cloud, returns agent info
 *   agent:disconnect    → close WS connection
 *   agent:status        → current connection status
 *   training:start      → start YOLO training job
 *   training:stop       → stop running training
 *   training:status     → current training status
 *   gpu:info            → GPU detection result
 *   clipIndex:start     → build CLIP retrieval index locally
 *   clipIndex:stop      → stop index build
 *   clipIndex:status    → current index build status
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const net = require('net');
const http = require('http');
const log = require('electron-log');
const Store = require('electron-store');
const WebSocket = require('ws');
const { installTrainingMonitor } = require('./training-monitor/service');

// ---- Logging ----
log.transports.file.level = 'info';
log.transports.console.level = 'debug';
log.info('Flowly Agent starting...');

// ---- Config Store ----
const store = new Store({
  defaults: {
    cloudUrl: process.env.FLOWLY_CLOUD_URL || 'http://localhost:8000',
    agentId: null,
    apiToken: null,
    autoLaunch: false,
  }
});

// ---- State ----
let mainWindow = null;
let ws = null;
let wsReconnectTimer = null;
let wsConnected = false;
let heartbeatTimer = null;
let trainingProcess = null;
let trainingResultFile = null;
let trainingPollTimer = null;
let clipIndexProcess = null;
let clipIndexResultFile = null;
let trainingMonitor = null;
const openWorkflow = process.argv.find(argument => argument.startsWith('--open-workflow='))?.slice('--open-workflow='.length);
const initialWorkflowRoute = /^[a-f0-9-]{36}$/i.test(openWorkflow || '') ? `/workflows/${openWorkflow}/edit` : null;

// GPU info cache
let gpuInfo = null;

// Training state
const trainingState = {
  running: false,
  jobId: null,
  startTime: null,
  progress: 0,
  currentEpoch: 0,
  totalEpochs: 0,
  bestFitness: 0,
  logs: [],
};

const clipIndexState = {
  running: false,
  jobId: null,
  startTime: null,
  progress: 0,
  phase: '',
  logs: [],
  result: null,
};

// =============================================================================
// Window Management
// =============================================================================

const DEV_SERVER_URL = process.env.FLOWLY_DEV_SERVER_URL || 'http://127.0.0.1:5200';
const RENDERER_INDEX = path.join(__dirname, 'renderer', 'index.html');

function getAppIconPath() {
  const assetsDir = path.join(__dirname, 'assets');
  const candidates = [];

  if (process.platform === 'win32') {
    candidates.push(path.join(assetsDir, 'icon.ico'));
  }
  if (process.platform === 'darwin') {
    candidates.push(path.join(assetsDir, 'icon.icns'));
  }
  candidates.push(path.join(assetsDir, 'icon.png'));

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return undefined;
}

function resolveRendererTarget() {
  const forceRenderer = process.argv.includes('--use-renderer');
  const forceDevServer = process.argv.includes('--use-dev-server');

  if (app.isPackaged) {
    return { mode: 'file', filePath: RENDERER_INDEX };
  }

  if (forceRenderer && fs.existsSync(RENDERER_INDEX)) {
    return { mode: 'file', filePath: RENDERER_INDEX };
  }

  if (forceDevServer || !fs.existsSync(RENDERER_INDEX)) {
    return { mode: 'url', url: DEV_SERVER_URL };
  }

  // Default local start: prefer built renderer for offline desktop experience
  return { mode: 'file', filePath: RENDERER_INDEX };
}

function createWindow() {
  const iconPath = getAppIconPath();

  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: 'Flowly',
    icon: iconPath,
    backgroundColor: '#0f1117',
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: true,
    },
  });

  const target = resolveRendererTarget();
  log.info('Loading renderer:', target);

  if (target.mode === 'file') {
    if (!fs.existsSync(target.filePath)) {
      log.error('Renderer bundle missing:', target.filePath);
      dialog.showErrorBox(
        '缺少前端资源',
        '未找到 renderer/index.html。请先运行：\n\n  npm run build:renderer\n\n或在开发模式运行：\n\n  npm run dev:full',
      );
      app.quit();
      return;
    }
    mainWindow.loadFile(target.filePath, initialWorkflowRoute ? { hash: initialWorkflowRoute } : {});
  } else {
    mainWindow.loadURL(initialWorkflowRoute ? `${target.url.replace(/\/$/, '')}${initialWorkflowRoute}` : target.url);
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.webContents.on('did-finish-load', () => {
    log.info('Renderer loaded');
    if (mainWindow) {
      mainWindow.webContents.send('agent:status', buildStatusPayload());
    }
  });

  mainWindow.webContents.on('did-fail-load', (_event, code, desc, validatedURL) => {
    log.error('Renderer failed to load:', code, desc, validatedURL);
    if (target.mode === 'url') {
      dialog.showErrorBox(
        '无法连接开发服务器',
        `请确认 Frontend 已启动（${DEV_SERVER_URL}）。\n\n推荐命令：npm run dev:full\n\n错误：${desc}`,
      );
    }
  });

  mainWindow.on('closed', () => {
    trainingMonitor?.stop();
    mainWindow = null;
    disconnectWS();
    stopTraining();
    if (process.platform !== 'darwin') {
      app.quit();
    }
  });

  if (process.argv.includes('--enable-logging')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

// =============================================================================
// GPU Detection
// =============================================================================

function detectGPU() {
  if (gpuInfo) return gpuInfo;

  const info = {
    available: false,
    name: null,
    memoryTotalMb: 0,
    memoryFreeMb: 0,
    utilizationPercent: null,
    computeCapability: null,
    driverVersion: null,
    cudnnVersion: null,
    deviceCount: 0,
  };

  try {
    const result = execSync('nvidia-smi --query-gpu=name,memory.total,memory.free,utilization.gpu,driver_version,compute_cap --format=csv,noheader,nounits', {
      encoding: 'utf-8',
      timeout: 5000,
    });

    const [name, memTotal, memFree, util, driver, compute] = result.trim().split(',').map(s => s.trim());
    info.available = true;
    info.name = name;
    info.memoryTotalMb = parseInt(memTotal, 10) || 0;
    info.memoryFreeMb = parseInt(memFree, 10) || 0;
    info.utilizationPercent = parseInt(util, 10) || 0;
    info.driverVersion = driver || null;
    info.computeCapability = compute || null;
    info.deviceCount = 1;
    log.info('GPU detected:', info.name);
  } catch (e) {
    log.info('No NVIDIA GPU detected:', e.message);
  }

  // Also check for ROCm / Apple Silicon
  if (!info.available) {
    try {
      const mps = execSync('clinfo 2>/dev/null | head -5 || echo "no-clinfo"', { encoding: 'utf-8', timeout: 3000 });
      if (mps.includes('Apple M')) {
        info.available = true;
        info.name = 'Apple Silicon GPU';
        info.deviceCount = 1;
        log.info('Apple Silicon GPU detected');
      }
    } catch {
      // Not Apple Silicon
    }
  }

  gpuInfo = info;
  return info;
}

// =============================================================================
// Training Script Execution
// =============================================================================

function getTrainingScriptPath() {
  const bundledPath = path.join(__dirname, 'training-scripts', 'train_model.py');
  if (fs.existsSync(bundledPath)) return bundledPath;

  const devPath = path.join(__dirname, '..', 'Backend', 'scripts', 'train_model.py');
  if (fs.existsSync(devPath)) return devPath;

  const resourcePath = path.join(process.resourcesPath || __dirname, 'training-scripts', 'train_model.py');
  if (fs.existsSync(resourcePath)) return resourcePath;

  return bundledPath;
}

function startTraining(jobConfig) {
  if (trainingState.running) {
    log.warn('Training already running, ignoring start request');
    return { success: false, error: 'Training already in progress' };
  }

  const scriptPath = getTrainingScriptPath();
  if (!fs.existsSync(scriptPath)) {
    log.error('Training script not found:', scriptPath);
    return { success: false, error: `Training script not found: ${scriptPath}` };
  }

  // Ensure output directory
  const outputDir = jobConfig.outputDir || path.join(app.getPath('userData'), 'training', jobConfig.jobId);
  fs.mkdirSync(outputDir, { recursive: true });

  trainingResultFile = path.join(outputDir, 'training_result.json');
  const configPath = path.join(outputDir, 'job_config.json');
  fs.writeFileSync(configPath, JSON.stringify(jobConfig, null, 2), 'utf-8');

  const pythonExecutable = resolvePythonExecutable();
  const env = {
    ...process.env,
    CUDA_VISIBLE_DEVICES: String(jobConfig.device ?? process.env.CUDA_VISIBLE_DEVICES ?? '0'),
    FLOWLY_JOB_ID: jobConfig.jobId || jobConfig.job_id,
    FLOWLY_OUTPUT_DIR: outputDir,
  };

  const jobId = jobConfig.jobId || jobConfig.job_id || `job-${Date.now()}`;
  log.info('Starting training:', jobId, 'python:', pythonExecutable, 'script:', scriptPath);

  trainingProcess = spawn(
    pythonExecutable,
    [
      scriptPath,
      '--config', configPath,
      '--job-id', jobId,
      '--output-dir', outputDir,
      '--streaming',
    ],
    {
      env,
      cwd: path.dirname(scriptPath),
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    },
  );

  trainingState.running = true;
  trainingState.jobId = jobId;
  trainingState.startTime = Date.now();
  trainingState.progress = 0;
  trainingState.currentEpoch = 0;
  trainingState.bestFitness = 0;
  trainingState.logs = [];
  trainingState.totalEpochs = jobConfig.epochs || jobConfig.total_epochs || 100;

  trainingProcess.stdout.on('data', (data) => {
    ingestTrainingOutput(data);
    broadcastTrainingProgress();
  });

  trainingProcess.stderr.on('data', (data) => {
    ingestTrainingOutput(data);
    broadcastTrainingProgress();
  });

  trainingProcess.on('exit', (code) => {
    log.info('Training process exited with code:', code);
    trainingProcess = null;
    pollResultFile(() => {
      trainingState.running = false;
      if (code === 0) {
        broadcastTrainingComplete();
      } else {
        broadcastTrainingError(`Training exited with code ${code}`);
      }
      notifyCloudComplete(code === 0);
    });
  });

  trainingProcess.on('error', (err) => {
    log.error('Training process error:', err);
    trainingState.running = false;
    broadcastTrainingError(err.message);
  });

  // Start polling for result file
  startResultPolling(outputDir);

  // Notify renderer
  if (mainWindow) {
    mainWindow.webContents.send('training:started', buildTrainingPayload());
  }

  // Notify cloud
  sendToCloud({
    type: 'training_started',
    jobId,
    gpu: detectGPU(),
    timestamp: Date.now(),
  });

  return { success: true, jobId, outputDir };
}

function stopTraining() {
  if (!trainingProcess || !trainingState.running) {
    return { success: false, error: 'No training running' };
  }

  log.info('Stopping training:', trainingState.jobId);

  trainingProcess.kill('SIGTERM');
  trainingProcess = null;
  trainingState.running = false;

  stopResultPolling();

  sendToCloud({
    type: 'training_cancelled',
    jobId: trainingState.jobId,
    timestamp: Date.now(),
  });

  if (mainWindow) {
    mainWindow.webContents.send('training:stopped', buildTrainingPayload());
  }

  return { success: true };
}

function startResultPolling(outputDir) {
  stopResultPolling();
  trainingPollTimer = setInterval(() => {
    const resultPath = path.join(outputDir, 'training_result.json');
    if (fs.existsSync(resultPath)) {
      try {
        const result = JSON.parse(fs.readFileSync(resultPath, 'utf-8'));
        if (result.current_epoch) {
          trainingState.currentEpoch = result.current_epoch;
          trainingState.totalEpochs = result.total_epochs || trainingState.totalEpochs;
          trainingState.progress = Math.round((trainingState.currentEpoch / trainingState.totalEpochs) * 100);
          trainingState.bestFitness = result.best_fitness || 0;
        }
        if (result.status === 'completed' || result.status === 'failed') {
          stopResultPolling();
          trainingState.running = false;
        }
        broadcastTrainingProgress();
      } catch (e) {
        log.warn('Failed to read result file:', e.message);
      }
    }
  }, 2000);
}

function pollResultFile(callback) {
  const check = () => {
    if (fs.existsSync(trainingResultFile)) {
      callback();
    } else {
      setTimeout(check, 1000);
    }
  };
  check();
}

function stopResultPolling() {
  if (trainingPollTimer) {
    clearInterval(trainingPollTimer);
    trainingPollTimer = null;
  }
}

// =============================================================================
// CLIP Index Script Execution (M4.14)
// =============================================================================

function getClipIndexScriptPath() {
  const bundledPath = path.join(__dirname, 'training-scripts', 'build_clip_index.py');
  if (fs.existsSync(bundledPath)) return bundledPath;

  const devPath = path.join(__dirname, '..', 'Backend', 'scripts', 'build_clip_index.py');
  if (fs.existsSync(devPath)) return devPath;

  const resourcePath = path.join(process.resourcesPath || __dirname, 'training-scripts', 'build_clip_index.py');
  if (fs.existsSync(resourcePath)) return resourcePath;

  return bundledPath;
}

function buildClipIndexPayload() {
  return {
    jobId: clipIndexState.jobId,
    running: clipIndexState.running,
    progress: clipIndexState.progress,
    phase: clipIndexState.phase,
    startTime: clipIndexState.startTime,
    elapsedMs: clipIndexState.startTime ? Date.now() - clipIndexState.startTime : 0,
    logs: clipIndexState.logs.slice(-50),
    result: clipIndexState.result,
  };
}

function broadcastClipIndexProgress() {
  const payload = buildClipIndexPayload();
  if (mainWindow) {
    mainWindow.webContents.send('clipIndex:progress', payload);
  }
}

function broadcastClipIndexComplete() {
  const payload = buildClipIndexPayload();
  if (mainWindow) {
    mainWindow.webContents.send('clipIndex:complete', payload);
  }
}

function broadcastClipIndexError(error) {
  const payload = { ...buildClipIndexPayload(), error };
  if (mainWindow) {
    mainWindow.webContents.send('clipIndex:error', payload);
  }
}

function ingestClipIndexOutput(raw) {
  const lines = raw.toString().split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    try {
      const payload = JSON.parse(trimmed);
      if (payload.type === 'clip_index_progress') {
        clipIndexState.progress = Math.round(payload.progress || clipIndexState.progress || 0);
        clipIndexState.phase = payload.phase || clipIndexState.phase;
        broadcastClipIndexProgress();
        continue;
      }
      if (payload.type === 'clip_index_complete') {
        clipIndexState.result = payload.result || null;
        clipIndexState.progress = 100;
        clipIndexState.phase = 'completed';
        continue;
      }
      if (payload.type === 'error') {
        clipIndexState.logs.push(`[ERR] ${payload.message || 'Index build error'}`);
        continue;
      }
      if (payload.message) {
        clipIndexState.logs.push(payload.message);
        continue;
      }
    } catch {
      // plain text log line
    }

    clipIndexState.logs.push(trimmed);
    if (clipIndexState.logs.length > 500) clipIndexState.logs.shift();
  }
}

function startClipIndex(jobConfig) {
  if (clipIndexState.running) {
    return { success: false, error: 'CLIP index build already in progress' };
  }

  const scriptPath = getClipIndexScriptPath();
  if (!fs.existsSync(scriptPath)) {
    return { success: false, error: `CLIP index script not found: ${scriptPath}` };
  }

  const outputDir = jobConfig.outputDir || jobConfig.output_dir
    || path.join(app.getPath('userData'), 'clip-index', jobConfig.jobId || `idx-${Date.now()}`);
  fs.mkdirSync(outputDir, { recursive: true });

  clipIndexResultFile = path.join(outputDir, 'index_result.json');
  const configPath = path.join(outputDir, 'clip_index_config.json');
  fs.writeFileSync(configPath, JSON.stringify(jobConfig, null, 2), 'utf-8');

  const pythonExecutable = resolvePythonExecutable();
  const jobId = jobConfig.jobId || jobConfig.job_id || `clip-index-${Date.now()}`;
  const env = {
    ...process.env,
    CUDA_VISIBLE_DEVICES: String(jobConfig.device ?? process.env.CUDA_VISIBLE_DEVICES ?? '0'),
    FLOWLY_JOB_ID: jobId,
    FLOWLY_OUTPUT_DIR: outputDir,
  };

  log.info('Starting CLIP index build:', jobId, 'python:', pythonExecutable, 'script:', scriptPath);

  clipIndexProcess = spawn(
    pythonExecutable,
    [
      scriptPath,
      '--config', configPath,
      '--job-id', jobId,
      '--output-dir', outputDir,
      '--streaming',
    ],
    {
      env,
      cwd: path.dirname(scriptPath),
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    },
  );

  clipIndexState.running = true;
  clipIndexState.jobId = jobId;
  clipIndexState.startTime = Date.now();
  clipIndexState.progress = 0;
  clipIndexState.phase = 'starting';
  clipIndexState.logs = [];
  clipIndexState.result = null;

  clipIndexProcess.stdout.on('data', (data) => {
    ingestClipIndexOutput(data);
    broadcastClipIndexProgress();
  });

  clipIndexProcess.stderr.on('data', (data) => {
    ingestClipIndexOutput(data);
    broadcastClipIndexProgress();
  });

  clipIndexProcess.on('exit', (code) => {
    log.info('CLIP index process exited with code:', code);
    clipIndexProcess = null;
    const finalize = () => {
      clipIndexState.running = false;
      if (code === 0 && clipIndexResultFile && fs.existsSync(clipIndexResultFile)) {
        try {
          clipIndexState.result = JSON.parse(fs.readFileSync(clipIndexResultFile, 'utf-8'));
        } catch (e) {
          log.warn('Failed to read index result:', e.message);
        }
        broadcastClipIndexComplete();
      } else {
        broadcastClipIndexError(`Index build exited with code ${code}`);
      }
    };

    if (clipIndexResultFile && fs.existsSync(clipIndexResultFile)) {
      finalize();
    } else {
      setTimeout(finalize, 800);
    }
  });

  clipIndexProcess.on('error', (err) => {
    log.error('CLIP index process error:', err);
    clipIndexState.running = false;
    broadcastClipIndexError(err.message);
  });

  if (mainWindow) {
    mainWindow.webContents.send('clipIndex:started', buildClipIndexPayload());
  }

  return { success: true, jobId, outputDir };
}

function stopClipIndex() {
  if (!clipIndexProcess || !clipIndexState.running) {
    return { success: false, error: 'No CLIP index build running' };
  }

  log.info('Stopping CLIP index build:', clipIndexState.jobId);
  clipIndexProcess.kill('SIGTERM');
  clipIndexProcess = null;
  clipIndexState.running = false;

  if (mainWindow) {
    mainWindow.webContents.send('clipIndex:stopped', buildClipIndexPayload());
  }

  return { success: true };
}

// =============================================================================
// WebSocket — Cloud Communication
// =============================================================================

function connectToCloud() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    log.info('WS already connected');
    return;
  }

  const cloudUrl = normalizeCloudUrl(store.get('cloudUrl'));
  const agentId = ensureAgentId();
  const apiToken = store.get('apiToken');

  if (!cloudUrl) {
    log.info('Cloud URL not configured, skipping cloud connection');
    return;
  }

  const wsUrl = cloudUrl
    .replace('http://', 'ws://')
    .replace('https://', 'wss://')
    + `/ws/agent/${agentId}/`;

  log.info('Connecting to cloud WS:', wsUrl);

  const headers = {};
  if (apiToken) {
    headers.Authorization = `Bearer ${apiToken}`;
  }

  ws = new WebSocket(wsUrl, { headers });

  ws.on('open', () => {
    log.info('WS connected to cloud');
    wsConnected = true;
    startHeartbeat();
    if (mainWindow) mainWindow.webContents.send('agent:status', buildStatusPayload());

    sendToCloud({
      type: 'agent_registered',
      agentId,
      hostname: os.hostname(),
      platform: process.platform,
      gpu: detectGPU(),
      capabilities: ['yolo_training', 'gpu_accelerated'],
    });
  });

  ws.on('message', (data) => {
    try {
      const msg = JSON.parse(data.toString());
      handleCloudMessage(msg);
    } catch (e) {
      log.warn('Failed to parse WS message:', e.message);
    }
  });

  ws.on('close', () => {
    log.info('WS disconnected from cloud');
    wsConnected = false;
    if (mainWindow) mainWindow.webContents.send('agent:status', buildStatusPayload());
    scheduleWSReconnect();
  });

  ws.on('error', (err) => {
    log.error('WS error:', err.message);
    wsConnected = false;
  });
}

function normalizeCloudUrl(url) {
  return String(url || '').trim().replace(/\/+$/, '');
}

function buildApiBase(cloudUrl) {
  const base = normalizeCloudUrl(cloudUrl);
  return `${base}/api/v1/agents/desktop`;
}

async function parseApiResponse(response) {
  const payload = await response.json();
  if (payload && typeof payload === 'object' && Object.prototype.hasOwnProperty.call(payload, 'data')) {
    if (!response.ok || (payload.code && payload.code >= 400)) {
      throw new Error(payload.message || `API error ${payload.code || response.status}`);
    }
    return payload.data;
  }
  if (!response.ok) {
    throw new Error(typeof payload === 'string' ? payload : JSON.stringify(payload).slice(0, 200));
  }
  return payload;
}

function ensureAgentId() {
  let agentId = store.get('agentId');
  if (!agentId) {
    const suffix = crypto.randomBytes(4).toString('hex');
    agentId = `agent-${os.hostname().replace(/[^a-zA-Z0-9-]/g, '-').slice(0, 24)}-${suffix}`;
    store.set('agentId', agentId);
  }
  return agentId;
}

function resolvePythonExecutable() {
  const candidates = [];
  if (process.env.FLOWLY_PYTHON) {
    candidates.push(process.env.FLOWLY_PYTHON);
  }
  if (process.platform === 'win32') {
    candidates.push('py', 'python', 'python3');
  } else {
    candidates.push('python3', 'python');
  }

  for (const cmd of candidates) {
    try {
      execSync(`"${cmd}" --version`, { encoding: 'utf-8', timeout: 5000, stdio: 'pipe', shell: true });
      return cmd;
    } catch {
      // try next candidate
    }
  }
  return 'python';
}

async function registerAgentViaRest(cloudUrl, agentId) {
  const gpu = detectGPU();
  const payload = {
    agent_id: agentId,
    display_name: `Flowly Agent (${os.hostname()})`,
    hostname: os.hostname(),
    platform: process.platform,
    gpu_info: gpu,
    gpu_available: gpu.available,
    gpu_name: gpu.name || '',
    capabilities: ['yolo_training', 'gpu_accelerated'],
    supports_yolo_training: true,
    cloud_url: normalizeCloudUrl(cloudUrl),
  };

  const response = await fetch(`${buildApiBase(cloudUrl)}/register/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  return parseApiResponse(response);
}

async function sendHeartbeat() {
  const cloudUrl = store.get('cloudUrl');
  const agentId = store.get('agentId');
  if (!cloudUrl || !agentId) return;

  try {
    await fetch(`${buildApiBase(cloudUrl)}/heartbeat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId,
        status: trainingState.running ? 'training' : 'online',
      }),
    });
  } catch (err) {
    log.warn('Heartbeat failed:', err.message);
  }
}

function startHeartbeat() {
  stopHeartbeat();
  heartbeatTimer = setInterval(() => {
    sendHeartbeat().catch((err) => log.warn('Heartbeat error:', err.message));
  }, 30000);
}

function stopHeartbeat() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
}

function ingestTrainingOutput(raw) {
  const lines = raw.toString().split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    try {
      const payload = JSON.parse(trimmed);
      if (payload.type === 'training_progress') {
        trainingState.currentEpoch = payload.epoch || trainingState.currentEpoch;
        trainingState.totalEpochs = payload.total_epochs || trainingState.totalEpochs;
        trainingState.progress = Math.round(payload.progress_percent || trainingState.progress || 0);
        trainingState.bestFitness = payload.metrics?.fitness
          ?? payload.best?.fitness
          ?? trainingState.bestFitness;
        broadcastTrainingProgress();
        continue;
      }
      if (payload.type === 'error') {
        trainingState.logs.push(`[ERR] ${payload.message || 'Training error'}`);
        continue;
      }
      if (payload.message) {
        trainingState.logs.push(payload.message);
        continue;
      }
    } catch {
      // plain text log line
    }

    trainingState.logs.push(trimmed);
    if (trainingState.logs.length > 500) trainingState.logs.shift();
  }
}

function scheduleWSReconnect() {
  if (wsReconnectTimer) return;
  wsReconnectTimer = setTimeout(() => {
    wsReconnectTimer = null;
    if (store.get('agentId')) {
      connectToCloud();
    }
  }, 5000);
}

function disconnectWS() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer);
    wsReconnectTimer = null;
  }
  stopHeartbeat();
  if (ws) {
    ws.close();
    ws = null;
  }
  wsConnected = false;
}

function sendToCloud(msg) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

function handleCloudMessage(msg) {
  const { type, payload = {} } = msg;

  switch (type) {
    case 'training_command':
      if (payload.command === 'start') {
        const config = payload.jobConfig || payload.job_config || {};
        if (!config.jobId && !config.job_id) {
          config.jobId = config.id || `job-${Date.now()}`;
        }
        startTraining(config);
      } else if (payload.command === 'stop') {
        stopTraining();
      }
      break;

    case 'connected':
      log.info('Cloud handshake:', msg.message || 'connected');
      break;

    case 'agent_registered_ack':
      log.info('Agent registered on cloud:', msg.agent_id || payload.agent_id);
      break;

    case 'ping':
      sendToCloud({ type: 'pong', timestamp: Date.now() });
      break;

    case 'get_status':
      sendToCloud({
        type: 'status_report',
        agentId: store.get('agentId'),
        status: buildStatusPayload(),
        gpu: detectGPU(),
        timestamp: Date.now(),
      });
      break;

    default:
      log.debug('Unhandled cloud message type:', type);
  }
}

// =============================================================================
// Training Progress Broadcasting
// =============================================================================

function broadcastTrainingProgress() {
  const payload = buildTrainingPayload();
  if (mainWindow) {
    mainWindow.webContents.send('training:progress', payload);
  }
  sendToCloud({
    type: 'training_progress',
    jobId: trainingState.jobId,
    ...payload,
    timestamp: Date.now(),
  });
}

function broadcastTrainingComplete() {
  const payload = buildTrainingPayload();
  if (mainWindow) {
    mainWindow.webContents.send('training:complete', payload);
  }
}

function broadcastTrainingError(error) {
  const payload = { ...buildTrainingPayload(), error };
  if (mainWindow) {
    mainWindow.webContents.send('training:error', payload);
  }
}

function notifyCloudComplete(success = true) {
  let result = {};
  if (trainingResultFile && fs.existsSync(trainingResultFile)) {
    try {
      result = JSON.parse(fs.readFileSync(trainingResultFile, 'utf-8'));
    } catch {
      result = { error: 'Failed to read result file' };
      success = false;
    }
  }
  sendToCloud({
    type: success ? 'training_complete' : 'training_error',
    jobId: trainingState.jobId,
    success,
    result,
    error: success ? undefined : (result.error || 'Training failed'),
    timestamp: Date.now(),
  });
}

// =============================================================================
// Payload Builders
// =============================================================================

function buildStatusPayload() {
  return {
    connected: wsConnected,
    cloudUrl: store.get('cloudUrl'),
    agentId: store.get('agentId'),
    gpu: detectGPU(),
    training: trainingState.running ? {
      jobId: trainingState.jobId,
      running: true,
    } : null,
    version: app.getVersion(),
    uptime: process.uptime(),
  };
}

function buildTrainingPayload() {
  return {
    jobId: trainingState.jobId,
    running: trainingState.running,
    progress: trainingState.progress,
    currentEpoch: trainingState.currentEpoch,
    totalEpochs: trainingState.totalEpochs,
    bestFitness: trainingState.bestFitness,
    startTime: trainingState.startTime,
    elapsedMs: trainingState.startTime ? Date.now() - trainingState.startTime : 0,
    logs: trainingState.logs.slice(-50),
  };
}

// =============================================================================
// Site Local Environment Provisioning (venv + pip install)
// =============================================================================

function getSiteVenvDir(backendDir) {
  return path.join(backendDir, '.venv');
}

function getVenvPythonPath(venvDir) {
  return process.platform === 'win32'
    ? path.join(venvDir, 'Scripts', 'python.exe')
    : path.join(venvDir, 'bin', 'python');
}

function runCommand(cmd, args, options = {}) {
  return new Promise((resolve, reject) => {
    const proc = spawn(cmd, args, {
      shell: process.platform === 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
      cwd: options.cwd,
      env: options.env || process.env,
    });
    let stderr = '';
    proc.stdout?.on('data', (chunk) => options.onOutput?.(chunk.toString()));
    proc.stderr?.on('data', (chunk) => {
      stderr += chunk.toString();
      options.onOutput?.(chunk.toString());
    });
    proc.on('error', reject);
    proc.on('exit', (code) => {
      if (code === 0) resolve({ stderr });
      else reject(new Error(`命令退出码 ${code}: ${cmd} ${args.join(' ')}\n${stderr.slice(-600)}`));
    });
  });
}

function emitEnvProgress(siteId, phase, message) {
  if (mainWindow) {
    mainWindow.webContents.send('runtime:envProgress', { siteId, phase, message, timestamp: Date.now() });
  }
  log.info(`[env:${siteId || 'site'}] ${phase} — ${message}`);
}

/**
 * Ensure a self-contained virtual environment exists inside the generated site's
 * backend/ directory and has its requirements.txt installed, so the site never
 * pollutes (or depends on) the Flowly Desktop / Django Python environment.
 * Idempotent: a marker file skips reinstall once dependencies are already present.
 */
async function ensureSiteEnv(backendDir, { siteId = '', skip = false } = {}) {
  const systemPython = resolvePythonExecutable();
  if (skip) {
    emitEnvProgress(siteId, 'ready', '已跳过自动环境配置，使用系统 Python');
    return { pythonExecutable: systemPython, venvUsed: false };
  }

  const venvDir = getSiteVenvDir(backendDir);
  const venvPython = getVenvPythonPath(venvDir);
  const requirementsPath = path.join(backendDir, 'requirements.txt');
  const markerPath = path.join(venvDir, '.flowly-installed');

  if (fs.existsSync(venvPython) && fs.existsSync(markerPath)) {
    emitEnvProgress(siteId, 'ready', '已检测到本地虚拟环境，跳过重复安装');
    return { pythonExecutable: venvPython, venvUsed: true };
  }

  try {
    if (!fs.existsSync(venvPython)) {
      emitEnvProgress(siteId, 'venv', '正在创建独立虚拟环境（backend/.venv）…');
      await runCommand(systemPython, ['-m', 'venv', venvDir]);
    }

    if (fs.existsSync(requirementsPath)) {
      emitEnvProgress(siteId, 'install', '正在安装依赖（pip install -r requirements.txt）…');
      await runCommand(venvPython, ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', requirementsPath], {
        onOutput: (text) => {
          const lastLine = text.trim().split(/\r?\n/).filter(Boolean).pop();
          if (lastLine) emitEnvProgress(siteId, 'install', lastLine);
        },
      });
    } else {
      emitEnvProgress(siteId, 'install', '未找到 requirements.txt，跳过依赖安装');
    }

    fs.writeFileSync(markerPath, JSON.stringify({ installedAt: new Date().toISOString() }), 'utf8');
    emitEnvProgress(siteId, 'ready', '本地环境已就绪');
    return { pythonExecutable: venvPython, venvUsed: true };
  } catch (err) {
    log.error('ensureSiteEnv failed, falling back to system Python:', err.message);
    emitEnvProgress(siteId, 'error', `虚拟环境准备失败，回退到系统 Python：${err.message.slice(0, 200)}`);
    return { pythonExecutable: systemPython, venvUsed: false, error: err.message };
  }
}

// =============================================================================
// Site Runtime (Flask local preview)
// =============================================================================

const PORT_RANGE_START = 49152;
const PORT_RANGE_END = 49252;
/** @type {Map<string, { proc: import('child_process').ChildProcess, port: number, outputDir: string, startedAt: number }>} */
const activeSites = new Map();

function getRuntimeManifestPath() {
  return path.join(app.getPath('userData'), 'runtime-manifest.json');
}

function loadRuntimeManifest() {
  const manifestPath = getRuntimeManifestPath();
  if (fs.existsSync(manifestPath)) {
    try {
      return JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    } catch (err) {
      log.warn('Invalid runtime manifest:', err.message);
    }
  }
  return { paths: [], allowSubprocess: false, allowLocalhost: false };
}

function saveRuntimeManifest(manifest) {
  fs.writeFileSync(getRuntimeManifestPath(), JSON.stringify(manifest, null, 2), 'utf8');
}

async function ensureRuntimePermission(outputDir) {
  const normalized = path.resolve(outputDir);
  const manifest = loadRuntimeManifest();
  if (
    manifest.allowSubprocess &&
    manifest.allowLocalhost &&
    Array.isArray(manifest.paths) &&
    manifest.paths.includes(normalized)
  ) {
    return manifest;
  }

  const { response } = await dialog.showMessageBox(mainWindow, {
    type: 'question',
    buttons: ['允许', '取消'],
    defaultId: 0,
    cancelId: 1,
    title: '本地站点运行权限',
    message: `Flowly Desktop 将在此目录启动 Flask 本地服务：\n\n${normalized}\n\n是否允许子进程与 localhost 访问？`,
  });

  if (response !== 0) {
    throw new Error('用户未授权本地站点运行');
  }

  const next = {
    paths: [...new Set([...(manifest.paths || []), normalized])],
    allowSubprocess: true,
    allowLocalhost: true,
    updatedAt: new Date().toISOString(),
  };
  saveRuntimeManifest(next);
  return next;
}

function pickFreePort() {
  const used = new Set([...activeSites.values()].map((s) => s.port));
  for (let port = PORT_RANGE_START; port <= PORT_RANGE_END; port += 1) {
    if (used.has(port)) continue;
    try {
      const server = net.createServer();
      server.listen(port, '127.0.0.1');
      server.close();
      return port;
    } catch (_) {
      // try next
    }
  }
  return PORT_RANGE_START;
}

function waitForHealth(healthUrl, maxAttempts = 24, intervalMs = 500) {
  return new Promise((resolve) => {
    let attempts = 0;
    const tick = () => {
      const req = http.get(healthUrl, (res) => {
        res.resume();
        resolve(res.statusCode >= 200 && res.statusCode < 300);
      });
      req.on('error', () => retry());
      req.setTimeout(2000, () => {
        req.destroy();
        retry();
      });
    };
    const retry = () => {
      attempts += 1;
      if (attempts >= maxAttempts) resolve(false);
      else setTimeout(tick, intervalMs);
    };
    tick();
  });
}

async function startSite({ outputDir, port, env = {}, siteId, autoSetupEnv = true }) {
  if (!outputDir) {
    return { success: false, error: 'outputDir 未指定' };
  }

  const resolvedDir = path.resolve(outputDir);
  const backendDir = path.join(resolvedDir, 'backend');
  const appPy = path.join(backendDir, 'app.py');
  if (!fs.existsSync(appPy)) {
    return { success: false, error: `缺少 backend/app.py（目录: ${resolvedDir}）` };
  }

  try {
    fs.accessSync(resolvedDir, fs.constants.R_OK | fs.constants.W_OK);
  } catch (err) {
    return { success: false, error: `输出目录不可读写: ${resolvedDir} (${err.message})` };
  }

  try {
    await ensureRuntimePermission(resolvedDir);
  } catch (err) {
    return { success: false, error: err.message };
  }

  const id = siteId || crypto.randomUUID();
  const assignedPort = port || pickFreePort();
  if (port && [...activeSites.values()].some((s) => s.port === assignedPort)) {
    return { success: false, error: `端口 ${assignedPort} 已被占用，请更换端口或停止其他预览站点` };
  }

  const { pythonExecutable, venvUsed } = await ensureSiteEnv(backendDir, { siteId: id, skip: !autoSetupEnv });
  const procEnv = { ...process.env, FLASK_RUN_PORT: String(assignedPort), ...env };

  emitEnvProgress(id, 'starting', `正在启动本地服务（端口 ${assignedPort}）…`);
  const proc = spawn(pythonExecutable, ['app.py'], {
    cwd: backendDir,
    env: procEnv,
    shell: process.platform === 'win32',
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  proc.stdout.on('data', (chunk) => log.debug('[site stdout]', chunk.toString()));
  proc.stderr.on('data', (chunk) => log.warn('[site stderr]', chunk.toString()));
  proc.on('exit', (code) => {
    if (activeSites.get(id)?.proc === proc) {
      activeSites.delete(id);
    }
    log.info(`Site ${id} exited with code ${code}`);
  });

  activeSites.set(id, {
    proc,
    port: assignedPort,
    outputDir: resolvedDir,
    startedAt: Date.now(),
  });

  const healthUrl = `http://127.0.0.1:${assignedPort}/health`;
  const ready = await waitForHealth(healthUrl);
  if (!ready) {
    stopSite(id);
    emitEnvProgress(id, 'error', 'Flask /health 未就绪，服务启动失败');
    return { success: false, error: 'Flask /health 未就绪' };
  }

  emitEnvProgress(id, 'ready', `本地站点已启动：http://127.0.0.1:${assignedPort}/`);
  return {
    success: true,
    siteId: id,
    port: assignedPort,
    previewUrl: `http://127.0.0.1:${assignedPort}/`,
    venvUsed,
    outputDir: resolvedDir,
  };
}

function stopSite(siteId) {
  const site = activeSites.get(siteId);
  if (!site) {
    return { success: false, error: '站点未运行' };
  }

  try {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', String(site.proc.pid), '/f', '/t'], { shell: true });
    } else {
      site.proc.kill('SIGTERM');
    }
  } catch (err) {
    log.warn('stopSite kill error:', err.message);
  }

  activeSites.delete(siteId);
  return { success: true };
}

function listSites() {
  return [...activeSites.entries()].map(([id, site]) => ({
    siteId: id,
    port: site.port,
    outputDir: site.outputDir,
    startedAt: site.startedAt,
    previewUrl: `http://127.0.0.1:${site.port}/`,
  }));
}

// =============================================================================
// IPC Handlers
// =============================================================================

function setupIPC() {
  // Agent connection
  ipcMain.handle('agent:connect', async (event, { cloudUrl, agentId, apiToken }) => {
    const normalizedUrl = normalizeCloudUrl(cloudUrl || store.get('cloudUrl') || 'http://127.0.0.1:8000');
    const resolvedAgentId = agentId || ensureAgentId();

    store.set('cloudUrl', normalizedUrl);
    store.set('agentId', resolvedAgentId);
    if (apiToken) {
      store.set('apiToken', apiToken);
    }

    await registerAgentViaRest(normalizedUrl, resolvedAgentId);
    connectToCloud();
    return buildStatusPayload();
  });

  ipcMain.handle('agent:getConfig', async () => ({
    cloudUrl: store.get('cloudUrl') || 'http://127.0.0.1:8000',
    agentId: ensureAgentId(),
    hasApiToken: Boolean(store.get('apiToken')),
  }));

  ipcMain.handle('agent:disconnect', async () => {
    disconnectWS();
    return buildStatusPayload();
  });

  ipcMain.handle('agent:status', async () => {
    return buildStatusPayload();
  });

  // GPU
  ipcMain.handle('gpu:info', async () => {
    return detectGPU();
  });

  // Training
  ipcMain.handle('training:start', async (event, jobConfig) => {
    return startTraining(jobConfig);
  });

  ipcMain.handle('training:stop', async () => {
    return stopTraining();
  });

  ipcMain.handle('training:status', async () => {
    return buildTrainingPayload();
  });

  ipcMain.handle('training:logs', async () => {
    return trainingState.logs;
  });

  // CLIP index (M4.14)
  ipcMain.handle('clipIndex:start', async (_event, jobConfig) => startClipIndex(jobConfig || {}));
  ipcMain.handle('clipIndex:stop', async () => stopClipIndex());
  ipcMain.handle('clipIndex:status', async () => buildClipIndexPayload());
  ipcMain.handle('clipIndex:logs', async () => clipIndexState.logs);

  // App info
  ipcMain.handle('app:info', async () => ({
    version: app.getVersion(),
    userData: app.getPath('userData'),
    platform: process.platform,
    arch: process.arch,
  }));

  // Dialog
  ipcMain.handle('dialog:selectDirectory', async (_event, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow, {
      title: options.title || '选择本地文件夹',
      defaultPath: options.defaultPath || undefined,
      properties: ['openDirectory', 'createDirectory'],
    });
    return result.canceled ? null : result.filePaths[0];
  });

  // Shell (open local folder in system file explorer)
  ipcMain.handle('shell:openFolder', async (_event, targetPath) => {
    if (!targetPath) return { success: false, error: '路径未指定' };
    try {
      const resolved = path.resolve(targetPath);
      const err = await shell.openPath(resolved);
      return err ? { success: false, error: err } : { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  // Site runtime
  ipcMain.handle('runtime:startSite', async (_event, options) => startSite(options || {}));
  ipcMain.handle('runtime:stopSite', async (_event, siteId) => stopSite(siteId));
  ipcMain.handle('runtime:listSites', async () => listSites());
  ipcMain.handle('runtime:getManifest', async () => loadRuntimeManifest());
  ipcMain.handle('runtime:grantPermission', async (_event, { outputDir }) => {
    if (!outputDir) return { success: false, error: 'outputDir 未指定' };
    try {
      const manifest = await ensureRuntimePermission(outputDir);
      return { success: true, manifest };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });
  ipcMain.handle('runtime:prepareEnv', async (_event, { outputDir, autoSetupEnv = true } = {}) => {
    if (!outputDir) return { success: false, error: 'outputDir 未指定' };
    const backendDir = path.join(path.resolve(outputDir), 'backend');
    if (!fs.existsSync(backendDir)) {
      return { success: false, error: `缺少 backend 目录: ${backendDir}` };
    }
    const siteId = crypto.randomUUID();
    try {
      const result = await ensureSiteEnv(backendDir, { siteId, skip: !autoSetupEnv });
      return { success: !result.error, siteId, ...result };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });
}

// =============================================================================
// App Lifecycle
// =============================================================================

app.whenReady().then(async () => {
  log.info('App ready, creating window');

  if (process.platform === 'win32') {
    app.setAppUserModelId('com.flowly.desktop');
  }

  ensureAgentId();
  setupIPC();
  trainingMonitor = installTrainingMonitor({ store, getWindow: () => mainWindow });
  createWindow();
  detectGPU();

  const cloudUrl = store.get('cloudUrl');
  if (cloudUrl) {
    try {
      await registerAgentViaRest(normalizeCloudUrl(cloudUrl), store.get('agentId'));
      connectToCloud();
    } catch (err) {
      log.warn('Auto-connect skipped:', err.message);
    }
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  disconnectWS();
  stopTraining();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  log.info('App quitting...');
  disconnectWS();
  stopTraining();
  for (const siteId of [...activeSites.keys()]) {
    stopSite(siteId);
  }
});

// ---- Global exception handler ----
process.on('uncaughtException', (err) => {
  log.error('Uncaught exception:', err);
});

process.on('unhandledRejection', (reason) => {
  log.error('Unhandled rejection:', reason);
});
