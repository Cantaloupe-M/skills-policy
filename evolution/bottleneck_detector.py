"""Extract hypotheses from agent exploration without confusing recovery with learning.

A command succeeding after another command fails is useful diagnostic evidence, but
it is not proof that a future task should be instructed to use that command.  A
verifier-passing trace can seed an experimental policy directly. Repeated
unresolved failures can also seed an experimental recovery policy, which must
earn active status through later verifier-passing reuse.
"""

from __future__ import annotations

import json
import re
from typing import Any

from evolution.exploration.trace_parser import extract_reusable_substeps
from evolution.reflection_memory import extract_reflective_memory_candidates
from evolution.types import BottleneckCandidate, ExplorationTrace, FailedAttempt, ReusableSubstep, ToolCallStep
from llm_config import TEMPERATURE_DETERMINISTIC, call_llm

INCIDENTAL_ERRORS = {"syntax", "transient", "runtime", "unknown"}


def _classify_error(text: str) -> str:
    lowered = (text or "").lower()
    if "syntax" in lowered or "indentation" in lowered:
        return "syntax"
    if "timeout" in lowered or "connection" in lowered or re.search(r"\b50[234]\b", lowered):
        return "transient"
    if "no such file" in lowered or "filenotfound" in lowered:
        return "missing_file"
    if "modulenotfound" in lowered or "importerror" in lowered or "command not found" in lowered:
        return "not_found"
    if any(
        word in lowered
        for word in (
            "schema", "layout", "merged", "encoding", "file format",
            "binary file", "cannot read binary", "text-only", "unsupported format",
        )
    ):
        return "data_obstacle"
    if "assert" in lowered or "failed" in lowered:
        return "validation"
    if "permission" in lowered:
        return "permission"
    return "runtime" if lowered else "unknown"


def _command(call: ToolCallStep) -> str:
    return (call.command or call.description or "").strip()


def _normalize_attempt(call: ToolCallStep) -> tuple[str, str, str]:
    command = _command(call).lower()
    command = re.sub(r"[/\\][\w./\\-]+", "<path>", command)
    command = re.sub(r"\b\d+(?:\.\d+)?\b", "<num>", command)
    command = re.sub(r"\s+", " ", command)[:240]
    return call.tool_name.lower(), command, _classify_error(call.error_message)


def _is_meaningful_success(call: ToolCallStep) -> bool:
    if call.success is not True:
        return False
    command = _command(call).lower()
    if not command:
        return False
    trivial = {"ls", "pwd", "cd", "echo", "cat", "head", "tail", "mkdir"}
    return command.split(maxsplit=1)[0] not in trivial


def _is_reusable(failures: list[FailedAttempt], winner: ToolCallStep | None) -> bool:
    error_types = {attempt.error_type for attempt in failures}
    if not error_types or error_types.issubset(INCIDENTAL_ERRORS):
        return False
    if winner is None:
        return True
    failed_commands = {re.sub(r"\s+", " ", attempt.command.lower()).strip() for attempt in failures}
    return _command(winner).lower() not in failed_commands


def _candidate(
    trace: ExplorationTrace,
    failures: list[ToolCallStep],
    winner: ToolCallStep | None,
    number: int,
    min_exploration_cost: int,
) -> BottleneckCandidate | None:
    distinct_failures = list(dict.fromkeys(_normalize_attempt(item) for item in failures))
    exploration_cost = len(distinct_failures) + (1 if winner else 0)
    required_cost = min_exploration_cost if winner else max(1, min_exploration_cost - 1)
    if exploration_cost < required_cost:
        return None

    normalized_failures = [
        FailedAttempt(
            step_index=item.step_index,
            tool_name=item.tool_name,
            command=_command(item),
            error_message=item.error_message,
            error_type=_classify_error(item.error_message),
        )
        for item in failures
    ]
    if not _is_reusable(normalized_failures, winner):
        return None

    calls = [*failures, *([winner] if winner else [])]
    artifacts = list(dict.fromkeys(path for call in calls for path in call.input_files + call.output_files))
    # Do not turn environment recovery (for example ``python`` -> ``python3``)
    # into a runtime skill just because the replacement command returned zero.
    # A failed trial has no evidence that its local recovery helped the artifact.
    label = "verified_success" if trace.verifier_passed else (
        "tool_recovery" if winner else "unresolved_failure"
    )
    winning_command = _command(winner) if winner else ""
    winning_tool = winner.tool_name if winner else ""
    return BottleneckCandidate(
        candidate_id=f"{trace.task_name}:{trace.attempt_number}:candidate-{number}",
        task_name=trace.task_name,
        task_family=trace.task_family,
        step_range=(failures[0].step_index, winner.step_index if winner else failures[-1].step_index),
        failed_attempts=normalized_failures,
        winning_command=winning_command,
        winning_tool=winning_tool,
        exploration_cost=exploration_cost,
        artifact_paths=artifacts,
        intent=f"resolve processing obstacle with {winning_tool or 'an alternative approach'}",
        obstacle="; ".join(sorted({item.error_type for item in normalized_failures})),
        resolution=(
            f"Use the verified {winning_tool} approach and validate its output."
            if winner
            else "Investigate the obstacle before committing to an implementation."
        ),
        evidence_label=label,
        candidate_kind="recovery_candidate",
    )


