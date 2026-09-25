#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f /root/Backup_Fuel_and_Refills_Latest.xlsx ]; then
  INPUT_FILE="/root/Backup_Fuel_and_Refills_Latest.xlsx"
  OUTPUT_FILE="/root/stochastic_refill_plan_october_2025.xlsx"
else
  INPUT_FILE="${TASK_DIR}/environment/Backup_Fuel_and_Refills_Latest.xlsx"
  OUTPUT_FILE="${TASK_DIR}/stochastic_refill_plan_october_2025.xlsx"
fi

if [ -d "${TASK_DIR}/node_modules" ]; then
  export NODE_PATH="${TASK_DIR}/node_modules:${NODE_PATH:-}"
fi

node "${SCRIPT_DIR}/solve.js" "${INPUT_FILE}" "${OUTPUT_FILE}"
