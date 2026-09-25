"""Run the OpenAI-to-Anthropic adapter used by Claude Code task containers."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = PROJECT_ROOT / "docker" / "llm-adapter" / "compose.yaml"
TASK_NETWORK_COMPOSE_PATH = PROJECT_ROOT / "docker" / "llm-adapter" / "task-network.yaml"
ADAPTER_NETWORK = "skillflow-llm-adapter"
ADAPTER_NETWORK_ENV = "SKILLFLOW_LLM_ADAPTER_NETWORK"
ADAPTER_COMPOSE_ENV = "SKILLFLOW_LLM_ADAPTER_COMPOSE"
LOCAL_MASTER_KEY = "sk-local-skillflow-adapter"


@dataclass(frozen=True)
class AdapterEndpoint:
    base_url: str
    api_key: str
    network: str
    hostname: str


def _safe_profile_name(profile: str) -> str:
    value = re.sub(r"[^a-z0-9-]+", "-", profile.lower()).strip("-")
    return value or "default"


def _runtime_dir(profile: str) -> Path:
    configured = os.getenv("LLM_ADAPTER_RUNTIME_DIR")
    root = Path(configured).expanduser() if configured else PROJECT_ROOT / ".runtime" / "llm-adapter"
    return root.resolve() / _safe_profile_name(profile)


def _write_litellm_config(path: Path, model: str) -> None:
    config = {
        "model_list": [
            {
                "model_name": model,
                "litellm_params": {
                    "model": f"openai/{model}",
                    "api_base": "os.environ/UPSTREAM_BASE_URL",
                    "api_key": "os.environ/UPSTREAM_API_KEY",
                },
            }
        ],
        "general_settings": {"master_key": "os.environ/LITELLM_MASTER_KEY"},
        "litellm_settings": {"drop_params": True},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(config, sort_keys=False)
    if path.exists() and path.read_text(encoding="utf-8") == rendered:
        return
    path.write_text(rendered, encoding="utf-8")


def _host_base_url(port_output: str) -> str:
    """Convert Docker Compose's published-port output to a loopback URL."""
    first_line = next((line.strip() for line in port_output.splitlines() if line.strip()), "")
    if not first_line or ":" not in first_line:
        raise RuntimeError(f"Could not resolve LiteLLM published port: {port_output!r}")
    port = first_line.rsplit(":", 1)[-1]
    if not port.isdigit():
        raise RuntimeError(f"Invalid LiteLLM published port: {first_line!r}")
    return f"http://127.0.0.1:{port}"


def ensure_openai_adapter(
    *,
    profile: str,
    model: str,
    base_url: str,
    api_key: str,
) -> AdapterEndpoint:
    """Start one profile-specific LiteLLM service and return its host URL."""
    if not model:
        raise ValueError(f"OpenAI profile '{profile}' has no model")
    if not base_url:
        raise ValueError(f"OpenAI profile '{profile}' has no base_url")
    if not api_key:
        raise ValueError(f"OpenAI profile '{profile}' has no api_key")
    if not COMPOSE_PATH.is_file():
        raise FileNotFoundError(f"LLM adapter compose file not found: {COMPOSE_PATH}")

    safe_profile = _safe_profile_name(profile)
    hostname = f"llm-adapter-{safe_profile}"
    config_path = _runtime_dir(profile) / "litellm-config.yaml"
    _write_litellm_config(config_path, model)

    compose_env = os.environ.copy()
    compose_env.update(
        {
            "LITELLM_ADAPTER_CONTAINER": f"skillflow-{hostname}",
            "LITELLM_ADAPTER_HOSTNAME": hostname,
            "LITELLM_ADAPTER_NETWORK": ADAPTER_NETWORK,
            "LITELLM_CONFIG_PATH": str(config_path),
            "LITELLM_MASTER_KEY": LOCAL_MASTER_KEY,
            "LITELLM_CONFIG_REVISION": sha256(model.encode("utf-8")).hexdigest()[:16],
            "UPSTREAM_API_KEY": api_key,
            "UPSTREAM_BASE_URL": base_url.rstrip("/"),
        }
    )
    command = [
        "docker",
        "compose",
        "--project-name",
        f"skillflow-llm-{safe_profile}",
        "--file",
        str(COMPOSE_PATH),
        "up",
        "--detach",
        "--wait",
        "--wait-timeout",
        os.getenv("LLM_ADAPTER_START_TIMEOUT", "120"),
    ]
    try:
        completed = subprocess.run(
            command,
            env=compose_env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Docker is required for OpenAI Claude Code profiles") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "unknown Docker Compose error").strip()
        raise RuntimeError(f"Could not start LLM adapter for profile '{profile}': {detail}")

    port_command = [
        "docker",
        "compose",
        "--project-name",
        f"skillflow-llm-{safe_profile}",
        "--file",
        str(COMPOSE_PATH),
        "port",
        "llm-adapter",
        "4000",
    ]
    published = subprocess.run(
        port_command,
        env=compose_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if published.returncode != 0:
        detail = (published.stderr or published.stdout or "unknown Docker Compose error").strip()
        raise RuntimeError(
            f"Could not resolve LLM adapter port for profile '{profile}': {detail}"
        )

    return AdapterEndpoint(
        base_url=_host_base_url(published.stdout),
        api_key=LOCAL_MASTER_KEY,
        network=ADAPTER_NETWORK,
        hostname=hostname,
    )