def find_candidates(
    trace: ExplorationTrace,
    *,
    min_exploration_cost: int = 2,
) -> list[BottleneckCandidate]:
    """Extract resolved and unresolved failure spans from one task attempt."""
    candidates: list[BottleneckCandidate] = []
    pending: list[ToolCallStep] = []

    for call in trace.tool_calls:
        if call.success is False:
            pending.append(call)
            continue
        if not pending or not _is_meaningful_success(call):
            continue
        candidate = _candidate(trace, pending, call, len(candidates) + 1, min_exploration_cost)
        if candidate:
            candidates.append(candidate)
        pending.clear()

    if pending:
        candidate = _candidate(trace, pending, None, len(candidates) + 1, min_exploration_cost)
        if candidate:
            candidates.append(candidate)
    return candidates


_ABSTRACTION_SYSTEM = """You extract reusable procedural knowledge from agent failure patterns.

For each candidate return:
- intent: the task-independent operation being attempted;
- obstacle: the root cause, not an error symptom;
- resolution: imperative guidance for a future task. For unresolved evidence, state the diagnostic next step without claiming it is proven.

The supplied evidence_label and evidence_source are immutable provenance. A
verified_success resolution was followed by verifier success and may be phrased
as positive procedural evidence. An unresolved_failure or failed retry is not a
proven solution: preserve it as a failed approach, constraint, or diagnostic
next step. When current intent, obstacle, and resolution are supplied from a
structured reflection, abstract them without discarding their meaning.

Write task-independent, parameterized guidance. Never copy task names, paths,
file names, record identifiers, literal source values, commands, code, or
verbatim error text.
Return JSON only: {"candidates": [{"index": 0, "intent": "...", "obstacle": "...", "resolution": "..."}]}.
"""


_MAX_TARGETED_REFINEMENT_RETRIES = 3


def _is_template_intent(candidate: BottleneckCandidate) -> bool:
    return (
        candidate.evidence_source == "trajectory"
        and "resolve processing obstacle with" in candidate.intent.lower()
    )


def _parse_refinement_response(response: str) -> list[dict[str, Any]]:
    """Parse one refinement response and return its candidate records."""
    match = re.search(r"\{.*\}", response, re.S)
    if not match:
        raise ValueError(
            f"LLM response does not contain valid JSON. Response preview: {response[:500]}"
        )
    data = json.loads(match.group(0))
    refined = data.get("candidates")
    if not isinstance(refined, list):
        raise ValueError(
            f"LLM response missing 'candidates' list. Response data: "
            f"{json.dumps(data, ensure_ascii=False)[:500]}"
        )
    return [item for item in refined if isinstance(item, dict)]


def _apply_refinement_item(
    candidate: BottleneckCandidate,
    item: dict[str, Any],
    *,
    expected_index: int,
) -> bool:
    """Apply one model item only when it targets the requested candidate."""
    index = item.get("index")
    if index != expected_index:
        return False
    old_values = (candidate.intent, candidate.obstacle, candidate.resolution)
    candidate.intent = str(item.get("intent") or candidate.intent)
    candidate.obstacle = str(item.get("obstacle") or candidate.obstacle)
    candidate.resolution = str(item.get("resolution") or candidate.resolution)
    return old_values != (candidate.intent, candidate.obstacle, candidate.resolution)


