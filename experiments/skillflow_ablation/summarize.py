#!/usr/bin/env python3
"""Summarize SkillFlow ablation outputs into JSON/CSV-friendly records."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evolution.trajectory_loader import load_trajectories


def _load(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _iter_family_dirs(variant_dir: Path):
    for summary_path in sorted(variant_dir.glob("*/summary.json")):
        summary = _load(summary_path)
        if summary is not None:
            yield summary_path.parent, summary


def _test_accuracy(family_dir: Path, summary: dict[str, Any]) -> float | None:
    records = []
    for result_path in family_dir.glob("test/**/result.json"):
        result = _load(result_path)
        if not result:
            continue
        reward = result.get("verifier_result", {}).get("rewards", {}).get("reward")
        if isinstance(reward, (int, float)):
            records.append(float(reward) >= 1.0)
    if not records:
        return None
    return sum(records) / len(records)


def _lineage_metrics(family_dir: Path) -> dict[str, int | float]:
    exposures = reused = successful_reuses = active_reuses = failed_active_reuses = same_batch = 0
    staged_dirs = sorted(family_dir.glob("train/**/evolution/staged_batch"))
    for staged in staged_dirs:
        batch_dir = staged.parent.parent
        lineage = _load(batch_dir / "skills_snapshot" / ".evolution" / "lineage.json") or {}
        raw_policies = lineage.get("policies", {})
        policies = raw_policies if isinstance(raw_policies, dict) else {}
        slugs = {
            str(policy.get("slug")): policy
            for policy in policies.values()
            if isinstance(policy, dict) and policy.get("slug")
        }
        active_slugs = {slug for slug, policy in slugs.items() if policy.get("status") == "active"}
        candidate_lineage = _load(batch_dir / "evolution" / "candidate" / ".evolution" / "lineage.json") or {}
        candidate_policies = candidate_lineage.get("policies", {})
        candidate_slugs = {
            str(policy.get("slug"))
            for policy in candidate_policies.values()
            if isinstance(policy, dict) and policy.get("slug")
        } if isinstance(candidate_policies, dict) else set()
        newly_induced = candidate_slugs - set(slugs)
        for trace in load_trajectories(staged):
            if slugs:
                exposures += 1
            used = set(trace.get("used_policy_ids", []))
            same_batch += len(used & newly_induced)
            matched = used & set(slugs)
            for _slug in matched:
                reused += 1
                if trace.get("verifier_passed"):
                    successful_reuses += 1
                if _slug in active_slugs:
                    active_reuses += 1
                    if not trace.get("verifier_passed"):
                        failed_active_reuses += 1
    return {
        "policy_exposures": exposures,
        "explicit_reuses": reused,
        "active_reuses": active_reuses,
        "failed_active_reuses": failed_active_reuses,
        "false_promotion_rate": (failed_active_reuses / active_reuses) if active_reuses else None,
        "same_batch_exposure": same_batch,
        "_successful_reuses": successful_reuses,
    }


def summarize(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for family_dir, summary in _iter_family_dirs(variant_dir):
            metrics = _lineage_metrics(family_dir)
            rows.append({
                "variant": variant_dir.name,
                "family": summary.get("task_family", family_dir.name),
                "heldout_accuracy": _test_accuracy(family_dir, summary),
                "train_final_accuracy": (
                    summary.get("final_epoch_successful", 0) / summary.get("total_tasks", 1)
                    if summary.get("total_tasks") else None
                ),
                "reuse_success": (
                    metrics["_successful_reuses"] / metrics["explicit_reuses"]
                    if metrics["explicit_reuses"] else None
                ),
                **{key: value for key, value in metrics.items() if not key.startswith("_")},
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("runs/skillflow-ablation"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    rows = summarize(args.root.expanduser().resolve())
    payload = json.dumps(rows, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload)
    if args.output and args.output.suffix.lower() == ".csv":
        fields = sorted({key for row in rows for key in row})
        with args.output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
