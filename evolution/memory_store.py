"""Persistent residual-memory storage and runtime MCP materialization.

Skills and memories deliberately have different lifecycles.  Recurring
cross-task patterns are compiled into skill-local policies, while unmatched
reflection records remain in this store for on-demand retrieval.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import warnings
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from evolution.memory_embedding_service import memory_embedding_model_name
from evolution.reflection_memory import (
    extract_reflective_memory_candidates,
    reflection_memory_fields,
)
from evolution.semantic_embeddings import EmbeddingConfigurationError, embed_texts
from evolution.skill_utils import find_skill_package_dirs, read_skill_name
from evolution.types import (
    BottleneckCandidate,
    ExplorationTrace,
    FailedAttempt,
    ReusableSubstep,
)

MEMORY_STORE_FILENAME = "memory_store.json"
RUNTIME_MEMORY_DIRNAME = ".memory"
MCP_SERVER_NAME = "experience_memory"
MCP_SEARCH_TOOL = f"mcp__{MCP_SERVER_NAME}__search_memories"
MCP_GET_TOOL = f"mcp__{MCP_SERVER_NAME}__get_memory"

MEMORY_RETRIEVAL_CONFIG: dict[str, float | int | str] = {
    "algorithm": "hybrid-semantic-bm25-v1",
    "semantic_weight": 0.75,
    "lexical_weight": 0.25,
    "min_semantic_similarity": 0.38,
    "min_hybrid_score": 0.34,
    "min_lexical_coverage": 0.5,
    "min_lexical_score": 0.2,
}


def _memory_embedding_text(record: dict[str, Any]) -> str:
    context = record.get("context") if isinstance(record.get("context"), dict) else {}
    values = (
        context.get("task_name"),
        context.get("task_family"),
        record.get("observation"),
        record.get("lesson"),
        record.get("rationale"),
        record.get("causal_evidence"),
        record.get("missing"),
        (record.get("cluster_input") or {}).get("intent"),
        (record.get("cluster_input") or {}).get("obstacle"),
    )
    return "\n".join(str(value or "").strip() for value in values if value)


def _attach_retrieval_embeddings(records: list[dict[str, Any]]) -> dict[str, Any]:
    config: dict[str, Any] = dict(MEMORY_RETRIEVAL_CONFIG)
    model_name = memory_embedding_model_name()
    config.update({"embedding_model": model_name, "semantic_available": False})
    if not records or os.environ.get("SKILLFLOW_MEMORY_EMBEDDING_DISABLED", "").strip() == "1":
        return config
    try:
        vectors = embed_texts(
            [_memory_embedding_text(record) for record in records],
            model_name=model_name,
        )
    except EmbeddingConfigurationError as exc:
        config["semantic_error"] = str(exc)
        warnings.warn(
            "Memory semantic retrieval is unavailable; runtime will use strict lexical fallback: "
            f"{exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return config
    for record, vector in zip(records, vectors):
        record["retrieval_embedding"] = vector.tolist()
    config["semantic_available"] = True
    config["embedding_dimensions"] = int(vectors.shape[1])
    return config


def _transition_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value[key]
        for key in ("from_attempt", "to_attempt", "retry_verifier_passed")
        if key in value
    }


def _canonical_memory_id(record: dict[str, Any]) -> str:
    context = record.get("context") if isinstance(record.get("context"), dict) else {}
    signature = json.dumps(
        {
            "task_family": context.get("task_family"),
            "task_name": context.get("task_name"),
            "attempt_number": context.get("attempt_number"),
            "candidate_kind": record.get("candidate_kind") or context.get("candidate_kind"),
            "intent": (record.get("cluster_input") or {}).get("intent"),
            "lesson": record.get("lesson"),
            "rationale": record.get("rationale"),
            "retry_outcome": record.get("retry_outcome"),
            "retry_transition": record.get("retry_transition"),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"memory-{hashlib.sha256(signature.encode('utf-8')).hexdigest()[:20]}"


def _policy_candidate_record(candidate: BottleneckCandidate) -> dict[str, Any]:
    """Serialize parameterized evidence for private cross-batch consolidation."""
    record: dict[str, Any] = {
        "candidate_id": candidate.candidate_id,
        "context": {
            "task_name": candidate.task_name,
            "task_family": candidate.task_family,
            "candidate_kind": candidate.candidate_kind,
            "evidence_source": candidate.evidence_source,
        },
        "observation": candidate.intent,
        "outcome": candidate.evidence_label,
        "verified_by_retry": candidate.evidence_label == "verified_success",
        "retry_outcome": candidate.retry_outcome,
        "retry_transition": _transition_summary(candidate.retry_transition),
        "lesson": candidate.resolution,
        "rationale": candidate.obstacle,
        "cluster_input": {
            "intent": candidate.intent,
            "obstacle": candidate.obstacle,
        },
        "candidate_kind": candidate.candidate_kind,
        "representation": "candidate",
    }
    if candidate.substep is not None:
        substep = candidate.substep
        record["substep"] = {
            "step_indices": list(substep.step_indices),
            "kind": substep.kind,
            "action": substep.action,
            "tool_name": substep.tool_name,
            "target": substep.target,
            "signature": substep.signature,
            "command_shape": substep.command_shape,
            "input_formats": list(substep.input_formats),
            "output_formats": list(substep.output_formats),
        }
    record["memory_id"] = _canonical_memory_id(record)
    return record


def build_reflection_memory_payload(traces: list[ExplorationTrace]) -> dict[str, Any]:
    """Build the paper's ``(context, observation, lesson, rationale)`` records."""
    memories = extract_reflective_memory_candidates(traces)
    records: list[dict[str, Any]] = []
    memory_ids: dict[tuple[str, int], str] = {}
    for candidate in memories:
        source = next(
            (
                trace
                for trace in traces
                if trace.task_name == candidate.task_name
                and trace.attempt_number == trace.reflection_source_attempt
                and candidate.candidate_id.startswith(f"{trace.task_name}:{trace.attempt_number}:")
            ),
            None,
        )
        attempt_number = source.attempt_number if source is not None else None
        fields = reflection_memory_fields(source) if source is not None else {
            "observation": candidate.intent,
            "lesson": candidate.resolution,
            "rationale": candidate.obstacle,
            "causal_evidence": "",
            "missing": "",
            "diagnosis_confidence": "",
        }
        record: dict[str, Any] = {
            "candidate_id": candidate.candidate_id,
            "context": {
                "task_name": candidate.task_name,
                "task_family": candidate.task_family,
                "attempt_number": attempt_number,
                "reflection_files": source.reflection_files if source else [],
            },
            "observation": fields["observation"],
            "outcome": candidate.evidence_label,
            "verified_by_retry": candidate.evidence_label == "verified_success",
            "retry_outcome": candidate.retry_outcome,
            "retry_transition": _transition_summary(candidate.retry_transition),
            "lesson": fields["lesson"],
            "rationale": fields["rationale"],
            "causal_evidence": fields["causal_evidence"],
            "missing": fields["missing"],
            "diagnosis_confidence": fields["diagnosis_confidence"],
            "representation": "memory",
            "memory_kind": "reflection_episode",
        }
        memory_id = _canonical_memory_id(record)
        record["memory_id"] = memory_id
        if attempt_number is not None:
            memory_ids[(candidate.task_name, attempt_number)] = memory_id
        records.append(record)

    task_retry_episodes: list[dict[str, Any]] = []
    for task_name in sorted({trace.task_name for trace in traces}):
        task_traces = sorted(
            (trace for trace in traces if trace.task_name == task_name),
            key=lambda trace: trace.attempt_number,
        )
        if not any(trace.reflection for trace in task_traces):
            continue
        task_retry_episodes.append(
            {
                "task_name": task_name,
                "task_family": task_traces[0].task_family,
                "final_success": any(trace.verifier_passed for trace in task_traces),
                "attempts": [
                    {
                        "attempt_number": trace.attempt_number,
                        "verifier_passed": trace.verifier_passed,
                        "reflection_memory_id": memory_ids.get((task_name, trace.attempt_number)),
                        "retry_outcome": trace.reflection_retry_outcome if trace.reflection else None,
                        "retry_transition": trace.retry_transition if trace.reflection else None,
                    }
                    for trace in task_traces
                ],
            }
        )
    return {
        "schema_version": 2,
        "representation": "reflective_memory",
        "fields": ["context", "observation", "lesson", "rationale"],
        "evidence_fields": ["outcome", "verified_by_retry", "retry_outcome", "retry_transition"],
        "memories": records,
        "policy_candidates": [_policy_candidate_record(candidate) for candidate in memories],
        "task_retry_episodes": task_retry_episodes,
    }


