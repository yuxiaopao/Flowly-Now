/**
 * Desktop package smoke test — validates entrypoint, training script sync, python.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync, spawn } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.join(__dirname, '..');

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

function launchElectronBriefly() {
  return new Promise((resolve, reject) => {
    const electronCli = path.join(desktopRoot, 'node_modules', 'electron', 'cli.js');
    const child = spawn(process.execPath, [electronCli, desktopRoot, '--enable-logging', '--use-renderer'], {
      cwd: desktopRoot,
      env: {
        ...process.env,
        ELECTRON_DISABLE_SECURITY_WARNINGS: 'true',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    let stderr = '';
    child.stderr.on('data', (chunk) => { stderr += chunk.toString(); });

    const timer = setTimeout(() => {
      child.kill('SIGTERM');
    }, 5000);

    child.on('error', reject);
    child.on('exit', (code, signal) => {
      clearTimeout(timer);
      if (signal === 'SIGTERM' || code === 0 || code === null) {
        pass('electron app launched and exited cleanly');
        resolve();
        return;
      }
      reject(new Error(`electron exited with code ${code}: ${stderr.slice(-500)}`));
    });
  });
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
