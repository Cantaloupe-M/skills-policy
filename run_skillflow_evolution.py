#!/usr/bin/env python3
"""Run SkillFlow benchmarks with skill self-evolution.

Flow per procedural family:
  1. Discover tasks and group them by family.
  2. Split each family into train/test partitions.
  3. Run train tasks in fixed-size batches through ``BatchEvolutionLoop``.
  4. Evolve a versioned ``.claude/skills/`` snapshot only after each batch.
  5. Freeze the final family skill snapshot.
  6. Run held-out test tasks with the frozen skills, without further evolution.

export LLM_OVERRIDES='{
  "train": {
    "provider": "anthropic",
    "model": "gpt-5.6-terra",
    "base_url": "https://code28.ccwu.cc",
    "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc"
  },
  "evolution": {
    "provider": "openai",
    "model": "gpt-5.6-terra",
    "base_url": "https://code28.ccwu.cc/v1",
    "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc"
  },
  "test": {
    "provider": "anthropic",
    "model": "gpt-5.6-terra",
    "base_url": "https://code28.ccwu.cc",
    "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc"
  }
}'

./.venv/bin/python run_skillflow_evolution.py \
  --config configs/myevolution.yaml \
    --run-root-dir runs/skillflow-gpt-2 \
    --max-retries 3 \
    --train-epochs 2 \
    --family-concurrency 3

export LLM_OVERRIDES='{
  "train": {
    "provider": "anthropic",
    "model": "gpt-5.6-terra",
    "base_url": "https://code28.ccwu.cc",
    "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc"
  },
  "evolution": {
    "provider": "openai",
    "model": "claude-sonnet-4-6",
    "base_url": "https://codeflow.asia/v1",
    "api_key": "sk-z4fTQVxjKR6zoblLjCjBhe1yS9hSn5FcNnl960fePSyTP1eH"
  },
  "test": {
    "provider": "anthropic",
    "model": "gpt-5.6-terra",
    "base_url": "https://code28.ccwu.cc",
    "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc"
  }
}'


./.venv/bin/python run_skillflow_evolution.py \
  --config configs/myevolution.yaml \
    --run-root-dir runs/skillflow-claude \
    --max-retries 3 \
    --train-epochs 2 \
    --family-concurrency 3
"""

from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import importlib
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llm_config import LLM_PROFILES

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

ENTRYPOINT = Path(__file__).resolve()
PROJECT_ROOT = ENTRYPOINT.parent


def _site_packages_dirs(venv_dir: Path) -> list[Path]:
    lib_dir = venv_dir / "lib"
    if not lib_dir.is_dir():
        return []
    return [path / "site-packages" for path in sorted(lib_dir.glob("python*"))
            if (path / "site-packages").is_dir()]


def _add_harbor_import_paths() -> None:
    candidates: list[Path] = []
    if os.environ.get("HARBOR_SITE_PACKAGES"):
        candidates.append(Path(os.environ["HARBOR_SITE_PACKAGES"]))
    candidates.extend(_site_packages_dirs(Path.home() / ".local" / "share" / "uv" / "tools" / "harbor"))
    for path in reversed(candidates):
        if (path / "harbor").is_dir() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from harbor import Job
    from harbor.models.job.config import JobConfig
    from harbor.models.task.paths import TaskPaths
except ModuleNotFoundError as exc:
    if exc.name != "harbor":
        raise
    _add_harbor_import_paths()
    try:
        from harbor import Job
        from harbor.models.job.config import JobConfig
        from harbor.models.task.paths import TaskPaths
    except ModuleNotFoundError as retry_exc:
        if retry_exc.name != "harbor":
            raise
        raise ModuleNotFoundError(
            "Could not import Harbor. Install it or set HARBOR_SITE_PACKAGES."
        ) from retry_exc

import yaml

from evolution.batch_loop import (
    BatchEvolutionLoop,
    BatchExecutor,
    EvolutionPolicy,
    TaskRef,
    TrialResult as BatchTrialResult,
)
from evolution.batch_reflection import run_reflection_retry_loop
from evolution.cli import add_evolution_arguments, evolution_config_from_args
from evolution.claude_config import (
    CLAUDE_API_ENV_KEYS,
    add_no_proxy_host,
    fill_claude_env_from_llm_config,
    resolve_claude_profile_runtime,
)
from evolution.config import EvolutionConfig
from evolution.family_split import FamilySplit
from evolution.integrations.claude_code_artifacts import (
    build_task_contract,
    compact_claude_trajectory,
)
from evolution.memory_embedding_service import ensure_memory_embedding_service
from evolution.memory_store import (
    MEMORY_STORE_FILENAME,
    memory_runtime_spec,
    prepare_runtime_skills,
)
from evolution.outcome import normalize_harbor_outcome
from evolution.runner import (
    RunResult,
    SPLIT_MANIFEST_FILENAME, TEST_PROGRESS_FILENAME,
    result_to_json,
    FAST_TEST_MAX_TURNS, FAST_TEST_REWARD,
)
from evolution.exploration.skill_compiler import resolve_family_skill_slug
from evolution.skill_utils import (
    freeze_final_version,
    get_latest_skill_version,
    hash_skill_tree,
    sanitize_name,
)
from evolution.initial_skill import prepare_initial_family_skill_store
from evolution.task_instruction import prepare_task_instruction

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

FLAT_SHARED_SKILLS_ENV_IMPORT = (
    "evolution.integrations.flat_shared_skills_env:FlatSharedSkillsDockerEnvironment"
)
FAST_TEST_ENV_KEY = "SKILLFLOW_FAST_TEST"
LLM_OVERRIDES_ENV_KEY = "LLM_OVERRIDES"
PROXY_ENV_GROUPS = (
    ("HTTP_PROXY", "http_proxy"),
    ("HTTPS_PROXY", "https_proxy"),
    ("NO_PROXY", "no_proxy"),
    ("ALL_PROXY", "all_proxy"),
)
SKILLFLOW_FAMILY_SPLITS_PATH = PROJECT_ROOT / "utils" / "skillflow_family_splits.json"
DEFAULT_RUN_ROOT = PROJECT_ROOT / "runs" / "skillflow"


# ═══════════════════════════════════════════════════════════════════════════
# SkillFlow-specific configuration (NOT shared across benchmarks)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SkillFlowConfig:
    """SkillFlow execution settings — local to this entrypoint."""
    evolution: EvolutionConfig
    run_root_dir: Path | None = None
    batch_concurrency: int = 1
    family_concurrency: int = 1
    copy_task_skills: bool = False
    fast_test: bool = False
    skip_existing_family: bool = False
    initialization: str = "task-derived"
    llm_overrides: dict[str, dict[str, str]] | None = None
    table2_method: str | None = None  # Table 2 memory method


LLM_OVERRIDES: dict[str, dict[str, str]] = {
    "train": {
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "base_url": "https://api.apiyi.com/v1",
        "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b",
    },
    "evolution": {
        "provider": "openai",
        "model": "claude-sonnet-4-6",
        "base_url": "https://codeflow.asia/v1",
        "api_key": "sk-z4fTQVxjKR6zoblLjCjBhe1yS9hSn5FcNnl960fePSyTP1eH"
    },
    "test": {
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "base_url": "https://api.apiyi.com/v1",
        "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b",
    },
}

def _load_env_llm_overrides() -> dict[str, dict[str, str]] | None:
    """Load profile overrides from ``LLM_OVERRIDES`` when it is set.

    The variable must contain a JSON object keyed by ``train``, ``evolution``
    and/or ``test``.  An explicitly set but invalid value fails fast instead
    of silently falling back to the in-code configuration.
    """
    raw = os.environ.get(LLM_OVERRIDES_ENV_KEY)
    if raw is None or not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY} must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY} must be a JSON object")
    allowed_keys = {"provider", "model", "base_url", "api_key"}
    parsed: dict[str, dict[str, str]] = {}
    for profile, values in payload.items():
        if profile not in {"train", "evolution", "test"}:
            raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY} has unknown profile {profile!r}")
        if not isinstance(values, dict):
            raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY}.{profile} must be a JSON object")
        unknown = set(values) - allowed_keys
        if unknown:
            names = ", ".join(sorted(str(key) for key in unknown))
            raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY}.{profile} has unknown field(s): {names}")
        if any(not isinstance(value, str) for value in values.values()):
            raise SystemExit(f"{LLM_OVERRIDES_ENV_KEY}.{profile} values must be strings")
        parsed[profile] = {key: value.strip() for key, value in values.items() if value.strip()}
    return parsed

