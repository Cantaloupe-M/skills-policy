#!/usr/bin/env python3
# ruff: noqa: E402
"""Run SkillLearnBench with the repository's skill self-evolution method.

The protocol groups instances by the six categories published in the
SkillLearnBench README and uses a fixed category-stratified 80/20 train/test
split. Splits are loaded from a checked-in manifest and never generated at
runtime.

export LLM_OVERRIDES='{
  "train": {
    "provider": "openai",
    "model": "gpt-5.6-luna",
    "base_url": "https://api.apiyi.com/v1",
    "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b"
  },
  "evolution": {
    "provider": "openai",
    "model": "gpt-5.6-terra",
    "base_url": "https://api.apiyi.com/v1",
    "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b"
  },
  "test": {
    "provider": "openai",
    "model": "gpt-5.6-luna",
    "base_url": "https://api.apiyi.com/v1",
    "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b"
  }
}'

export LLM_OVERRIDES='{
  "train": {
    "provider": "openai",
    "model": "gpt-5.6-luna",
    "base_url": "https://api.apiyi.com/v1",
    "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b"
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
    "api_key": "sk-NbSGnWX0V7j8of9KDd1dD355E30b48EeA8383c7f2f2c5b0b"
  }
}'

./.venv/bin/python run_skilllearnbench_evolution.py \
    --dataset-root /data01/syt/研究项目/skill自进化/SkillLearnBench \
    --run-root-dir runs/skilllearnbench-gpt-2 \
    --max-retries 3 \
    --train-epochs 2 \
    --family-concurrency 2
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib
import json
import multiprocessing
import os
import re
import shlex
import shutil
import subprocess
import sys
import types
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

ENTRYPOINT = Path(__file__).resolve()
PROJECT_ROOT = ENTRYPOINT.parent
DEFAULT_DATASET_ROOT = Path("/data01/syt/研究项目/skill自进化/SkillLearnBench")
DEFAULT_SPLIT_FILE = PROJECT_ROOT / "utils" / "skilllearnbench_splits.json"
DEFAULT_RUN_ROOT = PROJECT_ROOT / "runs" / "skilllearnbench-evolution_retry"
LLM_OVERRIDES_ENV_KEY = "LLM_OVERRIDES"

# Optional in-code overrides; unset values continue to use llm_config.py.
LLM_OVERRIDES: dict[str, dict[str, str]] = {"train": {}, "evolution": {}, "test": {}}


def _load_env_llm_overrides() -> dict[str, dict[str, str]] | None:
    """Load profile overrides from ``LLM_OVERRIDES`` when it is set."""
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


def _apply_llm_overrides(args: argparse.Namespace) -> None:
    llm_config = importlib.import_module("llm_config")
    configured_overrides = _load_env_llm_overrides()
    if configured_overrides is None:
        configured_overrides = LLM_OVERRIDES
    for profile in ("train", "evolution", "test"):
        configured = dict(getattr(llm_config, "LLM_PROFILES", {}).get(profile, {}))
        configured.update({k: v for k, v in configured_overrides.get(profile, {}).items() if v})
        for key in ("provider", "model", "base_url", "api_key"):
            value = getattr(args, f"{profile}_llm_{key}", None)
            if value:
                configured[key] = str(value).strip()
        provider = str(configured.get("provider") or "").lower()
        if provider and provider not in {"anthropic", "openai"}:
            raise SystemExit(f"Unsupported {profile} provider {provider!r}; use 'anthropic' or 'openai'")
        if provider:
            configured["provider"] = provider
        llm_config.LLM_PROFILES[profile] = configured
    sync = getattr(llm_config, "_sync_legacy_globals", None)
    if callable(sync):
        sync()

from evolution.batch_loop import (
    BatchEvolutionLoop,
    BatchExecutor,
    EvolutionPolicy,
    TaskRef,
    TrialResult,
)
from evolution.batch_reflection import run_reflection_retry_loop
from evolution.claude_config import (
    activate_claude_profile,
    add_no_proxy_host,
    resolve_claude_profile_runtime,
)
from evolution.cli import add_evolution_arguments, evolution_config_from_args
from evolution.initial_skill import prepare_initial_family_skill_store
from evolution.integrations.claude_code_artifacts import compact_claude_trajectory
from evolution.llm_adapter import ADAPTER_NETWORK_ENV
from evolution.memory_embedding_service import (
    MEMORY_EMBEDDING_ENDPOINT_ENV,
    ensure_memory_embedding_service,
)
from evolution.memory_store import (
    MCP_GET_TOOL,
    MCP_SEARCH_TOOL,
    MEMORY_STORE_FILENAME,
    memory_runtime_spec,
    prepare_runtime_skills,
)
from evolution.outcome import TaskContract, TrialOutcome
from evolution.skill_utils import (
    freeze_final_version,
    get_latest_skill_version,
    hash_skill_tree,
    sanitize_name,
)
from evolution.task_instruction import prepare_task_instruction


@dataclass(frozen=True)
class SkillLearnSplit:
    category: str
    display_name: str
    train: tuple[Path, ...]
    test: tuple[Path, ...]


def discover_instances(dataset_root: Path) -> dict[str, dict[str, Path]]:
    """Return every valid two-level SkillLearnBench task instance."""
    tasks_root = dataset_root / "tasks"
    if not tasks_root.is_dir():
        raise ValueError(f"SkillLearnBench tasks directory not found: {tasks_root}")

    task_groups: dict[str, dict[str, Path]] = {}
    for task_group_dir in sorted(tasks_root.iterdir()):
        if not task_group_dir.is_dir():
            continue
        instances: dict[str, Path] = {}
        for task_dir in sorted(task_group_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            required = (
                task_dir / "instruction.md",
                task_dir / "environment" / "Dockerfile",
                task_dir / "tests",
            )
            if all(path.exists() for path in required):
                instances[f"{task_group_dir.name}/{task_dir.name}"] = task_dir.resolve()
        if instances:
            task_groups[task_group_dir.name] = instances
    return task_groups


def load_fixed_splits(
    split_file: Path,
    dataset_root: Path,
    discovered: dict[str, dict[str, Path]] | None = None,
) -> dict[str, SkillLearnSplit]:
    """Load and strictly validate the canonical, leakage-free split manifest."""
    discovered = discovered or discover_instances(dataset_root)
    try:
        payload = json.loads(split_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Fixed split manifest not found: {split_file}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid split JSON {split_file}: {exc}") from exc

    raw_categories = payload.get("categories") if isinstance(payload, dict) else None
    if not isinstance(raw_categories, dict):
        raise ValueError(f"Split manifest must contain a 'categories' object: {split_file}")
    train_ratio = payload.get("train_ratio")
    if train_ratio != 0.8:
        raise ValueError(f"Split manifest must declare train_ratio=0.8: {split_file}")

    resolved: dict[str, SkillLearnSplit] = {}
    assigned_task_groups: set[str] = set()
    for category, entry in raw_categories.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid split entry for category '{category}'")
        display_name = entry.get("display_name")
        task_groups = entry.get("tasks")
        train_ids = entry.get("train_tasks")
        test_ids = entry.get("test_tasks")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError(f"Category '{category}' must define a display_name")
        if not isinstance(task_groups, list) or not task_groups:
            raise ValueError(f"Category '{category}' must define a non-empty tasks list")
        if not isinstance(train_ids, list) or not isinstance(test_ids, list):
            raise ValueError(f"Category '{category}' must define train_tasks and test_tasks lists")

        task_group_set = {str(name) for name in task_groups}
        if len(task_group_set) != len(task_groups):
            raise ValueError(f"Category '{category}' contains duplicate task groups")
        unknown_groups = task_group_set - set(discovered)
        duplicate_groups = task_group_set & assigned_task_groups
        if unknown_groups:
            raise ValueError(f"Category '{category}' contains unknown task groups: {sorted(unknown_groups)}")
        if duplicate_groups:
            raise ValueError(f"Task groups assigned to multiple categories: {sorted(duplicate_groups)}")
        assigned_task_groups.update(task_group_set)

        instances = {task_id: path for task_group in task_group_set for task_id, path in discovered[task_group].items()}

        train_set = {str(task_id) for task_id in train_ids}
        test_set = {str(task_id) for task_id in test_ids}
        if len(train_set) != len(train_ids) or len(test_set) != len(test_ids):
            raise ValueError(f"Category '{category}' contains duplicate task IDs")
        overlap = train_set & test_set
        planned = train_set | test_set
        available = set(instances)
        if overlap:
            raise ValueError(f"Category '{category}' has train/test overlap: {sorted(overlap)}")
        if not train_set or not test_set:
            raise ValueError(f"Category '{category}' must have non-empty train and test partitions")
        if planned != available:
            missing = sorted(available - planned)
            extra = sorted(planned - available)
            raise ValueError(f"Category '{category}' split does not cover its task groups exactly; missing={missing}, extra={extra}")
        expected_test = max(1, round(len(available) * (1 - train_ratio)))
        if len(test_ids) != expected_test:
            raise ValueError(
                f"Category '{category}' does not follow the 80/20 split: "
                f"train={len(train_ids)}, test={len(test_ids)}, expected_test={expected_test}"
            )

        resolved[category] = SkillLearnSplit(
            category=category,
            display_name=display_name.strip(),
            train=tuple(instances[task_id] for task_id in train_ids),
            test=tuple(instances[task_id] for task_id in test_ids),
        )

    unassigned = set(discovered) - assigned_task_groups
    if unassigned:
        raise ValueError(f"Split categories do not cover dataset task groups: {sorted(unassigned)}")
    return resolved


_EVAL_RUNNER: Any | None = None


class _DockerNetworkSubprocess:
    """Module proxy that attaches SkillLearnBench task containers to one network."""

    def __init__(self, delegate: Any, network: str) -> None:
        self._delegate = delegate
        self.network = network

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def run(self, *popenargs: Any, **kwargs: Any) -> Any:
        if popenargs:
            command = _with_docker_network(popenargs[0], self.network)
            popenargs = (command, *popenargs[1:])
        elif "args" in kwargs:
            kwargs["args"] = _with_docker_network(kwargs["args"], self.network)
        return self._delegate.run(*popenargs, **kwargs)


def _docker_run_task_context(command: Any) -> tuple[str, Path] | None:
    """Extract ``(container_name, prepared_task_dir)`` from a task ``docker run``."""
    if not isinstance(command, (list, tuple)) or len(command) < 3:
        return None
    if list(command[:2]) != ["docker", "run"] or "-d" not in command:
        return None

    try:
        name_index = list(command).index("--name")
        container_name = str(command[name_index + 1])
    except (ValueError, IndexError):
        return None

    # eval_runner mounts the prepared task's tests directory at /tests.  The
    # sibling environment directory is the instance-specific input source.
    for part in command:
        text = str(part)
        marker = ":/tests:ro"
        if text.endswith(marker):
            tests_dir = Path(text[: -len(marker)])
            return container_name, tests_dir.parent
    return None


def _dockerfile_copy_sources(environment_dir: Path) -> list[tuple[Path, str]]:
    """Resolve non-skill Dockerfile COPY sources to container destinations.

    The official task Dockerfiles copy instance data (for example,
    ``calendar.pdf``) into fixed paths such as ``/root/calendar.pdf``.  The
    task-level base image is built from instance 1, so these files must be
    overlaid at runtime for every other instance.
    """
    dockerfile = environment_dir / "Dockerfile"
    if not dockerfile.is_file():
        return []

    # Join Dockerfile continuation lines before tokenising.  This keeps the
    # parser deliberately small while handling the forms used by the dataset.
    logical_lines: list[str] = []
    pending = ""
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if pending:
            pending += " " + line
        else:
            pending = line
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
        else:
            logical_lines.append(pending)
            pending = ""
    if pending:
        logical_lines.append(pending)

    resolved: list[tuple[Path, str]] = []
    for line in logical_lines:
        try:
            tokens = shlex.split(line, comments=True, posix=True)
        except ValueError:
            continue
        if not tokens or tokens[0].upper() != "COPY":
            continue
        options = [token for token in tokens[1:] if token.startswith("--")]
        if any(option.startswith("--from=") or option == "--from" for option in options):
            # COPY --from refers to another image/build stage, not this
            # instance's host-side data.
            continue
        args = [token for token in tokens[1:] if not token.startswith("--")]
        if len(args) < 2:
            continue
        sources, destination = args[:-1], args[-1]
        if not destination.startswith("/"):
            # Relative destinations depend on WORKDIR and cannot be safely
            # reconstructed without implementing all Dockerfile semantics.
            continue
        for source_pattern in sources:
            source_pattern = source_pattern.lstrip("./")
            if source_pattern == "skills" or source_pattern.startswith("skills/"):
                continue
            if source_pattern in {".", ""}:
                continue
            matches = sorted(environment_dir.glob(source_pattern))
            if not matches:
                raise FileNotFoundError(
                    f"Dockerfile COPY source {source_pattern!r} not found in {environment_dir}"
                )
            multiple = len(sources) > 1 or destination.endswith("/")
            for source in matches:
                target = destination.rstrip("/")
                if source.is_dir() and destination.endswith("/"):
                    target = f"{target}/{source.name}"
                elif not source.is_dir() and multiple:
                    target = f"{target}/{source.name}"
                resolved.append((source, target))
    return resolved


def _sync_instance_inputs(
    container_name: str,
    prepared_task_dir: Path,
    run_callable: Any,
) -> int:
    """Overlay this instance's Dockerfile COPY inputs into a running container."""
    environment_dir = prepared_task_dir / "environment"
    copies = _dockerfile_copy_sources(environment_dir)
    for source, destination in copies:
        # Remove the image's instance-1 copy first.  This also makes directory
        # COPYs deterministic instead of allowing Docker's nesting semantics.
        run_callable(
            ["docker", "exec", container_name, "rm", "-rf", destination],
            capture_output=True,
            check=True,
        )
        parent = str(Path(destination).parent)
        run_callable(
            ["docker", "exec", container_name, "mkdir", "-p", parent],
            capture_output=True,
            check=True,
        )
        run_callable(
            ["docker", "cp", str(source), f"{container_name}:{destination}"],
            capture_output=True,
            check=True,
        )
    return len(copies)


