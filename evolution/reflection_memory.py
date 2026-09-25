"""Extract instance-grounded reflective memories for policy consolidation.

Retry reflections are written beside the failed attempt as Markdown sidecars.
This module turns their structured fields into the same candidate contract used
by semantic clustering, while preserving whether a later retry verified the
proposed correction.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from evolution.outcome import sanitize_retry_text
from evolution.types import BottleneckCandidate, ExplorationTrace, FailedAttempt

_FIELD_NAMES = (
    "FAILURE OBSERVABLE",
    "CAUSAL STEP(S)",
    "CAUSAL EVIDENCE",
    "DIAGNOSIS CONFIDENCE",
    "ROOT CAUSE",
    "CORRECTIVE ACTION",
    "MISSING",
)


def _field(text: str, name: str) -> str:
    pattern = rf"(?im)^\s*{re.escape(name)}\s*:\s*(.*?)(?=^\s*(?:{'|'.join(map(re.escape, _FIELD_NAMES))})\s*:|\Z)"
    match = re.search(pattern, text or "", re.S)
    return " ".join(match.group(1).split())[:2_400] if match else ""


def _memory_text(text: str) -> str:
    """Sanitize an episodic memory without erasing its useful task details."""
    value, _ = sanitize_retry_text(str(text or ""))
    return re.sub(r"\s+", " ", value).strip()[:2_400]


def reflection_memory_fields(trace: ExplorationTrace) -> dict[str, str]:
    """Return rich retrieval fields, separate from policy parameterization.

    Policy candidates deliberately replace literals so they can cluster across
    tasks.  Retrieval memory has the opposite job: preserve the concrete
    symptom, cause, evidence, and correction from one training episode.  We
    still apply the retry sanitizer so credentials, absolute paths, and
    answer-bearing verifier comparisons never enter the store.
    """
    observable = _memory_text(_field(trace.reflection, "FAILURE OBSERVABLE"))
    root_cause = _memory_text(_field(trace.reflection, "ROOT CAUSE"))
    corrective = _memory_text(_field(trace.reflection, "CORRECTIVE ACTION"))
    evidence = _memory_text(_field(trace.reflection, "CAUSAL EVIDENCE"))
    missing = _memory_text(_field(trace.reflection, "MISSING"))
    confidence = _memory_text(_field(trace.reflection, "DIAGNOSIS CONFIDENCE"))
    return {
        "observation": observable or "A prior training attempt failed verification.",
        "lesson": corrective or "Validate the causal step and repair it before retrying.",
        "rationale": root_cause or evidence or "The reflection did not establish a root cause.",
        "causal_evidence": evidence,
        "missing": missing,
        "diagnosis_confidence": confidence,
    }


def _parameterize(text: str) -> str:
    value, _ = sanitize_retry_text(str(text or ""))
    value = re.sub(r"[/\\][\w./\\-]+", "<path>", value)
    value = re.sub(r"(?i)(?<![\w$])\$?[a-z]{1,3}\$?\d+(?!\w)", "<cell>", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\b", "<num>", value)
    return re.sub(r"\s+", " ", value).strip()[:600]


def _failed_attempts(trace: ExplorationTrace) -> list[FailedAttempt]:
    failures = [call for call in trace.tool_calls if call.success is False][-3:]
    if failures:
        return [
            FailedAttempt(
                step_index=call.step_index,
                tool_name=call.tool_name,
                command=_parameterize(call.command or call.description),
                error_message=_parameterize(call.error_message),
                error_type="reflection_diagnosis",
            )
            for call in failures
        ]
    return [
        FailedAttempt(
            step_index=0,
            tool_name="verifier",
            command="final artifact verification",
            error_message="reflection reported a verifier failure",
            error_type="validation",
        )
    ]


def _candidate(trace: ExplorationTrace, number: int) -> BottleneckCandidate:
    observable = _parameterize(_field(trace.reflection, "FAILURE OBSERVABLE"))
    root_cause = _parameterize(_field(trace.reflection, "ROOT CAUSE"))
    corrective = _parameterize(_field(trace.reflection, "CORRECTIVE ACTION"))
    evidence = _parameterize(_field(trace.reflection, "CAUSAL EVIDENCE"))
    failures = _failed_attempts(trace)
    return BottleneckCandidate(
        candidate_id=f"{trace.task_name}:{trace.attempt_number}:reflection-{number}",
        task_name=trace.task_name,
        task_family=trace.task_family,
        step_range=(failures[0].step_index, failures[-1].step_index),
        failed_attempts=failures,
        winning_command="",
        winning_tool="",
        exploration_cost=max(1, len(failures)),
        intent=observable or "recover from a verifier-reported task failure",
        obstacle=root_cause or evidence or "reflection did not establish a root cause",
        resolution=corrective or "Validate the stated causal step and repair it before retrying.",
        evidence_label="verified_success" if trace.reflection_verified_by_retry else "unresolved_failure",
        evidence_source="reflection",
        retry_outcome=trace.reflection_retry_outcome,
        retry_transition=dict(trace.retry_transition),
        candidate_kind="recovery_candidate",
    )


def extract_reflective_memory_candidates(
    traces: Iterable[ExplorationTrace],
) -> list[BottleneckCandidate]:
    """Return one reusable candidate for each persisted reflection memory."""
    candidates: list[BottleneckCandidate] = []
    for trace in traces:
        if trace.reflection.strip():
            candidates.append(_candidate(trace, len(candidates) + 1))
    return candidates
