"""Create bounded contract and implementation proposals from failure evidence.

The designer is deliberately separate from the compiler.  It proposes a small,
parameterized script and an operational contract; it cannot directly mark the
proposal as trusted.  Promotion is handled later from a successful runtime trace.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

from evolution.exploration.skill_patcher import SkillSection
from evolution.types import CapabilityCluster, ExplorationTrace
from llm_config import TEMPERATURE_DETERMINISTIC, call_llm

_SYSTEM = """You design one reusable SkillPolicy contract and one optional executable implementation.
Return JSON only with: existing_policy_id (an ID from existing_contracts, or null),
name, purpose, trigger, procedure (1-4 strings), invariants (1-4 strings), recovery
(1-3 strings), and optional script. Reuse an existing_policy_id only when its goal,
preconditions, postconditions, and constraints fully explain the evidence without
task-specific assumptions; then the proposed procedure/script is a new implementation.
Otherwise set existing_policy_id to null and propose a new contract. A SkillPolicy is
the primary result: it specifies when to act, ordered decisions, quality constraints,
and what to do when evidence is insufficient. For verified successful substeps,
turn the observed operation shape into parameterized procedure steps; do not require
a failure before learning. script is null unless deterministic,
repeated work would genuinely benefit from automation. When present, script is an
object with filename and source. Use Python only. The module must export a CAPABILITY
dictionary containing name, purpose, and usage. A script must use argparse, accept
all paths/values as command line arguments, write only to an explicit --output path,
and contain no task names, absolute paths, source values, expected answers,
networking, subprocesses, shell execution, package installation, or destructive
filesystem operations. The observed action and signature fields are internal
trajectory labels, not runtime tools; never expose names such as write_json,
read_file, or search_text as callable operations. Generic file/JSON serialization
should remain an implementation detail unless the evidence defines a
domain-specific adapter with a stable input/output contract. Do not propose advice
such as checking a path or changing an interpreter; those are diagnostics, not
reusable SkillPolicies."""

# Resolution text is deliberately excluded from semantic cluster membership.
# The designer receives it after clustering, paired with its verifier outcome,
# so different methods for the same problem can be compared rather than split.
_SYSTEM += """

The cluster groups a shared intent and obstacle, not a shared solution. Use
resolution_evidence outcome labels when consolidating methods:
- verified_success: eligible positive evidence for procedure steps;
- unresolved_failure, tool_recovery, or retry_outcome=failure: a failed or
  unverified approach, useful for constraints, recovery, and validation
  requirements, but never as a proven procedure;
- retry_outcome=missing: insufficient evidence.
When successful approaches differ, extract their common invariant or express a
safe conditional choice. Do not average successful and failed methods into an
ambiguous procedure. Use retry_transition to compare the operations before and
after each reflection. Added or changed operations followed by verifier success
are positive hypotheses; the same changes followed by failure are negative or
unresolved evidence, not causal proof."""

_PATCH_SYSTEM = """You are editing a reusable Markdown skill after a bottleneck was
observed. Return JSON only with target_section_id, replacement, and reason.

You may replace exactly one supplied section. The replacement must begin with the
same Markdown heading, retain the section's scope, and make a concrete reusable
improvement supported by the supplied evidence. Every part of the skill is editable,
including the initial content; do not assume any section is immutable.

Do not append generic workflow advice, repeat existing validation instructions,
include task-specific paths/values, or create a new policy card. If none of the
supplied sections should change, return {"target_section_id": null, "replacement":
"", "reason": "no relevant section"}."""

_WORKFLOW_SYSTEM = """You improve a reusable family SKILL.md from a batch of agent
execution steps. Return JSON only with keys: changed (boolean), skill_markdown,
reason. Compare the current skill with the supplied agent steps (successful and
failed) and abstract only workflow decisions that generalize across the batch.
Use failures only to identify missing checks or recovery gates; do not copy a
failed task-specific repair. Keep task
paths, filenames, values, answers, credentials, and verifier internals as runtime
variables. Preserve YAML frontmatter and the skill's family scope. The result must
remain an operational Markdown skill, not an explanation of the batch.

