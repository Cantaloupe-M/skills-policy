"""Four-stage exploration-aware skill evolution pipeline.

Trajectory -> candidate discovery -> problem grouping -> capability compilation.
Verifier-passing traces and repeated verifier failures both create experimental
policies; only later verified reuse promotes a policy to active.
"""

from __future__ import annotations

import json
from pathlib import Path

from evolution.bottleneck_clusterer import group_candidates
from evolution.bottleneck_detector import discover_candidates_cross_trial
from evolution.cluster_quality_checker import assess_cluster_quality
from evolution.exploration.skill_compiler import compile_family_skill
from evolution.exploration.trace_parser import is_public_substep_action
from evolution.memory_store import (
    build_candidate_memory_payload,
    build_reflection_memory_payload,
    merge_memory_store,
    residual_memory_candidates,
)
from evolution.semantic_embeddings import EmbeddingConfigurationError
from evolution.types import BottleneckCandidate, CapabilityCluster, ExplorationReport, ExplorationTrace


def _sync_memory_artifacts(job_dir: Path, store: dict) -> None:
    """Mirror committed store representations into batch-local audit views."""
    store_by_id = {
        str(record.get("memory_id")): record
        for record in store.get("memories", [])
        if record.get("memory_id")
    }
    for filename in ("experience_memories.json", "reflection_memories.json"):
        path = Path(job_dir) / filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for record in payload.get("memories", []):
            persisted = store_by_id.get(str(record.get("memory_id")))
            if persisted:
                record["representation"] = persisted.get("representation", "memory")
        payload["store_counts"] = store.get("counts", {})
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def finalize_memory_compilation(
    memory_store_path: Path,
    job_dir: Path,
    compiled_candidate_ids: list[str],
) -> dict:
    """Commit the memory-to-skill transition after skill version publication."""
    store = merge_memory_store(
        memory_store_path,
        {"memories": []},
        compiled_candidate_ids=compiled_candidate_ids,
    )
    _sync_memory_artifacts(Path(job_dir), store)
    return store


