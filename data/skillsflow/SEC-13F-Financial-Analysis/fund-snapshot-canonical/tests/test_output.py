from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_legacy_pytest_suite() -> None:
    local_test = Path(__file__).with_name("test_outputs.py")
    harness_test = Path("/tests/test_outputs.py")
    test_file = harness_test if harness_test.exists() else local_test

    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError((result.stdout or "") + "\n" + (result.stderr or ""))

