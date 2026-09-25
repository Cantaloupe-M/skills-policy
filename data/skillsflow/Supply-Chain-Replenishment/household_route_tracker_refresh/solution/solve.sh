#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -d /root ] && [ -f /root/Household_Route_Template.xlsx ]; then
  INPUT_ROOT="/root"
  OUTPUT_ROOT="/root"
else
  INPUT_ROOT="${TASK_DIR}/environment"
  OUTPUT_ROOT="${TASK_DIR}"
fi

python3 "${SCRIPT_DIR}/solve.py" "${INPUT_ROOT}" "${OUTPUT_ROOT}"