Prefer a short ordered workflow with inspection, transformation, validation, and
recovery decisions. Remove paragraphs, bullets, and procedures that are not
supported by the supplied traces, are task-specific, or duplicate another part
of the current skill. A shorter skill is preferred when it preserves coverage.
Do not copy raw commands unless they are parameterized tool choices. Do not add
policy cards, scripts, citations, or generic agent advice; those are handled by
the next compilation stage. Keep the result below 1,800 words. If the evidence
does not justify a reusable change, return changed=false and skill_markdown equal
to the current skill. Never invent steps that are absent from the evidence."""


@dataclass(frozen=True)
class PolicyProposal:
    existing_policy_id: str | None
    name: str
    purpose: str
    trigger: str
    procedure: tuple[str, ...]
    invariants: tuple[str, ...]
    script_name: str | None = None
    script_source: str | None = None
    recovery: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillPatchProposal:
    target_section_id: str
    replacement: str
    reason: str


def _safe_step_text(value: object, limit: int = 900) -> str:
    """Bound trajectory evidence while removing instance-specific literals."""
    text = str(value or "")
    text = re.sub(r"(?:[A-Za-z]:)?(?:/|\\)(?:[^\s/\\]+(?:/|\\))+[^\s]*", "<path>", text)
    text = re.sub(r"\b\d{4,}(?:\.\d+)?\b", "<value>", text)
    text = re.sub(r"\b[A-Fa-f0-9]{24,}\b", "<token>", text)
    return " ".join(text.split())[:limit]


def _workflow_evidence(traces: list[ExplorationTrace]) -> list[dict[str, Any]]:
    """Render batch steps as compact, model-readable evidence."""
    evidence: list[dict[str, Any]] = []
    for trace in traces:
        steps: list[dict[str, str]] = []
        for index, raw in enumerate(trace.raw_steps[:80], start=1):
            if not isinstance(raw, dict):
                continue
            extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
            args = extra.get("raw_arguments") if isinstance(extra, dict) else {}
            message = raw.get("message") or raw.get("content") or raw.get("text") or ""
            item = {
                "step": str(index),
                "source": _safe_step_text(raw.get("source", ""), 40),
                "tool": _safe_step_text(extra.get("tool_use_name", "") if isinstance(extra, dict) else "", 80),
                "action": _safe_step_text(message, 700),
            }
            if args:
                item["arguments"] = _safe_step_text(json.dumps(args, ensure_ascii=False), 500)
            if any(item.values()):
                steps.append(item)
        if steps:
            evidence.append(
                {
                    "task": _safe_step_text(trace.task_name, 120),
                    "verifier_passed": trace.verifier_passed,
                    "steps": steps,
                }
            )
    return evidence[:8]


def design_workflow_update(
    current_skill: str,
    traces: list[ExplorationTrace],
    task_family: str,
) -> tuple[str, str] | None:
    """Perform a bidirectional skill review before policy clustering.

    The review checks both coverage (reusable decisions present in the traces but
    absent from the skill) and precision (skill content unsupported by the traces
    or duplicated elsewhere).
    """
    evidence = _workflow_evidence(traces)
    if not evidence:
        return None
    payload = {"task_family": task_family, "current_skill": current_skill[:20_000], "batch_agent_steps": evidence}
    try:
        data = _parse_json(
            call_llm(
                messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                system=_WORKFLOW_SYSTEM,
                temperature=TEMPERATURE_DETERMINISTIC,
                profile="evolution",
            )
        )
    except Exception:
        return None
    if not bool(data.get("changed")):
        return None
    replacement = str(data.get("skill_markdown") or "").strip()
    reason = _text(data.get("reason"), 700)
    if not replacement or reason is None or len(replacement) > 24_000:
        return None
    if not re.match(r"(?s)^---\s*\n.*?\n---\s*\n", replacement) or "#" not in replacement:
        return None
    if re.search(r"(?:^|\s)/(?:[^\s/]+/)+[^\s]*", replacement) or re.search(r"\b\d{4,}\b", replacement):
        return None
    # Keep model rewrites from turning a compact family contract into a log of
    # every observed operation.  The model may still return a shorter rewrite.
    if len(replacement.split()) > 1_800:
        return None
    return replacement + "\n", reason


def _text(value: object, limit: int = 300) -> str | None:
    text = " ".join(str(value or "").split())
    if not text or len(text) > limit:
        return None
    if re.search(r"(?:^|\s)/(?:[^\s/]+/)+", text) or re.search(r"\b\d{4,}\b", text):
        return None
    return text


def _parse_json(response: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", response, re.S)
    if not match:
        return {}
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _safe_script(filename: object, source: object) -> tuple[str, str] | None:
    name = str(filename or "")
    code = str(source or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,60}\.py", name):
        return None
    if (
        not code
        or len(code) > 16_000
        or "argparse" not in code
        or "__main__" not in code
        or "CAPABILITY" not in code
        or "--output" not in code
        or "args.output" not in code
    ):
        return None
    try:
        tree = ast.parse(code, filename=name)
    except SyntaxError:
        return None
    forbidden_imports = {"subprocess", "socket", "requests", "httpx", "urllib", "shutil", "os"}
    forbidden_calls = {"eval", "exec", "compile", "__import__", "system", "popen", "rmtree", "unlink"}
    capability_declared = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name.split(".", 1)[0] for alias in node.names]
            if any(module in forbidden_imports for module in modules):
                return None
        if isinstance(node, ast.Call):
            name_part = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            if name_part in forbidden_calls:
                return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/"):
            return None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "CAPABILITY" for target in node.targets)
            and isinstance(node.value, ast.Dict)
        ):
            capability_declared = True
            continue
        if isinstance(node, ast.If):
            is_main_guard = isinstance(node.test, ast.Compare) and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"
            if is_main_guard:
                continue
        return None
    if not capability_declared:
        return None
    return name, code.rstrip() + "\n"


def validate_experimental_source(filename: str, source: str) -> None:
    """Validate without executing generated code before it becomes a package file."""
    if _safe_script(filename, source) is None:
        raise ValueError(f"Invalid experimental helper source: {filename}")


def _task_context(cluster: CapabilityCluster, traces: list[ExplorationTrace]) -> list[str]:
    """Provide contract shape, rather than raw transcripts, to the designer."""
    task_names = {candidate.task_name for candidate in cluster.candidates}
    contexts: list[str] = []
    for trace in traces:
        if trace.task_name not in task_names:
            continue
        text = " ".join(
            str(step.get("message", "")) for step in trace.raw_steps if step.get("source") in {"user", "system"} and step.get("message")
        )
        text = re.sub(r"/(?:[^\s/]+/)+[^\s]+", "<path>", text)
        text = re.sub(r"\b\d{4,}(?:\.\d+)?\b", "<value>", text)
        text = " ".join(text.split())
        if text:
            contexts.append(text[:2_000])
    return contexts[:3]


def _resolution_evidence(cluster: CapabilityCluster) -> list[dict[str, Any]]:
    """Keep alternative resolutions paired with immutable outcome provenance."""
    evidence: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for candidate in cluster.candidates:
        resolution = _safe_step_text(candidate.resolution, 900)
        if not resolution:
            continue
        key = (
            candidate.evidence_source,
            candidate.evidence_label,
            candidate.retry_outcome or "",
            resolution,
            json.dumps(candidate.retry_transition, ensure_ascii=False, sort_keys=True),
        )
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            {
                "source": candidate.evidence_source,
                "outcome": candidate.evidence_label,
                "retry_outcome": candidate.retry_outcome,
                "resolution": resolution,
                "retry_transition": candidate.retry_transition,
            }
        )
    return evidence[:12]


def _fallback_proposal(cluster: CapabilityCluster) -> PolicyProposal:
    """Return a safe generic policy when proposal synthesis is unavailable.

    Failure evolution should not disappear merely because the optional evolution
    LLM is unavailable.  This fallback is deliberately conservative: it adds a
    verifier pre-flight, never task values or a guessed repair.
    """
    return PolicyProposal(
        existing_policy_id=None,
        name="contract-preflight-validation",
        purpose="Validate a generated artifact against its explicit output contract before submission.",
        trigger="when a task has a verifier or an explicit artifact structure and value-type contract",
        procedure=(
            "Extract required output paths, containers, fields, row counts, value types, and formula rules from the task contract.",
            "Inspect the generated artifact after saving and check every required contract item, including output existence.",
            "Run the supplied verifier or focused contract checks and repair each reported failure before completion.",
        ),
        invariants=(
            "Preserve exact required names, ordering, locations, and value types.",
            "Do not treat a plausible formula or display format as proof that a required cached value has the correct type.",
        ),
        recovery=("Stop promotion when a required check is unresolved; record the failing contract item and retry after repair.",),
    )


def design_policy_proposal(
    cluster: CapabilityCluster,
    traces: list[ExplorationTrace] | None = None,
    existing_contracts: list[dict[str, str]] | None = None,
) -> PolicyProposal | None:
    """Ask for one safe candidate; use a conservative fallback for invalid output."""
    evidence = {
        "intent": cluster.intent,
        "obstacle": cluster.obstacle,
        "resolution_evidence": _resolution_evidence(cluster),
        "successful_operations": [
            {
                "kind": candidate.substep.kind,
                "action": candidate.substep.action,
                "tool": candidate.substep.tool_name,
                "signature": candidate.substep.signature,
                "command_shape": candidate.substep.command_shape,
            }
            for candidate in cluster.candidates
            if candidate.substep is not None
        ][:8],
        "failed_operations": [
            {
                "tool": attempt.tool_name,
                "error_type": attempt.error_type,
                "command_shape": re.sub(r"[/\\][^\s]+", "<path>", attempt.command)[:240],
            }
            for candidate in cluster.candidates[:3]
            for attempt in candidate.failed_attempts[:3]
        ],
        "task_contracts": _task_context(cluster, traces or []),
        "existing_contracts": existing_contracts or [],
    }
    try:
        data = _parse_json(
            call_llm(
                messages=[{"role": "user", "content": json.dumps(evidence, ensure_ascii=False)}],
                system=_SYSTEM,
                temperature=TEMPERATURE_DETERMINISTIC,
                profile="evolution",
            )
        )
    except Exception:
        return _fallback_proposal(cluster)
    name = _text(data.get("name"), 80)
    purpose = _text(data.get("purpose"))
    trigger = _text(data.get("trigger"))
    procedure = tuple(item for value in data.get("procedure", [])[:4] if (item := _text(value)))
    invariants = tuple(item for value in data.get("invariants", [])[:4] if (item := _text(value)))
    recovery = tuple(item for value in data.get("recovery", [])[:3] if (item := _text(value)))
    if not all((name, purpose, trigger, procedure, invariants, recovery)):
        return _fallback_proposal(cluster)
    script = data.get("script")
    checked = _safe_script(script.get("filename"), script.get("source")) if isinstance(script, dict) else None
    if isinstance(script, dict) and checked is None:
        return _fallback_proposal(cluster)
    existing_policy_id = _text(data.get("existing_policy_id"), 100)
    known_ids = {str(item.get("policy_id", "")) for item in existing_contracts or []}
    if existing_policy_id not in known_ids:
        existing_policy_id = None
    if checked is None:
        return PolicyProposal(existing_policy_id, name, purpose, trigger, procedure, invariants, recovery=recovery)
    return PolicyProposal(existing_policy_id, name, purpose, trigger, procedure, invariants, *checked, recovery)


def design_skill_patch(
    cluster: CapabilityCluster,
    sections: list[SkillSection],
    proposal: PolicyProposal,
) -> SkillPatchProposal | None:
    """Propose one evidence-grounded replacement for a retrieved skill section."""
    if not sections:
        return None
    allowed_ids = {section.section_id for section in sections}
    evidence = {
        "bottleneck": {
            "intent": cluster.intent,
            "obstacle": cluster.obstacle,
            "resolution_evidence": _resolution_evidence(cluster),
            "supporting_tasks": sorted({candidate.task_name for candidate in cluster.candidates})[:5],
        },
        "policy_proposal": {
            "purpose": proposal.purpose,
            "trigger": proposal.trigger,
            "procedure": proposal.procedure,
            "invariants": proposal.invariants,
            "recovery": proposal.recovery,
        },
        "editable_sections": [
            {
                "section_id": section.section_id,
                "heading": "#" * section.level + " " + section.heading,
                "content": section.content[:5_000],
            }
            for section in sections
        ],
    }
    try:
        data = _parse_json(
            call_llm(
                messages=[{"role": "user", "content": json.dumps(evidence, ensure_ascii=False)}],
                system=_PATCH_SYSTEM,
                temperature=TEMPERATURE_DETERMINISTIC,
                profile="evolution",
            )
        )
    except Exception:
        return None
    target_section_id = str(data.get("target_section_id") or "")
    replacement = str(data.get("replacement") or "").strip()
    reason = _text(data.get("reason"), 500)
    if target_section_id not in allowed_ids or not replacement or reason is None:
        return None
    return SkillPatchProposal(target_section_id, replacement, reason)
