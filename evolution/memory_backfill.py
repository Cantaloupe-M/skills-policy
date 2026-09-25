"""Reconstruct evaluation memory from historical training artifacts only.

Older runs predate ``memory_store.json``.  This module gives test-only
evaluation a deterministic migration path without reading held-out test
trajectories or mutating the source run.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from evolution.bottleneck_detector import discover_candidates_cross_trial
from evolution.exploration.trace_parser import parse_trajectories
from evolution.memory_store import (
    MEMORY_STORE_FILENAME,
    build_candidate_memory_payload,
    merge_memory_store,
)
from evolution.trajectory_loader import load_trajectories


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _task_fingerprint(task_name: str) -> str:
    return hashlib.sha256(task_name.encode("utf-8")).hexdigest()[:16]


def _normalized_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _lineage_evidence(final_version_root: Path) -> list[dict[str, Any]]:
    lineage = _read_json(final_version_root / ".evolution" / "lineage.json")
    policies = lineage.get("policies")
    if not isinstance(policies, dict):
        return []
    evidence: list[dict[str, Any]] = []
    for policy_id, policy in policies.items():
        if not isinstance(policy, dict):
            continue
        for item in policy.get("resolution_evidence", []):
            if isinstance(item, dict):
                evidence.append({"policy_id": str(policy_id), **item})
    return evidence


def _record_match_mode(
    record: dict[str, Any],
    evidence: dict[str, Any],
) -> str | None:
    context = record.get("context") if isinstance(record.get("context"), dict) else {}
    task_name = str(context.get("task_name") or "")
    if not task_name or _task_fingerprint(task_name) != evidence.get("task_fingerprint"):
        return None

    source = str(context.get("evidence_source") or "")
    if not source and context.get("reflection_files"):
        source = "reflection"
    if source and evidence.get("source") and source != evidence.get("source"):
        return None
    if record.get("outcome") and evidence.get("label"):
        if record.get("outcome") != evidence.get("label"):
            return None
    if record.get("retry_outcome") is not None and evidence.get("retry_outcome") is not None:
        if record.get("retry_outcome") != evidence.get("retry_outcome"):
            return None
    if _normalized_text(record.get("lesson")) == _normalized_text(evidence.get("resolution")):
        return "exact_resolution"
    # Historical evolution used an LLM to rewrite trajectory resolutions, so
    # exact text cannot always be reconstructed. The lineage still preserves
    # immutable task/source/outcome provenance. Use that weaker match only for
    # trajectory observations; reflections remain instance memory unless their
    # actual corrective lesson appears in the published lineage.
    if source == "trajectory":
        return "trajectory_provenance"
    return None


def backfill_memory_store(
    source_family_dir: Path,
    destination_store: Path,
    *,
    task_family: str,
) -> dict[str, Any]:
    """Build one store from ``train/`` artifacts and final skill lineage.

    No LLM is called. Exact lineage matches mark the corresponding reflection
    memory as ``memory_residual`` and the consolidation input as
    ``skill_factored``. Generic workflow candidates remain private state.
    """
    source_family_dir = Path(source_family_dir).resolve()
    destination_store = Path(destination_store)
    train_root = source_family_dir / "train"
    staged_dirs = sorted(
        path
        for path in train_root.glob("epoch_*/batch_*/evolution/staged_batch")
        if path.is_dir()
    )

    memories_by_id: dict[str, dict[str, Any]] = {}
    policy_candidates_by_id: dict[str, dict[str, Any]] = {}
    trace_count = 0
    candidate_count = 0
    for staged_dir in staged_dirs:
        trials = load_trajectories(staged_dir)
        traces = parse_trajectories(trials, task_family=task_family)
        candidates = discover_candidates_cross_trial(traces, use_llm=False)
        payload = build_candidate_memory_payload(candidates, traces)
        trace_count += len(traces)
        candidate_count += len(candidates)
        for record in payload.get("memories", []):
            if isinstance(record, dict) and record.get("memory_id"):
                memories_by_id[str(record["memory_id"])] = record
        for record in payload.get("policy_candidates", []):
            if isinstance(record, dict) and record.get("memory_id"):
                policy_candidates_by_id[str(record["memory_id"])] = record

    lineage = _lineage_evidence(source_family_dir / "skill_versions" / "final")
    compiled_memory_ids: set[str] = set()
    matched_lineage_indices: set[int] = set()
    exact_matches: set[str] = set()
    provenance_matches: set[str] = set()
    for memory_id, record in policy_candidates_by_id.items():
        for index, evidence in enumerate(lineage):
            match_mode = _record_match_mode(record, evidence)
            if match_mode:
                compiled_memory_ids.add(memory_id)
                matched_lineage_indices.add(index)
                if match_mode == "exact_resolution":
                    exact_matches.add(memory_id)
                else:
                    provenance_matches.add(memory_id)

    destination_store.parent.mkdir(parents=True, exist_ok=True)
    destination_store.unlink(missing_ok=True)
    store = merge_memory_store(
        destination_store,
        {
            "task_family": task_family,
            "memories": list(memories_by_id.values()),
            "policy_candidates": list(policy_candidates_by_id.values()),
        },
        compiled_candidate_ids=compiled_memory_ids,
    )
    provenance = {
        "source": "train_artifact_backfill",
        "source_family_dir": str(source_family_dir),
        "source_scope": "train/epoch_*/batch_*/evolution/staged_batch",
        "source_files": [str(path.relative_to(source_family_dir)) for path in staged_dirs],
        "staged_batches": len(staged_dirs),
        "traces": trace_count,
        "candidates": candidate_count,
        "retrieval_memories": len(memories_by_id),
        "lineage_evidence": len(lineage),
        "matched_lineage_evidence": len(matched_lineage_indices),
        "unmatched_lineage_evidence": len(lineage) - len(matched_lineage_indices),
        "exact_resolution_candidates": len(exact_matches),
        "trajectory_provenance_candidates": len(provenance_matches - exact_matches),
        "audit_limitation": (
            "Historical LLM-refined or full-workflow skill rewrites may not have an exact "
            "deterministic candidate match. Trajectory records with matching immutable "
            "lineage provenance are treated as skill-factored; reflections require an exact "
            "resolution match. Only sanitized reflection episodes are agent-retrievable; "
            "generic workflow candidates remain private consolidation state."
        ),
    }
    store["provenance"] = provenance
    destination_store.write_text(
        json.dumps(store, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {**provenance, "store_path": str(destination_store), "counts": store["counts"]}


def prepare_test_memory_store(
    source_family_dir: Path,
    destination_store: Path,
    *,
    task_family: str,
) -> dict[str, Any]:
    """Copy a native train store or backfill one for a historical run."""
    source_family_dir = Path(source_family_dir).resolve()
    destination_store = Path(destination_store)
    native_store = source_family_dir / "skill_versions" / MEMORY_STORE_FILENAME
    if native_store.is_file():
        destination_store.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(native_store, destination_store)
        # Rewrite through the loader so a schema-v1 source is separated into
        # retrieval memories and private policy candidates at the destination.
        store = merge_memory_store(
            destination_store,
            {"task_family": task_family, "memories": [], "policy_candidates": []},
        )
        return {
            "source": "native_training_store",
            "source_family_dir": str(source_family_dir),
            "store_path": str(destination_store),
            "counts": store["counts"],
        }
    return backfill_memory_store(
        source_family_dir,
        destination_store,
        task_family=task_family,
    )