class _DockerInstanceInputSubprocess:
    """Subprocess proxy that overlays per-instance inputs after ``docker run``."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def run(self, *popenargs: Any, **kwargs: Any) -> Any:
        command = popenargs[0] if popenargs else kwargs.get("args")
        command = _with_docker_host_gateway(command)
        if popenargs:
            popenargs = (command, *popenargs[1:])
        elif "args" in kwargs:
            kwargs["args"] = command
        result = self._delegate.run(*popenargs, **kwargs)
        context = _docker_run_task_context(command)
        if context is not None and getattr(result, "returncode", 1) == 0:
            container_name, prepared_task_dir = context
            count = _sync_instance_inputs(
                container_name,
                prepared_task_dir,
                self._delegate.run,
            )
            if count:
                print(
                    f"[2a/5] Overlaid {count} instance input(s) for {container_name}...",
                    flush=True,
                )
        return result


def _with_docker_host_gateway(command: Any) -> Any:
    """Expose the authenticated host embedding service to task containers."""
    if not os.environ.get(MEMORY_EMBEDDING_ENDPOINT_ENV) or not isinstance(command, (list, tuple)):
        return command
    parts = list(command)
    if len(parts) < 2 or parts[:2] != ["docker", "run"]:
        return command
    if "host.docker.internal:host-gateway" in parts:
        return command
    adapted = [*parts[:2], "--add-host", "host.docker.internal:host-gateway", *parts[2:]]
    return tuple(adapted) if isinstance(command, tuple) else adapted


def _with_docker_network(command: Any, network: str) -> Any:
    """Add ``--network`` to Docker run commands without mutating the caller's list."""
    if not network or not isinstance(command, (list, tuple)):
        return command
    parts = list(command)
    if len(parts) < 2 or parts[:2] != ["docker", "run"]:
        return command
    if "--network" in parts or any(str(part).startswith("--network=") for part in parts):
        return command
    adapted = [*parts[:2], "--network", network, *parts[2:]]
    return tuple(adapted) if isinstance(command, tuple) else adapted


