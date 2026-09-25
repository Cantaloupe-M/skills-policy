#!/usr/bin/env python3
"""Run the SkillFlow mechanism-ablation matrix.

Each variant gets an isolated output directory:
  <output-root>/<variant>/myevolution__<family>/

Only variants whose mechanism is implemented are executed. Use --dry-run to
inspect all commands, including pending variants, before spending compute.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
DEFAULT_VARIANTS = HERE / "variants.json"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "runs" / "skillflow-ablation"
RUNNER = PROJECT_ROOT / "run_skillflow_evolution.py"
SECRET_OPTIONS = frozenset({
    "--train-llm-api-key",
    "--evolution-llm-api-key",
    "--test-llm-api-key",
})

# Same profile-level override shape as ``run_skillflow_evolution.py``.
# Edit this mapping to use one LLM configuration for the whole ablation run.
# A missing/empty field leaves the child runner's configured default unchanged.
LLM_OVERRIDES: dict[str, dict[str, str]] = {
    "train": {
        "provider": "anthropic",
        "model": "gpt-5.6-luna",
        "base_url": "https://code28.ccwu.cc",
        "api_key": "sk-Bvv6kFf73HLFNHjUgk8jblonbd2syPA2oJqvxwuMv94ogZbJ",
    },
    "evolution": {
        "provider": "openai",
        "model": "gpt-5.6-terra",
        "base_url": "https://code28.ccwu.cc/v1",
        "api_key": "sk-Bvv6kFf73HLFNHjUgk8jblonbd2syPA2oJqvxwuMv94ogZbJ",
    },
    "test": {
        "provider": "anthropic",
        "model": "gpt-5.6-luna",
        "base_url": "https://code28.ccwu.cc",
        "api_key": "sk-Bvv6kFf73HLFNHjUgk8jblonbd2syPA2oJqvxwuMv94ogZbJ",
    },
}


def load_variants(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"Invalid variant registry: {path}")
    return payload


def redact_command(command: list[str]) -> list[str]:
    """Hide CLI secrets before printing commands or writing manifests."""
    redacted = list(command)
    for index, value in enumerate(redacted[:-1]):
        if value in SECRET_OPTIONS:
            redacted[index + 1] = "<redacted>"
    return redacted


def _llm_overrides(args: argparse.Namespace) -> dict[str, dict[str, str]]:
    """Merge module defaults with optional one-off CLI overrides."""
    overrides = {profile: dict(values) for profile, values in LLM_OVERRIDES.items()}
    for profile in ("train", "evolution", "test"):
        target = overrides.setdefault(profile, {})
        for key in ("provider", "model", "base_url", "api_key"):
            value = getattr(args, f"{profile}_llm_{key}", None)
            if value:
                target[key] = value
    return overrides


def build_command(
    variant: str,
    spec: dict,
    args: argparse.Namespace,
    output_dir: Path,
) -> list[str]:
    values = spec.get("args", {})
    launcher = ["uv", "run", "python"] if args.launcher == "uv" else [sys.executable]
    dataset_args = (
        ["--dataset-path", str(args.dataset_path)]
        if args.dataset_path is not None
        else []
    )
    command = [
        *launcher,
        str(RUNNER),
        "--config", str(args.config),
        *dataset_args,
        "--initialization", str(values.get("initialization", "scaffold")),
        "--min-occurrences", str(values.get("min_occurrences", 2)),
        "--run-root-dir", str(output_dir),
        "--batch-size", str(args.batch_size),
        "--max-retries", str(args.max_retries),
        "--train-epochs", str(args.train_epochs),
        "--train-shuffle-seed", str(args.train_shuffle_seed),
        "--batch-concurrency", str(args.batch_concurrency),
        "--family-concurrency", str(args.family_concurrency),
        "--max-evolution-workers", str(args.max_evolution_workers),
    ]
    # The child runner treats an omitted dataset path as "all datasets from
    # the config".  Do not stringify ``None`` into a bogus path; that would
    # disable the config-driven all-family mode.
    if values.get("failure_evidence") is not None:
        command.extend(["--failure-evidence", str(values["failure_evidence"])])
    if values.get("qualification") is not None:
        command.extend(["--qualification", str(values["qualification"])])
    if values.get("promotion") is not None:
        command.extend(["--promotion", str(values["promotion"])])
    for profile, values in _llm_overrides(args).items():
        label = profile.replace("_", "-")
        for key, option in (("provider", "provider"), ("model", "model"),
                            ("base_url", "base-url"), ("api_key", "api-key")):
            value = values.get(key)
            if value:
                command.extend([f"--{label}-llm-{option}", str(value)])
    if args.only_family:
        command.extend(["--only-family", args.only_family])
    if args.no_skip_existing:
        command.append("--no-skip-existing-family")
    if args.fast_test:
        command.append("--fast-test")
    return command


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", action="append", dest="variants", help="Variant name; repeatable. Default: all implemented variants")
    parser.add_argument("--list", action="store_true", help="List registered variants and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing them")
    parser.add_argument(
        "--launcher",
        choices=("uv", "python"),
        default="uv",
        help="Run through the project uv environment by default so embedding dependencies are available.",
    )
    parser.add_argument("--run-pending", action="store_true", help="Attempt pending variants (will fail until their switches exist)")
    parser.add_argument("--variants-file", type=Path, default=DEFAULT_VARIANTS)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs" / "myevolution.yaml")
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=None,
        help="Dataset directory for --only-family; omit to run every dataset in --config.",
    )
    parser.add_argument("--only-family", default=None, help="Run one family from --dataset-path.")
    parser.add_argument("--batch-size", type=int, default=3)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--train-epochs", type=int, default=2)
    parser.add_argument("--train-shuffle-seed", type=int, default=0)
    parser.add_argument("--batch-concurrency", type=int, default=3)
    parser.add_argument("--family-concurrency", type=int, default=1)
    parser.add_argument("--max-evolution-workers", type=int, default=3)
    for profile in ("train", "evolution", "test"):
        label = profile.replace("_", "-")
        parser.add_argument(
            f"--{label}-llm-provider",
            choices=("anthropic", "openai"),
            default=None,
            help=f"Override the {profile} LLM provider.",
        )
        parser.add_argument(f"--{label}-llm-model", default=None, help=f"Override the {profile} LLM model.")
        parser.add_argument(f"--{label}-llm-base-url", default=None, help=f"Override the {profile} LLM base URL.")
        parser.add_argument(f"--{label}-llm-api-key", default=None, help=f"Override the {profile} LLM API key.")
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--fast-test", action="store_true")
    args = parser.parse_args(argv)
    if args.only_family and args.dataset_path is None:
        parser.error("--dataset-path is required with --only-family")
    args.config = args.config.expanduser().resolve()
    if args.dataset_path is not None:
        args.dataset_path = args.dataset_path.expanduser().resolve()
    args.output_root = args.output_root.expanduser().resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    variants = load_variants(args.variants_file.expanduser().resolve())
    if args.list:
        for name, spec in variants.items():
            status = "ready" if spec.get("implemented") else "pending"
            print(f"{name}\t{status}\t{spec.get('label', '')}")
        return 0

    selected = args.variants or [name for name, spec in variants.items() if spec.get("implemented")]
    unknown = sorted(set(selected) - set(variants))
    if unknown:
        raise SystemExit(f"Unknown variant(s): {', '.join(unknown)}")

    manifest = {
        "dataset_path": str(args.dataset_path) if args.dataset_path is not None else None,
        "config": str(args.config),
        "variants": selected,
        "commands": [],
    }
    exit_code = 0
    for name in selected:
        spec = variants[name]
        if not spec.get("implemented") and not args.run_pending:
            print(f"[SKIP] {name}: pending ({spec.get('requires', 'mechanism switch not implemented')})")
            continue
        output_dir = args.output_root / name
        command = build_command(name, spec, args, output_dir)
        display_command = redact_command(command)
        manifest["commands"].append({"variant": name, "output_dir": str(output_dir), "command": display_command})
        print(f"\n[{name}] {spec.get('label', name)}")
        print(" ".join(display_command))
        if args.dry_run:
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("UV_CACHE_DIR", str(args.output_root / ".uv-cache"))
        completed = subprocess.run(command, cwd=PROJECT_ROOT, env=env, check=False)
        if completed.returncode != 0:
            exit_code = completed.returncode
            print(f"[{name}] failed with exit code {completed.returncode}")
        else:
            print(f"[{name}] completed: {output_dir}")
    if not args.dry_run:
        args.output_root.mkdir(parents=True, exist_ok=True)
        (args.output_root / "ablation_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
