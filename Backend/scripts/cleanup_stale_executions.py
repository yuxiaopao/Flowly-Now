#!/usr/bin/env python
"""CLI wrapper for cleanup_stale_executions management command."""
import os
import subprocess
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = os.environ.get("FLOWLY_PYTHON", sys.executable)


def main():
    args = sys.argv[1:] or ["--hours=1"]
    cmd = [PYTHON, "manage.py", "cleanup_stale_executions", *args]
    return subprocess.call(cmd, cwd=BACKEND_DIR)


if __name__ == "__main__":
    sys.exit(main())