def _attach_runner_to_adapter_network(runner: Any, network: str) -> None:
    """Scope Docker network injection to the imported SkillLearnBench runner."""
    current = runner.subprocess
    if isinstance(current, _DockerNetworkSubprocess):
        if current.network != network:
            raise RuntimeError(
                f"SkillLearnBench runner already uses Docker network {current.network!r}, "
                f"cannot switch to {network!r}"
            )
        return
    runner.subprocess = _DockerNetworkSubprocess(current, network)


def _prepare_claude_task_adapters(
    agent_id: str,
    *,
    train_model: str | None = None,
    test_model: str | None = None,
) -> None:
    """Start profile adapters once before spawning independent family workers."""
    if agent_id != "claude-code":
        return
    for profile, model_override in (("train", train_model), ("test", test_model)):
        runtime = resolve_claude_profile_runtime(
            profile,
            start_adapter=True,
            model_override=model_override,
        )
        print(
            f"[SkillLearnBench] {profile} API: provider={runtime.provider}, "
            f"model={runtime.model or ''}, base_url={runtime.env.get('ANTHROPIC_BASE_URL', '')}"
        )


def load_skilllearnbench_eval_runner(dataset_root: Path) -> Any:
    """Import SkillLearnBench's own agent/verifier runner only for real runs."""
    global _EVAL_RUNNER
    if _EVAL_RUNNER is not None:
        return _EVAL_RUNNER

    root_text = str(dataset_root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    try:
        importlib.import_module("json_repair")
    except ModuleNotFoundError:
        # SkillLearnBench uses json-repair only for best-effort parsing of
        # line-delimited agent usage records. Agent stream lines are valid JSON,
        # so the standard parser is a sufficient compatibility fallback.
        compatibility_module = types.ModuleType("json_repair")
        compatibility_module.loads = json.loads  # type: ignore[attr-defined]
        sys.modules["json_repair"] = compatibility_module
    try:
        module = importlib.import_module("core.eval_runner")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Could not import SkillLearnBench's evaluation runner. Install the dataset's runtime dependencies in this Python environment."
        ) from exc
    module_path = Path(module.__file__).resolve()
    if dataset_root.resolve() not in module_path.parents:
        raise RuntimeError(f"Imported the wrong core.eval_runner module: {module_path}")
    # The upstream runner's task-level image is built from instance 1.  Keep
    # that image for dependencies, but overlay the current instance's data
    # files immediately after each container starts (before the agent runs).
    if not isinstance(module.subprocess, _DockerInstanceInputSubprocess):
        module.subprocess = _DockerInstanceInputSubprocess(module.subprocess)
    _EVAL_RUNNER = module
    return module


