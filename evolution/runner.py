"""Shared runner types for SkillFlow benchmark execution.

Extracted from ``run_skillflow_evolution.py`` to keep the entrypoint thin
and make these types reusable across different benchmark scripts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    """Outcome of running one benchmark group job."""
    group_name: str
    job_name: str
    job_dir: Path
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def result_to_json(result: RunResult, *, indent: int | None = None) -> str:
    """Serialize a RunResult for entrypoint output."""
    return json.dumps(
        {
            "group_name": result.group_name,
            "job_name": result.job_name,
            "job_dir": str(result.job_dir),
            "success": result.success,
            "message": result.message,
        },
        ensure_ascii=False,
        indent=indent,
    )


# ---------------------------------------------------------------------------
# Fast-test defaults (used by both benchmark entry points)
# ---------------------------------------------------------------------------

FAST_TEST_MAX_TURNS = 5
FAST_TEST_REWARD = 1.0

SPLIT_MANIFEST_FILENAME = "skillflow_split.json"
TEST_PROGRESS_FILENAME = "test_progress.json"