def _apply_llm_overrides(overrides: dict[str, dict[str, str]] | None = None) -> None:
    """Apply custom train/evolution/test settings to shared llm_config."""
    llm_config = importlib.import_module("llm_config")
    configured_overrides = _load_env_llm_overrides()
    if configured_overrides is None:
        configured_overrides = LLM_OVERRIDES
    for profile in ("train", "evolution", "test"):
        configured = dict(getattr(llm_config, "LLM_PROFILES", {}).get(profile, {}))
        configured.update({k: v for k, v in configured_overrides.get(profile, {}).items() if v})
        configured.update({k: v for k, v in (overrides or {}).get(profile, {}).items() if v})
        provider = str(configured.get("provider") or "").lower()
        if provider and provider not in {"anthropic", "openai"}:
            raise SystemExit(f"Unsupported {profile} provider {provider!r}; use 'anthropic' or 'openai'")
        if provider:
            configured["provider"] = provider
        llm_config.LLM_PROFILES[profile] = configured
    sync = getattr(llm_config, "_sync_legacy_globals", None)
    if callable(sync):
        sync()


# ═══════════════════════════════════════════════════════════════════════════
# Utility helpers
# ═══════════════════════════════════════════════════════════════════════════

def _fast_test_enabled(*sources: Any) -> bool:
    for source in sources:
        if source is not None and bool(getattr(source, "fast_test", False)):
            return True
    return os.environ.get(FAST_TEST_ENV_KEY, "").strip() == "1"