def refine_candidates_with_llm(
    candidates: list[BottleneckCandidate],
    *,
    refinement_diagnostics: list[dict[str, Any]] | None = None,
    max_targeted_retries: int = _MAX_TARGETED_REFINEMENT_RETRIES,
) -> list[BottleneckCandidate]:
    if not candidates:
        return []

    # Identify trajectory-based candidates that need refinement
    trajectory_candidates = [c for c in candidates if c.evidence_source == "trajectory"]
    if not trajectory_candidates:
        # All candidates are from reflection or other high-quality sources
        return candidates

    payload = [
        {
            "index": index,
            "current_intent": candidate.intent,
            "current_obstacle": candidate.obstacle,
            "current_resolution": candidate.resolution,
            "failed_attempts": [
                {"command": attempt.command, "error": attempt.error_message}
                for attempt in candidate.failed_attempts
            ],
            "winning_command": candidate.winning_command,
            "evidence_label": candidate.evidence_label,
            "evidence_source": candidate.evidence_source,
            "retry_outcome": candidate.retry_outcome,
            "retry_transition": candidate.retry_transition,
        }
        for index, candidate in enumerate(candidates)
    ]
    batch_refinement_error: str | None = None
    try:
        response = call_llm(
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            system=_ABSTRACTION_SYSTEM,
            temperature=TEMPERATURE_DETERMINISTIC,
            profile="evolution",
        )
        data = {"candidates": _parse_refinement_response(response)}
    except Exception as exc:
        batch_refinement_error = f"{type(exc).__name__}: {exc}"
        data = {"candidates": []}
        print(
            f"[evolution] WARNING: Batch refinement failed for "
            f"{len(trajectory_candidates)} trajectory candidate(s): "
            f"{batch_refinement_error}. Retrying template candidates individually."
        )

    refined_count = 0
    for item in data["candidates"]:
        index = item.get("index")
        if not isinstance(index, int) or not 0 <= index < len(candidates):
            continue
        candidate = candidates[index]
        old_intent = candidate.intent
        candidate.intent = str(item.get("intent") or candidate.intent)
        candidate.obstacle = str(item.get("obstacle") or candidate.obstacle)
        candidate.resolution = str(item.get("resolution") or candidate.resolution)
        if old_intent != candidate.intent:
            refined_count += 1

    # A malformed or incomplete batch response should not discard all useful
    # refinements. Retry only the candidates that still contain the generated
    # placeholder, then exclude unrecoverable candidates from evolution.
    still_template = [candidate for candidate in candidates if _is_template_intent(candidate)]
    dropped_ids: set[str] = set()
    for candidate in still_template:
        original_template_intent = candidate.intent
        retry_errors = (
            [f"batch refinement: {batch_refinement_error}"]
            if batch_refinement_error
            else []
        )
        for retry_number in range(1, max(0, max_targeted_retries) + 1):
            retry_payload = [{
                "index": 0,
                "current_intent": candidate.intent,
                "current_obstacle": candidate.obstacle,
                "current_resolution": candidate.resolution,
                "failed_attempts": [
                    {"command": attempt.command, "error": attempt.error_message}
                    for attempt in candidate.failed_attempts
                ],
                "winning_command": candidate.winning_command,
                "evidence_label": candidate.evidence_label,
                "evidence_source": candidate.evidence_source,
                "retry_outcome": candidate.retry_outcome,
                "retry_transition": candidate.retry_transition,
            }]
            try:
                retry_response = call_llm(
                    messages=[{"role": "user", "content": json.dumps(retry_payload, ensure_ascii=False)}],
                    system=(
                        _ABSTRACTION_SYSTEM
                        + "\nRefine this single candidate now. Return exactly one candidate with index 0. "
                        "Do not repeat the template intent."
                    ),
                    temperature=TEMPERATURE_DETERMINISTIC,
                    profile="evolution",
                )
                retry_items = _parse_refinement_response(retry_response)
                changed = any(
                    _apply_refinement_item(candidate, item, expected_index=0)
                    for item in retry_items
                )
                if not _is_template_intent(candidate):
                    refined_count += 1
                    break
                if not changed:
                    retry_errors.append(f"retry {retry_number}: response did not change the candidate")
                else:
                    retry_errors.append(f"retry {retry_number}: template intent remained")
            except Exception as exc:
                retry_errors.append(f"retry {retry_number}: {type(exc).__name__}: {exc}")
        if _is_template_intent(candidate):
            dropped_ids.add(candidate.candidate_id)
            if refinement_diagnostics is not None:
                refinement_diagnostics.append({
                    "candidate_id": candidate.candidate_id,
                    "task_name": candidate.task_name,
                    "original_intent": original_template_intent,
                    "final_intent": candidate.intent,
                    "reason": "template intent remained after targeted refinement retries",
                    "max_targeted_retries": max(0, max_targeted_retries),
                    "retry_errors": retry_errors,
                    "evidence_source": candidate.evidence_source,
                    "evidence_label": candidate.evidence_label,
                })

    if dropped_ids:
        candidates = [candidate for candidate in candidates if candidate.candidate_id not in dropped_ids]
        print(
            f"[evolution] Dropped {len(dropped_ids)} candidate(s) after "
            "targeted refinement retries; recorded as diagnostics"
        )

    print(f"[evolution] Successfully refined {refined_count}/{len(trajectory_candidates)} trajectory-based candidates")
    return candidates


