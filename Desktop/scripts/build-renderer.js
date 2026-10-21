/**
 * Build Frontend for Electron and copy dist -> Desktop/renderer
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const desktopRoot = path.join(__dirname, '..');
const frontendRoot = path.join(desktopRoot, '..', 'Frontend');
const rendererDir = path.join(desktopRoot, 'renderer');
const frontendDist = path.join(frontendRoot, 'dist');

if (!fs.existsSync(path.join(frontendRoot, 'package.json'))) {
  console.error('[build-renderer] Frontend directory not found:', frontendRoot);
  process.exit(1);
}

console.log('[build-renderer] Building Frontend (electron mode)...');
execSync('npm run build:electron', {
  cwd: frontendRoot,
  stdio: 'inherit',
  env: { ...process.env },
});

if (!fs.existsSync(path.join(frontendDist, 'index.html'))) {
  console.error('[build-renderer] Frontend dist missing index.html');
  process.exit(1);
}

console.log('[build-renderer] Copying dist -> Desktop/renderer ...');
fs.rmSync(rendererDir, { recursive: true, force: true });
fs.cpSync(frontendDist, rendererDir, { recursive: true });
console.log('[build-renderer] Done.');
