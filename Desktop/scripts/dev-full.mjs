/**
 * Start Frontend dev server + Electron (full desktop dev experience)
 */
import { spawn } from 'child_process';
import http from 'http';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.join(__dirname, '..');
const frontendRoot = path.join(desktopRoot, '..', 'Frontend');
const devUrl = process.env.FLOWLY_DEV_SERVER_URL || 'http://127.0.0.1:5200';

function waitForServer(url, timeoutMs = 120000) {
  const started = Date.now();
  const { hostname, port } = new URL(url);

  return new Promise((resolve, reject) => {
    const tick = () => {
      const req = http.get({ hostname, port, path: '/', timeout: 2000 }, (res) => {
        res.resume();
        resolve();
      });
      req.on('error', () => {
        if (Date.now() - started > timeoutMs) {
          reject(new Error(`Dev server timeout: ${url}`));
          return;
        }
        setTimeout(tick, 1000);
      });
    };
    tick();
  });
}

function spawnLogged(label, command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: 'inherit',
    shell: process.platform === 'win32',
    ...options,
  });
  child.on('exit', (code) => {
    if (code && code !== 0) {
      console.error(`[dev-full] ${label} exited with code ${code}`);
      process.exit(code);
    }
  });
  return child;
}

console.log('[dev-full] Starting Frontend dev server...');
const vite = spawnLogged('vite', 'npm', ['run', 'dev'], { cwd: frontendRoot });

async function main() {
  await waitForServer(devUrl);
  console.log('[dev-full] Frontend ready at', devUrl);

  console.log('[dev-full] Starting Electron...');
  const electronCli = path.join(desktopRoot, 'node_modules', 'electron', 'cli.js');
  const electron = spawnLogged('electron', process.execPath, [
    electronCli,
    desktopRoot,
    '--enable-logging',
    '--use-dev-server',
  ], {
    cwd: desktopRoot,
    env: {
      ...process.env,
      FLOWLY_DEV_SERVER_URL: devUrl,
    },
  });

  const shutdown = () => {
    vite.kill('SIGTERM');
    electron.kill('SIGTERM');
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  electron.on('exit', () => {
    vite.kill('SIGTERM');
    process.exit(0);
  });
}

main().catch((err) => {
  console.error('[dev-full] Failed:', err.message);
  vite.kill('SIGTERM');
  process.exit(1);
});
