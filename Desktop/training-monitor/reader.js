const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFile } = require('node:child_process');

const SETTINGS = Object.freeze({
  refreshMs: 2000,
  gpuRefreshMs: 5000,
  gpuTimeoutMs: 3000,
  maxJsonBytes: 12 * 1024 * 1024,
  tailBytes: 64 * 1024,
  logLines: 70,
  memoryPressureRatio: 0.9,
});
const ACTIVE_STAGES = new Set(['training', 'evaluating_val', 'evaluating_test', 'exporting']);
const TERMINAL_STAGES = new Set(['ready_for_system_test', 'quality_gate_failed', 'failed', 'completed']);

function contained(root, target) {
  const relative = path.relative(root, target);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function safePath(root, relative) {
  const target = path.resolve(root, relative);
  if (!contained(root, target)) throw new Error('训练文件路径超出所选项目');
  if (fs.existsSync(target) && !contained(fs.realpathSync(root), fs.realpathSync(target))) {
    throw new Error('训练文件链接指向项目之外');
  }
  return target;
}

function jsonFile(root, relative, required = false) {
  const file = safePath(root, relative);
  if (!fs.existsSync(file)) {
    if (required) throw new Error(`缺少训练文件：${relative}`);
    return null;
  }
  if (fs.statSync(file).size > SETTINGS.maxJsonBytes) throw new Error(`训练文件过大：${relative}`);
  return JSON.parse(fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
}

function tailFile(root, relative) {
  const file = safePath(root, relative);
  if (!fs.existsSync(file)) return '';
  const descriptor = fs.openSync(file, 'r');
  try {
    const size = fs.fstatSync(descriptor).size;
    const offset = Math.max(0, size - SETTINGS.tailBytes);
    const buffer = Buffer.alloc(size - offset);
    fs.readSync(descriptor, buffer, 0, buffer.length, offset);
    const text = buffer.toString('utf8').replace(/\u001b\[[0-9;]*[A-Za-z]/g, '');
    return offset ? text.slice(text.indexOf('\n') + 1) : text;
  } finally {
    fs.closeSync(descriptor);
  }
}

function parseHistory(text) {
  const [header, ...lines] = text.replace(/^\uFEFF/, '').trim().split(/\r?\n/);
  if (!header) return [];
  const columns = header.split(',').map(value => value.trim());
  const rows = new Map();
  for (const line of lines) {
    const cells = line.split(',').map(value => value.trim());
    if (cells.length !== columns.length || cells.some(value => value === '')) continue;
    const values = cells.map(Number);
    if (!values.every(Number.isFinite)) continue;
    const raw = Object.fromEntries(columns.map((name, index) => [name, values[index]]));
    if (!Number.isInteger(raw.epoch) || raw.epoch < 1) continue;
    rows.set(raw.epoch, {
      epoch: raw.epoch, seconds: raw.time, trainLoss: raw['train/loss'],
      valLoss: raw['val/loss'], top1: raw['metrics/accuracy_top1'],
      top5: raw['metrics/accuracy_top5'], learningRate: raw['lr/pg0'],
    });
  }
  return [...rows.values()].sort((a, b) => a.epoch - b.epoch);
}

function parseBatch(text) {
  const pattern = /(\d+)\/(\d+)\s+([\d.]+)G\s+([\d.eE+-]+)\s+\d+\s+\d+:\s*[\d.]+%.*?(\d+)\/(\d+)(?:\s|$)/;
  let latest = null;
  for (const line of text.split(/[\r\n]+/)) {
    const match = line.match(pattern);
    if (match) latest = {
      epoch: Number(match[1]), epochs: Number(match[2]), gpuMemoryGb: Number(match[3]),
      loss: Number(match[4]), batch: Number(match[5]), batches: Number(match[6]),
    };
  }
  return latest;
}

function processAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return null;
  try { process.kill(pid, 0); return true; }
  catch (error) { return error.code === 'ESRCH' ? false : null; }
}

function queryGpu() {
  return new Promise(resolve => {
    execFile('nvidia-smi', [
      '--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw',
      '--format=csv,noheader,nounits',
    ], { windowsHide: true, timeout: SETTINGS.gpuTimeoutMs }, (error, stdout) => {
      if (error) { resolve({ available: false, reason: '当前无法读取 NVIDIA GPU 状态' }); return; }
      const values = stdout.trim().split('\n')[0].split(',').map(value => value.trim());
      const number = value => Number.isFinite(Number(value)) ? Number(value) : null;
      resolve({
        available: true, name: values[0], memoryUsedMb: number(values[1]),
        memoryTotalMb: number(values[2]), utilization: number(values[3]),
        temperature: number(values[4]), powerWatts: number(values[5]), sampledAt: Date.now(),
      });
    });
  });
}

class TrainingMonitorReader {
  constructor(projectRoot, options = {}) {
    this.root = fs.realpathSync(path.resolve(projectRoot));
    this.config = jsonFile(this.root, 'training/config.json', true);
    const name = this.config.training?.name;
    if (typeof name !== 'string' || !/^[\w.-]+$/.test(name) || name === '.' || name === '..') {
      throw new Error('训练名称无效，无法定位训练输出');
    }
    this.run = `runs/classify/${name}`;
    this.candidate = `models/candidates/${name}`;
    this.gpuEnabled = options.gpu !== false;
    this.gpu = null;
    this.gpuReadAt = 0;
    this.previousCpu = null;
  }

  hostSnapshot() {
    const cpu = os.cpus().reduce((sum, item) => ({
      idle: sum.idle + item.times.idle,
      total: sum.total + Object.values(item.times).reduce((total, value) => total + value, 0),
    }), { idle: 0, total: 0 });
    const elapsed = this.previousCpu ? cpu.total - this.previousCpu.total : 0;
    const utilization = elapsed > 0
      ? Math.max(0, Math.min(100, (1 - (cpu.idle - this.previousCpu.idle) / elapsed) * 100)) : null;
    this.previousCpu = cpu;
    const totalMemory = os.totalmem();
    const availableMemory = os.freemem();
    const memoryUsedRatio = (totalMemory - availableMemory) / totalMemory;
    return { cpuUtilization: utilization, totalMemory, availableMemory, memoryUsedRatio,
      memoryPressure: memoryUsedRatio >= SETTINGS.memoryPressureRatio };
  }

  artifactList() {
    const definitions = [
      ['best', '最佳检查点 best.pt', `${this.run}/weights/best.pt`, 'PyTorch'],
      ['last', '恢复检查点 last.pt', `${this.run}/weights/last.pt`, 'PyTorch'],
      ['history', '逐轮指标 results.csv', `${this.run}/results.csv`, 'CSV'],
      ['candidate-pt', '最终候选 best.pt', `${this.candidate}/best.pt`, 'PyTorch'],
      ['onnx', '推理模型 model.onnx', `${this.candidate}/model.onnx`, 'ONNX'],
      ['manifest', '导出参数与类别 manifest.json', `${this.candidate}/manifest.json`, 'JSON'],
      ['val-report', '完整验证集报告', `${this.run}/val-report.json`, 'JSON'],
      ['test-report', '独立测试集报告', `${this.run}/test-report.json`, 'JSON'],
      ['verification', '真实模型系统联调报告', 'training/system-verification.json', 'JSON'],
    ];
    return definitions.map(([id, label, relative, format]) => {
      const filename = safePath(this.root, relative);
      const stat = fs.existsSync(filename) ? fs.statSync(filename) : null;
      return { id, label, format, path: filename, exists: Boolean(stat), bytes: stat?.size ?? null,
        modifiedAt: stat ? stat.mtimeMs : null };
    });
  }

  artifact(id) {
    const artifact = this.artifactList().find(item => item.id === id);
    if (!artifact?.exists) throw new Error('该训练文件尚未生成');
    return artifact.path;
  }

  async snapshot() {
    const state = jsonFile(this.root, 'training/status.json', true);
    const dataset = jsonFile(this.root, 'datasets/plantvillage/dataset-report.json');
    const labels = jsonFile(this.root, 'training/labels.json') || [];
    const network = jsonFile(this.root, 'training/network.json');
    const transfer = jsonFile(this.root, 'training/transfer-report.json');
    const environment = jsonFile(this.root, 'training/environment.json');
    const historyFile = safePath(this.root, `${this.run}/results.csv`);
    const history = fs.existsSync(historyFile) ? parseHistory(fs.readFileSync(historyFile, 'utf8')) : [];
    const log = tailFile(this.root, '.logs/training/bootstrap.out.log');
    const errors = tailFile(this.root, '.logs/training/bootstrap.err.log');
    const batch = parseBatch(log);
    const latest = history.at(-1) || null;
    const totalEpochs = state.epochs || this.config.training.epochs;
    const completedEpochs = Math.min(totalEpochs, latest?.epoch ?? state.epoch ?? 0);
    const activeBatch = state.stage === 'training' && batch && batch.epoch > completedEpochs ? batch : null;
    const progress = Math.min(100, ((completedEpochs + (activeBatch ? activeBatch.batch / activeBatch.batches : 0)) / totalEpochs) * 100);
    const durations = history.slice(1).map((row, index) => row.seconds - history[index].seconds).filter(value => value > 0);
    const recentDurations = durations.slice(-5);
    const average = recentDurations.length ? recentDurations.reduce((sum, value) => sum + value, 0) / recentDurations.length : null;
    const trainingCompletion = jsonFile(this.root, `${this.run}/training-complete.json`);
    const trainingFinished = Boolean(trainingCompletion);
    const eta = average && !trainingFinished
      ? Math.max(0, (totalEpochs - completedEpochs - (activeBatch ? activeBatch.batch / activeBatch.batches : 0)) * average) : null;
    const best = history.reduce((current, row) => !current || row.top1 > current.top1 ? row : current, null);
    const alive = ACTIVE_STAGES.has(state.stage) ? processAlive(state.pid) : false;
    const interrupted = ACTIVE_STAGES.has(state.stage) && alive === false;
    if (this.gpuEnabled && Date.now() - this.gpuReadAt >= SETTINGS.gpuRefreshMs) {
      this.gpu = await queryGpu();
      this.gpuReadAt = Date.now();
    }
    const manifest = jsonFile(this.root, `${this.candidate}/manifest.json`);
    const classes = (dataset?.classes || manifest?.classes?.map(item => item.key) || []).map((key, index) => {
      const label = labels.find(item => item.key === key) || manifest?.classes?.find(item => item.key === key);
      return { index, key, crop: label?.crop || key.split('___')[0], disease: label?.disease || key.split('___')[1],
        label: label?.label || key, healthy: label?.healthy ?? key.endsWith('___healthy'),
        description: label?.description || '', counts: dataset?.per_class?.[key] || {} };
    });
    return {
      schemaVersion: 1, observedAt: Date.now(), refreshMs: SETTINGS.refreshMs, projectRoot: this.root,
      name: this.config.training.name, stage: interrupted ? 'interrupted' : state.stage,
      sourceStage: state.stage, running: ACTIVE_STAGES.has(state.stage) && alive !== false,
      terminal: TERMINAL_STAGES.has(state.stage), processAlive: alive, pid: state.pid,
      startedAt: state.started_at * 1000, epochUpdatedAt: state.updated_at * 1000,
      completedEpochs, totalEpochs, activeBatch, progress, trainingFinished,
      elapsedSeconds: Math.max(0, (TERMINAL_STAGES.has(state.stage) ? state.updated_at : Date.now() / 1000) - state.started_at),
      etaSeconds: eta, averageEpochSeconds: average, latest, best, history,
      evaluation: { evaluated: state.evaluated ?? null, total: state.total ?? null },
      error: state.error || (interrupted ? '训练进程已退出，尚未记录完成状态；请检查日志并恢复检查点。' : null),
      config: this.config, network, transfer, environment, gpu: this.gpu, host: this.hostSnapshot(), classes,
      dataset: dataset ? {
        images: dataset.images, counts: dataset.counts, invalidImages: dataset.invalid_images,
        crossSplitLeafOverlap: dataset.cross_split_leaf_overlap, crossSplitHashOverlap: dataset.cross_split_sha256_overlap,
        manifestSha256: dataset.manifest_sha256, source: dataset.source,
      } : null,
      validation: jsonFile(this.root, `${this.run}/val-report.json`),
      test: jsonFile(this.root, `${this.run}/test-report.json`), manifest,
      deployment: jsonFile(this.root, 'training/deployment.json'),
      verification: jsonFile(this.root, 'training/system-verification.json'),
      artifacts: this.artifactList(),
      logs: log.split(/[\r\n]+/).filter(Boolean).slice(-SETTINGS.logLines),
      errors: errors.split(/[\r\n]+/).filter(Boolean).slice(-SETTINGS.logLines),
    };
  }
}

module.exports = { TrainingMonitorReader, SETTINGS, parseHistory, parseBatch, safePath, contained };