def build_candidate_memory_payload(
    candidates: Iterable[BottleneckCandidate],
    traces: list[ExplorationTrace],
) -> dict[str, Any]:
    """Build retrieval memories and private cross-batch policy candidates.

    Only reflection episodes are agent-retrievable memories. Parameterized
    atomic/workflow candidates are retained separately so recurrence can span
    batches without flooding retrieval with generic workflow templates.
    """
    payload = build_reflection_memory_payload(traces)
    policy_candidates = {
        str(record.get("candidate_id")): record
        for record in payload["policy_candidates"]
        if record.get("candidate_id")
    }
    for candidate in candidates:
        policy_candidates[candidate.candidate_id] = _policy_candidate_record(candidate)
    payload["task_family"] = traces[0].task_family if traces else ""
    payload["source"] = "matched_clustering_candidates"
    payload["policy_candidates"] = list(policy_candidates.values())
    return payload


def load_memory_store(path: Path) -> dict[str, Any]:
    """Load a store and migrate the former candidate-as-memory layout."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    raw_memories = [
        item for item in payload.get("memories", []) if isinstance(item, dict)
    ]
    raw_candidates = [
        item for item in payload.get("policy_candidates", []) if isinstance(item, dict)
    ]
    if not raw_candidates and int(payload.get("schema_version", 1) or 1) < 2:
        # Schema v1 called every clustering candidate a memory. Keep all of
        # them as private consolidation state, but expose only actual
        # reflection episodes through the retrieval server.
        raw_candidates = []
        reflection_memories: list[dict[str, Any]] = []
        for source in raw_memories:
            context = source.get("context") if isinstance(source.get("context"), dict) else {}
            item = dict(source)
            item["representation"] = (
                "skill_factored"
                if source.get("representation") == "memory_residual"
                else "candidate"
            )
            raw_candidates.append(item)
            is_reflection = bool(context.get("reflection_files")) or (
                context.get("evidence_source") == "reflection"
            ) or ":reflection-" in str(source.get("candidate_id") or "")
            if is_reflection:
                memory = dict(source)
                memory["memory_kind"] = "reflection_episode"
                reflection_memories.append(memory)
        raw_memories = reflection_memories
    return {
        "schema_version": 2,
        "task_family": str(payload.get("task_family") or ""),
        "representation_boundary": {
            "memory": "sanitized, instance-specific reflection episode retrieved on demand",
            "policy_candidate": "parameterized consolidation evidence; never exposed by memory retrieval",
            "skill": "cross-task procedural invariant compiled into a policy",
        },
        "memories": raw_memories,
        "policy_candidates": raw_candidates,
    }


def merge_memory_store(
    path: Path,
    batch_payload: dict[str, Any],
    *,
    compiled_candidate_ids: Iterable[str] = (),
) -> dict[str, Any]:
    """Merge a batch and mark procedures factored into the published skill."""
    store = load_memory_store(path)
    compiled = {str(item) for item in compiled_candidate_ids}

    memories_by_id = {
        str(item.get("memory_id")): dict(item)
        for item in store["memories"]
        if item.get("memory_id")
    }
    for record in batch_payload.get("memories", []):
        if not isinstance(record, dict):
            continue
        item = dict(record)
        memory_id = str(item.get("memory_id") or _canonical_memory_id(item))
        item["memory_id"] = memory_id
        previous = memories_by_id.get(memory_id, {})
        if previous.get("representation") == "memory_residual":
            item["representation"] = "memory_residual"
        memories_by_id[memory_id] = {**previous, **item}

    policy_by_id = {
        str(item.get("memory_id")): dict(item)
        for item in store["policy_candidates"]
        if item.get("memory_id")
    }
    for record in batch_payload.get("policy_candidates", []):
        if not isinstance(record, dict):
            continue
        item = dict(record)
        memory_id = str(item.get("memory_id") or _canonical_memory_id(item))
        item["memory_id"] = memory_id
        previous = policy_by_id.get(memory_id, {})
        if previous.get("representation") == "skill_factored":
            item["representation"] = "skill_factored"
        policy_by_id[memory_id] = {**previous, **item}

    compiled_source_ids = {
        str(item.get("candidate_id") or "")
        for memory_id, item in policy_by_id.items()
        if memory_id in compiled
    }
    for memory_id, item in policy_by_id.items():
        candidate_id = str(item.get("candidate_id") or "")
        if memory_id in compiled or candidate_id in compiled:
            item["representation"] = "skill_factored"
            item["procedural_invariant_location"] = "family_skill"
            compiled_source_ids.add(candidate_id)
    for memory_id, item in memories_by_id.items():
        candidate_id = str(item.get("candidate_id") or "")
        if memory_id in compiled or candidate_id in compiled or candidate_id in compiled_source_ids:
            item["representation"] = "memory_residual"
            item["procedural_invariant_location"] = "family_skill"

    family = str(batch_payload.get("task_family") or "")
    if not family:
        records = [
            *batch_payload.get("memories", []),
            *batch_payload.get("policy_candidates", []),
        ]
        if records and isinstance(records[0], dict):
            context = records[0].get("context")
            if isinstance(context, dict):
                family = str(context.get("task_family") or "")
    store["task_family"] = family or store.get("task_family", "")
    store["memories"] = sorted(
        memories_by_id.values(), key=lambda item: str(item.get("memory_id"))
    )
    store["policy_candidates"] = sorted(
        policy_by_id.values(), key=lambda item: str(item.get("memory_id"))
    )
    store["counts"] = {
        "total": len(store["memories"]),
        "retrievable": len(store["memories"]),
        "unpromoted": sum(item.get("representation") == "memory" for item in store["memories"]),
        "skill_factored": sum(
            item.get("representation") == "memory_residual" for item in store["memories"]
        ),
        "policy_candidates": len(store["policy_candidates"]),
        "pending_policy_candidates": sum(
            item.get("representation") == "candidate"
            for item in store["policy_candidates"]
        ),
        "compiled_policy_candidates": sum(
            item.get("representation") == "skill_factored"
            for item in store["policy_candidates"]
        ),
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    return store


def residual_memory_candidates(path: Path) -> list[BottleneckCandidate]:
    """Rehydrate private policy candidates so recurrence spans batches."""
    candidates: list[BottleneckCandidate] = []
    for record in load_memory_store(path)["policy_candidates"]:
        if record.get("representation") != "candidate":
            continue
        context = record.get("context") if isinstance(record.get("context"), dict) else {}
        cluster_input = record.get("cluster_input") if isinstance(record.get("cluster_input"), dict) else {}
        outcome = str(record.get("outcome") or "unresolved_failure")
        if outcome not in {"verified_success", "unresolved_failure", "tool_recovery"}:
            outcome = "unresolved_failure"
        raw_substep = record.get("substep") if isinstance(record.get("substep"), dict) else None
        substep = None
        if raw_substep:
            substep = ReusableSubstep(
                step_indices=tuple(int(item) for item in raw_substep.get("step_indices", [])),
                kind=str(raw_substep.get("kind") or "atomic"),
                action=str(raw_substep.get("action") or ""),
                tool_name=str(raw_substep.get("tool_name") or ""),
                target=raw_substep.get("target"),
                signature=str(raw_substep.get("signature") or ""),
                command_shape=str(raw_substep.get("command_shape") or ""),
                input_formats=tuple(str(item) for item in raw_substep.get("input_formats", [])),
                output_formats=tuple(str(item) for item in raw_substep.get("output_formats", [])),
            )
        kind = str(record.get("candidate_kind") or context.get("candidate_kind") or "recovery_candidate")
        if kind not in {"recovery_candidate", "atomic_substep", "workflow"}:
            kind = "recovery_candidate"
        source = str(context.get("evidence_source") or "reflection")
        if source not in {"trajectory", "reflection"}:
            source = "reflection"
        candidates.append(
            BottleneckCandidate(
                candidate_id=str(record.get("memory_id") or _canonical_memory_id(record)),
                task_name=str(context.get("task_name") or "unknown-task"),
                task_family=str(context.get("task_family") or ""),
                step_range=(0, 0),
                failed_attempts=[
                    FailedAttempt(
                        step_index=0,
                        tool_name="memory",
                        command="",
                        error_message=str(record.get("rationale") or ""),
                        error_type="historical_reflection",
                    )
                ],
                winning_command="",
                winning_tool="",
                exploration_cost=1,
                intent=str(cluster_input.get("intent") or "recover from a prior task failure"),
                obstacle=str(cluster_input.get("obstacle") or record.get("rationale") or ""),
                resolution=str(record.get("lesson") or ""),
                evidence_label=outcome,
                substep=substep,
                evidence_source=source,
                retry_outcome=record.get("retry_outcome"),
                retry_transition=dict(record.get("retry_transition") or {}),
                candidate_kind=kind,
            )
        )
    return candidates


def materialize_memory_runtime(skills_dir: Path, store_path: Path) -> Path | None:
    """Place a read-only MCP bundle in a disposable skills snapshot."""
    packages = find_skill_package_dirs(Path(skills_dir))
    if len(packages) != 1:
        return None
    package = packages[0]
    runtime = package / RUNTIME_MEMORY_DIRNAME
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)

    store = load_memory_store(store_path)
    residual: list[dict[str, Any]] = []
    for source in store["memories"]:
        item = dict(source)
        if item.get("representation") == "memory_residual":
            item.pop("cluster_input", None)
            item.pop("substep", None)
            transition = item.pop("retry_transition", None)
            if isinstance(transition, dict):
                item["retry_transition"] = {
                    key: transition[key]
                    for key in ("from_attempt", "to_attempt", "retry_verifier_passed")
                    if key in transition
                }
            item["lesson"] = (
                "The recurring procedure from this episode was compiled into the family skill. "
                "Use this memory only for its instance context, observation, rationale, and outcome."
            )
        residual.append(item)
    if not residual:
        shutil.rmtree(runtime)
        return None
    retrieval = _attach_retrieval_embeddings(residual)
    public_store = {
        "schema_version": 2,
        "task_family": store.get("task_family", ""),
        "read_only": True,
        "retrieval": retrieval,
        "memories": residual,
    }
    (runtime / "records.json").write_text(
        json.dumps(public_store, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy2(Path(__file__).with_name("memory_mcp_server.py"), runtime / "server.py")

    slug = read_skill_name(package)
    container_runtime = f"/root/.claude/skills/{slug}/{RUNTIME_MEMORY_DIRNAME}"
    config = {
        "mcpServers": {
            MCP_SERVER_NAME: {
                "type": "stdio",
                "command": "python3",
                "args": [f"{container_runtime}/server.py", "--store", f"{container_runtime}/records.json"],
            }
        }
    }
    (runtime / "mcp.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return runtime


def prepare_runtime_skills(
    source_skills_dir: Path,
    destination_skills_dir: Path,
    store_path: Path,
) -> Path:
    """Copy frozen skills and add ephemeral memory runtime files for evaluation."""
    destination = Path(destination_skills_dir)
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_skills_dir, destination)
    materialize_memory_runtime(destination, store_path)
    return destination


def memory_runtime_spec(skills_dir: Path) -> dict[str, Any] | None:
    """Return the in-container stdio MCP configuration for a materialized tree."""
    packages = find_skill_package_dirs(Path(skills_dir))
    if len(packages) != 1 or not (packages[0] / RUNTIME_MEMORY_DIRNAME / "server.py").is_file():
        return None
    slug = read_skill_name(packages[0])
    root = f"/root/.claude/skills/{slug}/{RUNTIME_MEMORY_DIRNAME}"
    records_path = packages[0] / RUNTIME_MEMORY_DIRNAME / "records.json"
    try:
        records = json.loads(records_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        records = {}
    retrieval = records.get("retrieval") if isinstance(records, dict) else {}
    return {
        "name": MCP_SERVER_NAME,
        "transport": "stdio",
        "command": "python3",
        "args": [f"{root}/server.py", "--store", f"{root}/records.json"],
        "config_path": f"{root}/mcp.json",
        "allowed_tools": [MCP_SEARCH_TOOL, MCP_GET_TOOL],
        "semantic_available": bool(
            isinstance(retrieval, dict) and retrieval.get("semantic_available")
        ),
        "embedding_model": (
            str(retrieval.get("embedding_model") or "")
            if isinstance(retrieval, dict)
            else ""
        ),
    }