def _task_id(task: TaskRef) -> str:
    return f"{task.source_path.parent.name}/{task.source_path.name}"


def _task_refs(paths: tuple[Path, ...], category: str) -> list[TaskRef]:
    return [TaskRef(name=path.name, family=category, source_path=path) for path in paths]


def _skill_slugs(skills_dir: Path) -> list[str]:
    return (
        [child.name for child in sorted(skills_dir.iterdir()) if child.is_dir() and (child / "SKILL.md").is_file()]
        if skills_dir.is_dir()
        else []
    )


def _configure_memory_mcp(runner: Any, agent_id: str, skills_dir: Path) -> None:
    """Expose the snapshot's read-only residual-memory server to Claude Code."""
    if agent_id != "claude-code":
        return
    spec = memory_runtime_spec(skills_dir)
    agent = runner.get_agent(agent_id)
    if spec is None or agent is None:
        return
    if spec.get("semantic_available"):
        embedding_runtime = ensure_memory_embedding_service(str(spec.get("embedding_model") or "") or None)
        if embedding_runtime is not None:
            os.environ.update(embedding_runtime.container_env)
            add_no_proxy_host(os.environ, "host.docker.internal")
            env_keys = agent.setdefault("env", [])
            for key in (*embedding_runtime.container_env, "NO_PROXY", "no_proxy"):
                if os.environ.get(key) and key not in env_keys:
                    env_keys.append(key)
    config_flag = f"--mcp-config {shlex.quote(str(spec['config_path']))} --strict-mcp-config"
    run_command = str(agent.get("run") or "")
    if "--mcp-config" not in run_command:
        agent["run"] = f"{run_command} {config_flag}"
    allowed = agent.setdefault("default_tools", [])
    for tool in (MCP_SEARCH_TOOL, MCP_GET_TOOL):
        if tool not in allowed:
            allowed.append(tool)


