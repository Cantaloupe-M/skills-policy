"""Dataset-independent configuration for the skill-evolution method."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionConfig:
    """Parameters that define skill-evolution behavior across benchmarks."""

    min_reward: float = 1.0
    demotion_threshold: int = 2
    provider: str | None = None
    model: str | None = None
    # Batch / retry controls
    batch_size: int = 0
    """Accumulate N trial outcomes before flushing through the engine.
    ``0`` or ``1`` means immediate processing (no batching).  Values ≥ 2
    defer evolution until at least *batch_size* outcomes are buffered.
    """
    max_evolution_workers: int = 4
    """Maximum worker threads for parallel batch processing.  When
    *batch_size* ≥ 2, buffered outcomes are processed concurrently
    with up to this many threads.  Set to ``1`` for serial processing.
    ``0`` uses the default (4).
    """
    max_retries: int = 3
    """Maximum total task attempts, including the initial attempt.

    The historical field name is retained for compatibility, but this value is
    an *attempt* budget: ``3`` permits attempts 1, 2, and 3, with reflection
    before every attempt after the first. ``0`` keeps the legacy one-attempt
    behavior for callers that explicitly disable retries.
    """
    train_epochs: int = 1
    """Number of full, shuffled passes over each family's training tasks."""
    train_shuffle_seed: int = 0
    """Base seed used to deterministically reshuffle tasks for every epoch."""
    min_occurrences: int = 3
    """Distinct-task support required before a candidate cluster is published."""
    # Mechanism switches used by controlled ablations.
    include_failure_evidence: bool = True
    strict_cross_task: bool = True
    require_policy_use: bool = True
    immediate_promotion: bool = False

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.batch_size < 0:
            raise ValueError("batch_size must be non-negative")
        if self.train_epochs < 1:
            raise ValueError("train_epochs must be at least 1")
        if self.min_occurrences < 1:
            raise ValueError("min_occurrences must be at least 1")

    @property
    def max_attempts(self) -> int:
        """Return the resolved total-attempt budget."""
        return max(self.max_retries, 1)

    @property
    def retry_budget(self) -> int:
        """Return the number of reflection-guided attempts after attempt one."""
        return self.max_attempts - 1
