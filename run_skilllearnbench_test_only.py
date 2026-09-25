#!/usr/bin/env python3
"""Rerun frozen SkillLearnBench tests with trained skills and train memory."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import shutil
from pathlib import Path
from typing import Any

import llm_config
from evolution.claude_config import resolve_claude_profile_runtime
from evolution.memory_backfill import prepare_test_memory_store
from evolution.memory_store import MEMORY_STORE_FILENAME
from evolution.skill_utils import hash_skill_tree, sanitize_name
from run_skilllearnbench_evolution import (
    DEFAULT_DATASET_ROOT,
    DEFAULT_SPLIT_FILE,
    SkillLearnBenchExecutor,
    SkillLearnSplit,
    _run_test_phase,
    _task_refs,
    _write_split_manifest,
    discover_instances,
    load_fixed_splits,
    load_skilllearnbench_eval_runner,
    resolve_prebuilt_images,
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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _validate_source_split(source_family_dir: Path, split: SkillLearnSplit) -> None:
    manifest_path = source_family_dir / "split_manifest.json"
    manifest = _read_json(manifest_path)
    expected = [f"{path.parent.name}/{path.name}" for path in split.test]
    observed = manifest.get("test_tasks")
    if observed != expected:
        raise ValueError(
            f"Historical test split differs from the configured fixed split: {manifest_path}"
        )


def _run_category(
    category: str,
    split: SkillLearnSplit,
    args: argparse.Namespace,
) -> dict[str, Any]:
    test_profile = _configure_test_profile(args)
    source_family_dir = args.source_run / sanitize_name(category)
    output_family_dir = args.output_dir / sanitize_name(category)
    result_path = output_family_dir / "result.json"
    if args.skip_existing_family and result_path.is_file():
        return _read_json(result_path)

    _validate_source_split(source_family_dir, split)
    source_version_root = source_family_dir / "skill_versions" / "final"
    if not source_version_root.is_dir():
        raise FileNotFoundError(f"Missing frozen skills: {source_version_root}")
    source_hash = hash_skill_tree(source_version_root)

    input_version_root = output_family_dir / "skill_versions" / "input"
    if input_version_root.exists():
        copied_hash = hash_skill_tree(input_version_root)
        if copied_hash != source_hash:
            raise ValueError(
                f"Existing frozen skill hash mismatch for {category}: "
                f"{copied_hash} != {source_hash}"
            )
    else:
        input_version_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_version_root, input_version_root)
        copied_hash = hash_skill_tree(input_version_root)

    memory_report = prepare_test_memory_store(
        source_family_dir,
        output_family_dir / "skill_versions" / MEMORY_STORE_FILENAME,
        task_family=category,
    )
    _write_json(output_family_dir / "memory_preparation.json", memory_report)
    _write_split_manifest(output_family_dir / "split_manifest.json", split, args.split_file)

    test_refs = _task_refs(split.test, category)
    image_tags = resolve_prebuilt_images(test_refs)
    executor = SkillLearnBenchExecutor(
        dataset_root=args.dataset_root,
        agent_id=args.agent,
        model=args.test_model,
        profile="test",
        max_steps=args.max_steps,
        concurrency=args.batch_concurrency,
        image_tags=image_tags,
    )
    passed, total, records = _run_test_phase(
        executor,
        test_refs,
        input_version_root / ".claude" / "skills",
        output_family_dir,
        args.batch_size,
    )
    result = {
        "category": category,
        "display_name": split.display_name,
        "source_run": str(args.source_run),
        "source_skill_version": "final",
        "source_skill_hash": source_hash,
        "copied_skill_hash": copied_hash,
        "memory": memory_report,
        "test_llm": _public_profile(test_profile),
        "test_passed": passed,
        "test_total": total,
        "test_pass_rate": passed / total if total else 0.0,
        "test_records": records,
    }
    _write_json(result_path, result)
    return result


def _aggregate(
    args: argparse.Namespace,
    categories: list[str],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for category in categories:
        path = args.output_dir / sanitize_name(category) / "result.json"
        if path.is_file():
            results.append(_read_json(path))
    passed = sum(int(item.get("test_passed", 0)) for item in results)
    total = sum(int(item.get("test_total", 0)) for item in results)
    payload = {
        "source_run": str(args.source_run),
        "output_dir": str(args.output_dir),
        "categories_planned": len(categories),
        "categories_completed": len(results),
        "test_passed": passed,
        "test_total": total,
        "test_pass_rate": passed / total if total else 0.0,
        "categories": results,
    }
    _write_json(args.output_dir / "result.json", payload)
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rerun SkillLearnBench held-out tests without training or evolution"
    )
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--split-file", type=Path, default=DEFAULT_SPLIT_FILE)
    parser.add_argument("--only-category", action="append", default=None)
    parser.add_argument("--agent", default="claude-code")
    parser.add_argument("--test-model", default=None)
    parser.add_argument("--test-llm-provider", choices=("anthropic", "openai"))
    parser.add_argument("--test-llm-model")
    parser.add_argument("--test-llm-base-url")
    parser.add_argument("--test-llm-api-key")
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--batch-concurrency", type=int, default=3)
    parser.add_argument("--family-concurrency", type=int, default=2)
    parser.add_argument(
        "--skip-existing-family",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    for name in ("source_run", "output_dir", "dataset_root", "split_file"):
        setattr(args, name, getattr(args, name).expanduser().resolve())
    for name in ("max_steps", "batch_size", "batch_concurrency", "family_concurrency"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be >= 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    test_profile = _configure_test_profile(args)
    splits = load_fixed_splits(
        args.split_file,
        args.dataset_root,
        discover_instances(args.dataset_root),
    )
    if args.only_category:
        unknown = sorted(set(args.only_category) - set(splits))
        if unknown:
            raise SystemExit(f"Unknown --only-category value(s): {unknown}")
        splits = {name: splits[name] for name in args.only_category}

    plans: list[dict[str, Any]] = []
    for category, split in splits.items():
        source_family_dir = args.source_run / sanitize_name(category)
        _validate_source_split(source_family_dir, split)
        source_version_root = source_family_dir / "skill_versions" / "final"
        if not source_version_root.is_dir():
            raise SystemExit(f"Missing frozen skills: {source_version_root}")
        plans.append(
            {
                "category": category,
                "test_tasks": len(split.test),
                "source_skill_hash": hash_skill_tree(source_version_root),
                "memory_source": (
                    "native_training_store"
                    if (source_family_dir / "skill_versions" / MEMORY_STORE_FILENAME).is_file()
                    else "train_artifact_backfill"
                ),
            }
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        args.output_dir / "plan.json",
        {
            "source_run": str(args.source_run),
            "output_dir": str(args.output_dir),
            "test_llm": _public_profile(test_profile),
            "families": plans,
        },
    )
    print(f"[SkillLearnBenchTest] Planned {len(plans)} categories in {args.output_dir}")
    if args.plan_only:
        return 0

    if shutil.which("docker") is None:
        raise SystemExit("Docker is required to run SkillLearnBench agent trials")
    runner = load_skilllearnbench_eval_runner(args.dataset_root)
    runner._load_dotenv()
    if args.agent == "claude-code":
        runtime = resolve_claude_profile_runtime(
            "test", start_adapter=True, model_override=args.test_model
        )
        print(
            f"[SkillLearnBenchTest] test API: provider={runtime.provider}, "
            f"model={runtime.model or ''}"
        )

    jobs = [
        (category, split)
        for category, split in splits.items()
        if not (
            args.skip_existing_family
            and (args.output_dir / sanitize_name(category) / "result.json").is_file()
        )
    ]
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(args.family_concurrency, len(jobs)) if jobs else 1,
        mp_context=context,
        max_tasks_per_child=1,
    ) as pool:
        futures = {
            pool.submit(_run_category, category, split, args): category
            for category, split in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            category = futures[future]
            result = future.result()
            print(
                f"[SkillLearnBenchTest] {category}: "
                f"{result['test_passed']}/{result['test_total']}"
            )

    aggregate = _aggregate(args, list(splits))
    print(
        f"[SkillLearnBenchTest] Overall: {aggregate['test_passed']}/"
        f"{aggregate['test_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
