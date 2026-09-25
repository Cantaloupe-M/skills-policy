#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f /root/Staffing_and_Shifts_Latest.xlsx ]; then
  INPUT_FILE="/root/Staffing_and_Shifts_Latest.xlsx"
  OUTPUT_FILE="/root/additional_shift_blocks_needed_august_2025.xlsx"
else
  INPUT_FILE="${TASK_DIR}/environment/Staffing_and_Shifts_Latest.xlsx"
  OUTPUT_FILE="${TASK_DIR}/additional_shift_blocks_needed_august_2025.xlsx"
fi

if [ -d "${TASK_DIR}/node_modules" ]; then
  export NODE_PATH="${TASK_DIR}/node_modules:${NODE_PATH:-}"
fi

node "${SCRIPT_DIR}/solve.js" "${INPUT_FILE}" "${OUTPUT_FILE}"
