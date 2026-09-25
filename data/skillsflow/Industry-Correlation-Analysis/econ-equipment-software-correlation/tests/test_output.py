from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_legacy_script_checks() -> None:
    local_script = Path(__file__).with_name("test_outputs.py")
    harness_script = Path("/tests/test_outputs.py")
    script = harness_script if harness_script.exists() else local_script

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError((result.stdout or "") + "\n" + (result.stderr or ""))

