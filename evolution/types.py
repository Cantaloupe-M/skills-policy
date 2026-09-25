"""Small data model for exploration-aware skill evolution.

The method has three evidence units:

* :class:`ExplorationTrace` records one verifier-labelled trial.
* :class:`BottleneckCandidate` records a reusable local failure pattern.

Candidates are published according to their direct evidence label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

CandidateKind = Literal["recovery_candidate", "atomic_substep", "workflow"]
EvidenceSource = Literal["trajectory", "reflection"]


@dataclass
class ToolCallStep:
    step_index: int
    tool_name: str
    command: str = ""
    description: str = ""
    input_files: list[str] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    success: bool | None = None
    error_message: str = ""
    exit_code: int | None = None
    duration_ms: int | None = None


@dataclass
class ThinkingSegment:
    step_indices: tuple[int, int]
    text: str = ""
    suggests_retry: bool = False
    mentions_fix: bool = False
    mentions_alternative: bool = False


@dataclass
class ErrorEvent:
    step_index: int
    tool_name: str
    error_message: str
    error_type: str = ""


@dataclass
class FileArtifact:
    path: str
    ext: str
    role: str = "intermediate"
    first_seen_at_step: int = 0
    last_seen_at_step: int = 0
    produced_by_steps: list[int] = field(default_factory=list)
    consumed_by_steps: list[int] = field(default_factory=list)
    size_bytes: int | None = None


@dataclass
class ExplorationTrace:
    task_name: str = ""
    task_family: str = ""
    attempt_id: str = ""
    attempt_number: int = 1
    verifier_passed: bool = False
    reward: float | None = None
    used_skill_ids: list[str] = field(default_factory=list)
    used_policy_ids: list[str] = field(default_factory=list)
    used_implementation_ids: list[str] = field(default_factory=list)
    used_script_ids: list[str] = field(default_factory=list)
    used_memory_ids: list[str] = field(default_factory=list)
    memory_query_count: int = 0
    raw_steps: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[ToolCallStep] = field(default_factory=list)
    thinking_segments: list[ThinkingSegment] = field(default_factory=list)
    errors: list[ErrorEvent] = field(default_factory=list)
    file_artifacts: list[FileArtifact] = field(default_factory=list)
    reusable_substeps: list[ReusableSubstep] = field(default_factory=list)
    # Reflection is produced for a failed attempt and is evidence for the
    # correction used by a subsequent retry.  Keep it on the trace so the
    # evolution stage can associate the memory with verifier outcomes.
    reflection: str = ""
    reflection_files: list[str] = field(default_factory=list)
    reflection_verified_by_retry: bool = False
    reflection_retry_outcome: Literal["success", "failure", "missing"] = "missing"
    retry_transition: dict[str, Any] = field(default_factory=dict)
    reflection_source_attempt: int | None = None

    @property
    def failed_tool_calls(self) -> int:
        return sum(call.success is False for call in self.tool_calls)

    @property
    def artifact_revisits(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for call in self.tool_calls:
            for name in {Path(path).name.lower() for path in call.input_files + call.output_files}:
                counts[name] = counts.get(name, 0) + 1
        return {name: count for name, count in counts.items() if count >= 2}


@dataclass
class NormalizedTraceEvent:
    idx: int
    trace_index: int = 0
    role: str = "tool"
    event_type: str = "tool_call"
    tool_name: str = ""
    raw_text: str = ""
    normalized_action: str = "other_tool"
    target: str | None = None
    signature_token: str = ""
    success: bool | None = None
    error_type: str = ""
    cost: float = 1.0


@dataclass
class ReusableSubstep:
    """A parameterized atomic operation mined from a successful trajectory."""

    step_indices: tuple[int, ...] = ()
    kind: str = "atomic"
    action: str = ""
    tool_name: str = ""
    target: str | None = None
    signature: str = ""
    command_shape: str = ""
    input_formats: tuple[str, ...] = ()
    output_formats: tuple[str, ...] = ()


@dataclass
class FailedAttempt:
    step_index: int
    tool_name: str
    command: str
    error_message: str
    error_type: str = ""


@dataclass
class BottleneckCandidate:
    """A reusable local failure pattern with evidence from one task attempt."""

    candidate_id: str
    task_name: str
    task_family: str
    step_range: tuple[int, int]
    failed_attempts: list[FailedAttempt]
    winning_command: str
    winning_tool: str
    exploration_cost: int
    artifact_paths: list[str] = field(default_factory=list)
    intent: str = ""
    obstacle: str = ""
    resolution: str = ""
    evidence_label: str = "unresolved_failure"
    substep: ReusableSubstep | None = None
    candidate_kind: CandidateKind = "recovery_candidate"
    evidence_source: EvidenceSource = "trajectory"
    retry_outcome: Literal["success", "failure", "missing"] | None = None
    retry_transition: dict[str, Any] = field(default_factory=dict)

    @property
    def dead_ends(self) -> list[str]:
        return list(
            dict.fromkeys(
                attempt.command or attempt.error_message
                for attempt in self.failed_attempts
                if attempt.command or attempt.error_message
            )
        )


@dataclass
class CapabilityCluster:
    capability_id: str
    intent: str
    obstacle: str
    candidates: list[BottleneckCandidate] = field(default_factory=list)
    grouping_algorithm: str = "semantic-v2"
    candidate_kind: CandidateKind = "recovery_candidate"

    @property
    def support(self) -> int:
        return len({candidate.task_name for candidate in self.candidates})

    @property
    def resolutions(self) -> list[str]:
        return list(dict.fromkeys(candidate.resolution for candidate in self.candidates if candidate.resolution))

    @property
    def commands(self) -> list[str]:
        return list(dict.fromkeys(candidate.winning_command for candidate in self.candidates if candidate.winning_command))


@dataclass
class ExplorationReport:
    task_family: str = ""
    num_trials: int = 0
    num_bottlenecks_detected: int = 0
    num_capabilities: int = 0
    num_active_capabilities: int = 0
    num_skills_updated: int = 0
    num_failure_diagnostics: int = 0
    num_missing_trajectory_attempts: int = 0
    publication_block_reason: str | None = None
    skill_dir: str = ""
    skill_md_path: str = ""
    summary: str = ""
    degradation_warning: dict[str, Any] | None = None
    rollback_applied: bool = False
    compiled_memory_ids: list[str] = field(default_factory=list)
    num_residual_memories: int = 0
    num_compiled_memories: int = 0


@dataclass
class ExplorationMetrics:
    task_name: str = ""
    with_skill: bool = False
    failed_attempts: int = 0
    total_tool_calls: int = 0
    final_success: bool = False
