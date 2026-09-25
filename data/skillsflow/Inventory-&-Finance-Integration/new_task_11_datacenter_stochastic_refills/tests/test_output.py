from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_legacy_node_checks() -> None:
    local_script = Path(__file__).with_name("test_outputs.js")
    harness_script = Path("/tests/test_outputs.js")
    script = harness_script if harness_script.exists() else local_script

    env = os.environ.copy()
    if not env.get("NODE_PATH"):
        local_node_modules = script.parents[1] / "node_modules"
        if local_node_modules.exists():
            env["NODE_PATH"] = str(local_node_modules)

    result = subprocess.run(
        ["node", str(script)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise AssertionError((result.stdout or "") + "\n" + (result.stderr or ""))

