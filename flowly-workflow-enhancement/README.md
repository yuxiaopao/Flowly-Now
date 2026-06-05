# flowly-workflow-enhancement

Multi-agent pipeline project managed by team-tasks.

## Structure

- `task.json` — Shared task registry
- `outputs/` — Agent output files
- `scripts/` — Task manager CLI

## Quick Start

```bash
# Add tasks
python3 scripts/task_manager.py add "task-1" --role code --desc "..."
python3 scripts/task_manager.py add "task-2" --role test --deps "task-1"

# Run pipeline
python3 scripts/task_manager.py run --mode dag

# Get summary
python3 scripts/task_manager.py summary
```