def _outcome_failure_candidate(
    trace: ExplorationTrace, number: int
) -> BottleneckCandidate | None:
    """Retain a final verifier rejection as a hypothesis even after tool recovery.

    Local command failures frequently recover before the final artifact is graded.
    The rejected artifact remains the important observation: it can motivate a
    diagnostic helper, but it cannot justify a trusted skill by itself.
    """
    if trace.verifier_passed:
        return None
    failures = [call for call in trace.tool_calls if call.success is False][-3:]
    if failures:
        failed_attempts = [
            FailedAttempt(
                step_index=call.step_index,
                tool_name=call.tool_name,
                command=_command(call),
                error_message=call.error_message,
                error_type=_classify_error(call.error_message),
            )
            for call in failures
        ]
    else:
        failed_attempts = [
            FailedAttempt(
                step_index=0,
                tool_name="verifier",
                command="final artifact verification",
                error_message="final verifier rejected the artifact",
                error_type="validation",
            )
        ]
    artifacts = [
        artifact.path for artifact in trace.file_artifacts if artifact.role in {"output", "intermediate"}
    ]
    return BottleneckCandidate(
        candidate_id=f"{trace.task_name}:{trace.attempt_number}:candidate-{number}",
        task_name=trace.task_name,
        task_family=trace.task_family,
        step_range=(failed_attempts[0].step_index, failed_attempts[-1].step_index),
        failed_attempts=failed_attempts,
        winning_command="",
        winning_tool="",
        exploration_cost=len(failed_attempts),
        artifact_paths=list(dict.fromkeys(artifacts)),
        intent="diagnose a verifier-rejected artifact against the task contract",
        obstacle="unexplained verifier rejection",
        resolution="Create a parameterized diagnostic that reports contract violations before final submission.",
        evidence_label="unresolved_failure",
        candidate_kind="recovery_candidate",
    )


def discover_candidates(
    trace: ExplorationTrace,
    *,
    use_llm: bool = True,
    min_exploration_cost: int = 2,
    refinement_diagnostics: list[dict[str, Any]] | None = None,
) -> list[BottleneckCandidate]:
    candidates = find_candidates(trace, min_exploration_cost=min_exploration_cost)
    return (
        refine_candidates_with_llm(candidates, refinement_diagnostics=refinement_diagnostics)
        if use_llm
        else candidates
    )


def discover_candidates_cross_trial(
    traces: list[ExplorationTrace],
    *,
    use_llm: bool = True,
    min_exploration_cost: int = 2,
    refinement_diagnostics: list[dict[str, Any]] | None = None,
) -> list[BottleneckCandidate]:
    candidates = [
        candidate
        for trace in traces
        for candidate in find_candidates(trace, min_exploration_cost=min_exploration_cost)
    ]
    # Reflection sidecars are instance-grounded memories in the paper's
    # representation. Include them explicitly, and mark a memory as verified
    # only when the retry it directly guided passed the verifier.
    candidates.extend(extract_reflective_memory_candidates(traces))
    # Successful traces are also evidence.  Mine their parameterized atomic
    # steps and short workflows so evolution can learn the actual procedure,
    # not only the recovery path after an error.
    seen_substeps: set[tuple[str, str]] = set()
    for trace in traces:
        if not trace.verifier_passed:
            continue
        if not trace.reusable_substeps:
            extract_reusable_substeps(trace)
        for substep in trace.reusable_substeps:
            key = (trace.task_name, substep.signature)
            if key in seen_substeps:
                continue
            seen_substeps.add(key)
            candidates.append(_successful_substep_candidate(trace, substep, len(candidates) + 1))
    candidates.extend(
        candidate
        for trace in traces
        if (candidate := _outcome_failure_candidate(trace, len(candidates) + 1)) is not None
    )
    return (
        refine_candidates_with_llm(candidates, refinement_diagnostics=refinement_diagnostics)
        if use_llm
        else candidates
    )


def _successful_substep_candidate(
    trace: ExplorationTrace,
    substep: ReusableSubstep,
    number: int,
) -> BottleneckCandidate:
    """Represent one verifier-backed substep as a reusable discovery candidate."""
    kind = "workflow" if substep.kind == "workflow" else "atomic operation"
    return BottleneckCandidate(
        candidate_id=f"{trace.task_name}:{trace.attempt_number}:substep-{number}",
        task_name=trace.task_name,
        task_family=trace.task_family,
        step_range=(substep.step_indices[0], substep.step_indices[-1]),
        failed_attempts=[],
        winning_command=substep.command_shape,
        winning_tool=substep.tool_name,
        exploration_cost=max(1, len(substep.step_indices)),
        intent=f"reuse a cross-format {kind}: {substep.action}",
        obstacle=f"recurring {substep.action} step with normalized artifact boundaries",
        resolution=(
            f"Apply the parameterized {substep.action} step and preserve its normalized "
            "input/output field types before continuing."
        ),
        evidence_label="verified_success",
        substep=substep,
        candidate_kind="workflow" if substep.kind == "workflow" else "atomic_substep",
    )
