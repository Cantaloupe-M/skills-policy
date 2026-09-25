#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="${TASK_ROOT:-/root}"

python3 "$SCRIPT_DIR/tools/run_audit.py" "$ROOT_DIR"
