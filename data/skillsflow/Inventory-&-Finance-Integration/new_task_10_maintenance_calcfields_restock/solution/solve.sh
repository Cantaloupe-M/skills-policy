#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TASK_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [ -f /root/Maintenance_Parts_and_Deliveries_Latest.xlsx ]; then
  INPUT_FILE="/root/Maintenance_Parts_and_Deliveries_Latest.xlsx"
  OUTPUT_FILE="/root/maintenance_resupply_actions_sep_2025.xlsx"
else
  INPUT_FILE="${TASK_DIR}/environment/Maintenance_Parts_and_Deliveries_Latest.xlsx"
  OUTPUT_FILE="${TASK_DIR}/maintenance_resupply_actions_sep_2025.xlsx"
fi

if [ -d "${TASK_DIR}/node_modules" ]; then
  export NODE_PATH="${TASK_DIR}/node_modules:${NODE_PATH:-}"
fi

node "${SCRIPT_DIR}/solve.js" "${INPUT_FILE}" "${OUTPUT_FILE}"