def run_evolution_pipeline(
    traces: list[ExplorationTrace],
    task_family: str,
    skills_dir: Path,
    *,
    use_llm: bool = True,
    min_exploration_cost: int = 2,
    min_occurrences: int = 3,
    include_failure_evidence: bool = True,
    strict_cross_task: bool = True,
    require_policy_use: bool = True,
    immediate_promotion: bool = False,
    dry_run: bool = False,
    verbose: bool = True,
    prior_memory_candidates: list[BottleneckCandidate] | None = None,
    discovered_candidates: list[BottleneckCandidate] | None = None,
) -> ExplorationReport:
    if not traces:
        return ExplorationReport(task_family=task_family, summary="No trajectories provided.")

    # The success-only ablation removes failed trajectories from the discovery
    # stream entirely; they are still present in the run artifacts for audit.
    discovery_traces = traces if include_failure_evidence else [
        trace for trace in traces if trace.verifier_passed
    ]

    candidates = list(discovered_candidates) if discovered_candidates is not None else discover_candidates_cross_trial(
        discovery_traces,
        use_llm=use_llm and not dry_run,
        min_exploration_cost=min_exploration_cost,
    )
    known_candidate_ids = {candidate.candidate_id for candidate in candidates}
    if include_failure_evidence:
        candidates.extend(
            candidate
            for candidate in (prior_memory_candidates or [])
            if candidate.candidate_id not in known_candidate_ids
        )
    # Keep low-level observations for lineage/audit, but do not turn generic
    # file and JSON primitives into family capabilities.  A successful task is
    # evidence that the whole task passed, not that every incidental tool call
    # deserves a public skill instruction.
    verified_candidates = [
        candidate
        for candidate in candidates
        if candidate.evidence_label == "verified_success"
        and (
            candidate.substep is None
            or is_public_substep_action(candidate.substep.action)
        )
    ]
    failure_candidates = [
        candidate for candidate in candidates if candidate.evidence_label == "unresolved_failure"
    ] if include_failure_evidence else []
    failed_method_candidates = [
        candidate for candidate in candidates if candidate.evidence_label == "tool_recovery"
    ] if include_failure_evidence else []
    failure_diagnostics = (
        sum(1 for candidate in candidates if candidate.evidence_label != "verified_success")
        if include_failure_evidence
        else 0
    )

    # Cluster problem identity independently of the proposed resolution and its
    # outcome.  This lets one recovery cluster contain multiple approaches to
    # the same intent/obstacle, including both successful and failed methods.
    # Labels remain attached to individual candidates for consolidation.
    def publishable(cluster: CapabilityCluster) -> bool:
        # A local tool recovery may describe a method that ultimately failed.
        # Keep it inside the problem cluster for comparison, but do not let such
        # evidence satisfy the cross-task publication threshold by itself.
        qualifying_tasks = {
            candidate.task_name
            for candidate in cluster.candidates
            if candidate.evidence_label in {"verified_success", "unresolved_failure"}
        }
        return len(qualifying_tasks) >= min_occurrences

    try:
        all_clusters = group_candidates(
            [*verified_candidates, *failure_candidates, *failed_method_candidates]
        )
        qualified_clusters = [cluster for cluster in all_clusters if publishable(cluster)]

        # Assess cluster quality to filter out low-quality clusters
        # caused by template intent/obstacle or overly broad groupings
        high_quality_clusters, _quality_report = assess_cluster_quality(
            qualified_clusters,
            min_confidence=0.7,
        )

        verified_clusters = [
            cluster
            for cluster in high_quality_clusters
            if any(candidate.evidence_label == "verified_success" for candidate in cluster.candidates)
        ]
        recurring_failure_clusters = [
            cluster
            for cluster in high_quality_clusters
            if not any(candidate.evidence_label == "verified_success" for candidate in cluster.candidates)
        ]
    except EmbeddingConfigurationError as exc:
        return ExplorationReport(
            task_family=task_family,
            num_trials=len(discovery_traces),
            num_bottlenecks_detected=len(candidates),
            num_failure_diagnostics=failure_diagnostics,
            publication_block_reason="embedding_unavailable",
            degradation_warning={"component": "semantic_clustering", "error": str(exc)},
            summary=f"Semantic clustering unavailable; no policy was published. {exc}",
        )
    update_clusters = [*verified_clusters, *recurring_failure_clusters]

    if verbose:
        passed = sum(trace.verifier_passed for trace in traces)
        print(
            f"[evolution] {task_family}: {passed}/{len(traces)} verifier-passed trials, "
            f"{len(candidates)} discovery candidates, {len(verified_clusters)} cluster(s) with "
            f"verified evidence and {len(recurring_failure_clusters)} failure-only update cluster(s)"
        )
        if failure_diagnostics:
            print(
                f"[evolution] {task_family}: {failure_diagnostics} failure diagnostic(s) "
                "observed; only cross-task recurrences become experimental policies."
            )

    if dry_run:
        return ExplorationReport(
            task_family=task_family,
            num_trials=len(discovery_traces),
            num_bottlenecks_detected=len(candidates),
            num_capabilities=len(update_clusters),
            num_failure_diagnostics=failure_diagnostics,
            publication_block_reason="no_reusable_evidence" if not update_clusters else None,
            summary=(
                f"[DRY RUN] {len(verified_candidates)} verified candidate(s) and "
                f"{len(recurring_failure_clusters)} failure-only cluster(s) in "
                f"{len(update_clusters)} experimental update cluster(s)."
            ),
        )

    if not update_clusters:
        # A later batch can validate an experimental policy without discovering
        # another recurrence cluster.  Let the compiler inspect explicit policy
        # reuse before declaring this batch diagnostics-only; it owns the
        # experimental -> active transition and writes the resulting evidence.
        skills_root = Path(skills_dir)
        metadata_root = (
            skills_root.parent.parent / ".evolution"
            if skills_root.name == "skills" and skills_root.parent.name == ".claude"
            else skills_root / ".evolution"
        )
        registry_path = metadata_root / "lineage.json"
        has_existing_policies = False
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            has_existing_policies = bool(registry.get("policies"))
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
        if has_existing_policies:
            report = compile_family_skill(
                [],
                discovery_traces,
                task_family,
                Path(skills_dir),
                workflow_traces=[],
                strict_cross_task=strict_cross_task,
                require_policy_use=require_policy_use,
                immediate_promotion=immediate_promotion,
            )
            report.num_failure_diagnostics = failure_diagnostics
            return report
        return ExplorationReport(
            task_family=task_family,
            num_trials=len(discovery_traces),
            num_bottlenecks_detected=len(candidates),
            num_capabilities=0,
            num_failure_diagnostics=failure_diagnostics,
            publication_block_reason="no_reusable_evidence",
            summary=(
                f"{len(candidates)} diagnostic candidate(s) retained; "
                f"no {min_occurrences}-task recurring evidence for an experimental SkillPolicy."
            ),
        )

    report = compile_family_skill(
        update_clusters,
        discovery_traces,
        task_family,
        Path(skills_dir),
        workflow_traces=[],
        strict_cross_task=strict_cross_task,
        require_policy_use=require_policy_use,
        immediate_promotion=immediate_promotion,
    )
    report.num_failure_diagnostics = failure_diagnostics
    if failure_diagnostics:
        report.summary += (
            " Repeated failure patterns were published as experimental policies; "
            "unmatched failures were retained as diagnostics."
        )
    return report


