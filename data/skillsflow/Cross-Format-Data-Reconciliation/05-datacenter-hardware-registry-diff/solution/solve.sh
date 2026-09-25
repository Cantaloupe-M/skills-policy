#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/tools/reconcile_snapshot.py" "$SCRIPT_DIR/task_config.json"
