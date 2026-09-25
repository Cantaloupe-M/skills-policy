#!/usr/bin/env python3
"""Audit whether evolved policies look spontaneous or exploration-induced.

This is intentionally an offline, read-only diagnostic.  It consumes an existing
run directory and writes a CSV/JSON report; it never calls an LLM or edits skills.
The labels are heuristic suggestions for human review, not claims of causality.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

LABELS = ("spontaneous", "exploration-induced", "task-specific", "ambiguous")
CSV_FIELDS = [
    "candidate_rank",
    "policy_id",
    "policy_name",
    "policy_status",
    "first_policy_version",
    "family",
    "origin_tasks",
    "observed_tasks",
    "subsequent_tasks",
    "adopted_tasks",
    "first_occurrence",
    "first_attempt_occurrence",
    "later_successful_occurrence",
    "origin_attempts",
    "origin_final_successes",
    "subsequent_final_successes",
    "origin_retry_mean",
    "subsequent_retry_mean",
    "retry_delta",
    "heuristic_label",
    "label_confidence",
    "human_label",
    "evidence",
    "review_notes",
]


def task_fingerprint(task_name: str) -> str:
    return hashlib.sha256(task_name.encode("utf-8")).hexdigest()[:16]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def _tokens(text: str) -> set[str]:
    return {
        x
        for x in re.findall(r"[a-z][a-z0-9-]{2,}", text.casefold())
        if x
        not in {
            "when",
            "use",
            "this",
            "task",
            "with",
            "from",
            "that",
            "into",
            "must",
            "should",
            "before",
            "after",
            "only",
            "required",
            "output",
            "input",
        }
    }


def _trajectory_text(trial: dict[str, Any]) -> str:
    return json.dumps(trial.get("raw_steps", trial.get("trajectory", [])), ensure_ascii=False)


def _occurs(policy: dict[str, Any], trial: dict[str, Any]) -> tuple[bool, str]:
    used = {str(x).casefold() for x in trial.get("used_policy_ids", []) + trial.get("used_policy_slugs", [])}
    pid = str(policy.get("policy_id", "")).casefold()
    slug = str(policy.get("slug", "")).casefold()
    if pid in used or slug in used:
        return True, "explicit_policy_use"
    text = _trajectory_text(trial).casefold()
    text_tokens = _tokens(text)
    observed = policy.get("observed_substeps", []) or []
    for item in observed:
        if not isinstance(item, dict):
            continue
        words = _tokens(str(item.get("command_shape", "")))
        distinctive = {word for word in words if word not in {"python", "python3", "import", "print", "open", "path", "artifact", "num"}}
        overlap = len(distinctive & text_tokens) / max(1, len(distinctive))
        if len(distinctive & text_tokens) >= 3 and overlap >= 0.30:
            return True, f"command_shape_overlap_{overlap:.2f}"
    # Policy prose is deliberately not matched against trajectories: generic
    # words such as validate/inspect otherwise make nearly every attempt occur.
    return False, "none"


def _load_attempts(run_dir: Path) -> list[dict[str, Any]]:
    """Load staged attempts, preferring one record per task/attempt number."""
    attempts: dict[tuple[str, int, str], dict[str, Any]] = {}
    for manifest_path in run_dir.glob("**/evolution/staged_batch/*/attempt_manifest.json"):
        task_dir = manifest_path.parent
        manifest = _read_json(manifest_path, {})
        task_name = str(manifest.get("task_name") or task_dir.name)
        batch_summary = _read_json(task_dir.parent / "batch_summary.json", {})
        snapshot = str(batch_summary.get("snapshot_version", ""))
        for item in manifest.get("attempts", []) if isinstance(manifest.get("attempts"), list) else []:
            if not isinstance(item, dict):
                continue
            number = int(item.get("number", 0) or 0)
            attempt_dir = task_dir / "attempts" / f"attempt_{number:02d}"
            raw = None
            trajectory = attempt_dir / "agent" / "trajectory.json"
            if trajectory.is_file():
                payload = _read_json(trajectory, {})
                raw = payload.get("steps", []) if isinstance(payload, dict) else []
            if raw is None:
                for candidate in ("claude-code.txt", "claude_code.txt"):
                    path = attempt_dir / "agent" / candidate
                    if path.is_file():
                        raw = path.read_text(encoding="utf-8", errors="replace")
                        break
            if raw is None:
                raw = []
            text = json.dumps(raw, ensure_ascii=False) if not isinstance(raw, str) else raw
            used = re.findall(r"references/(?:policies/)?([a-z0-9][a-z0-9-]+)\.md", text, re.I)
            used += re.findall(r"(?:\.claude|\.codex|\.agents)/skills/([a-z0-9][a-z0-9-]+)/SKILL\.md", text, re.I)
            record = {
                "task_name": task_name,
                "attempt_number": number,
                "success": bool(item.get("success", False)),
                "reward": item.get("reward"),
                "retries": max(0, number - 1),
                "snapshot": snapshot,
                "used_policy_ids": list(dict.fromkeys(used)),
                "raw_steps": raw,
            }
            key = (task_name, number, snapshot)
            attempts[key] = record
    return sorted(attempts.values(), key=lambda x: (x["task_name"], x["attempt_number"], x["snapshot"]))


def _final_lineage(run_dir: Path) -> tuple[Path | None, dict[str, Any]]:
    candidates = sorted(run_dir.glob("skill_versions/final/.evolution/lineage.json"))
    if not candidates:
        candidates = sorted(run_dir.glob("**/skill_versions/final/.evolution/lineage.json"))
    path = candidates[0] if candidates else None
    return path, _read_json(path, {}) if path else {}


def _version_number(value: str) -> int | None:
    match = re.fullmatch(r"v(\d+)", str(value or ""))
    return int(match.group(1)) if match else None


def _policy_first_versions(run_dir: Path) -> dict[str, str]:
    first: dict[str, tuple[int, str]] = {}
    for path in run_dir.glob("skill_versions/v*/.evolution/lineage.json"):
        version = path.parents[1].name
        number = _version_number(version)
        if number is None:
            continue
        lineage = _read_json(path, {})
        for policy_id in lineage.get("policies") or {}:
            current = first.get(policy_id)
            if current is None or number < current[0]:
                first[policy_id] = (number, version)
    return {policy_id: value[1] for policy_id, value in first.items()}


def _classify(
    policy: dict[str, Any],
    groups: dict[str, list[dict[str, Any]]],
    origin_names: set[str],
    first_policy_version: str | None,
) -> tuple[str, dict[str, Any]]:
    all_rows = [row for rows in groups.values() for row in rows]
    first_version_number = _version_number(first_policy_version or "")
    origin_rows = [
        row
        for name in origin_names
        for row in groups.get(name, [])
        if first_version_number is None
        or (_version_number(row.get("snapshot", "")) is not None and _version_number(row.get("snapshot", "")) < first_version_number)
    ]
    origin_rows.sort(key=lambda x: x["attempt_number"])
    origin_all = origin_rows
    first_rows = [row for row in origin_all if row["attempt_number"] == 1]
    first_occurs = [row for row in first_rows if row["occurs"]]
    later_success = [row for row in origin_all if row["attempt_number"] > 1 and row["occurs"] and row["success"]]
    improved_tasks = {
        row["task_name"]
        for row in later_success
        if any(
            prev["task_name"] == row["task_name"] and not prev["success"] and prev["attempt_number"] < row["attempt_number"]
            for prev in origin_all
        )
    }
    observed_tasks = {row["task_name"] for row in all_rows if row["occurs"]}
    subsequent = [
        row
        for row in all_rows
        if first_version_number is not None
        and _version_number(row.get("snapshot", "")) is not None
        and _version_number(row.get("snapshot", "")) >= first_version_number
    ]
    adopted = [row for row in subsequent if row["occurs"] and row["attempt_number"] == 1]
    labels = {str(item.get("label", "")) for item in policy.get("observations", []) if isinstance(item, dict)}
    has_matchable_evidence = bool(policy.get("observed_substeps")) or any(row["occurrence_signal"] == "explicit_policy_use" for row in all_rows)
    if not origin_names or first_version_number is None or not has_matchable_evidence:
        label = "ambiguous"
        confidence = "low"
    elif later_success and improved_tasks and not first_occurs:
        label = "exploration-induced"
        confidence = "high"
    elif first_occurs and not later_success:
        label = "spontaneous"
        confidence = "medium"
    elif labels == {"unresolved_failure"}:
        label = "ambiguous"
        confidence = "low"
    else:
        label = "ambiguous"
        confidence = "low"
    origin_retries = [max(row["attempt_number"] - 1, 0) for row in origin_rows]
    subsequent_retries = [max(row["attempt_number"] - 1, 0) for row in subsequent]
    return label, {
        "origin_rows": origin_rows,
        "first_occurs": first_occurs,
        "later_success": later_success,
        "observed_tasks": observed_tasks,
        "subsequent": subsequent,
        "adopted": adopted,
        "origin_retries": origin_retries,
        "subsequent_retries": subsequent_retries,
        "confidence": confidence,
    }


def groups_for_names(groups: dict[str, list[dict[str, Any]]], names: set[str]) -> list[dict[str, Any]]:
    return [row for name in names for row in groups.get(name, [])]


def audit_run(run_dir: Path, limit: int = 30) -> dict[str, Any]:
    lineage_path, lineage = _final_lineage(run_dir)
    first_versions = _policy_first_versions(run_dir)
    policies = list((lineage.get("policies") or {}).values())
    policies.sort(key=lambda p: (str(p.get("status", "")) != "active", str(p.get("policy_id", ""))))
    policies = policies[: max(0, limit)]
    attempts = _load_attempts(run_dir)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attempts:
        groups[row["task_name"]].append(row)
    for row in attempts:
        row["occurs"] = False
        row["occurrence_signal"] = "none"
    rows: list[dict[str, Any]] = []
    for rank, policy in enumerate(policies, 1):
        origin_fp = {str(x.get("task_fingerprint")) for x in policy.get("observations", []) if isinstance(x, dict)}
        origins = {name for name in groups if task_fingerprint(name) in origin_fp}
        if not origins:
            origins = set()
        local_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for name, task_rows in groups.items():
            for row in task_rows:
                copy = dict(row)
                copy["occurs"], copy["occurrence_signal"] = _occurs(policy, row)
                local_groups[name].append(copy)
        first_policy_version = first_versions.get(str(policy.get("policy_id", "")))
        label, info = _classify(policy, local_groups, origins, first_policy_version)
        origin_rows = info["origin_rows"]
        subsequent = info["subsequent"]

        def final_success_count(rows_for_tasks: list[dict[str, Any]]) -> int:
            latest: dict[str, dict[str, Any]] = {}
            for item in rows_for_tasks:
                current = latest.get(item["task_name"])
                if current is None or item["attempt_number"] >= current["attempt_number"]:
                    latest[item["task_name"]] = item
            return sum(bool(item["success"]) for item in latest.values())

        origin_final_successes = final_success_count(origin_rows)
        subsequent_final_successes = final_success_count(subsequent)

        def mean_task_retries(rows_for_tasks: list[dict[str, Any]]) -> float | None:
            maxima: dict[str, int] = {}
            for item in rows_for_tasks:
                maxima[item["task_name"]] = max(maxima.get(item["task_name"], 0), item["attempt_number"] - 1)
            return sum(maxima.values()) / len(maxima) if maxima else None

        mean_origin = mean_task_retries(origin_rows)
        mean_sub = mean_task_retries(subsequent)
        evidence = []
        if info["first_occurs"]:
            evidence.append("attempt1_occurrence")
        if info["later_success"]:
            evidence.append("later_occurrence_on_success")
        if info["adopted"]:
            evidence.append("subsequent_attempt1_occurrence")
        rows.append(
            {
                "candidate_rank": rank,
                "policy_id": policy.get("policy_id", ""),
                "policy_name": policy.get("name", ""),
                "policy_status": policy.get("status", ""),
                "first_policy_version": first_policy_version or "",
                "family": lineage.get("task_family", run_dir.name),
                "origin_tasks": ";".join(sorted(origins)),
                "observed_tasks": ";".join(sorted(info["observed_tasks"])),
                "subsequent_tasks": len({x["task_name"] for x in subsequent}),
                "adopted_tasks": len({x["task_name"] for x in info["adopted"]}),
                "first_occurrence": "yes" if info["first_occurs"] else "no",
                "first_attempt_occurrence": len(info["first_occurs"]),
                "later_successful_occurrence": len(info["later_success"]),
                "origin_attempts": len(origin_rows),
                "origin_final_successes": origin_final_successes,
                "subsequent_final_successes": subsequent_final_successes,
                "origin_retry_mean": "" if mean_origin is None else round(mean_origin, 3),
                "subsequent_retry_mean": "" if mean_sub is None else round(mean_sub, 3),
                "retry_delta": "" if mean_origin is None or mean_sub is None else round(mean_sub - mean_origin, 3),
                "heuristic_label": label,
                "label_confidence": info["confidence"],
                "human_label": "",
                "evidence": ";".join(evidence),
                "review_notes": "",
            }
        )
    return {"run_dir": str(run_dir), "lineage": str(lineage_path) if lineage_path else None, "rows": rows, "workflow": workflow_audit(run_dir)}


def audit_runs_root(runs_root: Path, limit: int = 30) -> dict[str, Any]:
    """Aggregate up to *limit* policies across all run families below a root."""
    reports: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for lineage_path in sorted(runs_root.glob("**/skill_versions/final/.evolution/lineage.json")):
        run_dir = lineage_path.parents[3]
        if run_dir in seen:
            continue
        seen.add(run_dir)
        report = audit_run(run_dir, limit=limit)
        if report["rows"]:
            reports.append(report)
    rows = [row for report in reports for row in report["rows"]]
    rows.sort(key=lambda row: (str(row.get("policy_status", "")) != "active", str(row.get("policy_id", ""))))
    unique_rows: list[dict[str, Any]] = []
    seen_policies: set[str] = set()
    for row in rows:
        key = str(row.get("policy_id", ""))
        if key in seen_policies:
            continue
        seen_policies.add(key)
        unique_rows.append(row)
        if len(unique_rows) >= max(0, limit):
            break
    rows = unique_rows
    for rank, row in enumerate(rows, 1):
        row["candidate_rank"] = rank
    return {
        "run_dir": str(runs_root),
        "lineage": None,
        "rows": rows,
        "workflow": {
            "runs_scanned": len(seen),
            "runs_with_policies": len(reports),
            "workflow_update_records": sum(report["workflow"].get("workflow_update_records", 0) for report in reports),
            "workflow_only_version_estimate": sum(report["workflow"].get("workflow_only_version_estimate", 0) for report in reports),
            "interpretation": "workflow-only estimate; inspect version diffs before treating as bypass",
        },
    }


def workflow_audit(run_dir: Path) -> dict[str, Any]:
    versions = sorted(run_dir.glob("skill_versions/v*/.evolution/workflow_updates.jsonl"))
    workflow_updates = sum(1 for path in versions for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    workflow_only = 0
    for path in versions:
        version_dir = path.parents[1]
        skill = version_dir / ".claude" / "skills"
        policy_files = list(skill.glob("*/references/policies/*.md"))
        scripts = list(skill.glob("*/scripts/**/*.py"))
        manifest = _read_json(version_dir / "manifest.json", {})
        parent = manifest.get("parent_version")
        parent_skill = run_dir / "skill_versions" / str(parent) / ".claude" / "skills" if parent else None
        parent_files = (
            list(parent_skill.glob("*/references/policies/*.md")) + list(parent_skill.glob("*/scripts/**/*.py"))
            if parent_skill and parent_skill.is_dir()
            else []
        )
        current_runtime = {str(p.relative_to(skill)): hashlib.sha256(p.read_bytes()).hexdigest() for p in policy_files + scripts}
        parent_runtime = (
            {str(p.relative_to(parent_skill)): hashlib.sha256(p.read_bytes()).hexdigest() for p in parent_files}
            if parent_files and parent_skill
            else {}
        )
        if current_runtime == parent_runtime:
            # A workflow update with no runtime policy/script addition is the
            # observable form of a change bypassing candidate publication.
            workflow_only += 1
    return {
        "workflow_update_records": workflow_updates,
        "workflow_only_version_estimate": workflow_only,
        "interpretation": "workflow-only estimate; inspect diff before treating as bypass",
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with (output / "candidate_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(report["rows"])
    summary: dict[str, Any] = {
        "run_dir": report["run_dir"],
        "lineage": report["lineage"],
        "workflow": report["workflow"],
        "candidate_count": len(report["rows"]),
        "by_label": {},
    }
    for label in LABELS:
        subset = [x for x in report["rows"] if x["heuristic_label"] == label]
        retry_deltas = [x["retry_delta"] for x in subset if isinstance(x["retry_delta"], (int, float))]
        subsequent_successes = sum(int(x["subsequent_final_successes"]) for x in subset)
        subsequent_tasks = sum(int(x["subsequent_tasks"]) for x in subset)
        summary["by_label"][label] = {
            "count": len(subset),
            "adoption_rate": round(sum(x["adopted_tasks"] > 0 for x in subset) / len(subset), 3) if subset else None,
            "subsequent_success_rate": round(subsequent_successes / subsequent_tasks, 3) if subsequent_tasks else None,
            "retry_delta_mean": round(sum(retry_deltas) / len(retry_deltas), 3) if retry_deltas else None,
        }
    (output / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "candidate_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir", type=Path, help="One run family directory, e.g. runs/skilllearnbench-evolution/information-retrieval")
    source.add_argument("--runs-root", type=Path, help="Aggregate run family directories below this root, e.g. runs")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    report = audit_run(args.run_dir, args.limit) if args.run_dir else audit_runs_root(args.runs_root, args.limit)
    output = args.output or (args.run_dir or args.runs_root) / "behavioral_delta_audit"
    write_report(report, output)
    print(f"Audited {len(report['rows'])} policies from {args.run_dir or args.runs_root}")
    print(f"Wrote {output / 'candidate_audit.csv'} and {output / 'audit_summary.json'}")


if __name__ == "__main__":
    main()
