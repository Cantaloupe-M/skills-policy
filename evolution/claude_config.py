"""Shared Claude Code configuration for benchmark runners.

Reads task-execution profile settings from ``llm_config.py`` and translates
them into Claude Code environment variables (Anthropic protocol).

Profile convention in this repo:
  - ``train``: task execution during acquisition / training runs
  - ``test``: task execution during held-out evaluation runs
  - ``evolution``: host-side self-evolution and synthesis calls
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from evolution.llm_adapter import (
    ADAPTER_COMPOSE_ENV,
    ADAPTER_NETWORK_ENV,
    TASK_NETWORK_COMPOSE_PATH,
    ensure_openai_adapter,
)

CLAUDE_API_ENV_KEYS = (
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    ADAPTER_NETWORK_ENV,
    ADAPTER_COMPOSE_ENV,
)


def add_no_proxy_host(env: dict[str, str], hostname: str) -> None:
    """Append an internal Docker hostname to both NO_PROXY spellings."""
    for key in ("NO_PROXY", "no_proxy"):
        current = env.get(key, "")
        entries = [item.strip() for item in current.split(",") if item.strip()]
        if hostname not in entries:
            entries.append(hostname)
        env[key] = ",".join(entries)


@dataclass(frozen=True)
class ClaudeProfileRuntime:
    profile: str
    provider: str
    model: str | None
    env: dict[str, str]


def _load_llm_config() -> Any | None:
    try:
        import llm_config
    except ImportError:
        return None
    return llm_config


def _get_profile_config(profile: str) -> dict[str, str]:
    """Return the named profile dict from llm_config, or {} if unavailable."""
    llm_config = _load_llm_config()
    if llm_config is None:
        return {}
    try:
        return llm_config.get_profile(profile)
    except Exception:
        # Fall back to reading module-level constants
        return {}


def resolve_claude_profile_runtime(
    profile: str = "train",
    *,
    start_adapter: bool = False,
    model_override: str | None = None,
) -> ClaudeProfileRuntime:
    """Translate a profile into the Anthropic environment Claude Code expects."""
    p = _get_profile_config(profile)
    provider = str(p.get("provider") or "anthropic").lower()
    model = model_override or (str(p["model"]) if p.get("model") else None)
    base_url = str(p.get("base_url") or "")
    api_key = str(p.get("api_key") or "")

    if provider == "anthropic":
        env = {}
        if base_url:
            env["ANTHROPIC_BASE_URL"] = base_url
        if api_key:
            env["ANTHROPIC_API_KEY"] = api_key
        return ClaudeProfileRuntime(profile, provider, model, env)

    if provider != "openai":
        raise ValueError(
            f"Unsupported Claude Code provider '{provider}' in profile '{profile}'. "
            "Use 'anthropic' or 'openai'."
        )

    hostname = f"llm-adapter-{profile.lower()}"
    adapter_base_url = f"http://{hostname}:4000"
    adapter_api_key = "sk-local-skillflow-adapter"
    if start_adapter:
        endpoint = ensure_openai_adapter(
            profile=profile,
            model=model or "",
            base_url=base_url,
            api_key=api_key,
        )
        adapter_base_url = endpoint.base_url
        adapter_api_key = endpoint.api_key

    return ClaudeProfileRuntime(
        profile,
        provider,
        model,
        {
            "ANTHROPIC_BASE_URL": adapter_base_url,
            "ANTHROPIC_API_KEY": adapter_api_key,
            ADAPTER_NETWORK_ENV: "skillflow-llm-adapter",
            ADAPTER_COMPOSE_ENV: str(TASK_NETWORK_COMPOSE_PATH),
        },
    )


def fill_claude_env_from_llm_config(
    claude_env: dict[str, str],
    profile: str = "train",
    *,
    start_adapter: bool = False,
) -> None:
    """Load one task-execution profile from ``llm_config.py`` into Claude env.

    Use ``train`` for acquisition/training tasks and ``test`` for held-out
    evaluation tasks. Self-evolution uses the separate ``evolution`` profile
    through host-side Python LLM calls.
    """
    if _load_llm_config() is None:
        return
    runtime = resolve_claude_profile_runtime(profile, start_adapter=start_adapter)
    for key in CLAUDE_API_ENV_KEYS:
        claude_env.pop(key, None)
    claude_env.update(runtime.env)


def activate_claude_profile(profile: str, *, start_adapter: bool = True) -> str | None:
    """Activate a profile in this process and return Claude Code's model name."""
    runtime = resolve_claude_profile_runtime(profile, start_adapter=start_adapter)
    for key in CLAUDE_API_ENV_KEYS:
        os.environ.pop(key, None)
    os.environ.update(runtime.env)
    if runtime.provider == "openai":
        adapter_host = urlsplit(runtime.env["ANTHROPIC_BASE_URL"]).hostname
        if adapter_host:
            add_no_proxy_host(os.environ, adapter_host)
    return runtime.model


def default_claude_model_from_llm_config(profile: str = "train") -> str | None:
    """Return the model name for Claude Code benchmark agents from the profile."""
    p = _get_profile_config(profile)
    model = p.get("model")
    return str(model) if model else None


def resolve_claude_model(
    explicit_model: str | None = None,
    profile: str = "train",
) -> str | None:
    """Prefer an explicit CLI model, otherwise use the profile's model."""
    return explicit_model or default_claude_model_from_llm_config(profile)
