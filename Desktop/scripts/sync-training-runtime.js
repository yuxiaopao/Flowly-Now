const fs = require('node:fs');
const path = require('node:path');

const desktopRoot = path.join(__dirname, '..');
const backendRoot = path.join(desktopRoot, '..', 'Backend');
const runtimeDirectory = path.join(desktopRoot, 'training-scripts', 'flowly_runtime');
const modules = [
  ['training/yolo_weights.py', 'yolo_weights.py'],
  ['training/clip_service.py', 'clip_service.py'],
  ['training/clip_trainer.py', 'clip_trainer.py'],
  ['training/tabular_artifacts.py', 'tabular_artifacts.py'],
  ['datasets/ml_format_validators.py', 'ml_format_validators.py'],
];
const imports = [
  ['training.yolo_weights', 'flowly_runtime.yolo_weights'],
  ['training.clip_service', 'flowly_runtime.clip_service'],
  ['training.clip_trainer', 'flowly_runtime.clip_trainer'],
  ['training.tabular_artifacts', 'flowly_runtime.tabular_artifacts'],
  ['datasets.ml_format_validators', 'flowly_runtime.ml_format_validators'],
];

function rewriteRuntimeImports(source) {
  return imports.reduce((result, [original, bundled]) => result.replaceAll(original, bundled), source);
}

function syncTrainingRuntime() {
  for (const [source] of modules) {
    if (!fs.existsSync(path.join(backendRoot, source))) throw new Error(`Training runtime source missing: ${source}`);
  }
  fs.mkdirSync(runtimeDirectory, { recursive: true });
  fs.writeFileSync(path.join(runtimeDirectory, '__init__.py'), '"""Generated standalone Flowly training helpers."""\n', 'utf8');
  for (const [source, target] of modules) {
    const code = fs.readFileSync(path.join(backendRoot, source), 'utf8');
    fs.writeFileSync(path.join(runtimeDirectory, target), rewriteRuntimeImports(code), 'utf8');
  }
}

module.exports = { rewriteRuntimeImports, syncTrainingRuntime };
