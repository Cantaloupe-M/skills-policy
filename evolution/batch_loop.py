"""Shared task-execution and batch-evolution orchestration for benchmark runners.

Provides the ``BatchExecutor`` interface, a reusable ``BatchTaskRunner`` for
batch task execution, and the ``BatchEvolutionLoop`` policy-driven orchestrator.
Each benchmark runner implements a concrete executor.

The runner handles:

* pulling batches from a pending queue
* executing each batch (delegated to the executor)
* reflecting on failures via LLM and retrying up to ``max_retries`` times
* collecting normalized trial results for downstream consumers

The evolution loop builds on top of the runner and additionally handles:

* using successful trials for discoveries and all trials for reuse evidence
* calling ``evolve_from_job_dir()`` after each batch to update skills
* marking exhausted failures as final outcomes for that batch
"""

from __future__ import annotations

import json
import os
import random
import shutil
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evolution.batch_reflection import run_reflection_retry_loop
from evolution.bottleneck_pipeline import evolve_from_job_dir, finalize_memory_compilation
from evolution.config import EvolutionConfig
from evolution.memory_store import MEMORY_STORE_FILENAME, materialize_memory_runtime
from evolution.outcome import TrialOutcome, outcome_digest
from evolution.skill_utils import (
    BatchSnapshotInfo,
    SkillVersionInfo,
    create_batch_snapshot,
    create_candidate_from_version,
    freeze_final_version,
    get_latest_skill_version,
    hash_skill_tree,
    initialize_skill_version_store,
    promote_candidate_version,
)
from evolution.types import ExplorationReport


def _copy_trial_tree(source: Path, destination: Path) -> list[str]:
    """Copy readable trial artifacts and report container-owned omissions."""
    skipped: set[str] = set()

    def relative(path: Path) -> str:
        return path.relative_to(source).as_posix()

    def ignore_unreadable(directory: str, names: list[str]) -> list[str]:
        ignored: list[str] = []
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            required = os.R_OK | (os.X_OK if path.is_dir() else 0)
            if not os.access(path, required):
                ignored.append(name)
                skipped.add(relative(path))
        return ignored

    def copy_readable_file(src: str, dst: str, *, follow_symlinks: bool = True) -> str:
        try:
            return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
        except PermissionError:
            skipped.add(relative(Path(src)))
            return dst

    shutil.copytree(
        source,
        destination,
        symlinks=True,
        ignore=ignore_unreadable,
        copy_function=copy_readable_file,
    )
    return sorted(skipped)

# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TaskRef:
    """Benchmark-agnostic reference to one task.

    Attributes:
        name: Task identifier (directory name, task_id, etc.).
        family: Task family / group name for evolution grouping.
        source_path: Filesystem path to the task definition.
        metadata: Arbitrary benchmark-specific data (e.g. agent kwargs).
    """

    name: str
    family: str
    source_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrialAttempt:
    """One execution attempt retained for failure-aware evolution."""

    number: int
    trial_name: str
    trial_dir: Path
    success: bool
    reward: float
    exception_info: str | None = None
    trajectory_path: Path | None = None
    outcome: TrialOutcome | None = None


@dataclass
class TrialResult:
    """Normalized outcome of one trial execution.

    Attributes:
        task_name: Which task this trial belongs to.
        trial_name: Trial identifier (directory name, UUID).
        trial_dir: Directory containing ``agent/trajectory.*`` and
            ``result.json``.  This is what ``evolve_from_job_dir()`` scans.
        success: ``True`` when reward is 1.0 and no exception occurred.
        reward: Numeric reward (1.0 = perfect success).
        exception_info: Exception message or ``None``.
        trajectory_path: Path to the trajectory file inside ``trial_dir``,
            or ``None`` if not found.
        retries_used: How many retries were consumed for this trial.
    """

    task_name: str
    trial_name: str
    trial_dir: Path
    success: bool
    reward: float = 0.0
    exception_info: str | None = None
    trajectory_path: Path | None = None
    outcome: TrialOutcome | None = None
    retries_used: int = 0
    attempts: list[TrialAttempt] = field(default_factory=list)


@dataclass
class BatchRound:
    """Execution outcome for one processed batch."""

    batch_index: int
    epoch_index: int
    batch_tasks: list[TaskRef]
    results: list[TrialResult]
    successful: list[TrialResult]
    failed: list[tuple[TaskRef, TrialResult]]
    round_dir: Path
    snapshot: BatchSnapshotInfo
    batch_summary_path: Path | None = None
    promoted_version: str | None = None
    promoted_hash: str | None = None