def _normalize_proxy_env(env: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (env or {}).items():
        if value:
            normalized[str(key)] = str(value)
    for upper_key, lower_key in PROXY_ENV_GROUPS:
        value = (
            normalized.get(upper_key)
            or normalized.get(lower_key)
            or os.environ.get(upper_key)
            or os.environ.get(lower_key)
        )
        if not value:
            continue
        normalized.setdefault(upper_key, value)
        normalized.setdefault(lower_key, value)
    return normalized


def load_job_config(path: Path) -> JobConfig:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return JobConfig.model_validate(data)


def load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


# ═══════════════════════════════════════════════════════════════════════════
# API environment setup from ``llm_config.py`` profiles
# - ``train``: task execution during acquisition / training runs
# - ``test``: task execution during held-out evaluation runs
# - ``evolution``: host-side self-evolution and synthesis calls
# ═══════════════════════════════════════════════════════════════════════════

def _apply_task_profile(base_config: Any, profile: str) -> None:
    """Inject one task-execution profile from ``llm_config.py`` into agents."""
    first_agent = base_config.agents[0] if base_config.agents else None
    if first_agent is None:
        raise ValueError("No agent configured in SkillFlow YAML")

    try:
        runtime = resolve_claude_profile_runtime(profile, start_adapter=True)
    except Exception as exc:
        print(f"[V2] {profile.title()} API from llm_config skipped: {exc}")
        raise

    model = runtime.model or ""
    if model:
        try:
            setattr(first_agent, "model_name", model)
        except Exception:
            pass

    env = getattr(first_agent, "env", None)
    if env is None:
        env = {}
        try:
            setattr(first_agent, "env", env)
        except Exception:
            return

    fill_claude_env_from_llm_config(env, profile=profile, start_adapter=False)

    print(
        f"[V2] {profile.title()} API: provider={runtime.provider}, "
        f"model={model}, base_url={runtime.env.get('ANTHROPIC_BASE_URL', '')}"
    )


def _setup_api_env(base_config: Any, task_profile: str = "train") -> None:
    """Load ``llm_config.py`` profiles for task execution and self-evolution.

    ``task_profile`` selects the task-execution profile injected into the agent
    env. Self-evolution and synthesis calls always use the host-side
    ``evolution`` profile.
    """
    first_agent = base_config.agents[0] if base_config.agents else None
    if first_agent is None:
        raise ValueError("No agent configured in SkillFlow YAML")

    # --- Evolution profile (host-side self-evolution / synthesis calls) ---
    try:
        from llm_config import resolve_llm_config
        evo_config = resolve_llm_config(profile="evolution")
        # Profile overrides are explicit configuration. Assignment is
        # intentional here: ``setdefault`` would silently preserve stale
        # process-level credentials/URLs and make CLI or ablation overrides
        # appear to be ignored.
        if evo_config.provider == "openai":
            os.environ["OPENAI_BASE_URL"] = evo_config.base_url
            os.environ["OPENAI_API_KEY"] = evo_config.api_key
        elif evo_config.provider == "anthropic":
            os.environ["ANTHROPIC_BASE_URL"] = evo_config.base_url
            os.environ["ANTHROPIC_API_KEY"] = evo_config.api_key
        print(f"[V2] Evolution API: provider={evo_config.provider}, model={evo_config.model}")
    except Exception as exc:
        print(f"[V2] Evolution API env skipped: {exc}")

    # --- Task-execution profile (train/test) ---
    _apply_task_profile(base_config, task_profile)



def _resolve_dataset_path(dataset_path: Path) -> Path:
    expanded = dataset_path.expanduser()
    if expanded.is_absolute():
        return expanded.resolve()
    return (PROJECT_ROOT / expanded).resolve()


def _load_group_task_ranking(dataset_root: Path) -> list[str] | None:
    ranking_path = dataset_root / "ALL_TASK_DIFFICULTY_RANKING.json"
    if not ranking_path.is_file():
        return None
    data = json.loads(ranking_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Invalid ranking file: {ranking_path}")
    ordered: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        task_name = item.strip()
        if not task_name or task_name in seen:
            continue
        ordered.append(task_name)
        seen.add(task_name)
    return ordered


def _is_valid_task_path(path: Path, disable_verification: bool) -> bool:
    task_paths = TaskPaths(path)
    is_valid = getattr(task_paths, "is_valid", None)
    if callable(is_valid):
        return bool(is_valid(disable_verification=disable_verification))
    base = task_paths.config_path.exists() and task_paths.environment_dir.exists()
    if not base:
        return False
    if task_paths.steps_dir.exists() and task_paths.has_configured_steps():
        return True
    return task_paths.instruction_path.exists() and (
        disable_verification or task_paths.discovered_test_path is not None
    )


def resolve_group_task_paths(dataset_path: Path, disable_verification: bool) -> list[Path]:
    dataset_root = _resolve_dataset_path(dataset_path)
    task_paths = sorted(
        [
            path.resolve()
            for path in dataset_root.iterdir()
            if _is_valid_task_path(path, disable_verification=disable_verification)
        ],
        key=lambda path: path.name,
    )
    if not task_paths:
        raise ValueError(f"No valid tasks found under dataset: {dataset_root}")
    ranking = _load_group_task_ranking(dataset_root)
    if not ranking:
        return task_paths
    task_by_name = {path.name: path for path in task_paths}
    ordered_paths = [task_by_name[name] for name in ranking if name in task_by_name]
    seen = {path.name for path in ordered_paths}
    return ordered_paths + [path for path in task_paths if path.name not in seen]


def _active_skill_slugs(shared_skills_dir: Path, task_family: str) -> list[str]:
    """Resolve the family's canonical evolvable skill."""
    slugs: list[str] = []
    family_slug = resolve_family_skill_slug(shared_skills_dir, task_family)
    if family_slug and family_slug not in slugs:
        slugs.append(family_slug)
    return slugs


def _configure_memory_mcp_agents(config_dict: dict[str, Any], shared_skills_dir: Path) -> bool:
    """Attach the snapshot's read-only memory server to every configured agent."""
    memory_spec = memory_runtime_spec(shared_skills_dir)
    if not memory_spec:
        return False
    server = {
        key: memory_spec[key]
        for key in ("name", "transport", "command", "args")
    }
    for agent in config_dict.get("agents", []):
        configured = agent.setdefault("mcp_servers", [])
        if not any(item.get("name") == server["name"] for item in configured):
            configured.append(server)
    return True


def _build_harbor_job_config(
    base_config: JobConfig,
    group_name: str,
    dataset_path: Path,
    task_paths: list[Path],
    run_root_dir: Path,
    shared_skills_dir: Path,
    cfg: SkillFlowConfig,
    *,
    job_name_override: str | None = None,
    task_profile: str = "train",
    reflection: str | None = None,
) -> JobConfig:
    """Build a Harbor JobConfig with FlatSharedSkillsDockerEnvironment.

    Handles task skill-injection, proxy normalization, and env override in one pass.
    """
    # --- Skill injection: resolve the family skill through its binding. ---
    skill_slugs = _active_skill_slugs(shared_skills_dir, group_name)
    if skill_slugs:
        prepared_root = (
            run_root_dir / ".skill_injected_tasks"
            / sanitize_name(group_name) / "__".join(sanitize_name(slug) for slug in skill_slugs)
        )
        prepared_root.mkdir(parents=True, exist_ok=True)
        prepared_paths: list[Path] = []
        for task_path in task_paths:
            dest = prepared_root / task_path.name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(task_path, dest)
            instruction_path = TaskPaths(dest).instruction_path
            original = instruction_path.read_text(encoding="utf-8") if instruction_path.is_file() else None
            instructions = prepare_task_instruction(
                original,
                skill_slugs,
                reflection,
                memory_available=memory_runtime_spec(shared_skills_dir) is not None,
            )
            if instructions is not None:
                instruction_path.parent.mkdir(parents=True, exist_ok=True)
                instruction_path.write_text(instructions, encoding="utf-8")
            prepared_paths.append(dest)
        task_paths = prepared_paths
        print(f"[SkillFlow] Prepared {len(task_paths)} task(s) with {', '.join('/' + slug for slug in skill_slugs)}")

    # --- Build config dict ---
    config_dict = base_config.model_dump()
    memory_attached = _configure_memory_mcp_agents(config_dict, shared_skills_dir)
    dataset_root = _resolve_dataset_path(dataset_path)
    base_job_name = config_dict.get("job_name", "job")
    config_dict["job_name"] = f"{base_job_name}__{sanitize_name(group_name)}"
    config_dict["jobs_dir"] = str(run_root_dir)
    config_dict["tasks"] = [
        {"path": str(p), "source": group_name} for p in task_paths
    ]
    config_dict["datasets"] = [{"path": str(dataset_root), "n_tasks": 0}]
    orchestrator = config_dict.get("orchestrator") or {}
    orchestrator["n_concurrent_trials"] = 1
    config_dict["orchestrator"] = orchestrator

    # --- Environment: normalize proxy + force FlatSharedSkills ---
    env = config_dict.get("environment") or {}
    env_vars = _normalize_proxy_env(env.get("env"))
    if env_vars:
        env["env"] = env_vars
    env["import_path"] = FLAT_SHARED_SKILLS_ENV_IMPORT
    kwargs = env.get("kwargs") or {}
    kwargs["copy_task_skills"] = cfg.copy_task_skills
    if memory_attached:
        memory_spec = memory_runtime_spec(shared_skills_dir) or {}
        embedding_runtime = ensure_memory_embedding_service(
            str(memory_spec.get("embedding_model") or "") or None
        )
        if embedding_runtime is not None:
            env_vars.update(embedding_runtime.container_env)
            add_no_proxy_host(env_vars, "host.docker.internal")
            env["env"] = env_vars
            kwargs["enable_host_gateway"] = True
    profile_runtime = resolve_claude_profile_runtime(task_profile, start_adapter=False)
    kwargs["llm_adapter_network"] = profile_runtime.env.get(
        "SKILLFLOW_LLM_ADAPTER_NETWORK"
    )
    if profile_runtime.provider == "openai":
        add_no_proxy_host(env_vars, f"llm-adapter-{task_profile.lower()}")
        env["env"] = env_vars
    env["kwargs"] = kwargs
    config_dict["environment"] = env

    group_config = JobConfig.model_validate(config_dict)
    if job_name_override:
        group_config.job_name = job_name_override

    _apply_task_profile(group_config, task_profile)

    # Copy injected env vars from base agents → group config agents
    for index, original_agent in enumerate(base_config.agents):
        for key, value in original_agent.env.items():
            if key not in CLAUDE_API_ENV_KEYS:
                group_config.agents[index].env.update({key: value})

    # Fast-test: limit Claude Code turns
    if _fast_test_enabled(cfg):
        for agent in getattr(group_config, "agents", []) or []:
            if hasattr(agent, "env") and isinstance(agent.env, dict):
                agent.env["CLAUDE_CODE_MAX_TURNS"] = str(FAST_TEST_MAX_TURNS)

    return group_config


# ═══════════════════════════════════════════════════════════════════════════
# Harbor job execution
# ═══════════════════════════════════════════════════════════════════════════

async def _run_harbor_job(
    group_config: Any,
    *,
    work_dir: Path | None = None,
    shared_skills_dir: Path | None = None,
) -> Any:
    job_name = group_config.job_name
    if work_dir is not None and shared_skills_dir is not None:
        SkillFlowExecutor._remove_skills_symlink(work_dir, job_name)
    job = await Job.create(config=group_config)
    if work_dir is not None and shared_skills_dir is not None:
        SkillFlowExecutor._ensure_skills_symlink(work_dir, job_name, shared_skills_dir)
    return await job.run()


# ═══════════════════════════════════════════════════════════════════════════
# Job preparation helpers
# ═══════════════════════════════════════════════════════════════════════════

def _write_family_split_manifest(job_dir: Path, family_name: str, family_split: FamilySplit) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / SPLIT_MANIFEST_FILENAME).write_text(
        json.dumps({
            "family_name": family_name,
            "train_tasks": [p.name for p in family_split.acquisition],
            "test_tasks": [p.name for p in family_split.deployment],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _collect_test_records(job_dir: Path, task_names: set[str]) -> list[dict]:
    records: list[dict] = []
    if not job_dir.exists():
        return records
    round_roots = sorted(path for path in job_dir.glob("round_*") if path.is_dir())
    search_roots = round_roots or [job_dir]
    for root in search_roots:
        for result_json in sorted(root.rglob("result.json")):
            if ".harbor" in result_json.parts:
                continue
            child = result_json.parent
            if not child.is_dir():
                continue
            result_data = load_json_if_exists(result_json) or {}
            config_data = load_json_if_exists(child / "config.json") or {}
            task_config = config_data.get("task") if isinstance(config_data.get("task"), dict) else {}
            raw_path = task_config.get("path")
            task_name = (
                Path(raw_path).name
                if isinstance(raw_path, str) and raw_path.strip()
                else result_data.get("task_name")
            )
            if not isinstance(task_name, str) or task_name not in task_names:
                continue
            records.append({"task_name": task_name, "trial_name": result_data.get("trial_name", child.name)})
    unique_records: dict[tuple[str, str], dict] = {}
    for record in records:
        key = (record["task_name"], record["trial_name"])
        unique_records.setdefault(key, record)
    return list(unique_records.values())


def _iter_harbor_job_files(job_dir: Path) -> list[Path]:
    if not job_dir.is_dir():
        return []
    return [path for path in sorted(job_dir.iterdir()) if path.is_file()]


def _cleanup_empty_harbor_tree(job_dir: Path, harbor_root: Path) -> None:
    current = job_dir
    while current.exists() and current != harbor_root:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
    try:
        harbor_root.rmdir()
    except OSError:
        pass


def _move_harbor_job_metadata(job_dir: Path, meta_dir: Path, job_name: str) -> None:
    meta_dir.mkdir(parents=True, exist_ok=True)
    for src in _iter_harbor_job_files(job_dir):
        dst = meta_dir / f"{job_name}__{src.name}"
        if dst.exists():
            continue
        shutil.move(str(src), str(dst))


def _write_test_progress(job_dir: Path, family_name: str, test_tasks: list[Path]) -> str:
    test_task_names = {path.name for path in test_tasks}
    records = _collect_test_records(job_dir / "test", test_task_names)
    completed = {r["task_name"] for r in records}
    pending = [path.name for path in test_tasks if path.name not in completed]
    (job_dir / TEST_PROGRESS_FILENAME).write_text(
        json.dumps({
            "family_name": family_name,
            "planned_test_tasks": [path.name for path in test_tasks],
            "planned_test_trials": len(test_tasks),
            "completed_test_trials": len(records),
            "pending_test_tasks": pending,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return f"test: {len(records)}/{len(test_tasks)} trial(s) done"


def _prepare_skill_version_store(
    job_dir: Path,
    task_family: str,
    train_tasks: list[Path] | None = None,
    *,
    initialization: str = "task-derived",
) -> Path:
    store_dir = job_dir / "skill_versions"
    initial = prepare_initial_family_skill_store(
        store_dir,
        task_family,
        train_tasks or [],
        initialization=initialization,
    )
    if initialization == "task-derived" and train_tasks and initial.version_label == "v000":
        print("[SkillFlow] Initial family skill: generated")
    elif initialization == "scaffold":
        print("[SkillFlow] Initial family skill: fixed scaffold (no train task content)")
    print(
        f"[SkillFlow] Prepared skill version store at {store_dir} "
        f"({initial.version_label}, hash={hash_skill_tree(initial.skills_dir)[:12]})"
    )
    return store_dir


def _group_skillflow_tasks_by_family(
    task_paths: list[Path],
    dataset_path: Path | None = None,
) -> dict[str, list[Path]]:
    family_name = dataset_path.name if dataset_path is not None else "default"
    return {family_name: list(task_paths)}


def _load_skillflow_family_split(
    split_path: Path,
    family_groups: dict[str, list[Path]],
) -> dict[str, FamilySplit] | None:
    if not split_path.is_file():
        return None

    data = json.loads(split_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid split manifest: {split_path}")

    families_data = data.get("families")
    if not isinstance(families_data, dict):
        raise ValueError(f"Invalid family split payload: {split_path}")

    families: dict[str, FamilySplit] = {}
    for family_name, family_tasks in family_groups.items():
        payload = families_data.get(family_name)
        if payload is None:
            continue
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid split entry for family '{family_name}' in {split_path}")
        task_by_name = {path.name: path for path in family_tasks}

        def _resolve(names_key: str) -> list[Path]:
            names = payload.get(names_key, [])
            if not isinstance(names, list):
                raise ValueError(
                    f"Invalid '{names_key}' list for family '{family_name}' in {split_path}"
                )
            resolved: list[Path] = []
            for raw_name in names:
                task_name = str(raw_name)
                task_path = task_by_name.get(task_name)
                if task_path is None:
                    raise ValueError(
                        f"Split manifest {split_path} references missing task "
                        f"'{task_name}' in family '{family_name}'"
                    )
                resolved.append(task_path)
            return resolved

        acquisition = _resolve("train_tasks")
        deployment = _resolve("test_tasks")
        probe = _resolve("probe_tasks") if "probe_tasks" in payload else []
        families[family_name] = FamilySplit(
            family_name=family_name,
            acquisition=acquisition,
            deployment=deployment,
            probe=probe,
        )

    return families


def _build_task_refs(task_paths: list[Path], family_name: str) -> list[TaskRef]:
    return [
        TaskRef(name=path.name, family=family_name, source_path=path)
        for path in task_paths
    ]


def _chunk_tasks(tasks: list[TaskRef], batch_size: int) -> list[list[TaskRef]]:
    size = max(batch_size, 1)
    return [tasks[i:i + size] for i in range(0, len(tasks), size)]


def _build_task_job_name(base_job_name: str, task_name: str) -> str:
    return f"{base_job_name}__{sanitize_name(task_name)}"


# ═══════════════════════════════════════════════════════════════════════════
# Per-task isolation (parallel batch workers)
# ═══════════════════════════════════════════════════════════════════════════

def _run_isolated_task_attempt(
    *,
    task: TaskRef,
    base_config: Any,
    base_job_name: str,
    group_name: str,
    dataset_path: Path,
    cfg: SkillFlowConfig,
    shared_skills_dir: Path,
    work_dir: Path,
    reflection: str | None = None,
    task_profile: str = "train",
) -> BatchTrialResult:
    """Run one isolated Harbor job for one task attempt."""
    work_dir.mkdir(parents=True, exist_ok=True)

    job_name = _build_task_job_name(base_job_name, task.name)
    group_config = _build_harbor_job_config(
        base_config, group_name, dataset_path,
        [task.source_path],
        SkillFlowExecutor._harbor_root(work_dir),
        shared_skills_dir, cfg,
        job_name_override=job_name,
        task_profile=task_profile,
        reflection=reflection,
    )
    attempt_label = "retry" if reflection else "initial"
    print(
        f"[SkillFlow] Launching Harbor job '{group_config.job_name}' "
        f"for task '{task.name}' ({attempt_label})"
    )
    job_result = asyncio.run(
        _run_harbor_job(group_config, work_dir=work_dir, shared_skills_dir=shared_skills_dir)
    )
    print(f"[SkillFlow] Harbor done for '{task.name}': {len(job_result.trial_results)} trial(s)")
    SkillFlowExecutor._flatten_job_trials(work_dir, group_config.job_name)

    results = SkillFlowExecutor._collect_results_from_dir(work_dir, group_config.job_name, [task])
    if results:
        return results[0]
    return BatchTrialResult(
        task_name=task.name, trial_name="", trial_dir=work_dir,
        success=False, exception_info="task attempt produced no results",
    )


def _run_parallel_task_job(
    index: int,
    task: TaskRef,
    *,
    base_config: Any,
    base_job_name: str,
    group_name: str,
    dataset_path: Path,
    cfg: SkillFlowConfig,
    shared_skills_dir: Path,
    work_dir: Path,
    max_retries: int,
    task_family: str,
) -> tuple[int, BatchTrialResult]:
    """Process worker: run one task to completion, including inline retries."""
    task_work_dir = work_dir / f"task_{index + 1:02d}_{sanitize_name(task.name)}"
    task_work_dir.mkdir(parents=True, exist_ok=True)

    result = _run_isolated_task_attempt(
        task=task, base_config=base_config, base_job_name=base_job_name,
        group_name=group_name, dataset_path=dataset_path, cfg=cfg,
        shared_skills_dir=shared_skills_dir, work_dir=task_work_dir,
    )

    family_name = task_family or group_name

    def retry(reflection: str, retry_number: int) -> BatchTrialResult:
        retry_dir = task_work_dir / f"retry_{retry_number:02d}"
        retry_dir.mkdir(parents=True, exist_ok=True)
        return _run_isolated_task_attempt(
            task=task, base_config=base_config, base_job_name=base_job_name,
            group_name=group_name, dataset_path=dataset_path, cfg=cfg,
            shared_skills_dir=shared_skills_dir, work_dir=retry_dir,
            reflection=reflection,
        )

    result = run_reflection_retry_loop(
        result,
        task_name=task.name,
        task_family=family_name,
        max_retries=max_retries,
        retry=retry,
        log_prefix="SkillFlow",
    )
    return index, result


# ═══════════════════════════════════════════════════════════════════════════
# SkillFlow batch executor
# ═══════════════════════════════════════════════════════════════════════════

class SkillFlowExecutor(BatchExecutor):
    """Execute batches of SkillFlow tasks via Harbor, with reflection retries."""

    def __init__(
        self,
        base_config: Any,
        group_name: str,
        dataset_path: Path,
        cfg: SkillFlowConfig,
    ):
        self._base_config = base_config
        self._base_job_name = base_config.job_name or "job"
        self._group_name = group_name
        self._dataset_path = dataset_path
        self._cfg = cfg

    # ------------------------------------------------------------------
    # BatchExecutor interface
    # ------------------------------------------------------------------

    def execute_batch(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
    ) -> list[BatchTrialResult]:
        """Run a batch of tasks via Harbor and return per-task results."""
        concurrency = max(1, self._cfg.batch_concurrency)
        if concurrency > 1 and len(tasks) > 1:
            return self._execute_batch_parallel(tasks, shared_skills_dir, work_dir, concurrency)

        task_paths = [t.source_path for t in tasks]
        group_config = _build_harbor_job_config(
            self._base_config, self._group_name, self._dataset_path,
            task_paths,
            self._harbor_root(work_dir),
            shared_skills_dir, self._cfg,
            task_profile="train",
        )

        skill_md = shared_skills_dir / "SKILL.md"
        script_count = len(list((shared_skills_dir / "scripts").glob("*.py"))) if (shared_skills_dir / "scripts").is_dir() else 0
        print(f"[SkillFlow] Skills: SKILL.md={'present' if skill_md.is_file() else 'ABSENT'}, "
              f"scripts={script_count} → injecting via FlatSharedSkillsDockerEnvironment")
        print(f"[SkillFlow] Launching Harbor job '{group_config.job_name}' "
              f"with {len(task_paths)} task(s)...")
        job_result = asyncio.run(
            _run_harbor_job(group_config, work_dir=work_dir, shared_skills_dir=shared_skills_dir)
        )
        print(f"[SkillFlow] Harbor done: {len(job_result.trial_results)} trial(s)")
        self._flatten_job_trials(work_dir, group_config.job_name)

        return self._collect_results(work_dir, group_config.job_name, tasks)

    def execute_batch_with_retries(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
        *,
        task_family: str,
        max_retries: int,
    ) -> list[BatchTrialResult]:
        """Keep retries inside each task worker when the batch is parallelized."""
        concurrency = max(1, self._cfg.batch_concurrency)
        if concurrency > 1 and len(tasks) > 1:
            return self._execute_batch_parallel(
                tasks, shared_skills_dir, work_dir, concurrency,
                max_retries=max_retries, task_family=task_family,
            )
        return self.execute_batch(tasks, shared_skills_dir, work_dir)

    def retry_one(
        self,
        task: TaskRef,
        shared_skills_dir: Path,
        work_dir: Path,
        reflection: str,
        *,
        task_profile: str = "train",
    ) -> BatchTrialResult:
        """Retry a single failed task with reflection guidance."""
        print(f"[SkillFlow] Retrying '{task.name}' with reflection...")
        return _run_isolated_task_attempt(
            task=task,
            base_config=self._base_config,
            base_job_name=self._base_job_name,
            group_name=self._group_name,
            dataset_path=self._dataset_path,
            cfg=self._cfg,
            shared_skills_dir=shared_skills_dir,
            work_dir=work_dir,
            reflection=reflection,
            task_profile=task_profile,
        )

    # ------------------------------------------------------------------
    # Parallel execution
    # ------------------------------------------------------------------

    def _execute_batch_parallel(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
        concurrency: int,
        *,
        max_retries: int = 0,
        task_family: str = "",
    ) -> list[BatchTrialResult]:
        """Fan out one Harbor job per task and run them concurrently."""
        print(f"[SkillFlow] Parallel batch: {len(tasks)} task(s), concurrency={concurrency}")
        results: list[BatchTrialResult | None] = [None] * len(tasks)

        max_workers = min(concurrency, len(tasks))
        ctx = multiprocessing.get_context("spawn")
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers, mp_context=ctx,
        ) as executor:
            future_map = {
                executor.submit(
                    _run_parallel_task_job,
                    index, task,
                    base_config=self._base_config,
                    base_job_name=self._base_job_name,
                    group_name=self._group_name,
                    dataset_path=self._dataset_path,
                    cfg=self._cfg,
                    shared_skills_dir=shared_skills_dir,
                    work_dir=work_dir,
                    max_retries=max_retries,
                    task_family=task_family or self._group_name,
                ): index
                for index, task in enumerate(tasks)
            }
            for future in concurrent.futures.as_completed(future_map):
                index, result = future.result()
                results[index] = result

        return [
            result if result is not None else BatchTrialResult(
                task_name=tasks[index].name, trial_name="", trial_dir=work_dir,
                success=False, exception_info="parallel batch result missing",
            )
            for index, result in enumerate(results)
        ]

    # ------------------------------------------------------------------
    # Harbor layout helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _harbor_root(work_dir: Path) -> Path:
        return work_dir / ".harbor"

    @staticmethod
    def _remove_skills_symlink(work_dir: Path, job_name: str) -> None:
        link = SkillFlowExecutor._harbor_root(work_dir) / job_name / "shared_skills"
        if link.is_symlink():
            link.unlink()

    @staticmethod
    def _ensure_skills_symlink(work_dir: Path, job_name: str, skills_dir: Path) -> None:
        job_dir = SkillFlowExecutor._harbor_root(work_dir) / job_name
        job_dir.mkdir(parents=True, exist_ok=True)
        link = job_dir / "shared_skills"
        if link.exists():
            if link.is_symlink():
                return
            try:
                if not any(link.iterdir()):
                    link.rmdir()
            except Exception:
                pass
        if not link.exists():
            link.symlink_to(skills_dir.resolve(), target_is_directory=True)

    @staticmethod
    def _flatten_job_trials(work_dir: Path, job_name: str) -> None:
        harbor_root = SkillFlowExecutor._harbor_root(work_dir)
        job_dir = harbor_root / job_name
        if not job_dir.is_dir():
            return
        for child in sorted(job_dir.iterdir()):
            if not child.is_dir() or not (child / "result.json").is_file():
                continue
            dest = work_dir / child.name
            if dest.exists():
                continue
            shutil.move(str(child), str(dest))
        meta_dir = work_dir / ".harbor"
        _move_harbor_job_metadata(job_dir, meta_dir, job_name)
        try:
            shared_skills_link = job_dir / "shared_skills"
            if shared_skills_link.is_symlink():
                shared_skills_link.unlink()
        except OSError:
            pass
        _cleanup_empty_harbor_tree(job_dir, harbor_root)

    # ------------------------------------------------------------------
    # Result collection
    # ------------------------------------------------------------------

    def _collect_results(
        self, work_dir: Path, job_name: str, tasks: list[TaskRef],
    ) -> list[BatchTrialResult]:
        return self._collect_results_from_dir(work_dir, job_name, tasks)

    @staticmethod
    def _collect_results_from_dir(
        work_dir: Path, job_name: str, tasks: list[TaskRef],
    ) -> list[BatchTrialResult]:
        job_dir = work_dir
        fallback_job_dir = SkillFlowExecutor._harbor_root(work_dir) / job_name
        results: list[BatchTrialResult] = []

        task_by_name: dict[str, TaskRef] = {}
        for t in tasks:
            task_by_name[t.name] = t
            task_by_name[t.source_path.name] = t

        if not job_dir.is_dir():
            return results

        trial_dirs = [
            child for child in sorted(job_dir.iterdir())
            if child.is_dir() and child.name != job_name and (child / "result.json").is_file()
        ]
        if not trial_dirs and fallback_job_dir.is_dir():
            trial_dirs = [
                child for child in sorted(fallback_job_dir.iterdir())
                if child.is_dir() and (child / "result.json").is_file()
            ]

        for child in trial_dirs:
            if not child.is_dir():
                continue
            result_json = child / "result.json"
            if not result_json.is_file():
                continue
            result_data = load_json_if_exists(result_json)
            if result_data is None:
                continue

            config_data = load_json_if_exists(child / "config.json") or {}
            task_cfg = config_data.get("task") if isinstance(config_data.get("task"), dict) else {}
            raw_path = task_cfg.get("path", "")
            task_name = (
                Path(raw_path).name
                if isinstance(raw_path, str) and raw_path.strip()
                else result_data.get("task_name", child.name)
            )

            exception_info = result_data.get("exception_info") or None
            if isinstance(exception_info, dict):
                exception_info = str(exception_info)

            reward = 0.0
            verifier = result_data.get("verifier_result") or {}
            if isinstance(verifier, dict):
                rewards = verifier.get("rewards") or {}
                if isinstance(rewards, dict):
                    reward = float(rewards.get("reward", 0) or 0)
            if reward == 0.0:
                reward = float(result_data.get("reward", 0) or 0)
            if _fast_test_enabled():
                reward = FAST_TEST_REWARD
                exception_info = None
                success = True
            else:
                success = exception_info is None and reward >= 1.0

            traj_path = None
            for candidate in [
                child / "agent" / "trajectory.json",
                child / "agent" / "claude_code.txt",
            ]:
                if candidate.is_file():
                    traj_path = candidate
                    break

            outcome = normalize_harbor_outcome(
                result_data=result_data,
                trial_dir=child,
                task_name=str(task_name),
                task_source=task_by_name.get(str(task_name), TaskRef(str(task_name), "", child)).family,
                success=success,
                reward=reward,
                exception_info=exception_info,
                task_contract=build_task_contract(
                    task_by_name.get(str(task_name), TaskRef(str(task_name), "", child)).source_path,
                    task_source=task_by_name.get(str(task_name), TaskRef(str(task_name), "", child)).family,
                ),
                compacted_trajectory=compact_claude_trajectory(child),
            )
            results.append(BatchTrialResult(
                task_name=str(task_name),
                trial_name=result_data.get("trial_name", child.name),
                trial_dir=child,
                success=success,
                reward=reward,
                exception_info=exception_info,
                trajectory_path=traj_path,
                outcome=outcome,
            ))

        return results


# ═══════════════════════════════════════════════════════════════════════════
# Held-out test execution
# ═══════════════════════════════════════════════════════════════════════════

def _run_test_batch_once(
    *,
    executor: SkillFlowExecutor,
    batch: list[TaskRef],
    shared_skills_dir: Path,
    work_dir: Path,
    group_config: Any,
) -> list[BatchTrialResult]:
    """Run each held-out task once with the supplied frozen skills snapshot."""
    job_name = group_config.job_name
    job_result = asyncio.run(
        _run_harbor_job(group_config, work_dir=work_dir, shared_skills_dir=shared_skills_dir)
    )
    print(f"[Test] Harbor done: {len(job_result.trial_results)} trial(s)")
    executor._flatten_job_trials(work_dir, job_name)

    results_by_task = {
        result.task_name: result
        for result in executor._collect_results(work_dir, job_name, batch)
    }
    final_results: list[BatchTrialResult] = []
    for task in batch:
        result = results_by_task.get(task.name)
        if result is None:
            result = BatchTrialResult(
                task_name=task.name,
                trial_name="",
                trial_dir=work_dir,
                success=False,
                exception_info="test attempt produced no results",
            )
        final_results.append(result)

    return final_results


def _run_test_phase(
    executor: SkillFlowExecutor,
    test_tasks: list[TaskRef],
    shared_skills_dir: Path,
    job_dir: Path,
    batch_size: int,
    *,
    base_config: Any,
    group_name: str,
    dataset_path: Path,
    cfg: SkillFlowConfig,
) -> tuple[int, int]:
    """Run held-out test tasks with the final skills, without evolution."""
    if not test_tasks:
        return 0, 0

    test_root = job_dir / "test"
    test_root.mkdir(parents=True, exist_ok=True)

    successful = 0
    total = len(test_tasks)
    batches = _chunk_tasks(test_tasks, batch_size)

    for batch_index, batch in enumerate(batches, start=1):
        work_dir = test_root / f"round_{batch_index:02d}"
        work_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n[Test] Round {batch_index}: {len(batch)} held-out task(s)")
        task_paths = [t.source_path for t in batch]
        group_config = _build_harbor_job_config(
            base_config,
            group_name,
            dataset_path,
            task_paths,
            executor._harbor_root(work_dir),
            shared_skills_dir,
            cfg,
            task_profile="test",
        )
        results = _run_test_batch_once(
            executor=executor,
            batch=batch,
            shared_skills_dir=shared_skills_dir,
            work_dir=work_dir,
            group_config=group_config,
        )
        for task, result in zip(batch, results):
            if result.success:
                successful += 1
                print(f"[Test] OK   {task.name} (reward={result.reward:.1f})")
            else:
                reason = result.exception_info or f"reward={result.reward:.1f}"
                print(f"[Test] FAIL {task.name}: {reason}")

    return successful, total


def _run_family_train_phase(
    *,
    base_config: Any,
    dataset_path: Path,
    cfg: SkillFlowConfig,
    family_name: str,
    family_split: FamilySplit,
    family_job_dir: Path,
    skill_versions_dir: Path,
) -> tuple[Any, Any]:
    # Paper-aligned Table2 methods require one shared representation bundle
    # across all conditions, which this training entrypoint cannot construct.
    method_adapter = None
    if cfg.table2_method:
        raise ValueError(
            "--table2-method is not supported by run_skillflow_evolution.py; "
            "use `python Table2/run_table2_from_logs.py` so all methods share "
            "the same reflection bundle and provenance"
        )

    train_task_refs = _build_task_refs(family_split.acquisition, family_name)
    executor = SkillFlowExecutor(
        base_config=base_config,
        group_name=family_name,
        dataset_path=dataset_path,
        cfg=cfg,
    )
    loop = BatchEvolutionLoop(
        executor=executor,
        config=cfg.evolution,
        task_family=family_name,
        skills_dir=skill_versions_dir,
        policy=EvolutionPolicy(
            include_failure_evidence=cfg.evolution.include_failure_evidence,
            strict_cross_task=cfg.evolution.strict_cross_task,
            require_policy_use=cfg.evolution.require_policy_use,
            immediate_promotion=cfg.evolution.immediate_promotion,
        ),
        min_occurrences=cfg.evolution.min_occurrences,
        verbose=True,
        method_adapter=method_adapter,  # Pass Table2 method adapter
    )

    print(f"\n{'=' * 60}")
    print(f"[SkillFlow] TRAIN family={family_name}")
    print(f"[SkillFlow] train_tasks={len(family_split.acquisition)} test_tasks={len(family_split.deployment) + len(family_split.probe)}")
    print(f"[SkillFlow] skill_versions={skill_versions_dir}")
    print(
        f"[SkillFlow] train_epochs={cfg.evolution.train_epochs} "
        f"batch_size={cfg.evolution.batch_size} max_retries={cfg.evolution.max_retries}"
    )
    print(f"{'=' * 60}")

    summary = loop.run(train_task_refs)
    final_version = freeze_final_version(skill_versions_dir, get_latest_skill_version(skill_versions_dir))
    return summary, final_version


def _run_family_test_phase(
    *,
    base_config: Any,
    dataset_path: Path,
    cfg: SkillFlowConfig,
    family_name: str,
    family_split: FamilySplit,
    family_job_dir: Path,
    final_skills_dir: Path,
) -> tuple[int, int, str]:
    runtime_skills_dir = prepare_runtime_skills(
        final_skills_dir,
        family_job_dir / "test" / "runtime_skills",
        final_skills_dir.parents[2] / MEMORY_STORE_FILENAME,
    )
    executor = SkillFlowExecutor(
        base_config=base_config,
        group_name=family_name,
        dataset_path=dataset_path,
        cfg=cfg,
    )
    test_task_refs = _build_task_refs(family_split.deployment + family_split.probe, family_name)
    test_successful, test_total = _run_test_phase(
        executor=executor,
        test_tasks=test_task_refs,
        shared_skills_dir=runtime_skills_dir,
        job_dir=family_job_dir,
        batch_size=cfg.evolution.batch_size,
        base_config=base_config,
        group_name=family_name,
        dataset_path=dataset_path,
        cfg=cfg,
    )
    test_progress = _write_test_progress(
        family_job_dir,
        family_name,
        family_split.deployment + family_split.probe,
    )
    return test_successful, test_total, test_progress


# ═══════════════════════════════════════════════════════════════════════════
# Core: run batch → evolve skills
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_run_root_dir(requested_root: Path | None) -> Path:
    if requested_root is not None:
        expanded = Path(requested_root).expanduser()
        if expanded.is_absolute():
            return expanded.resolve()
        return (PROJECT_ROOT / expanded).resolve()
    return DEFAULT_RUN_ROOT.resolve()


# ═══════════════════════════════════════════════════════════════════════════
# Multi-group orchestration (subprocess isolation)
# ═══════════════════════════════════════════════════════════════════════════

def _render_progress(completed: int, total: int, width: int = 30) -> str:
    if total <= 0:
        return "[------------------------------] 0/0"
    ratio = min(max(completed / total, 0.0), 1.0)
    filled = int(width * ratio)
    return f"[{'#' * filled + '-' * (width - filled)}] {completed}/{total} ({ratio:.1%})"


def _parse_subprocess_result(stdout: str) -> RunResult | None:
    lines = [l for l in stdout.splitlines() if l.strip()]
    if not lines or not lines[-1].startswith("{"):
        return None
    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return RunResult(
        group_name=data.get("group_name", ""),
        job_name=data.get("job_name", ""),
        job_dir=Path(data.get("job_dir", "")),
        success=bool(data.get("success", False)),
        message=data.get("message", ""),
    )


def _relay_stream(stream: Any, collected: list[str], target: Any) -> None:
    try:
        for line in iter(stream.readline, ""):
            collected.append(line)
            print(line, end="", file=target, flush=True)
    finally:
        stream.close()


def _run_subprocess_streaming(cmd: list[str], *, cwd: Path, env: dict[str, str]) -> tuple[int, str, str]:
    process = subprocess.Popen(cmd, cwd=cwd, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, bufsize=1)
    out_lines: list[str] = []
    err_lines: list[str] = []
    t1 = threading.Thread(target=_relay_stream, args=(process.stdout, out_lines, sys.stdout), daemon=True)
    t2 = threading.Thread(target=_relay_stream, args=(process.stderr, err_lines, sys.stderr), daemon=True)
    t1.start(); t2.start()
    rc = process.wait()
    t1.join(); t2.join()
    return rc, "".join(out_lines), "".join(err_lines)


def run_group_in_subprocess(
    base_config_path: Path, group_name: str, dataset_path: Path, cfg: SkillFlowConfig,
) -> RunResult:
    base_config = load_job_config(base_config_path)
    base_job_name = base_config.job_name or "job"
    job_name = f"{base_job_name}__{sanitize_name(group_name)}"
    run_root = _resolve_run_root_dir(cfg.run_root_dir)

    cmd = [
        sys.executable, str(ENTRYPOINT),
        "--only-family", group_name,
        "--config", str(base_config_path),
        "--dataset-path", str(dataset_path),
        "--batch-size", str(cfg.evolution.batch_size),
        "--batch-concurrency", str(cfg.batch_concurrency),
        "--max-retries", str(cfg.evolution.max_retries),
        "--train-epochs", str(cfg.evolution.train_epochs),
        "--train-shuffle-seed", str(cfg.evolution.train_shuffle_seed),
        "--min-reward", str(cfg.evolution.min_reward),
        "--min-occurrences", str(cfg.evolution.min_occurrences),
        "--demotion-threshold", str(cfg.evolution.demotion_threshold),
        "--max-evolution-workers", str(cfg.evolution.max_evolution_workers),
        "--failure-evidence", "on" if cfg.evolution.include_failure_evidence else "off",
        "--qualification", "strict-cross-task" if cfg.evolution.require_policy_use else "outcome-only",
        "--promotion", "immediate" if cfg.evolution.immediate_promotion else "delayed",
        "--initialization", cfg.initialization,
    ]
    if cfg.evolution.provider:
        cmd.extend(["--evolution-provider", cfg.evolution.provider])
    if cfg.evolution.model:
        cmd.extend(["--evolution-model", cfg.evolution.model])
    for profile, values in (cfg.llm_overrides or {}).items():
        label = profile.replace("_", "-")
        for key, option in (("provider", "provider"), ("model", "model"),
                            ("base_url", "base-url"), ("api_key", "api-key")):
            if values.get(key):
                cmd.extend([f"--{label}-llm-{option}", str(values[key])])
    if cfg.copy_task_skills:
        cmd.append("--copy-task-skills")
    if _fast_test_enabled(cfg):
        cmd.append("--fast-test")
    if cfg.run_root_dir:
        cmd.extend(["--run-root-dir", str(cfg.run_root_dir)])

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    if _fast_test_enabled(cfg):
        env[FAST_TEST_ENV_KEY] = "1"
    rc, stdout, stderr = _run_subprocess_streaming(cmd, cwd=PROJECT_ROOT, env=env)

    parsed = _parse_subprocess_result(stdout)
    if parsed is not None:
        return parsed
    if rc == 0:
        return RunResult(group_name, job_name, run_root / job_name, True, stdout)
    return RunResult(group_name, job_name, run_root / job_name, False,
                     f"Subprocess failed (rc={rc}):\nstdout:\n{stdout}\nstderr:\n{stderr}")


def run_all_groups(
    base_config_path: Path, base_config: Any, cfg: SkillFlowConfig,
) -> list[RunResult]:
    if cfg.batch_concurrency < 1:
        raise ValueError("--batch-concurrency must be >= 1")
    if cfg.family_concurrency < 1:
        raise ValueError("--family-concurrency must be >= 1")

    cfg.run_root_dir = _resolve_run_root_dir(cfg.run_root_dir)
    cfg.run_root_dir.mkdir(parents=True, exist_ok=True)
    print(f"Run output: {cfg.run_root_dir}")

    datasets = base_config.datasets or []
    if not datasets:
        raise ValueError("No datasets in config.")

    results: list[RunResult] = []
    family_jobs = [
        (Path(dataset.path).name, Path(dataset.path))
        for dataset in datasets
    ]
    if cfg.skip_existing_family:
        pending_jobs = []
        skipped_families = []
        for group_name, dataset_path in family_jobs:
            family_dir = cfg.run_root_dir / f"{base_config.job_name or 'job'}__{sanitize_name(group_name)}"
            if (family_dir / "result.json").is_file():
                print(f"[SkillFlow] Skip existing family: {group_name} (result exists at {family_dir})")
                skipped_families.append(group_name)
            else:
                pending_jobs.append((group_name, dataset_path))
        if skipped_families:
            print(f"[SkillFlow] Skipped {len(skipped_families)} existing famil{'y' if len(skipped_families) == 1 else 'ies'}: {', '.join(skipped_families)}")
        family_jobs = pending_jobs
    total = len(family_jobs)
    concurrency = min(cfg.family_concurrency, total) if total else 1
    if concurrency == 1:
        completed = 0
        for group_name, dataset_path in family_jobs:
            result = run_group_in_subprocess(base_config_path, group_name, dataset_path, cfg)
            results.append(result)
            completed += 1
            status = "OK" if result.success else "FAIL"
            msg = result.message[:200] if result.success else result.message
            print(f"\n{status} [{_render_progress(completed, total)}] {result.group_name}: {msg}")
    else:
        print(f"[SkillFlow] Parallel families: {total} family(s), concurrency={concurrency}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = {
                pool.submit(run_group_in_subprocess, base_config_path, group_name, dataset_path, cfg): group_name
                for group_name, dataset_path in family_jobs
            }
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                status = "OK" if result.success else "FAIL"
                msg = result.message[:200] if result.success else result.message
                print(f"\n{status} [{_render_progress(completed, total)}] {result.group_name}: {msg}")

    ok = sum(1 for r in results if r.success)
    print(f"\nDone: {ok}/{len(results)} groups succeeded.")
    return results


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    """Parse all CLI arguments — SkillFlow-specific + evolution (shared)."""
    parser = argparse.ArgumentParser(
        description="Run SkillFlow benchmarks with skill self-evolution"
    )
    # Config / dataset
    parser.add_argument(
        "-c", "--config", type=Path,
        default=PROJECT_ROOT / "configs" / "myevolution.yaml",
    )
    parser.add_argument(
        "--dataset-path", type=Path,
        default=None,
    )
    # Execution
    parser.add_argument(
        "--run-root-dir", type=Path, default=DEFAULT_RUN_ROOT,
        help="Run artifacts root directory (default: runs/skillflow)",
    )
    for profile in ("train", "evolution", "test"):
        label = profile.replace("_", "-")
        parser.add_argument(f"--{label}-llm-provider", choices=("anthropic", "openai"))
        parser.add_argument(f"--{label}-llm-model")
        parser.add_argument(f"--{label}-llm-base-url")
        parser.add_argument(f"--{label}-llm-api-key")
    parser.add_argument(
        "--batch-concurrency", type=int, default=3,
        help="Max tasks in parallel inside one batch (1 = serial)",
    )
    parser.add_argument(
        "--family-concurrency", type=int, default=2,
        help="Max independent family subprocesses in parallel (1 = serial)",
    )
    parser.add_argument(
        "--skip-existing-family", action=argparse.BooleanOptionalAction, default=False,
        help="Skip families whose output directory already exists",
    )
    parser.add_argument("--copy-task-skills", action="store_true")
    parser.add_argument(
        "--fast-test", action="store_true",
        help="Limit Claude Code to 5 turns and force reward=1.0",
    )
    # Table 2 method integration
    parser.add_argument(
        "--table2-method",
        choices=["flat_policy", "reflective_memory", "consolidated_memory",
                 "skill_raw_memory", "skill_local_policy"],
        default=None,
        help="Deprecated; use Table2/run_table2_from_logs.py for matched-information evaluation",
    )
    # Evolution (shared)
    add_evolution_arguments(parser)
    # Group execution
    parser.add_argument("--only-family", default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def _cfg_from_args(args: argparse.Namespace) -> SkillFlowConfig:
    llm_overrides = {
        profile: {
            key: value for key in ("provider", "model", "base_url", "api_key")
            if (value := getattr(args, f"{profile}_llm_{key}", None))
        }
        for profile in ("train", "evolution", "test")
    }
    return SkillFlowConfig(
        evolution=evolution_config_from_args(args),
        run_root_dir=args.run_root_dir,
        batch_concurrency=args.batch_concurrency,
        family_concurrency=args.family_concurrency,
        copy_task_skills=args.copy_task_skills,
        fast_test=bool(args.fast_test),
        skip_existing_family=args.skip_existing_family,
        initialization=args.initialization,
        llm_overrides=llm_overrides,
        table2_method=getattr(args, "table2_method", None),
    )



def main() -> None:
    args = parse_args()
    _apply_llm_overrides({
        profile: {
            key: value for key in ("provider", "model", "base_url", "api_key")
            if (value := getattr(args, f"{profile}_llm_{key}", None))
        }
        for profile in ("train", "evolution", "test")
    })
    cfg = _cfg_from_args(args)

    if cfg.fast_test:
        os.environ[FAST_TEST_ENV_KEY] = "1"
    else:
        os.environ.pop(FAST_TEST_ENV_KEY, None)

    base_config = load_job_config(args.config)
    if args.only_family:
        if not args.dataset_path:
            raise SystemExit("--dataset-path required with --only-family")

        _setup_api_env(base_config, task_profile="train")
        run_root_dir = _resolve_run_root_dir(cfg.run_root_dir)
        run_root_dir.mkdir(parents=True, exist_ok=True)
        dataset_path = Path(args.dataset_path)
        disable_verification = bool(
            (base_config.model_dump().get("verifier") or {}).get("disable", False)
        )
        task_paths = resolve_group_task_paths(
            dataset_path, disable_verification=disable_verification
        )
        family_name = args.only_family
        family_groups = _group_skillflow_tasks_by_family(task_paths, dataset_path)
        if family_name not in family_groups:
            raise SystemExit(f"Family '{family_name}' not found in dataset {dataset_path}")
        loaded_families = _load_skillflow_family_split(SKILLFLOW_FAMILY_SPLITS_PATH, family_groups)
        if loaded_families is None:
            raise SystemExit(
                f"Missing canonical SkillFlow split file: {SKILLFLOW_FAMILY_SPLITS_PATH}"
            )
        if family_name not in loaded_families:
            raise SystemExit(
                f"Canonical SkillFlow split file {SKILLFLOW_FAMILY_SPLITS_PATH} "
                f"does not define family '{family_name}'"
            )
        family_split = loaded_families[family_name]
        base_job_name = base_config.job_name or "job"

        print(f"\n{'=' * 60}")
        print(f"[SkillFlow] Family: {family_name}")
        if _fast_test_enabled(cfg):
            print(f"[SkillFlow] Fast test: enabled (Claude max turns={FAST_TEST_MAX_TURNS}, forced reward={FAST_TEST_REWARD:.1f})")
        print(f"{'=' * 60}")

        family_job_dir = run_root_dir / f"{base_job_name}__{sanitize_name(family_name)}"
        if cfg.skip_existing_family and family_job_dir.exists():
            print(f"[SkillFlow] Skip existing family: {family_name} ({family_job_dir})")
            raise SystemExit(0)
        family_job_dir.mkdir(parents=True, exist_ok=True)
        _write_family_split_manifest(family_job_dir, family_name, family_split)
        skill_versions_dir = _prepare_skill_version_store(
            family_job_dir,
            family_name,
            train_tasks=family_split.acquisition,
            initialization=cfg.initialization,
        )

        try:
            summary, final_version = _run_family_train_phase(
                base_config=base_config,
                dataset_path=dataset_path,
                cfg=cfg,
                family_name=family_name,
                family_split=family_split,
                family_job_dir=family_job_dir,
                skill_versions_dir=skill_versions_dir,
            )
            test_successful, test_total, test_progress = _run_family_test_phase(
                base_config=base_config,
                dataset_path=dataset_path,
                cfg=cfg,
                family_name=family_name,
                family_split=family_split,
                family_job_dir=family_job_dir,
                final_skills_dir=final_version.skills_dir,
            )
            overall = RunResult(
                group_name=family_name,
                job_name=f"{base_job_name}__{sanitize_name(family_name)}",
                job_dir=family_job_dir,
                success=summary.all_successful and test_successful == test_total,
                message="; ".join([
                    f"train batches: {summary.batches_run}",
                    f"train final epoch: {summary.final_epoch_successful}/{summary.total_tasks}",
                    f"train executions: {summary.total_successful}/{summary.total_task_executions}",
                    f"test succeeded: {test_successful}/{test_total}",
                    f"final={final_version.version_label}:{final_version.content_hash[:12]}",
                    test_progress,
                ]),
            )
        except Exception as exc:
            import traceback
            overall = RunResult(
                group_name=family_name,
                job_name=f"{base_job_name}__{sanitize_name(family_name)}",
                job_dir=family_job_dir,
                success=False,
                message=f"Family run failed: {exc}\n{traceback.format_exc()}",
            )

        status = "OK" if overall.success else "FAIL"
        print(f"\nDone: {status} family {family_name}.")
        print(f"  {status} {family_name}: {overall.message}")
        print(result_to_json(overall))
        raise SystemExit(0 if overall.success else 1)

    results = run_all_groups(args.config, base_config, cfg)
    raise SystemExit(0 if all(r.success for r in results) else 1)


if __name__ == "__main__":
    main()
