/**
 * Generate Desktop app icons from Frontend/public/logo.png
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const desktopRoot = path.join(__dirname, '..');
const assetsDir = path.join(desktopRoot, 'assets');
const sourceLogo = path.join(desktopRoot, '..', 'Frontend', 'public', 'logo.png');
const iconPng = path.join(assetsDir, 'icon.png');
const iconIco = path.join(assetsDir, 'icon.ico');
const generator = path.join(__dirname, 'generate_icons.py');

if (!fs.existsSync(sourceLogo)) {
  console.error('[sync-icons] Source logo not found:', sourceLogo);
  process.exit(1);
}

const pyCandidates = process.platform === 'win32'
  ? ['py', 'python', 'python3']
  : ['python3', 'python'];

let generated = false;
for (const py of pyCandidates) {
  try {
    execSync(`"${py}" "${generator}" "${sourceLogo}" "${iconPng}" "${iconIco}"`, {
      stdio: 'inherit',
      shell: true,
    });
    generated = true;
    break;
  } catch {
    // try next
  }
}

if (!generated) {
  fs.mkdirSync(assetsDir, { recursive: true });
  fs.copyFileSync(sourceLogo, iconPng);
  console.warn('[sync-icons] Pillow unavailable — copied logo.png only. Run: pip install Pillow');
  process.exit(0);
}

console.log('[sync-icons] Done — icons synced from Frontend/public/logo.png');