@dataclass
class BatchRunSummary:
    """Aggregate execution summary independent from skill evolution."""

    task_family: str
    total_tasks: int = 0
    batches_run: int = 0
    total_successful: int = 0
    total_failed: int = 0
    batch_rounds: list[BatchRound] = field(default_factory=list)

    @property
    def all_successful(self) -> bool:
        return self.total_failed == 0 and self.total_successful == self.total_tasks


@dataclass
class LoopSummary:
    """Aggregate result returned by ``BatchEvolutionLoop.run()``.

    Attributes:
        task_family: The task family / group name.
        total_tasks: Number of unique tasks submitted per epoch.
        batches_run: How many batches were executed.
        total_successful: Successful task executions across all epochs.
        total_failed: Failed task executions across all epochs.
        evolve_reports: One ``ExplorationReport`` per batch that produced
            at least one successful trial.
    """

    task_family: str
    total_tasks: int = 0
    train_epochs: int = 1
    total_task_executions: int = 0
    batches_run: int = 0
    total_successful: int = 0
    total_failed: int = 0
    final_epoch_successful: int = 0
    final_epoch_failed: int = 0
    batches_without_success: int = 0
    evolve_reports: list[ExplorationReport] = field(default_factory=list)
    batch_metrics_history: list[dict[str, Any]] = field(default_factory=list)
    initial_version: str | None = None
    final_version: str | None = None
    final_hash: str | None = None
    tasks_using_evolved_version: int = 0
    batch_rounds: list[BatchRound] = field(default_factory=list)
    version_history: list[dict[str, Any]] = field(default_factory=list)
    epoch_metrics: list[dict[str, Any]] = field(default_factory=list)

    @property
    def all_successful(self) -> bool:
        return (
            self.final_epoch_failed == 0
            and self.final_epoch_successful == self.total_tasks
        )


# ═══════════════════════════════════════════════════════════════════════════
# Abstract executor
# ═══════════════════════════════════════════════════════════════════════════

