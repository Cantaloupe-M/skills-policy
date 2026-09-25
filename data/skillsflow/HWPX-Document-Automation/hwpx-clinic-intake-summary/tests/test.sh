#!/bin/bash

VERIFIER_DIR="/logs/verifier"
mkdir -p "${VERIFIER_DIR}" >/dev/null 2>&1 || true
if [ ! -d "${VERIFIER_DIR}" ] || [ ! -w "${VERIFIER_DIR}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  VERIFIER_DIR="${SCRIPT_DIR}/.verifier"
  mkdir -p "${VERIFIER_DIR}"
fi

TEST_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/test_output.py"
if [ -f /tests/test_output.py ]; then
  TEST_SCRIPT="/tests/test_output.py"
fi

if [ -d /root ]; then
  cd /root || true
fi

python3 -m pytest --ctrf "${VERIFIER_DIR}/ctrf.json" "${TEST_SCRIPT}" -rA -v
PYTEST_EXIT_CODE=$?

if [ $PYTEST_EXIT_CODE -eq 0 ]; then
  SCORE=1
  PASSED=1
  FAILED=0
  STATUS="passed"
else
  SCORE=0
  PASSED=0
  FAILED=1
  STATUS="failed"
fi

printf "%s\n" "$SCORE" > "${VERIFIER_DIR}/reward.txt"

if [ ! -f "${VERIFIER_DIR}/ctrf.json" ]; then
  cat > "${VERIFIER_DIR}/ctrf.json" <<EOF
{"results":{"tool":{"name":"python3 -m pytest"},"summary":{"tests":1,"passed":${PASSED},"failed":${FAILED},"skipped":0,"pending":0,"other":0},"tests":[{"name":"$(basename "${TEST_SCRIPT}")","status":"${STATUS}"}]}}
EOF
fi

exit 0
