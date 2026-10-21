/**
 * Ensure Desktop training-scripts/build_clip_index.py exists for bundled builds.
 * Dev mode resolves Backend/scripts/build_clip_index.py from main.js; this copy
 * is used when packaging without the monorepo Backend tree.
 */
const fs = require('fs');
const path = require('path');

const desktopRoot = path.join(__dirname, '..');
const targetDir = path.join(desktopRoot, 'training-scripts');
const target = path.join(targetDir, 'build_clip_index.py');

const sources = [
  path.join(desktopRoot, 'training-scripts', 'build_clip_index.py'),
  path.join(desktopRoot, '..', 'Backend', 'scripts', 'build_clip_index.py'),
];

let copied = false;
for (const source of sources) {
  if (!fs.existsSync(source)) continue;
  const content = fs.readFileSync(source, 'utf-8');
  const desktopVariant = content.includes('parents[2]')
    ? content
    : content.replace(
      /BACKEND = Path\(__file__\)\.resolve\(\)\.parents\[1\]/,
      "BACKEND = Path(__file__).resolve().parents[2] / 'Backend'",
    );

  fs.mkdirSync(targetDir, { recursive: true });
  fs.writeFileSync(target, desktopVariant, 'utf-8');
  console.log('[sync-clip-index-script] build_clip_index.py ready at training-scripts/');
  copied = true;
  break;
}

if (!copied) {
  console.warn('[sync-clip-index-script] No source build_clip_index.py found — skip');
}