def _materialize_task(task: TaskRef, root: Path, instruction: str) -> tuple[Path, str]:
    """Create a lightweight task view with a per-attempt instruction."""
    task_id = _task_id(task)
    destination = root / task_id
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source in task.source_path.iterdir():
        if source.name == "instruction.md":
            continue
        target = destination / source.name
        if source.name == "tests" and source.is_dir():
            shutil.copytree(source, target)
            for script in target.rglob("*.sh"):
                content = script.read_bytes()
                normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                if normalized != content:
                    script.write_bytes(normalized)
            continue
        target.symlink_to(source.resolve(), target_is_directory=source.is_dir())
    (destination / "instruction.md").write_text(instruction.rstrip() + "\n", encoding="utf-8")
    return root, task_id


def _task_contract(task: TaskRef) -> TaskContract:
    """Build task evidence without reading the held-back verifier implementation."""
    instruction_path = task.source_path / "instruction.md"
    objective = instruction_path.read_text(encoding="utf-8", errors="replace").strip()
    inputs: list[dict[str, Any]] = []
    environment = task.source_path / "environment"
    if environment.is_dir():
        for path in sorted(environment.iterdir()):
            if path.is_file() and path.name not in {"Dockerfile"}:
                inputs.append({"path": path.name, "type": path.suffix.lstrip(".") or "file"})
    return TaskContract(
        family=task.family,
        objective=objective,
        input_artifacts=inputs,
        required_capabilities=[task.family],
    )


def _trajectory_path(trial_dir: Path) -> Path | None:
    candidates = (
        trial_dir / "agent" / "trajectory.json",
        trial_dir / "agent" / "claude-code.txt",
        trial_dir / "agent" / "claude_code.txt",
        trial_dir / "agent" / "codex.txt",
        trial_dir / "sessions" / "agent.log",
    )
    return next((path for path in candidates if path.is_file()), None)


def _failure_reason(result: dict[str, Any], return_code: int) -> str | None:
    if result.get("passed") is True:
        return None
    if result.get("error"):
        return str(result["error"])
    if result.get("agent_timed_out"):
        return "agent timed out"
    verifier_exit = result.get("verifier_exit")
    if verifier_exit not in (None, 0):
        return f"verifier failed with exit code {verifier_exit}"
    return f"SkillLearnBench trial failed with return code {return_code}"


