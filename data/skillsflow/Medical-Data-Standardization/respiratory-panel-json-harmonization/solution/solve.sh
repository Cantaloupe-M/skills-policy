#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd /root
python3 "$SCRIPT_DIR/run.py"
