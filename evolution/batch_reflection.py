"""Verifier-grounded failure reflection for the batch evolution loop."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from evolution.outcome import TrialOutcome, sanitize_retry_text

REFLECTION_SYSTEM_PROMPT = """\
You diagnose failed AI-agent trials from verifier evidence and a numbered trajectory.

Your job is to explain *which prior step caused the observed failure*, not merely how
one could solve the task. Never infer a causal relationship from temporal proximity
alone. Every causal claim must cite one or more supplied trajectory step IDs and a
verifier check ID. If the evidence cannot establish a cause, write UNKNOWN instead
of guessing and prescribe a diagnostic validation action.

Do not reveal expected values, reference outputs, full test assertions, secrets, or
absolute paths. Keep corrective actions focused on independently checking the task
contract and repairing the identified process error.

Output format:
FAILURE OBSERVABLE: <verifier failure or runtime failure>
CAUSAL STEP(S): <s1, s2 | UNKNOWN>
CAUSAL EVIDENCE: <verifier check and trajectory evidence>
DIAGNOSIS CONFIDENCE: <confirmed | likely | insufficient-evidence>
ROOT CAUSE: <1-2 sentences>
CORRECTIVE ACTION: <2-3 specific, non-answer-bearing instructions>
MISSING: <skills, tools, or validation capability>
"""

MAX_TRAJECTORY_CHARS = 4_000
MAX_VERIFIER_ITEMS = 25
MAX_CAUSAL_STEPS = 10


def _read_trajectory_text(trajectory_path: Path | None) -> str:
    """Read a fallback trajectory excerpt, capped without hiding its ending."""
    if trajectory_path is None or not trajectory_path.is_file():
        return "(no trajectory available)"
    try:
        text = trajectory_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "(could not read trajectory)"
    if len(text) <= MAX_TRAJECTORY_CHARS:
        return text
    half = MAX_TRAJECTORY_CHARS // 2
    return text[:half] + "\n\n# ... [middle snipped] ...\n\n" + text[-half:]


def _normalized_steps(result: Any) -> list[dict[str, str]]:
    outcome = getattr(result, "outcome", None)
    if isinstance(outcome, TrialOutcome) and outcome.compacted_trajectory:
        steps: list[dict[str, str]] = []
        for index, raw in enumerate(outcome.compacted_trajectory, start=1):
            if not isinstance(raw, dict):
                continue
            step_id = f"s{raw.get('step') or index}"
            action = str(raw.get("action") or raw.get("tool") or "agent_action")
            detail = str(raw.get("code") or raw.get("command_or_summary") or raw.get("result") or "")
            safe_detail, _ = sanitize_retry_text(detail[:1_000])
            steps.append({"id": step_id, "action": action, "detail": safe_detail})
        # ``compacted_trajectory`` is already selected across the full attempt
        # by the runner.  Do not turn it back into a tail-only window here.
        return steps
    return []


def _candidate_steps(steps: list[dict[str, str]]) -> list[dict[str, str]]:
    """Select potentially relevant actions conservatively; candidates are not causes."""
    action_words = ("write", "edit", "create", "save", "bash", "tool_result_error")
    candidates = [step for step in steps if any(word in step["action"].lower() for word in action_words)]
    return candidates[-MAX_CAUSAL_STEPS:]


def build_reflection_evidence(result: Any, task_family: str = "") -> dict[str, Any]:
    """Create bounded, retry-safe evidence for one failed attempt."""
    outcome = getattr(result, "outcome", None)
    verifier_feedback: list[dict[str, Any]] = []
    failed_checks: list[str] = []
    objective = ""
    constraints: list[str] = []
    if isinstance(outcome, TrialOutcome):
        objective, _ = sanitize_retry_text(outcome.task_contract.objective[:2_000])
        constraints = [sanitize_retry_text(item[:500])[0] for item in outcome.task_contract.constraints[:10]]
        failed_checks = outcome.failed_test_names[:MAX_VERIFIER_ITEMS]
        for item in outcome.verifier_feedback[:MAX_VERIFIER_ITEMS]:
            if not isinstance(item, dict):
                continue
            message, redacted = sanitize_retry_text(str(item.get("message") or ""))
            verifier_feedback.append({
                "name": str(item.get("name") or "verifier"),
                "status": str(item.get("status") or "unknown"),
                "message": message[:1_000],
                "redacted": bool(redacted),
            })
    steps = _normalized_steps(result)
    exception, _ = sanitize_retry_text(str(getattr(result, "exception_info", "") or ""))
    return {
        "task": str(getattr(result, "task_name", "")),
        "trial": str(getattr(result, "trial_name", "")),
        "task_family": task_family,
        "reward": float(getattr(result, "reward", 0.0) or 0.0),
        "exception": exception[:2_000] or None,
        "objective": objective,
        "constraints": constraints,
        "failed_verifier_checks": failed_checks,
        "verifier_feedback": verifier_feedback,
        "trajectory_steps": steps,
        "causal_candidates": _candidate_steps(steps),
        "fallback_trajectory": "" if steps else _read_trajectory_text(getattr(result, "trajectory_path", None)),
        "truncation": {
            "max_verifier_items": MAX_VERIFIER_ITEMS,
            "max_causal_steps": MAX_CAUSAL_STEPS,
            "fallback_trajectory_chars": MAX_TRAJECTORY_CHARS,
        },
    }


def _render_evidence(evidence: dict[str, Any]) -> str:
    return json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True)


def reflect_on_failure(
    task_name: str,
    trial_name: str,
    reward: float,
    exception_info: str | None,
    trajectory_path: Path | None = None,
    *,
    extra_context: str = "",
) -> str:
    """Backward-compatible fallback reflection entrypoint."""
    from llm_config import call_llm
    prompt = (
        "Analyze this failed agent trial.\n\n"
        f"Task: {task_name}\nTrial: {trial_name}\nReward: {reward}\n"
        f"Exception: {exception_info or '(none)'}\n\nTrajectory:\n"
        f"{_read_trajectory_text(trajectory_path)}"
    )
    if extra_context:
        prompt += f"\n\nAdditional context:\n{extra_context}"
    try:
        return call_llm(messages=[{"role": "user", "content": prompt}], system=REFLECTION_SYSTEM_PROMPT, temperature=0.3, profile="evolution").strip()
    except Exception as exc:
        return (
            "FAILURE OBSERVABLE: Reflection service unavailable.\n"
            "CAUSAL STEP(S): UNKNOWN\n"
            "CAUSAL EVIDENCE: No model diagnosis was produced.\n"
            "DIAGNOSIS CONFIDENCE: insufficient-evidence\n"
            f"ROOT CAUSE: Reflection LLM failed ({exc}).\n"
            "CORRECTIVE ACTION: Independently inspect the task contract and run the available verifier before retrying.\n"
            "MISSING: verifier-grounded diagnosis"
        )


def reflect_on_trial_result(result: Any, task_family: str = "") -> tuple[str, dict[str, Any]]:
    """Diagnose a failed result using bounded verifier and trajectory evidence."""
    from llm_config import call_llm
    evidence = build_reflection_evidence(result, task_family)
    prompt = "Analyze this failed agent trial from the following evidence packet:\n\n" + _render_evidence(evidence)
    try:
        reflection = call_llm(
            messages=[{"role": "user", "content": prompt}],
            system=REFLECTION_SYSTEM_PROMPT,
            temperature=0.3,
            profile="evolution",
        ).strip()
    except Exception as exc:
        reflection = (
            "FAILURE OBSERVABLE: Verifier-reported failure could not be analyzed automatically.\n"
            "CAUSAL STEP(S): UNKNOWN\n"
            "CAUSAL EVIDENCE: Reflection LLM call failed.\n"
            "DIAGNOSIS CONFIDENCE: insufficient-evidence\n"
            f"ROOT CAUSE: Reflection LLM failed ({exc}).\n"
            "CORRECTIVE ACTION: Inspect the task contract and run the verifier after independently validating the artifact.\n"
            "MISSING: verifier-grounded diagnosis"
        )
    return reflection, evidence


def retry_brief(reflection: str) -> str:
    """Return the only reflection text eligible for injection into a retry task."""
    safe, _ = sanitize_retry_text(reflection)
    return safe


def run_reflection_retry_loop[T](
    initial_result: T,
    *,
    task_name: str,
    task_family: str,
    max_retries: int,
    retry: Callable[[str, int], T],
    log_prefix: str = "Reflection",
    reflector: Callable[[T, str, str], tuple[str, dict[str, Any]]] | None = None,
) -> T:
    """Reflect and retry while preserving legacy semantics.

    ``reflector`` is an optional method adapter.  The default remains the
    verifier-grounded reflection used by SkillFlow.  ExpeL can provide its
    own previous-trial reflection protocol without changing the batch loop.
    """
    result = initial_result
    attempt_results = [initial_result]
    retries_used = max(0, int(getattr(result, "retries_used", 0)))
    while not bool(getattr(result, "success", False)) and retries_used < max(0, max_retries):
        retry_number = retries_used + 1
        if reflector is None:
            reflection, evidence = reflect_on_trial_result(result, task_family)
        else:
            reflection, evidence = reflector(result, task_name, task_family)
        trial_dir = Path(result.trial_dir)
        trial_dir.mkdir(parents=True, exist_ok=True)
        (trial_dir / f"reflection_input_attempt_{retry_number:02d}.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
        )
        (trial_dir / f"reflection_attempt_{retry_number:02d}.md").write_text(reflection, encoding="utf-8")
        safe_brief = retry_brief(reflection)
        (trial_dir / f"retry_brief_attempt_{retry_number:02d}.md").write_text(safe_brief, encoding="utf-8")
        print(f"[{log_prefix}] Reflecting on '{task_name}' (retry {retry_number}/{max_retries}): {safe_brief[:200].replace(chr(10), ' ')}...")
        result = retry(safe_brief, retry_number)
        attempt_results.append(result)
        result.retries_used = retry_number
        retries_used = retry_number
    result.attempt_results = attempt_results
    return result