class SkillLearnBenchExecutor(BatchExecutor):
    """Adapter from SkillLearnBench's Docker runner to BatchEvolutionLoop."""

    def __init__(
        self,
        *,
        dataset_root: Path,
        agent_id: str,
        model: str | None,
        profile: str,
        max_steps: int,
        concurrency: int,
        image_tags: dict[str, str],
    ) -> None:
        self.dataset_root = dataset_root
        self.agent_id = agent_id
        self.model = model
        self.profile = profile
        self.max_steps = max_steps
        self.concurrency = max(1, concurrency)
        self.image_tags = image_tags
        self.runner = load_skilllearnbench_eval_runner(dataset_root)

    def _activate_profile(self) -> str | None:
        if self.agent_id != "claude-code":
            return self.model
        runtime = resolve_claude_profile_runtime(
            self.profile,
            start_adapter=False,
            model_override=self.model,
        )
        profile_model = activate_claude_profile(self.profile, start_adapter=False)
        if runtime.provider == "openai":
            network = runtime.env.get(ADAPTER_NETWORK_ENV)
            if not network:
                raise RuntimeError(
                    f"OpenAI profile {self.profile!r} did not provide an LLM adapter network"
                )
            _attach_runner_to_adapter_network(self.runner, network)
        resolved_model = self.model or profile_model
        agent = self.runner.get_agent(self.agent_id)
        if agent is not None:
            env_keys = agent.setdefault("env", [])
            for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "NO_PROXY", "no_proxy"):
                if os.environ.get(key) and key not in env_keys:
                    env_keys.append(key)
        return resolved_model

    def execute_batch(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
    ) -> list[TrialResult]:
        return self._execute_tasks(
            tasks,
            shared_skills_dir,
            work_dir,
            task_family="",
            max_retries=0,
        )

    def execute_batch_with_retries(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
        *,
        task_family: str,
        max_retries: int,
    ) -> list[TrialResult]:
        """Run each task's reflection retries immediately after its failure."""
        return self._execute_tasks(
            tasks,
            shared_skills_dir,
            work_dir,
            task_family=task_family,
            max_retries=max_retries,
        )

    def _execute_tasks(
        self,
        tasks: list[TaskRef],
        shared_skills_dir: Path,
        work_dir: Path,
        *,
        task_family: str,
        max_retries: int,
    ) -> list[TrialResult]:
        model = self._activate_profile()
        results: list[TrialResult | None] = [None] * len(tasks)

        def execute(index: int, task: TaskRef) -> None:
            task_work_dir = work_dir / task.name
            result = self._run_one(task, shared_skills_dir, task_work_dir, model=model)

            def retry(reflection: str, retry_number: int) -> TrialResult:
                retry_dir = task_work_dir / f"retry_{retry_number:02d}"
                return self._run_one(
                    task,
                    shared_skills_dir,
                    retry_dir,
                    reflection=reflection,
                    model=model,
                )

            results[index] = run_reflection_retry_loop(
                result,
                task_name=task.name,
                task_family=task_family or task.family,
                max_retries=max_retries,
                retry=retry,
                log_prefix="SkillLearnBench",
            )

        if self.concurrency == 1:
            for index, task in enumerate(tasks):
                execute(index, task)
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as pool:
                futures = [pool.submit(execute, index, task) for index, task in enumerate(tasks)]
                for future in futures:
                    future.result()
        return [result for result in results if result is not None]

    def retry_one(
        self,
        task: TaskRef,
        shared_skills_dir: Path,
        work_dir: Path,
        reflection: str,
    ) -> TrialResult:
        model = self._activate_profile()
        return self._run_one(task, shared_skills_dir, work_dir, reflection=reflection, model=model)

    def _run_one(
        self,
        task: TaskRef,
        shared_skills_dir: Path,
        work_dir: Path,
        *,
        model: str | None,
        reflection: str | None = None,
    ) -> TrialResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        original = (task.source_path / "instruction.md").read_text(encoding="utf-8", errors="replace")
        instruction = prepare_task_instruction(
            original,
            _skill_slugs(shared_skills_dir),
            reflection,
            memory_available=memory_runtime_spec(shared_skills_dir) is not None,
        )
        prepared_root, task_id = _materialize_task(
            task,
            work_dir / "prepared_tasks",
            instruction or original,
        )
        trial_id = f"trial_{uuid.uuid4().hex[:12]}"
        trials_root = work_dir / "trials"
        skill_config = "self_evolution"
        trial_dir = trials_root / skill_config / Path(task_id) / trial_id
        image_tag = self.image_tags[task_id]
        _configure_memory_mcp(self.runner, self.agent_id, shared_skills_dir)

        return_code, result = self.runner.run_task(
            task_id,
            task_root=prepared_root,
            agent_id=self.agent_id,
            model=model,
            record=True,
            skill_config=skill_config,
            skill_source_dir=shared_skills_dir,
            trial_id=trial_id,
            max_steps=self.max_steps,
            prebuilt_image_tag=image_tag,
            prebuilt_has_agent=True,
            trials_dir=trials_root,
        )
        trial_dir.mkdir(parents=True, exist_ok=True)
        result_path = trial_dir / "result.json"
        if not result_path.is_file():
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        reward = float(result.get("reward", 0) or 0)
        success = bool(result.get("passed") is True and reward >= 1.0)
        exception_info = _failure_reason(result, return_code)
        trajectory = compact_claude_trajectory(trial_dir)
        outcome = TrialOutcome(
            trial_name=str(result.get("trial_name") or trial_id),
            task_name=task.name,
            task_source=task.family,
            verifier_passed=success,
            reward=reward,
            compacted_trajectory=trajectory,
            failed_test_names=[] if success else ["skilllearnbench_verifier"],
            exception_message=exception_info,
            task_contract=_task_contract(task),
            verifier_feedback=[
                {
                    "name": "skilllearnbench_verifier",
                    "status": "passed" if success else "failed",
                    "message": "",
                }
            ],
        )
        return TrialResult(
            task_name=task.name,
            trial_name=str(result.get("trial_name") or trial_id),
            trial_dir=trial_dir,
            success=success,
            reward=reward,
            exception_info=exception_info,
            trajectory_path=_trajectory_path(trial_dir),
            outcome=outcome,
        )


def _task_image_tag(task_id: str) -> str:
    """Return SkillLearnBench's official stable tag for a parent task."""
    task_name = Path(task_id).parts[0]
    safe = re.sub(r"[^a-z0-9._-]", "-", task_name.lower())
    safe = re.sub(r"-{2,}", "-", safe).strip("-")
    return f"eval-hyper-{safe}:stable"


def resolve_prebuilt_images(tasks: list[TaskRef]) -> dict[str, str]:
    """Map instances to the official per-parent-task prebuilt images."""
    tags: dict[str, str] = {}
    missing: dict[str, str] = {}
    inspected: dict[str, bool] = {}
    for task in tasks:
        task_id = _task_id(task)
        task_name = Path(task_id).parts[0]
        tag = _task_image_tag(task_id)
        if tag not in inspected:
            result = subprocess.run(["docker", "image", "inspect", tag], capture_output=True)
            inspected[tag] = result.returncode == 0
        if not inspected[tag]:
            missing[task_name] = tag
        tags[task_id] = tag

    if missing:
        formatted = "\n".join(f"  {task}: {tag}" for task, tag in sorted(missing.items()))
        raise RuntimeError(
            "Missing official SkillLearnBench task images:\n"
            f"{formatted}\n"
            "Build the missing task-level images with "
            "scripts/datasets/skilllearnbench/prebuild_images.sh."
        )
    return tags


