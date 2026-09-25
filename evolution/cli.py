"""Shared command-line options for the evolution method and runner."""

from __future__ import annotations

import argparse
from pathlib import Path

from evolution.config import EvolutionConfig


def add_evolution_arguments(parser: argparse.ArgumentParser) -> None:
    """Add method-level evolution arguments to a benchmark entrypoint."""
    parser.add_argument(
        "--initialization",
        choices=("task-derived", "scaffold"),
        default="task-derived",
        help=(
            "Initial v000 skill source. 'task-derived' synthesizes v000 from "
            "training task contracts; 'scaffold' uses the fixed generic scaffold "
            "and does not read training task content during initialization."
        ),
    )
    parser.add_argument("--min-reward", type=float, default=1.0)
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=3,
        help="Distinct-task support threshold for reusable evidence (default: 3).",
    )
    parser.add_argument(
        "--demotion-threshold",
        type=int,
        default=2,
        help="Consecutive compiled failures needed for demotion",
    )
    parser.add_argument("--evolution-provider", choices=["anthropic", "openai"], default=None)
    parser.add_argument("--evolution-model", default=None)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Accumulate N trial outcomes before flushing through the evolution engine. "
             "0 or 1 = immediate processing (default: 0).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum total attempts per failed task, including the initial attempt. "
             "0 = one attempt with retries disabled; 3 = at most three attempts "
             "with reflection after failures (default: 3).",
    )
    parser.add_argument(
        "--train-epochs",
        type=int,
        default=2,
        help="Full shuffled passes over each family's training tasks (default: 1).",
    )
    parser.add_argument(
        "--train-shuffle-seed",
        type=int,
        default=0,
        help="Base seed for deterministic per-epoch task shuffling (default: 0).",
    )
    parser.add_argument(
        "--max-evolution-workers",
        type=int,
        default=3,
        help="Maximum worker threads for parallel batch processing. "
             "When batch_size ≥ 2, buffered outcomes are processed concurrently "
             "with up to this many threads. Set to 1 for serial (default: 4).",
    )
    parser.add_argument(
        "--failure-evidence", choices=("on", "off"), default="on",
        help="Whether unresolved failure evidence can induce experimental recovery policies.",
    )
    parser.add_argument(
        "--qualification", choices=("strict-cross-task", "outcome-only"),
        default="strict-cross-task",
        help="Qualification policy for promoting experimental procedures.",
    )
    parser.add_argument(
        "--promotion", choices=("delayed", "immediate"), default="delayed",
        help="Whether policies require downstream reuse before activation.",
    )


def evolution_config_from_args(args: argparse.Namespace) -> EvolutionConfig:
    """Build the shared method configuration from parsed arguments."""
    return EvolutionConfig(
        min_reward=getattr(args, "min_reward", 1.0),
        demotion_threshold=getattr(args, "demotion_threshold", 2),
        provider=getattr(args, "evolution_provider", None),
        model=getattr(args, "evolution_model", None),
        batch_size=getattr(args, "batch_size", 0),
        max_evolution_workers=getattr(args, "max_evolution_workers", 4),
        max_retries=getattr(args, "max_retries", 3),
        train_epochs=getattr(args, "train_epochs", 1),
        train_shuffle_seed=getattr(args, "train_shuffle_seed", 0),
        min_occurrences=getattr(args, "min_occurrences", 3),
        include_failure_evidence=getattr(args, "failure_evidence", "on") == "on",
        strict_cross_task=getattr(args, "strict_cross_task", True),
        require_policy_use=getattr(args, "qualification", "strict-cross-task") != "outcome-only",
        immediate_promotion=getattr(args, "promotion", "delayed") == "immediate",
    )


# ---------------------------------------------------------------------------
# Experiment protocol arguments (Phase 0-3 protocol)
# ---------------------------------------------------------------------------

def add_experiment_arguments(parser: argparse.ArgumentParser) -> None:
    """Add experiment protocol CLI arguments for the multi-phase protocol."""
    parser.add_argument(
        "--acquisition-ratio",
        type=float,
        default=0.4,
        help="Fraction of tasks per family used for skill acquisition (default: 0.4)",
    )
    parser.add_argument(
        "--probe-interval",
        type=int,
        default=5,
        help="Evaluate probe set every k tasks in Phase 3 (default: 5)",
    )
    parser.add_argument(
        "--probe-count",
        type=int,
        default=2,
        help="Number of probe tasks reserved per family (default: 2)",
    )
    parser.add_argument(
        "--family-mapping",
        type=Path,
        default=None,
        dest="family_mapping_path",
        help="Path to JSON file with manual family overrides",
    )
    parser.add_argument(
        "--conditions",
        type=str,
        default="base,memory,summary,executable",
        help="Comma-separated list of conditions for Phase 2 deployment "
             "(default: base,memory,summary,executable)",
    )
    parser.add_argument(
        "--skills-snapshot",
        type=Path,
        default=None,
        dest="skills_snapshot_path",
        help="Path to frozen skill library snapshot for Phase 2 resume",
    )
