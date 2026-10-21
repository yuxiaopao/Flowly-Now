/**
 * Copy Backend train_model.py into training-scripts for production bundles.
 */
const fs = require('fs');
const path = require('path');

const source = path.join(__dirname, '..', '..', 'Backend', 'scripts', 'train_model.py');
const targetDir = path.join(__dirname, '..', 'training-scripts');
const target = path.join(targetDir, 'train_model.py');

if (!fs.existsSync(source)) {
  console.warn('[sync-training-script] Source not found:', source);
  process.exit(0);
}

fs.mkdirSync(targetDir, { recursive: true });
fs.copyFileSync(source, target);
console.log('[sync-training-script] Copied train_model.py to training-scripts/');
