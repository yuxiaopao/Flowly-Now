/** Bundle the canonical index builder and its pure standalone runtime helpers. */
const fs = require('node:fs');
const path = require('node:path');
const { syncTrainingRuntime, rewriteRuntimeImports } = require('./sync-training-runtime');

const desktopRoot = path.join(__dirname, '..');
const source = path.join(desktopRoot, '..', 'Backend', 'scripts', 'build_clip_index.py');
const targetDirectory = path.join(desktopRoot, 'training-scripts');
if (!fs.existsSync(source)) throw new Error('Canonical CLIP index script is missing');
syncTrainingRuntime();
fs.mkdirSync(targetDirectory, { recursive: true });
fs.writeFileSync(path.join(targetDirectory, 'build_clip_index.py'), rewriteRuntimeImports(fs.readFileSync(source, 'utf8')), 'utf8');
console.log('[sync-clip-index-script] Canonical builder and standalone runtime are ready');
