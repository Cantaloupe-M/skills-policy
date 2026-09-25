#!/usr/bin/env python3
"""Evaluate held-out SkillFlow tasks using the skills frozen after one epoch."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import llm_config
from evolution.config import EvolutionConfig
from evolution.family_split import FamilySplit
from evolution.memory_backfill import prepare_test_memory_store
from evolution.memory_store import MEMORY_STORE_FILENAME
from evolution.skill_utils import hash_skill_tree
from run_skillflow_evolution import (
    SkillFlowConfig,
    _run_family_test_phase,
    _setup_api_env,
    load_job_config,
    resolve_group_task_paths,
)

PROJECT_ROOT = Path(__file__).resolve().parent


def _configure_test_profile(args: argparse.Namespace) -> dict[str, str]:
    """Use ``llm_config.py`` directly, with optional CLI overrides."""
    profile = dict(llm_config.LLM_PROFILES["test"])
    for key in ("provider", "model", "base_url", "api_key"):
        value = getattr(args, f"test_llm_{key}", None)
        if value:
            profile[key] = str(value).strip()
    llm_config.LLM_PROFILES["test"] = profile
    llm_config._sync_legacy_globals()
    return profile


def _public_profile(profile: dict[str, str]) -> dict[str, str]:
    return {
        "source": "llm_config.py:test",
        "provider": profile.get("provider", ""),
        "model": profile.get("model", ""),
        "base_url": profile.get("base_url", ""),
        "api_key": "[redacted]",
    }


def _json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _epoch_skill_version(source_family_dir: Path, epoch: int) -> tuple[str, str]:
    summary = _json(source_family_dir / "summary.json")
    history = summary.get("version_history")
    if not isinstance(history, list):
        raise ValueError(f"Missing version_history in {source_family_dir / 'summary.json'}")
    entries = [
        item for item in history
        if isinstance(item, dict) and int(item.get("epoch_index", -1)) == epoch
    ]
    if not entries:
        raise ValueError(f"No epoch {epoch} version history in {source_family_dir}")
    entries.sort(key=lambda item: int(item.get("batch_index", 0)))
    last = entries[-1]
    version = str(last.get("promoted_version") or last.get("snapshot_version") or "")
    if not version:
        raise ValueError(f"Cannot resolve the final skill version for epoch {epoch}")
    skills_dir = source_family_dir / "skill_versions" / version
    if not skills_dir.is_dir():
        raise FileNotFoundError(f"Resolved skill version does not exist: {skills_dir}")
    return version, hash_skill_tree(skills_dir)


def _selected_skill_version(
    source_family_dir: Path,
    epoch: int | None,
) -> tuple[str, Path, str]:
    if epoch is not None:
        version, content_hash = _epoch_skill_version(source_family_dir, epoch)
        return version, source_family_dir / "skill_versions" / version, content_hash
    version = "final"
    version_root = source_family_dir / "skill_versions" / version
    if not version_root.is_dir():
        raise FileNotFoundError(f"Final skill version does not exist: {version_root}")
    return version, version_root, hash_skill_tree(version_root)


def _family_dataset(base_config: Any, family_name: str) -> Path:
    matches = [
        Path(dataset.path)
        for dataset in (base_config.datasets or [])
        if Path(dataset.path).name == family_name
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one dataset for {family_name!r}, found {len(matches)}"
        )
    return matches[0]


def _family_split(source_family_dir: Path, dataset_path: Path, base_config: Any) -> FamilySplit:
    manifest = _json(source_family_dir / "skillflow_split.json")
    family_name = str(manifest["family_name"])
    verifier = base_config.model_dump().get("verifier") or {}
    tasks = resolve_group_task_paths(
        dataset_path,
        disable_verification=bool(verifier.get("disable", False)),
    )
    by_name = {path.name: path for path in tasks}

    def resolve(key: str) -> list[Path]:
        names = manifest.get(key, [])
        if not isinstance(names, list):
            raise ValueError(f"Invalid {key} in {source_family_dir / 'skillflow_split.json'}")
        missing = [str(name) for name in names if str(name) not in by_name]
        if missing:
            raise ValueError(f"Dataset is missing {key}: {', '.join(missing)}")
        return [by_name[str(name)] for name in names]

    return FamilySplit(
        family_name=family_name,
        acquisition=resolve("train_tasks"),
        deployment=resolve("test_tasks"),
        probe=resolve("probe_tasks") if "probe_tasks" in manifest else [],
    )


def _task_results(family_output_dir: Path, planned_tasks: list[str]) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for result_path in sorted((family_output_dir / "test").glob("round_*/*/result.json")):
        data = _json(result_path)
        task_name = str(data.get("task_name") or "")
        if task_name not in planned_tasks:
            continue
        exception = data.get("exception_info")
        verifier = data.get("verifier_result") or {}
        rewards = verifier.get("rewards") if isinstance(verifier, dict) else {}
        reward = float((rewards or {}).get("reward", data.get("reward", 0)) or 0)
        found[task_name] = {
            "task_name": task_name,
            "trial_name": data.get("trial_name", result_path.parent.name),
            "success": exception is None and reward >= 1.0,
            "reward": reward,
            "exception_info": exception,
            "result_path": str(result_path.resolve()),
        }
    return [
        found.get(name, {
            "task_name": name,
            "trial_name": "",
            "success": False,
            "reward": 0.0,
            "exception_info": "test attempt produced no result",
            "result_path": None,
        })
        for name in planned_tasks
    ]


def _run_one_family(args: argparse.Namespace) -> int:
    source_root = args.source_run.resolve()
    output_root = args.output_dir.resolve()
    source_family_dir = source_root / args.family_dir_name
    manifest = _json(source_family_dir / "skillflow_split.json")
    family_name = str(manifest["family_name"])
    family_output_dir = output_root / args.family_dir_name
    result_path = family_output_dir / "result.json"
    if args.skip_existing_family and result_path.is_file():
        print(f"[EpochTest] Skip completed family: {family_name}")
        return 0

    version, source_version_root, source_hash = _selected_skill_version(
        source_family_dir, args.epoch
    )
    input_version_root = family_output_dir / "skill_versions" / "input"
    input_skills = input_version_root / ".claude" / "skills"
    family_output_dir.mkdir(parents=True, exist_ok=True)
    if input_version_root.exists():
        existing = hash_skill_tree(input_version_root)
        if existing != source_hash:
            raise ValueError(
                f"Existing frozen skill hash mismatch for {family_name}: "
                f"{existing} != {source_hash}"
            )
    else:
        shutil.copytree(source_version_root, input_version_root)
    copied_hash = hash_skill_tree(input_version_root)
    memory_report = prepare_test_memory_store(
        source_family_dir,
        family_output_dir / "skill_versions" / MEMORY_STORE_FILENAME,
        task_family=family_name,
    )
    _write_json(family_output_dir / "memory_preparation.json", memory_report)

    base_config = load_job_config(args.config)
    dataset_path = _family_dataset(base_config, family_name)
    split = _family_split(source_family_dir, dataset_path, base_config)
    shutil.copy2(source_family_dir / "skillflow_split.json", family_output_dir / "skillflow_split.json")

    cfg = SkillFlowConfig(
        evolution=EvolutionConfig(batch_size=args.batch_size, max_retries=0),
        run_root_dir=output_root,
        batch_concurrency=1,
        family_concurrency=1,
        copy_task_skills=args.copy_task_skills,
        skip_existing_family=args.skip_existing_family,
        llm_overrides=None,
    )
    test_profile = _configure_test_profile(args)
    _setup_api_env(base_config, task_profile="test")

    planned = [path.name for path in split.deployment + split.probe]
    started_at = datetime.now(UTC).isoformat()
    successful, total, progress = _run_family_test_phase(
        base_config=base_config,
        dataset_path=dataset_path,
        cfg=cfg,
        family_name=family_name,
        family_split=split,
        family_job_dir=family_output_dir,
        final_skills_dir=input_skills,
    )
    records = _task_results(family_output_dir, planned)
    payload = {
        "family_name": family_name,
        "source_run": str(source_root),
        "source_epoch": args.epoch,
        "source_skill_version": version,
        "source_skill_hash": source_hash,
        "copied_skill_hash": copied_hash,
        "memory": memory_report,
        "test_llm": _public_profile(test_profile),
        "test_successful": successful,
        "test_total": total,
        "accuracy": successful / total if total else 0.0,
        "progress": progress,
        "tasks": records,
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
    }
    _write_json(result_path, payload)
    print(f"[EpochTest] {family_name}: {successful}/{total} ({payload['accuracy']:.2%})")
    return 0


def _family_dirs(source_root: Path) -> list[Path]:
    return sorted(
        path for path in source_root.iterdir()
        if path.is_dir()
        and (path / "summary.json").is_file()
        and (path / "skillflow_split.json").is_file()
    )


def _child_command(args: argparse.Namespace, family_dir_name: str) -> list[str]:
    cmd = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--source-run", str(args.source_run),
        "--output-dir", str(args.output_dir),
        "--config", str(args.config),
        "--batch-size", str(args.batch_size),
        "--only-family-dir", family_dir_name,
    ]
    for option, value in (
        ("--test-llm-provider", args.test_llm_provider),
        ("--test-llm-model", args.test_llm_model),
        ("--test-llm-base-url", args.test_llm_base_url),
    ):
        if value:
            cmd.extend([option, value])
    if args.epoch is not None:
        cmd.extend(["--epoch", str(args.epoch)])
    if args.copy_task_skills:
        cmd.append("--copy-task-skills")
    if args.skip_existing_family:
        cmd.append("--skip-existing-family")
    else:
        cmd.append("--no-skip-existing-family")
    return cmd


def _launch_child(args: argparse.Namespace, family_dir_name: str) -> tuple[str, int]:
    log_path = args.output_dir.resolve() / "logs" / f"{family_dir_name}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if args.test_llm_api_key:
        env["SKILLFLOW_TEST_API_KEY_OVERRIDE"] = args.test_llm_api_key
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.run(
            _child_command(args, family_dir_name),
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    return family_dir_name, process.returncode


def _write_aggregate(args: argparse.Namespace, family_dir_names: list[str]) -> dict[str, Any]:
    family_results: list[dict[str, Any]] = []
    for name in family_dir_names:
        path = args.output_dir.resolve() / name / "result.json"
        if path.is_file():
            family_results.append(_json(path))
    successful = sum(int(item.get("test_successful", 0)) for item in family_results)
    total = sum(int(item.get("test_total", 0)) for item in family_results)
    payload = {
        "source_run": str(args.source_run.resolve()),
        "source_epoch": args.epoch,
        "output_dir": str(args.output_dir.resolve()),
        "test_llm": _public_profile(_configure_test_profile(args)),
        "families_planned": len(family_dir_names),
        "families_completed": len(family_results),
        "test_successful": successful,
        "test_total": total,
        "accuracy": successful / total if total else 0.0,
        "family_results": [
            {
                "family_name": item.get("family_name"),
                "source_skill_version": item.get("source_skill_version"),
                "source_skill_hash": item.get("source_skill_hash"),
                "test_successful": item.get("test_successful"),
                "test_total": item.get("test_total"),
                "accuracy": item.get("accuracy"),
            }
            for item in family_results
        ],
        "written_at": datetime.now(UTC).isoformat(),
    }
    _write_json(args.output_dir.resolve() / "summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run SkillFlow held-out tests with the skill version at the end of a chosen epoch"
    )
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--epoch",
        type=int,
        default=None,
        help="Use the last version from this epoch; default uses skill_versions/final",
    )
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "myevolution.yaml")
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--family-concurrency", type=int, default=3)
    parser.add_argument("--test-llm-provider", choices=("anthropic", "openai"))
    parser.add_argument("--test-llm-model")
    parser.add_argument("--test-llm-base-url")
    parser.add_argument(
        "--test-llm-api-key",
        default=os.environ.get("SKILLFLOW_TEST_API_KEY_OVERRIDE"),
        help="Optional override; default reads llm_config.py test.api_key",
    )
    parser.add_argument("--copy-task-skills", action="store_true")
    parser.add_argument("--skip-existing-family", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--only-family-dir", dest="family_dir_name", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.epoch is not None and args.epoch < 1:
        raise SystemExit("--epoch must be >= 1")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be >= 1")
    if args.family_concurrency < 1:
        raise SystemExit("--family-concurrency must be >= 1")
    args.source_run = args.source_run.resolve()
    args.output_dir = args.output_dir.resolve()
    args.config = args.config.resolve()
    test_profile = _configure_test_profile(args)

    if args.family_dir_name:
        try:
            return _run_one_family(args)
        except Exception:
            traceback.print_exc()
            return 1

    family_dirs = _family_dirs(args.source_run)
    if not family_dirs:
        raise SystemExit(f"No completed family directories found under {args.source_run}")
    plans = []
    for family_dir in family_dirs:
        version, _version_root, content_hash = _selected_skill_version(
            family_dir, args.epoch
        )
        split_manifest = _json(family_dir / "skillflow_split.json")
        plans.append({
            "family_dir": family_dir.name,
            "family_name": split_manifest["family_name"],
            "test_tasks": len(split_manifest.get("test_tasks", []))
            + len(split_manifest.get("probe_tasks", [])),
            "version": version,
            "hash": content_hash,
            "memory_source": (
                "native_training_store"
                if (family_dir / "skill_versions" / MEMORY_STORE_FILENAME).is_file()
                else "train_artifact_backfill"
            ),
        })
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "plan.json", {
        "source_run": str(args.source_run),
        "source_epoch": args.epoch,
        "test_llm": _public_profile(test_profile),
        "families": plans,
    })
    print(f"[EpochTest] Planned {len(plans)} families in {args.output_dir}")
    if args.plan_only:
        return 0

    failures: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.family_concurrency) as pool:
        futures = {
            pool.submit(_launch_child, args, item["family_dir"]): item["family_dir"]
            for item in plans
        }
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            family_dir_name, returncode = future.result()
            completed += 1
            status = "OK" if returncode == 0 else "FAIL"
            print(f"[EpochTest] {status} {completed}/{len(plans)} {family_dir_name}", flush=True)
            if returncode != 0:
                failures.append(family_dir_name)

    aggregate = _write_aggregate(args, [item["family_dir"] for item in plans])
    print(
        f"[EpochTest] Overall: {aggregate['test_successful']}/{aggregate['test_total']} "
        f"({aggregate['accuracy']:.2%}); families "
        f"{aggregate['families_completed']}/{aggregate['families_planned']}"
    )
    if failures:
        print(f"[EpochTest] Failed families: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