def _write_split_manifest(path: Path, split: SkillLearnSplit, source_file: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "category": split.category,
                "display_name": split.display_name,
                "source_split_file": str(source_file.resolve()),
                "train_tasks": [f"{task.parent.name}/{task.name}" for task in split.train],
                "test_tasks": [f"{task.parent.name}/{task.name}" for task in split.test],
                "test_is_frozen": True,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_test_phase(
    executor: SkillLearnBenchExecutor,
    tasks: list[TaskRef],
    skills_dir: Path,
    family_dir: Path,
    batch_size: int,
) -> tuple[int, int, list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    test_root = family_dir / "test"
    skills_dir = prepare_runtime_skills(
        skills_dir,
        test_root / "runtime_skills",
        skills_dir.parents[2] / MEMORY_STORE_FILENAME,
    )
    for offset in range(0, len(tasks), max(1, batch_size)):
        batch = tasks[offset : offset + max(1, batch_size)]
        round_index = offset // max(1, batch_size) + 1
        results = executor.execute_batch(batch, skills_dir, test_root / f"round_{round_index:03d}")
        for task, result in zip(batch, results):
            records.append(
                {
                    "task": _task_id(task),
                    "success": result.success,
                    "reward": result.reward,
                    "trial_dir": str(result.trial_dir),
                    "exception_info": result.exception_info,
                }
            )
            label = "OK" if result.success else "FAIL"
            print(f"[Test] {label:4s} {_task_id(task)} reward={result.reward:g}")
    return sum(bool(row["success"]) for row in records), len(records), records


def run_family(
    split: SkillLearnSplit,
    *,
    args: argparse.Namespace,
    run_dir: Path,
) -> dict[str, Any]:
    _apply_llm_overrides(args)
    family_dir = run_dir / sanitize_name(split.category)
    family_dir.mkdir(parents=True, exist_ok=True)
    _write_split_manifest(family_dir / "split_manifest.json", split, args.split_file)

    train_refs = _task_refs(split.train, split.category)
    test_refs = _task_refs(split.test, split.category)
    all_refs = train_refs + test_refs
    image_tags = resolve_prebuilt_images(all_refs)

    skills_store = family_dir / "skill_versions"
    initial = prepare_initial_family_skill_store(
        skills_store,
        split.category,
        list(split.train),
        initialization=args.initialization,
    )
    print(f"[SkillLearnBench] {split.category}: initial={initial.version_label} hash={initial.content_hash[:12]}")

    train_executor = SkillLearnBenchExecutor(
        dataset_root=args.dataset_root,
        agent_id=args.agent,
        model=args.model,
        profile="train",
        max_steps=args.max_steps,
        concurrency=args.batch_concurrency,
        image_tags=image_tags,
    )
    evolution_config = evolution_config_from_args(args)
    loop = BatchEvolutionLoop(
        executor=train_executor,
        config=evolution_config,
        task_family=split.category,
        skills_dir=skills_store,
        policy=EvolutionPolicy(
            include_failure_evidence=evolution_config.include_failure_evidence,
            strict_cross_task=evolution_config.strict_cross_task,
            require_policy_use=evolution_config.require_policy_use,
            immediate_promotion=evolution_config.immediate_promotion,
        ),
        min_occurrences=evolution_config.min_occurrences,
        verbose=True,
    )
    train_summary = loop.run(train_refs)
    final_version = freeze_final_version(skills_store, get_latest_skill_version(skills_store))

    test_executor = SkillLearnBenchExecutor(
        dataset_root=args.dataset_root,
        agent_id=args.agent,
        model=args.test_model,
        profile="test",
        max_steps=args.max_steps,
        concurrency=args.batch_concurrency,
        image_tags=image_tags,
    )
    test_passed, test_total, test_records = _run_test_phase(
        test_executor,
        test_refs,
        final_version.skills_dir,
        family_dir,
        args.batch_size,
    )
    result = {
        "category": split.category,
        "display_name": split.display_name,
        "initialization": args.initialization,
        "train_tasks": len(train_refs),
        "train_epochs": train_summary.train_epochs,
        "train_final_epoch_passed": train_summary.final_epoch_successful,
        "train_final_epoch_failed": train_summary.final_epoch_failed,
        "final_version": final_version.version_label,
        "final_hash": hash_skill_tree(final_version.skills_dir),
        "final_skills_dir": str(final_version.skills_dir),
        "test_passed": test_passed,
        "test_total": test_total,
        "test_pass_rate": test_passed / test_total if test_total else 0.0,
        "test_records": test_records,
    }
    (family_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _run_family_jobs(
    jobs: list[tuple[str, SkillLearnSplit]],
    *,
    args: argparse.Namespace,
    run_dir: Path,
) -> list[dict[str, Any]]:
    """Run every family in a fresh spawned process, with bounded concurrency."""
    if not jobs:
        return []

    concurrency = min(args.family_concurrency, len(jobs))
    print(
        f"[SkillLearnBench] family processes: {len(jobs)} family(s), "
        f"concurrency={concurrency}"
    )
    context = multiprocessing.get_context("spawn")
    completed: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=concurrency,
        mp_context=context,
        max_tasks_per_child=1,
    ) as pool:
        futures = {
            pool.submit(run_family, split, args=args, run_dir=run_dir): category
            for category, split in jobs
        }
        finished = 0
        for future in concurrent.futures.as_completed(futures):
            category = futures[future]
            try:
                completed[category] = future.result()
            except Exception as exc:
                # Preserve the worker's concrete failure in the top-level
                # message.  ProcessPoolExecutor otherwise leaves users with
                # only the opaque family label, making configuration/runtime
                # problems (missing images, Docker permissions, API setup,
                # etc.) needlessly difficult to diagnose.
                detail = str(exc).strip() or exc.__class__.__name__
                raise RuntimeError(
                    f"SkillLearnBench family failed: {category}: {detail}"
                ) from exc
            finished += 1
            print(f"[SkillLearnBench] family complete: {category} ({finished}/{len(jobs)})")

    return [completed[category] for category, _split in jobs]


def _load_completed_family_results(
    run_dir: Path,
    splits: dict[str, SkillLearnSplit],
) -> list[dict[str, Any]]:
    """Load completed family results in canonical category order."""
    results: list[dict[str, Any]] = []
    for category in splits:
        result_path = run_dir / sanitize_name(category) / "result.json"
        if not result_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Invalid completed family result: {result_path}") from exc
        if not isinstance(result, dict) or result.get("category") != category:
            raise RuntimeError(f"Completed family result does not match category '{category}': {result_path}")
        results.append(result)
    return results


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SkillLearnBench skill self-evolution runner")
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--split-file", type=Path, default=DEFAULT_SPLIT_FILE)
    parser.add_argument("--run-root-dir", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--only-category",
        "--only-family",
        dest="only_categories",
        action="append",
        default=None,
        help="Run only the named README category (repeatable; --only-family is a compatibility alias)",
    )
    parser.add_argument("--agent", default="claude-code")
    parser.add_argument("--model", default=None, help="Override the train task-agent model")
    parser.add_argument("--test-model", default=None, help="Override the held-out task-agent model")
    for profile in ("train", "evolution", "test"):
        label = profile.replace("_", "-")
        parser.add_argument(f"--{label}-llm-provider", choices=("anthropic", "openai"))
        parser.add_argument(f"--{label}-llm-model")
        parser.add_argument(f"--{label}-llm-base-url")
        parser.add_argument(f"--{label}-llm-api-key")
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--batch-concurrency", type=int, default=3)
    parser.add_argument(
        "--family-concurrency",
        type=int,
        default=2,
        help="Max independent family processes (each process uses --batch-concurrency internally)",
    )
    parser.add_argument(
        "--skip-existing-family",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip families that already have a completed result.json (default: enabled)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the fixed split only")
    add_evolution_arguments(parser)
    args = parser.parse_args(argv)
    args.dataset_root = args.dataset_root.expanduser().resolve()
    args.split_file = args.split_file.expanduser().resolve()
    args.run_root_dir = args.run_root_dir.expanduser().resolve()
    if args.batch_concurrency < 1:
        parser.error("--batch-concurrency must be >= 1")
    if args.family_concurrency < 1:
        parser.error("--family-concurrency must be >= 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _apply_llm_overrides(args)
    discovered = discover_instances(args.dataset_root)
    all_splits = load_fixed_splits(args.split_file, args.dataset_root, discovered)
    splits = all_splits
    if args.only_categories:
        requested = set(args.only_categories)
        unknown = sorted(requested - set(splits))
        if unknown:
            raise SystemExit(f"Unknown --only-category value(s): {unknown}")
        splits = {name: split for name, split in splits.items() if name in requested}

    total_train = sum(len(split.train) for split in splits.values())
    total_test = sum(len(split.test) for split in splits.values())
    print(f"[SkillLearnBench] fixed category-stratified split validated: categories={len(splits)} train={total_train} test={total_test}")
    for split in splits.values():
        print(f"  {split.category}: train={len(split.train)} test={len(split.test)}")
    if args.dry_run:
        return 0

    if shutil.which("docker") is None:
        raise SystemExit("Docker is required to run SkillLearnBench agent trials")
    runner = load_skilllearnbench_eval_runner(args.dataset_root)
    runner._load_dotenv()
    _prepare_claude_task_adapters(
        args.agent,
        train_model=args.model,
        test_model=args.test_model,
    )

    run_dir = args.run_root_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[str, SkillLearnSplit]] = []
    skipped_categories: list[str] = []
    for category, split in splits.items():
        family_dir = run_dir / sanitize_name(category)
        if args.skip_existing_family and (family_dir / "result.json").is_file():
            print(f"[SkillLearnBench] skip existing category: {category}")
            skipped_categories.append(category)
            continue
        jobs.append((category, split))

    if skipped_categories:
        print(f"[SkillLearnBench] Skipped {len(skipped_categories)} existing categor{'y' if len(skipped_categories) == 1 else 'ies'}: {', '.join(skipped_categories)}")

    if jobs:
        _run_family_jobs(jobs, args=args, run_dir=run_dir)
    else:
        print("[SkillLearnBench] No new families to process - all results already exist")

    results = _load_completed_family_results(run_dir, all_splits)

    aggregate = {
        "dataset_root": str(args.dataset_root),
        "split_file": str(args.split_file),
        "initialization": args.initialization,
        "categories_completed": len(results),
        "test_passed": sum(row["test_passed"] for row in results),
        "test_total": sum(row["test_total"] for row in results),
        "categories": results,
    }
    aggregate["test_pass_rate"] = aggregate["test_passed"] / aggregate["test_total"] if aggregate["test_total"] else 0.0
    (run_dir / "result.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n[SkillLearnBench] complete: {aggregate['test_passed']}/{aggregate['test_total']} held-out tasks passed; results={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
