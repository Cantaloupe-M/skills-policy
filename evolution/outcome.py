"""Dataset-independent trial outcome and verifier evidence helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

VERIFIER_MESSAGE_LIMIT = 1_500
VERIFIER_FEEDBACK_LIMIT = 25
_SECRET_RE = re.compile(r"(?i)(?:api[_-]?key|token|secret|password)\s*[=:]\s*\S+")
_ABSOLUTE_PATH_RE = re.compile(r"(?<!\w)/(?:[^\s`'\"]+/)+[^\s`'\"]+")
_EXPECTED_VALUE_RE = re.compile(
    r"(?i)(?:expected|want|should be|must equal)\s+[^\n]{1,240}(?:\s+(?:got|actual|received)\s+[^\n]{1,240})?"
)


@dataclass
class TaskContract:
    """Task-level evidence used to keep evolved skills semantically grounded."""

    family: str = ""
    objective: str = ""
    input_artifacts: list[dict[str, Any]] = field(default_factory=list)
    output_artifacts: list[dict[str, Any]] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    verifier_checks: list[str] = field(default_factory=list)


@dataclass
class TrialOutcome:
    """Normalized result emitted by a benchmark-specific runner."""

    trial_name: str
    task_name: str
    task_source: str
    verifier_passed: bool
    reward: float | None
    compacted_trajectory: list[dict[str, Any]] = field(default_factory=list)
    failed_test_names: list[str] = field(default_factory=list)
    final_agent_message: str | None = None
    exception_type: str | None = None
    exception_message: str | None = None
    task_contract: TaskContract = field(default_factory=TaskContract)
    verifier_feedback: list[dict[str, Any]] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    used_skill_ids: list[str] = field(default_factory=list)


def normalize_harbor_outcome(
    *,
    result_data: dict[str, Any],
    trial_dir: Path,
    task_name: str,
    task_source: str,
    success: bool,
    reward: float,
    exception_info: str | None,
    task_contract: TaskContract | None = None,
    compacted_trajectory: list[dict[str, Any]] | None = None,
) -> TrialOutcome:
    """Normalize Harbor verifier payloads without assuming one verifier schema."""
    verifier = result_data.get("verifier_result")
    # Harbor keeps the useful pytest/CTRF diagnostics in a sidecar file while
    # result.json commonly contains only the aggregate reward.  Include that
    # sidecar so reflection can identify failed checks and their traces.
    ctrf_path = trial_dir / "verifier" / "ctrf.json"
    if ctrf_path.is_file():
        try:
            ctrf_payload = json.loads(ctrf_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            ctrf_payload = None
        if isinstance(ctrf_payload, dict):
            if isinstance(verifier, dict):
                verifier = {**verifier, **ctrf_payload}
            elif verifier is None:
                verifier = ctrf_payload
    feedback = normalize_verifier_feedback(verifier)
    failed = [item["name"] for item in feedback if item["status"] not in {"passed", "success"}]
    return TrialOutcome(
        trial_name=str(result_data.get("trial_name") or trial_dir.name),
        task_name=task_name,
        task_source=task_source,
        verifier_passed=success,
        reward=reward,
        compacted_trajectory=compacted_trajectory or [],
        failed_test_names=failed,
        exception_message=exception_info,
        task_contract=task_contract or TaskContract(family=task_source),
        verifier_feedback=feedback,
    )


def normalize_verifier_feedback(payload: Any) -> list[dict[str, str]]:
    """Return deterministic, bounded verifier feedback from common result shapes."""
    entries: list[dict[str, str]] = []

    def add(name: Any, status: Any, message: Any = "") -> None:
        status_text = str(status or "failed").lower()
        if status_text in {"pass", "passed", "success", "resolved", "true"}:
            status_text = "passed"
        elif status_text in {"fail", "failed", "error", "false", "call_failed"}:
            status_text = "failed"
        entries.append({
            "name": str(name or "verifier"),
            "status": status_text,
            "message": _bounded_text(message, VERIFIER_MESSAGE_LIMIT),
        })

    if isinstance(payload, dict):
        result_container = payload.get("results")
        if isinstance(result_container, dict) and "tests" not in payload:
            payload = {**payload, "tests": result_container.get("tests", [])}
        tests = payload.get("tests")
        if isinstance(tests, list):
            for item in tests:
                if isinstance(item, dict):
                    message = item.get("message") or ""
                    trace = item.get("trace") or ""
                    detail = "\n".join(str(value) for value in (message, trace) if value)
                    add(item.get("name"), item.get("status") or item.get("raw_status"), detail)
        parser_results = payload.get("parser_results")
        if isinstance(parser_results, dict):
            for name, status in sorted(parser_results.items(), key=lambda item: str(item[0])):
                if isinstance(status, dict):
                    add(name, status.get("status") or status.get("passed"), status.get("message") or status.get("error"))
                else:
                    add(name, status)
        elif isinstance(parser_results, list):
            for index, item in enumerate(parser_results):
                if isinstance(item, dict):
                    add(item.get("name", index), item.get("status") or item.get("passed"), item.get("message") or item.get("error"))
                else:
                    add(index, item)
        error = payload.get("error")
        if error:
            add("verifier_error", "failed", error)
        if not entries and payload:
            rewards = payload.get("rewards")
            reward = rewards.get("reward") if isinstance(rewards, dict) else payload.get("reward")
            if reward is not None:
                add("reward", "passed" if float(reward or 0) >= 1 else "failed", "")
            else:
                add("verifier_payload", "unknown", json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif payload is not None:
        add("verifier_payload", "unknown", repr(payload))

    return entries[:VERIFIER_FEEDBACK_LIMIT]


def outcome_digest(outcome: TrialOutcome | None) -> dict[str, Any] | None:
    """Return non-sensitive manifest data for a normalized outcome."""
    if outcome is None:
        return None
    return {
        "task_source": outcome.task_source,
        "verifier_passed": outcome.verifier_passed,
        "failed_test_names": outcome.failed_test_names[:VERIFIER_FEEDBACK_LIMIT],
        "verifier_feedback": [
            {"name": item.get("name", "verifier"), "status": item.get("status", "unknown")}
            for item in outcome.verifier_feedback[:VERIFIER_FEEDBACK_LIMIT]
        ],
    }


def sanitize_retry_text(text: str) -> tuple[str, int]:
    """Remove answer-bearing verifier details before they reach a retry prompt."""
    original = str(text or "")
    cleaned = _SECRET_RE.sub("[redacted credential]", original)
    cleaned = _ABSOLUTE_PATH_RE.sub("[redacted path]", cleaned)
    cleaned = _EXPECTED_VALUE_RE.sub("[redacted expected-value comparison]", cleaned)
    return cleaned, int(cleaned != original)


def _bounded_text(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else text[:limit] + "… [truncated]"
