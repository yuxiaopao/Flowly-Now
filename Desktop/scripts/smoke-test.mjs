/**
 * Desktop package smoke test — validates entrypoint, training script sync, python.
 */
import fs from 'fs';
import path from 'path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'url';
import { execSync, spawn } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.join(__dirname, '..');
const require = createRequire(import.meta.url);
const { stopOwnedProcess } = require('../training-control');

function fail(message) {
  console.error(`[FAIL] ${message}`);
  process.exit(1);
}

function pass(message) {
  console.log(`[PASS] ${message}`);
}

function readJson(relPath) {
  return JSON.parse(fs.readFileSync(path.join(desktopRoot, relPath), 'utf-8'));
}

function checkPackageEntry() {
  const pkg = readJson('package.json');
  const mainPath = path.join(desktopRoot, pkg.main);
  if (!fs.existsSync(mainPath)) {
    fail(`package.json main not found: ${pkg.main}`);
  }
  pass(`package main -> ${pkg.main}`);
}

function checkRequiredFiles() {
  for (const rel of ['main.js', 'preload.js']) {
    const full = path.join(desktopRoot, rel);
    if (!fs.existsSync(full)) fail(`missing ${rel}`);
  }
  pass('core desktop files present');
}

function ensureRendererBundle() {
  const rendererIndex = path.join(desktopRoot, 'renderer', 'index.html');
  if (fs.existsSync(rendererIndex)) {
    pass('renderer bundle present');
    return true;
  }
  console.log('[smoke] renderer missing — building Frontend for Electron...');
  execSync('node scripts/build-renderer.js', { cwd: desktopRoot, stdio: 'inherit' });
  if (!fs.existsSync(rendererIndex)) fail('renderer/index.html missing after build');
  pass('renderer bundle built');
  return true;
}

function syncTrainingScript() {
  execSync('node scripts/sync-training-script.js', { cwd: desktopRoot, stdio: 'inherit' });
  const target = path.join(desktopRoot, 'training-scripts', 'train_model.py');
  if (!fs.existsSync(target)) fail('training-scripts/train_model.py missing after sync');
  pass('training script synced');
}

function syncClipIndexScript() {
  execSync('node scripts/sync-clip-index-script.js', { cwd: desktopRoot, stdio: 'inherit' });
  const target = path.join(desktopRoot, 'training-scripts', 'build_clip_index.py');
  if (!fs.existsSync(target)) fail('training-scripts/build_clip_index.py missing after sync');
  const mainJs = fs.readFileSync(path.join(desktopRoot, 'main.js'), 'utf-8');
  if (!mainJs.includes('clipIndex:start')) fail('main.js missing clipIndex:start IPC');
  pass('CLIP index script + IPC present');
  for (const module of ['yolo_weights.py', 'clip_service.py', 'clip_trainer.py', 'ml_format_validators.py']) {
    if (!fs.existsSync(path.join(desktopRoot, 'training-scripts', 'flowly_runtime', module))) {
      fail(`missing standalone training helper: ${module}`);
    }
  }
}

function checkPython() {
  const candidates = process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python'];
  for (const cmd of candidates) {
    try {
      const version = execSync(`"${cmd}" --version`, { encoding: 'utf-8', shell: true }).trim();
      pass(`python available: ${cmd} (${version})`);
      return cmd;
    } catch {
      // continue
    }
  }
  console.warn('[WARN] Python not found — training subprocess will fail until Python is installed');
  return null;
}

function checkElectronBinary() {
  const electronCli = path.join(desktopRoot, 'node_modules', 'electron', 'cli.js');
  if (!fs.existsSync(electronCli)) {
    fail('electron not installed — run npm install in Desktop/');
  }
  const version = execSync(`node "${electronCli}" --version`, { encoding: 'utf-8' }).trim();
  pass(`electron binary ${version}`);
}

async function launchElectronBriefly() {
  const temporaryRoot = fs.realpathSync(os.tmpdir());
  const qaDirectory = fs.mkdtempSync(path.join(temporaryRoot, 'flowly-qa-'));
  const environment = { ...process.env, FLOWLY_QA_MODE: '1', FLOWLY_QA_USER_DATA_DIR: qaDirectory };
  delete environment.ELECTRON_RUN_AS_NODE;
  const child = spawn(require('electron'), [desktopRoot, '--enable-logging', '--use-renderer'], {
      cwd: desktopRoot,
      env: environment,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: process.platform !== 'win32',
    });
  let output = '';
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Electron did not finish loading its renderer')), 15000);
      function inspect(chunk) {
        output = (output + chunk.toString()).slice(-12000);
        if (output.includes('Renderer loaded')) { clearTimeout(timer); resolve(); }
      }
      child.stdout.on('data', inspect);
      child.stderr.on('data', inspect);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', code => { clearTimeout(timer); reject(new Error(`Electron exited before renderer load (${code}): ${output.slice(-500)}`)); });
    });
    const settings = JSON.parse(fs.readFileSync(path.join(qaDirectory, 'config.json'), 'utf8'));
    if (settings.apiToken) throw new Error('Isolated smoke profile unexpectedly contains a cloud credential');
    pass('native Electron loaded the renderer with a fresh profile and no cloud credentials');
  } finally {
    await stopOwnedProcess(child);
    const relative = path.relative(temporaryRoot, qaDirectory);
    if (relative.startsWith('..') || path.isAbsolute(relative) || !path.basename(qaDirectory).startsWith('flowly-qa-')) {
      throw new Error('Refusing to remove an unexpected smoke profile path');
    }
    fs.rmSync(qaDirectory, { recursive: true, force: true });
  }
}

async function main() {
  checkPackageEntry();
  checkRequiredFiles();
  ensureRendererBundle();
  syncTrainingScript();
  syncClipIndexScript();
  checkPython();
  checkElectronBinary();
  await launchElectronBriefly();
  console.log('\nDesktop smoke test passed.');
}

main().catch((err) => fail(err.message));
