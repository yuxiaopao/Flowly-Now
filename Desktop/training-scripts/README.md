# Training Scripts

This directory contains the training scripts that are bundled with the Flowly Agent desktop app.

## Contents

- `train_model.py` — Main training script (symlinked from `../Backend/scripts/train_model.py`)

The Electron builder copies this directory to:
- `%APPDATA%/Flowly Agent/resources/training-scripts/` (Windows)
- `~/Library/Application Support/Flowly Agent/resources/training-scripts/` (macOS)
- `~/.config/Flowly Agent/resources/training-scripts/` (Linux)

## Usage

The `train_model.py` script is called by the Electron main process with these arguments:

```
python train_model.py --config <json_config_path> --job-id <job_id> --output-dir <output_dir>
```

During development, the Electron app uses `../Backend/scripts/train_model.py` directly.
During production build, it uses the bundled copy in `resources/training-scripts/`.

## Building

To rebuild the training scripts bundle:

```bash
cd Desktop
npm run build
```

The build process copies `../Backend/scripts/train_model.py` into this directory.
