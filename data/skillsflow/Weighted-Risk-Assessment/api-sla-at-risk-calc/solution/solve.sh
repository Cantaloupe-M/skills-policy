#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /root/output
python3 "$SCRIPT_DIR/tools/solve_workbook.py" /root/data/workbook.xlsx /root/output/result.xlsx