class BatchExecutor(ABC):
    """Benchmark-specific batch execution interface.

    Each benchmark implements this ABC so the shared execution layer can drive execution
    without knowing the underlying framework.
    """

    @abstractmethod
    def execute_batch(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
    ) -> list[TrialResult]:
        """Execute a batch of tasks with the given shared skills.

        Args:
            tasks: The tasks to execute in this batch.
            shared_skills_dir: Path to the ``SKILL.md`` + ``scripts/``
                directory to mount/inject into the agent environment.
            work_dir: A directory the executor may use for job output.
                Trial subdirectories are expected to appear here.

        Returns:
            One ``TrialResult`` per task, in the same order as *tasks*.
        """
        ...

    def execute_batch_with_retries(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
        *,
        task_family: str,
        max_retries: int,
    ) -> list[TrialResult]:
        """Execute one batch, optionally handling retries inside the executor.

        Executors that run each task in its own worker process may override
        this to keep the full "run → reflect → retry" loop local to that
        worker.  The default behavior is a plain batch execution, leaving
        retries to ``BatchTaskRunner``.
        """
        del task_family, max_retries
        return self.execute_batch(tasks, shared_skills_dir, work_dir)

    @abstractmethod
    def retry_one(
        self,
        task: TaskRef,
        shared_skills_dir: Path,
        work_dir: Path,
        reflection: str,
    ) -> TrialResult:
        """Retry a single failed task with reflection guidance.

        Args:
            task: The task to retry.
            shared_skills_dir: Path to current skills (may have been
                updated by a prior evolution round).
            work_dir: Directory for trial output.
            reflection: Natural-language failure analysis from
                ``reflect_on_failure()`` to inject as guidance.

        Returns:
            The trial result for the retry attempt.
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════
# Batch execution runner
# ═══════════════════════════════════════════════════════════════════════════

class BatchTaskRunner:
    """Run tasks in batches with retries, without imposing evolution policy."""

    def __init__(
        self,
        executor: BatchExecutor,
        config: EvolutionConfig,
        task_family: str,
        skills_dir: Path,
        *,
        verbose: bool = True,
    ):
        self._executor = executor
        self._config = config
        self._task_family = task_family
        self._skills_dir = Path(skills_dir)
        self._verbose = verbose

    def iter_rounds(self, tasks: list[TaskRef], *, epoch_index: int = 1):
        """Execute and yield each batch round before the next one starts.

        Callers that evolve skills between batches must consume this iterator
        synchronously, so a promoted version is available when the next round
        resolves its snapshot source.
        """
        batch_size = max(self._config.batch_size, 1)
        max_retries = self._config.retry_budget
        pending: deque[TaskRef] = deque(tasks)
        batch_index = 0

        self._skills_dir.mkdir(parents=True, exist_ok=True)
        (self._skills_dir.parent / "test").mkdir(parents=True, exist_ok=True)
        (self._skills_dir.parent / "train" / f"epoch_{epoch_index:03d}").mkdir(
            parents=True,
            exist_ok=True,
        )

        while pending:
            batch = [pending.popleft() for _ in range(min(batch_size, len(pending)))]
            batch_index += 1
            current_version = get_latest_skill_version(self._skills_dir)
            if self._verbose:
                print(
                    f"\n[BatchRunner] Epoch {epoch_index}, batch {batch_index}: "
                    f"{len(batch)} task(s), "
                    f"{len(pending)} pending"
                )
                print(
                    f"[BatchRunner]   Skills snapshot source: {current_version.version_label} "
                    f"hash={current_version.content_hash[:12]}"
                )

            yield self._run_batch_round(
                batch,
                batch_index=batch_index,
                epoch_index=epoch_index,
                max_retries=max_retries,
                current_version=current_version,
            ), list(pending)

    def run(self, tasks: list[TaskRef]) -> BatchRunSummary:
        """Execute all tasks batch-by-batch without applying evolution policy."""
        batch_rounds: list[BatchRound] = []
        total_successful = 0
        total_failed = 0

        for round_info, _pending in self.iter_rounds(tasks):
            batch_rounds.append(round_info)
            total_successful += len(round_info.successful)
            total_failed += len(round_info.failed)

        return BatchRunSummary(
            task_family=self._task_family,
            total_tasks=len(tasks),
            batches_run=len(batch_rounds),
            total_successful=total_successful,
            total_failed=total_failed,
            batch_rounds=batch_rounds,
        )

    def _run_batch_round(
        self,
        batch: list[TaskRef],
        *,
        batch_index: int,
        epoch_index: int,
        max_retries: int,
        current_version: SkillVersionInfo,
    ) -> BatchRound:
        """Execute one batch and exhaust its post-initial retry budget."""
        round_dir = (
            self._skills_dir.parent
            / "train"
            / f"epoch_{epoch_index:03d}"
            / f"batch_{batch_index:03d}"
        )
        round_dir.mkdir(parents=True, exist_ok=True)
        snapshot = create_batch_snapshot(
            current_version,
            round_dir,
            batch_index=batch_index,
        )
        if self._config.include_failure_evidence:
            materialize_memory_runtime(
                snapshot.skills_dir,
                self._skills_dir / MEMORY_STORE_FILENAME,
            )

        results = list(
            self._executor.execute_batch_with_retries(
                batch,
                snapshot.skills_dir,
                round_dir,
                task_family=self._task_family,
                max_retries=max_retries,
            )
        )
        if len(results) < len(batch):
            results.extend(
                TrialResult(
                    task_name=task.name,
                    trial_name="",
                    trial_dir=round_dir,
                    success=False,
                    exception_info="executor returned fewer results than tasks",
                )
                for task in batch[len(results):]
            )
        elif len(results) > len(batch):
            results = results[:len(batch)]

        for i, task in enumerate(batch):
            result = results[i]

            executor_attempts = getattr(result, "attempt_results", None)
            if executor_attempts is None:
                executor_attempts = [result]
            if not result.success and len(executor_attempts) == 1:

                def retry(
                    reflection: str,
                    retry_number: int,
                    task_ref: TaskRef = task,
                ) -> TrialResult:
                    retry_work_dir = round_dir / task_ref.name / f"trial_{retry_number + 1:02d}"
                    retry_work_dir.mkdir(parents=True, exist_ok=True)
                    return self._executor.retry_one(
                        task_ref,
                        snapshot.skills_dir,
                        retry_work_dir,
                        reflection,
                    )

                result = run_reflection_retry_loop(
                    result,
                    task_name=task.name,
                    task_family=self._task_family,
                    max_retries=max_retries,
                    retry=retry,
                    log_prefix="BatchRunner",
                )
                executor_attempts = getattr(result, "attempt_results", [result])

            result.attempts = [
                TrialAttempt(
                    number=number,
                    trial_name=attempt.trial_name,
                    trial_dir=attempt.trial_dir,
                    success=attempt.success,
                    reward=attempt.reward,
                    exception_info=attempt.exception_info,
                    trajectory_path=attempt.trajectory_path,
                    outcome=getattr(attempt, "outcome", None),
                )
                for number, attempt in enumerate(executor_attempts, start=1)
            ]
            results[i] = result

        successful = [r for r in results if r.success]
        failed = [
            (batch[i], results[i])
            for i in range(len(batch))
            if not results[i].success
        ]

        if self._verbose:
            print(
                f"[BatchRunner]   {len(successful)} succeeded, "
                f"{len(failed)} exhausted -> marking final failure"
            )

        batch_summary_path = round_dir / "batch_summary.json"
        batch_summary_path.write_text(
            json.dumps(
                {
                    "batch_index": batch_index,
                    "epoch_index": epoch_index,
                    "snapshot_version": snapshot.version_label,
                    "snapshot_hash": snapshot.content_hash,
                    "max_attempts": self._config.max_attempts,
                    "retry_budget": max_retries,
                    "tasks": [task.name for task in batch],
                    "successful": [result.task_name for result in successful],
                    "failed": [task.name for task, _ in failed],
                    "results": [
                        {
                            "task_name": result.task_name,
                            "trial_name": result.trial_name,
                            "success": result.success,
                            "reward": result.reward,
                            "retries_used": result.retries_used,
                            "exception_info": result.exception_info,
                            "trial_dir": str(result.trial_dir),
                        }
                        for result in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return BatchRound(
            batch_index=batch_index,
            epoch_index=epoch_index,
            batch_tasks=list(batch),
            results=list(results),
            successful=successful,
            failed=failed,
            round_dir=round_dir,
            snapshot=snapshot,
            batch_summary_path=batch_summary_path,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Batch policies
# ═══════════════════════════════════════════════════════════════════════════

class BatchPolicy(ABC):
    """Policy hook applied after each completed batch."""

    @abstractmethod
    def on_batch_complete(
        self,
        loop: BatchEvolutionLoop,
        round_info: BatchRound,
        pending: list[TaskRef],
    ) -> dict[str, Any]:
        """Handle successful/failed results from one completed batch."""
        ...


class EvolutionPolicy(BatchPolicy):
    """Preserve the existing evolve-after-each-batch behavior."""

    def __init__(
        self,
        *,
        include_failure_evidence: bool = True,
        strict_cross_task: bool = False,
        require_policy_use: bool = True,
        immediate_promotion: bool = False,
    ) -> None:
        self._prev_metrics: dict[str, Any] | None = None
        self._include_failure_evidence = include_failure_evidence
        self._strict_cross_task = strict_cross_task
        self._require_policy_use = require_policy_use
        self._immediate_promotion = immediate_promotion

    def _promotion_block_reason(
        self,
        loop: BatchEvolutionLoop,
        current_version: SkillVersionInfo,
        candidate: SkillVersionInfo,
    ) -> str | None:
        """Reject malformed candidates; family skill changes are the experiment."""
        del loop, current_version
        if not (candidate.skills_dir.is_dir() and any(candidate.skills_dir.glob("*/SKILL.md"))):
            return "missing_family_skill"
        return None

    def on_batch_complete(
        self,
        loop: BatchEvolutionLoop,
        round_info: BatchRound,
        pending: list[TaskRef],
    ) -> dict[str, Any]:
        successful = round_info.successful
        staged = loop._stage_batch_outcomes(round_info)
        current_version = get_latest_skill_version(loop._skills_dir)
        candidate = create_candidate_from_version(
            current_version,
            round_info.round_dir / "evolution" / "candidate",
        )

        try:
            report = evolve_from_job_dir(
                job_dir=staged,
                task_family=loop._task_family,
                skills_dir=candidate.skills_dir,
                verbose=loop._verbose,
                min_occurrences=loop._min_occurrences,
                include_failure_evidence=self._include_failure_evidence,
                strict_cross_task=self._strict_cross_task,
                require_policy_use=self._require_policy_use,
                immediate_promotion=self._immediate_promotion,
                memory_store_path=loop._skills_dir / MEMORY_STORE_FILENAME,
            )
            if report.publication_block_reason:
                if loop._verbose:
                    print(
                        "[BatchLoop]   Evidence retained without publishing skills: "
                        f"{report.publication_block_reason}; {report.summary}"
                    )
                return {
                    "evolve_report": report,
                    "batch_metrics": loop._compute_batch_metrics(round_info.results),
                    "batches_without_success_increment": 1 if not successful else 0,
                    "promotion_decision": "cold_start_diagnostics" if not successful else "blocked",
                    "promoted_version": None,
                }

            candidate_hash = hash_skill_tree(candidate.skills_dir)
            promotion_reason = self._promotion_block_reason(loop, current_version, candidate)
            if promotion_reason:
                if loop._verbose:
                    print(f"[BatchLoop]   Candidate retained without promotion: {promotion_reason}.")
                return {
                    "evolve_report": report,
                    "batch_metrics": loop._compute_batch_metrics(round_info.results),
                    "batches_without_success_increment": 0 if successful else 1,
                    "promotion_decision": promotion_reason,
                    "promoted_version": None,
                }
            if candidate_hash == current_version.content_hash:
                if loop._verbose:
                    print("[BatchLoop]   Candidate matches current skills; no new version promoted.")
                return {
                    "evolve_report": report,
                    "batch_metrics": loop._compute_batch_metrics(round_info.results),
                    "batches_without_success_increment": 0 if successful else 1,
                    "promotion_decision": "unchanged",
                    "promoted_version": None,
                }

            promoted_version = promote_candidate_version(
                loop._skills_dir,
                candidate.skills_dir,
                parent_version=current_version.version_label,
            )
            memory_store = finalize_memory_compilation(
                loop._skills_dir / MEMORY_STORE_FILENAME,
                staged,
                report.compiled_memory_ids,
            )
            report.num_residual_memories = int(memory_store["counts"]["retrievable"])
            report.num_compiled_memories = int(memory_store["counts"]["skill_factored"])
            round_info.promoted_version = promoted_version.version_label
            round_info.promoted_hash = promoted_version.content_hash

            curr_metrics = loop._compute_batch_metrics(round_info.results)
            curr_metrics["batch_num"] = round_info.batch_index
            curr_metrics["snapshot_version"] = round_info.snapshot.version_label
            curr_metrics["snapshot_hash"] = round_info.snapshot.content_hash
            curr_metrics["promoted_version"] = promoted_version.version_label
            curr_metrics["promoted_hash"] = promoted_version.content_hash

            if self._prev_metrics is not None:
                degradation = loop._check_degradation(self._prev_metrics, curr_metrics)
                if degradation["degraded"]:
                    report.degradation_warning = degradation
                    if loop._verbose:
                        print(f"[BatchLoop]   Skill degradation detected: {degradation['issues']}")
            self._prev_metrics = curr_metrics

            if loop._verbose:
                print(
                    f"[BatchLoop]   Skills updated -> {report.summary} "
                    f"({promoted_version.version_label}, hash={promoted_version.content_hash[:12]})"
                )
                if pending:
                    print(
                        f"[BatchLoop]   Next batch ({len(pending)} pending) will use "
                        f"{promoted_version.version_label}."
                    )

            return {
                "evolve_report": report,
                "batch_metrics": curr_metrics,
                "batches_without_success_increment": 0 if successful else 1,
                "promotion_decision": "promoted",
                "promoted_version": promoted_version,
            }
        except Exception as exc:
            if loop._verbose:
                print(f"[BatchLoop]   Evolution failed: {exc}")
            raise


class NoOpBatchPolicy(BatchPolicy):
    """Collect batch execution results without evolving skills."""

    def on_batch_complete(
        self,
        loop: BatchEvolutionLoop,
        round_info: BatchRound,
        pending: list[TaskRef],
    ) -> dict[str, Any]:
        del pending
        if loop._verbose:
            if round_info.successful:
                print("[BatchLoop]   Successful trials collected; evolution disabled by policy.")
            else:
                print("[BatchLoop]   No successful trials in this batch.")
        return {
            "evolve_report": None,
            "batch_metrics": None,
            "batches_without_success_increment": 1 if not round_info.successful else 0,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Batch evolution loop
# ═══════════════════════════════════════════════════════════════════════════

class BatchEvolutionLoop:
    """Orchestrates: pull batch → execute → policy hook → repeat.

    Usage::

        executor = SkillFlowExecutor(base_config, ...)
        loop = BatchEvolutionLoop(
            executor=executor,
            config=EvolutionConfig(batch_size=3, max_retries=3),
            task_family="My-Family",
            skills_dir=Path("shared_skills/"),
        )
        summary = loop.run(task_refs)
        print(f"{summary.total_successful}/{summary.total_tasks} succeeded")
    """

    def __init__(
        self,
        executor: BatchExecutor,
        config: EvolutionConfig,
        task_family: str,
        skills_dir: Path,
        *,
        policy: BatchPolicy | None = None,
        min_occurrences: int = 3,
        verbose: bool = True,
        method_adapter = None,  # Table2 method adapter
    ):
        self._executor = executor
        self._config = config
        self._task_family = task_family
        self._skills_dir = Path(skills_dir)
        self._policy = policy or EvolutionPolicy()
        self._min_occurrences = min_occurrences
        self._verbose = verbose
        self._method_adapter = method_adapter  # Store Table2 adapter
        self._skills_dir.mkdir(parents=True, exist_ok=True)
        self._current_version = initialize_skill_version_store(
            self._skills_dir,
            task_family=self._task_family,
        )
        self._runner = BatchTaskRunner(
            executor=executor,
            config=config,
            task_family=task_family,
            skills_dir=self._skills_dir,
            verbose=verbose,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, tasks: list[TaskRef]) -> LoopSummary:
        """Run the full batch loop over *tasks*.

        Each epoch shuffles the training tasks with the configured seed, then
        pulls them in batches of ``config.batch_size``. Failed trials are
        retried with LLM reflection up to ``config.max_retries`` times. After
        each batch, the configured policy may publish a version for the next
        batch or epoch to use.

        Always writes ``summary.json``, even when the loop is interrupted
        or Harbour fails partway through.
        """
        reports: list[ExplorationReport] = []
        batches_without_success = 0
        batch_metrics_history: list[dict[str, Any]] = []
        version_history: list[dict[str, Any]] = []
        batch_rounds: list[BatchRound] = []
        total_successful = 0
        total_failed = 0
        epoch_metrics: list[dict[str, Any]] = []
        final_epoch_successful = 0
        final_epoch_failed = 0

        for epoch_index in range(1, self._config.train_epochs + 1):
            epoch_tasks = list(tasks)
            random.Random(self._config.train_shuffle_seed + epoch_index).shuffle(epoch_tasks)
            epoch_successful = 0
            epoch_failed = 0
            if self._verbose:
                print(
                    f"\n[BatchLoop] Epoch {epoch_index}/{self._config.train_epochs}: "
                    f"{len(epoch_tasks)} training task(s)"
                )

            for round_info, pending in self._runner.iter_rounds(
                epoch_tasks,
                epoch_index=epoch_index,
            ):
                batch_rounds.append(round_info)
                epoch_successful += len(round_info.successful)
                epoch_failed += len(round_info.failed)

                # Update Table2 method memory after batch completes
                if self._method_adapter:
                    self._update_method_memory(round_info.results)

                outcome = self._policy.on_batch_complete(self, round_info, pending)
                report = outcome.get("evolve_report")
                if report is not None:
                    reports.append(report)
                metrics = outcome.get("batch_metrics")
                if metrics is not None:
                    metrics["epoch_index"] = epoch_index
                    metrics["batch_index"] = round_info.batch_index
                    batch_metrics_history.append(metrics)
                promoted = outcome.get("promoted_version")
                if promoted is not None:
                    self._current_version = promoted
                version_history.append(
                    {
                        "epoch_index": epoch_index,
                        "batch_index": round_info.batch_index,
                        "snapshot_version": round_info.snapshot.version_label,
                        "snapshot_hash": round_info.snapshot.content_hash,
                        "promotion_decision": outcome.get("promotion_decision", "unchanged"),
                        "promoted_version": getattr(promoted, "version_label", None),
                        "promoted_hash": getattr(promoted, "content_hash", None),
                        "batch_summary_path": str(round_info.batch_summary_path)
                        if round_info.batch_summary_path
                        else None,
                    }
                )
                batches_without_success += int(
                    outcome.get("batches_without_success_increment", 0)
                )

            total_successful += epoch_successful
            total_failed += epoch_failed
            final_epoch_successful = epoch_successful
            final_epoch_failed = epoch_failed
            epoch_metrics.append(
                {
                    "epoch_index": epoch_index,
                    "success_count": epoch_successful,
                    "failure_count": epoch_failed,
                    "success_rate": round(epoch_successful / len(tasks), 4) if tasks else 0.0,
                }
            )

        final_version = freeze_final_version(self._skills_dir, self._current_version)
        tasks_using_evolved_version = sum(
            len(round_info.batch_tasks)
            for round_info in batch_rounds
            if round_info.snapshot.version_label != "v000"
        )
        summary = LoopSummary(
            task_family=self._task_family,
            total_tasks=len(tasks),
            train_epochs=self._config.train_epochs,
            total_task_executions=len(tasks) * self._config.train_epochs,
            batches_run=len(batch_rounds),
            total_successful=total_successful,
            total_failed=total_failed,
            final_epoch_successful=final_epoch_successful,
            final_epoch_failed=final_epoch_failed,
            batches_without_success=batches_without_success,
            evolve_reports=reports,
            batch_metrics_history=batch_metrics_history,
            initial_version="v000",
            final_version=final_version.version_label,
            final_hash=final_version.content_hash,
            tasks_using_evolved_version=tasks_using_evolved_version,
            batch_rounds=batch_rounds,
            version_history=version_history,
            epoch_metrics=epoch_metrics,
        )
        self._write_summary(summary)
        return summary



    # ------------------------------------------------------------------
    # Table2 integration
    # ------------------------------------------------------------------

    def _update_method_memory(self, results: list[TrialResult]) -> None:
        """Update Table2 method memory after a batch completes."""
        if not self._method_adapter:
            return

        for result in results:
            # Read trace if available
            trace_content = ""
            if result.trajectory_path and result.trajectory_path.is_file():
                try:
                    trace_content = result.trajectory_path.read_text(encoding="utf-8")
                except Exception:
                    pass

            # Detect replans (use retries_used as proxy)
            replans = getattr(result, "retries_used", 0)

            # Build task result for method update
            task_result = {
                "task_name": result.task_name,
                "success": result.success,
                "trace": trace_content,
                "exception_info": result.exception_info,
                "replans": replans,
            }

            # Update method memory
            try:
                self._method_adapter.post_task_update(task_result)
            except Exception as exc:
                if self._verbose:
                    print(f"[Table2] Warning: Failed to update memory for {result.task_name}: {exc}")


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stage_batch_outcomes(round_info: BatchRound) -> Path:
        """Stage every task attempt so discovery can learn from failed retries."""
        staged = round_info.round_dir / "evolution" / "staged_batch"
        if staged.exists():
            shutil.rmtree(staged)
        staged.mkdir(parents=True, exist_ok=True)

        staged_attempts: list[dict[str, Any]] = []
        for task, result in zip(round_info.batch_tasks, round_info.results):
            task_dir = staged / task.name
            attempts_dir = task_dir / "attempts"
            attempts_dir.mkdir(parents=True)
            attempts = result.attempts or [
                TrialAttempt(
                    number=1,
                    trial_name=result.trial_name,
                    trial_dir=result.trial_dir,
                    success=result.success,
                    reward=result.reward,
                    exception_info=result.exception_info,
                    trajectory_path=result.trajectory_path,
                    outcome=result.outcome,
                )
            ]
            manifest_attempts: list[dict[str, Any]] = []
            for attempt in attempts:
                destination = attempts_dir / f"attempt_{attempt.number:02d}"
                skipped_unreadable: list[str] = []
                if attempt.trial_dir.exists():
                    skipped_unreadable = _copy_trial_tree(attempt.trial_dir, destination)
                    if skipped_unreadable:
                        print(
                            f"[BatchLoop]   Skipped unreadable artifacts for "
                            f"{task.name} attempt {attempt.number}: "
                            f"{', '.join(skipped_unreadable)}"
                        )
                else:
                    destination.mkdir()
                reflection_files = sorted(
                    path.name for path in destination.glob("reflection_attempt_*.md")
                )
                entry = {
                    "task_name": task.name,
                    "number": attempt.number,
                    "success": attempt.success,
                    "reward": attempt.reward,
                    "exception_info": attempt.exception_info,
                    "final": attempt.number == attempts[-1].number,
                    "reflection_files": reflection_files,
                    "skipped_unreadable_artifacts": skipped_unreadable,
                    "outcome": outcome_digest(attempt.outcome),
                    "trajectory_available": any(
                        path.is_file()
                        for path in (
                            destination / "agent" / "trajectory.json",
                            destination / "agent" / "claude-code.txt",
                            destination / "agent" / "claude_code.txt",
                            destination / "sessions" / "agent.log",
                        )
                    ),
                }
                manifest_attempts.append({key: value for key, value in entry.items() if key != "task_name"})
                staged_attempts.append(entry)
            (task_dir / "attempt_manifest.json").write_text(
                json.dumps({"task_name": task.name, "attempts": manifest_attempts}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        (staged / "batch_evidence.json").write_text(
            json.dumps(
                {
                    "positive_anchors": sum(item["success"] for item in staged_attempts),
                    "failure_attempts": sum(not item["success"] for item in staged_attempts),
                    "missing_trajectory_attempts": sum(
                        not item["success"] and not item["trajectory_available"]
                        for item in staged_attempts
                    ),
                    "skipped_unreadable_artifacts": sum(
                        len(item["skipped_unreadable_artifacts"])
                        for item in staged_attempts
                    ),
                    "attempts": staged_attempts,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if round_info.batch_summary_path and round_info.batch_summary_path.is_file():
            shutil.copy2(round_info.batch_summary_path, staged / "batch_summary.json")
        return staged

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_batch_metrics(results: list[TrialResult]) -> dict[str, Any]:
        """Compute exploration metrics for a batch of trial results."""
        if not results:
            return {}
        success_count = sum(1 for r in results if r.success)
        return {
            "num_results": len(results),
            "success_count": success_count,
            "success_rate": round(success_count / len(results), 4),
            "failure_count": len(results) - success_count,
            "total_retries": sum(r.retries_used for r in results),
        }

    @staticmethod
    def _check_degradation(
        prev_metrics: dict[str, Any],
        curr_metrics: dict[str, Any],
        threshold: float = 0.20,
    ) -> dict[str, Any]:
        """Check if skill evolution degraded performance."""
        issues: list[str] = []
        for key, worse_is_lower in [("success_rate", True)]:
            prev_val = prev_metrics.get(key, 0)
            curr_val = curr_metrics.get(key, 0)
            if prev_val == 0:
                continue
            delta = (curr_val - prev_val) / prev_val
            if worse_is_lower and delta < -threshold:
                issues.append(f"{key} dropped {abs(delta):.0%} ({prev_val:.3f} → {curr_val:.3f})")
            elif not worse_is_lower and delta > threshold:
                issues.append(f"{key} increased {delta:.0%} ({prev_val:.1f} → {curr_val:.1f})")

        for key in ["total_retries"]:
            prev_val = prev_metrics.get(key, 0)
            curr_val = curr_metrics.get(key, 0)
            if prev_val == 0:
                continue
            prev_avg = prev_val / max(1, prev_metrics.get("num_results", 1))
            curr_avg = curr_val / max(1, curr_metrics.get("num_results", 1))
            if prev_avg > 0:
                delta = (curr_avg - prev_avg) / prev_avg
                if delta > threshold:
                    issues.append(f"avg {key} increased {delta:.0%} ({prev_avg:.1f} → {curr_avg:.1f})")

        severity = "critical" if len(issues) >= 2 else "warning" if issues else "none"
        return {"degraded": len(issues) > 0, "issues": issues, "severity": severity}

    @staticmethod
    def _backup_skill(skills_dir: Path, backup_dir: Path) -> bool:
        """Backup current skill before evolving. Returns True on success."""
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            if skills_dir.exists() and any(skills_dir.iterdir()):
                shutil.copytree(skills_dir, backup_dir, symlinks=True)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _rollback_skill(skills_dir: Path, backup_dir: Path) -> bool:
        """Restore previous skill version from backup. Returns True on success."""
        try:
            if backup_dir.exists() and any(backup_dir.iterdir()):
                shutil.rmtree(skills_dir, ignore_errors=True)
                shutil.copytree(backup_dir, skills_dir, symlinks=True)
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def _write_summary(self, summary: LoopSummary) -> None:
        """Write ``summary.json`` at the top of the job directory."""
        import json

        job_dir = self._skills_dir.parent
        last_report = summary.evolve_reports[-1] if summary.evolve_reports else None

        data = {
            "task_family": self._task_family,
            "total_tasks": summary.total_tasks,
            "train_epochs": summary.train_epochs,
            "total_task_executions": summary.total_task_executions,
            "batches_run": summary.batches_run,
            "successful": summary.total_successful,
            "failed": summary.total_failed,
            "final_epoch_successful": summary.final_epoch_successful,
            "final_epoch_failed": summary.final_epoch_failed,
            "all_successful": summary.all_successful,
            "written_at": datetime.now(UTC).isoformat(),
            "initial_version": summary.initial_version,
            "final_version": summary.final_version,
            "final_hash": summary.final_hash,
            "tasks_using_evolved_version": summary.tasks_using_evolved_version,
            "version_history": summary.version_history,
            "epoch_metrics": summary.epoch_metrics,
        }
        if last_report:
            data["skills"] = {
                "capabilities": last_report.num_capabilities,
                "active_capabilities": last_report.num_active_capabilities,
                "summary": last_report.summary,
            }
            data["memory"] = {
                "store": str(self._skills_dir / MEMORY_STORE_FILENAME),
                "retrievable_memories": last_report.num_residual_memories,
                "skill_factored_memories": last_report.num_compiled_memories,
                "access": "read_only_mcp",
            }
        elif summary.batches_without_success > 0 and summary.batches_run > 0:
            data["skills"] = {
                "status": "diagnostics_only",
                "reason": "No successful sub-operation was found; failure evidence retained for validation.",
            }
        elif summary.batches_run == 0:
            data["skills"] = {
                "status": "not_started",
                "reason": "No batches were executed",
            }

        degradations_detected = 0
        rollbacks_applied = 0
        for report in summary.evolve_reports:
            if report.degradation_warning and report.degradation_warning.get("degraded"):
                degradations_detected += 1
            if report.rollback_applied:
                rollbacks_applied += 1

        data["evaluation"] = {
            "degradations_detected": degradations_detected,
            "rollbacks_applied": rollbacks_applied,
            "batches_evaluated": len(summary.evolve_reports),
        }
        if summary.batch_metrics_history:
            data["evaluation"]["batch_metrics"] = summary.batch_metrics_history
            rates = [m.get("success_rate", 0) for m in summary.batch_metrics_history if "success_rate" in m]
            if len(rates) >= 2:
                trend = "improving" if rates[-1] > rates[0] else "degrading" if rates[-1] < rates[0] else "stable"
                data["evaluation"]["trend"] = trend

        (job_dir / "summary.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
