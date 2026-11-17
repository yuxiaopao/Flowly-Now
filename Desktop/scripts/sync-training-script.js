/**
 * Copy Backend train_model.py into training-scripts for production bundles.
 */
const fs = require('fs');
const path = require('path');
const { syncTrainingRuntime, rewriteRuntimeImports } = require('./sync-training-runtime');

const source = path.join(__dirname, '..', '..', 'Backend', 'scripts', 'train_model.py');
const targetDir = path.join(__dirname, '..', 'training-scripts');
const target = path.join(targetDir, 'train_model.py');

if (!fs.existsSync(source)) {
  throw new Error(`[sync-training-script] Source not found: ${source}`);
}

fs.mkdirSync(targetDir, { recursive: true });
syncTrainingRuntime();
fs.writeFileSync(target, rewriteRuntimeImports(fs.readFileSync(source, 'utf8')), 'utf8');
console.log('[sync-training-script] Copied train_model.py to training-scripts/');