def _write_failure_diagnostics(
    job_dir: Path,
    candidates: list,
    refinement_failures: list[dict[str, object]] | None = None,
) -> None:
    """Preserve complete failure evidence beside the staged batch for audit and reuse."""
    diagnostics = [candidate for candidate in candidates if candidate.evidence_label != "verified_success"]
    refinement_failures = list(refinement_failures or [])
    if not diagnostics and not refinement_failures:
        return
    payload = {
        "status": "diagnostic",
        "publication_block_reason": "no_reusable_evidence",
        "count": len(diagnostics),
        "refinement_failure_count": len(refinement_failures),
        "refinement_failures": refinement_failures,
        "diagnostics": [
            {
                "candidate_id": candidate.candidate_id,
                "task_name": candidate.task_name,
                "intent": candidate.intent,
                "obstacle": candidate.obstacle,
                "resolution": candidate.resolution,
                "evidence_source": candidate.evidence_source,
                "evidence_label": candidate.evidence_label,
                "retry_outcome": candidate.retry_outcome,
                "retry_transition": candidate.retry_transition,
                "exploration_cost": candidate.exploration_cost,
                "failed_attempts": [
                    {
                        "tool_name": attempt.tool_name,
                        "error_type": attempt.error_type,
                    }
                    for attempt in candidate.failed_attempts
                ],
            }
            for candidate in diagnostics
        ],
    }
    path = Path(job_dir) / "failure_diagnostics.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_reflection_memories(job_dir: Path, traces: list[ExplorationTrace]) -> None:
    """Persist the paper-style memory representation used for clustering."""
    payload = build_reflection_memory_payload(traces)
    if not payload["memories"]:
        return
    (Path(job_dir) / "reflection_memories.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _write_missing_trajectory_diagnostics(job_dir: Path) -> int:
    """Record failed staged attempts whose raw execution artifact was unavailable."""
    missing: list[dict[str, object]] = []
    for manifest_path in Path(job_dir).glob("*/attempt_manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        task_name = str(manifest.get("task_name") or manifest_path.parent.name)
        for item in manifest.get("attempts", []):
            if not isinstance(item, dict) or bool(item.get("success", False)):
                continue
            number = int(item.get("number", 0) or 0)
            attempt_dir = manifest_path.parent / "attempts" / f"attempt_{number:02d}"
            has_raw_artifact = any(
                path.is_file()
                for path in (
                    attempt_dir / "agent" / "trajectory.json",
                    attempt_dir / "agent" / "claude-code.txt",
                    attempt_dir / "agent" / "claude_code.txt",
                    attempt_dir / "sessions" / "agent.log",
                )
            )
            if not has_raw_artifact:
                missing.append(
                    {
                        "task_name": task_name,
                        "attempt_number": number,
                        "exception_info": item.get("exception_info"),
                    }
                )
    if missing:
        (Path(job_dir) / "missing_trajectory_diagnostics.json").write_text(
            json.dumps(
                {
                    "status": "artifact_missing",
                    "publication_block_reason": "missing_raw_trajectory",
                    "count": len(missing),
                    "attempts": missing,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return len(missing)


def evolve_from_job_dir(
    job_dir: Path,
    task_family: str,
    skills_dir: Path,
    *,
    use_llm: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
    min_exploration_cost: int = 2,
    min_occurrences: int = 3,
    include_failure_evidence: bool = True,
    strict_cross_task: bool = True,
    require_policy_use: bool = True,
    immediate_promotion: bool = False,
    memory_store_path: Path | None = None,
) -> ExplorationReport:
    from evolution.exploration.trace_parser import parse_trajectories
    from evolution.trajectory_loader import load_trajectories

    missing_trajectory_attempts = _write_missing_trajectory_diagnostics(Path(job_dir))
    trial_data = load_trajectories(Path(job_dir))
    traces = parse_trajectories(trial_data, task_family)
    discovery_traces = traces if include_failure_evidence else [
        trace for trace in traces if trace.verifier_passed
    ]
    refinement_failures: list[dict[str, object]] = []
    current_candidates = discover_candidates_cross_trial(
        discovery_traces,
        use_llm=use_llm and not dry_run,
        min_exploration_cost=min_exploration_cost,
        refinement_diagnostics=refinement_failures,
    ) if traces else []
    if refinement_failures:
        # Persist the exclusion decision before clustering/compilation so a
        # later downstream failure cannot erase why these candidates vanished.
        _write_failure_diagnostics(Path(job_dir), [], refinement_failures)
    reflection_memory_payload = build_reflection_memory_payload(traces)
    batch_memory_payload = build_candidate_memory_payload(current_candidates, traces)
    _write_reflection_memories(Path(job_dir), traces)
    prior_memories = residual_memory_candidates(memory_store_path) if memory_store_path else []
    report = run_evolution_pipeline(
        traces,
        task_family,
        Path(skills_dir),
        use_llm=use_llm,
        min_exploration_cost=min_exploration_cost,
        min_occurrences=min_occurrences,
        include_failure_evidence=include_failure_evidence,
        strict_cross_task=strict_cross_task,
        require_policy_use=require_policy_use,
        immediate_promotion=immediate_promotion,
        dry_run=dry_run,
        verbose=verbose,
        prior_memory_candidates=prior_memories,
        discovered_candidates=current_candidates,
    )
    if memory_store_path is not None and include_failure_evidence and not dry_run:
        store = merge_memory_store(
            memory_store_path,
            batch_memory_payload,
        )
        report.num_residual_memories = int(store["counts"]["retrievable"])
        report.num_compiled_memories = int(store["counts"]["skill_factored"])
        if batch_memory_payload["memories"]:
            batch_memory_payload["store_counts"] = store["counts"]
            (Path(job_dir) / "experience_memories.json").write_text(
                json.dumps(batch_memory_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            reflection_memory_payload["store_counts"] = store["counts"]
            if reflection_memory_payload["memories"]:
                (Path(job_dir) / "reflection_memories.json").write_text(
                    json.dumps(reflection_memory_payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            _sync_memory_artifacts(Path(job_dir), store)
    report.num_missing_trajectory_attempts = missing_trajectory_attempts
    if not traces and missing_trajectory_attempts:
        report.publication_block_reason = "missing_raw_trajectory"
        report.summary = (
            f"{missing_trajectory_attempts} failed attempt(s) retained as artifact-missing diagnostics; "
            "no parseable trajectory available for evolution."
        )
    if traces:
        candidates = discover_candidates_cross_trial(
            traces,
            use_llm=False,
            min_exploration_cost=min_exploration_cost,
        )
        _write_failure_diagnostics(Path(job_dir), candidates, refinement_failures)
    elif refinement_failures:
        _write_failure_diagnostics(Path(job_dir), [], refinement_failures)
    return report
