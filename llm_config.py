"""
LLM Configuration Module
------------------------
Centralized configuration for LLM API clients (Anthropic Claude & OpenAI).

Three named profiles for different phases:
  - train     → task execution / trajectory collection
  - evolution → skill generation & family synthesis
  - test      → held-out evaluation

Usage:
    from llm_config import call_llm, get_profile, set_active_profile

    # Use a specific profile
    response = call_llm(messages=[{"role": "user", "content": "Hello"}], profile="evolution")

    # Switch default profile globally
    set_active_profile("train")
    response = call_llm(messages=[{"role": "user", "content": "Hello"}])

    # Get profile details
    p = get_profile("evolution")
    print(p["provider"], p["model"])
"""

import logging
import os
import time
from copy import deepcopy
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT = float(os.getenv("LLM_REQUEST_TIMEOUT", "120"))
MAX_RETRIES = 4
RETRY_BASE_DELAY = 2.0  # seconds: 2s → 4s → 8s → 16s


def _response_value(response: object, key: str) -> object | None:
    """Read a value from either an SDK object or a plain dict response."""
    if isinstance(response, dict):
        return response.get(key)
    return getattr(response, key, None)


def _format_openai_error(response: object) -> str:
    """Return a concise, non-secret error summary from an OpenAI-like response."""
    error = _response_value(response, "error")
    if not error:
        return "No error object was included in the response."

    if isinstance(error, dict):
        parts = [
            str(error.get("message") or "").strip(),
            f"type={error.get('type')}" if error.get("type") else "",
            f"code={error.get('code')}" if error.get("code") else "",
        ]
        return " ".join(part for part in parts if part) or repr(error)

    message = getattr(error, "message", None)
    error_type = getattr(error, "type", None)
    code = getattr(error, "code", None)
    parts = [
        str(message or "").strip(),
        f"type={error_type}" if error_type else "",
        f"code={code}" if code else "",
    ]
    return " ".join(part for part in parts if part) or repr(error)


# ══════════════════════════════════════════════════════════
#  Three Named LLM Profiles
# ══════════════════════════════════════════════════════════

LLM_PROFILES: dict[str, dict[str, str]] = {

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
    # "test": {
    #     "provider": "anthropic",
    #     "model": "gpt-5.6-luna",
    #     "base_url": "https://code28.ccwu.cc",
    #     "api_key": "sk-ER6uVUst5gC9lgwpiYDV8MjroFJdy9FJbnMK7wUvvWvXZsXc",
    # },
    # "xxx": {
    #     "provider": "openai",
    #     "model": "gpt-5.6-luna",
        # "base_url": "https://api.apiyi.com/v1",
        # "api_key": "sk-WZKSDwmrOQgOfbjF4539078509Aa4bF1801cF5A650BfEc8a",
    # },
        # "xxx": {
    #     "provider": "openai",
    #     "model": "gpt-5.6-luna",
    #     "base_url": "https://api.koozhan.com/v1",
    #     "api_key": "sk-dz--Tr6u5S2GKN-rIgZT9d06V4iFbF_OD0_v7PDXeKsW7M_AjDB",
    # },
}

# Active profile — used by call_llm / get_llm_client when profile= is not explicit.
ACTIVE_PROFILE: str = "evolution"

_VALID_PROFILES = frozenset({"train", "evolution", "test"})


@dataclass(frozen=True)
class LLMConfig:
    profile: str
    provider: str
    model: str
    base_url: str
    api_key: str


def _require_profile(name: str) -> dict[str, str]:
    if name not in _VALID_PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Valid profiles: {sorted(_VALID_PROFILES)}")
    return LLM_PROFILES[name]


def _profile_value(name: str, key: str) -> str:
    return _require_profile(name)[key]



def get_profile(name: str) -> dict[str, str]:
    """Return a copy of the named profile."""
    return deepcopy(_require_profile(name))


def get_profile_provider(name: str) -> str:
    return _profile_value(name, "provider")


def get_profile_model(name: str) -> str:
    return _profile_value(name, "model")


def get_profile_base_url(name: str) -> str:
    return _profile_value(name, "base_url")


def get_profile_api_key(name: str) -> str:
    return _profile_value(name, "api_key")


def _sync_legacy_globals() -> None:
    global DEFAULT_PROVIDER, LLM_MODEL
    DEFAULT_PROVIDER = _profile_value(ACTIVE_PROFILE, "provider")
    LLM_MODEL = _profile_value(ACTIVE_PROFILE, "model")


def set_active_profile(name: str) -> None:
    """Switch the default LLM profile globally.

    Example:
        set_active_profile("train")   # subsequent call_llm() uses train profile
        set_active_profile("evolution")
    """
    global ACTIVE_PROFILE
    _require_profile(name)
    ACTIVE_PROFILE = name
    _sync_legacy_globals()


# Backward-compatible constants for older local scripts.
ANTHROPIC_BASE_URL = _profile_value("train", "base_url")
ANTHROPIC_API_KEY = _profile_value("train", "api_key")
ANTHROPIC_MODEL = _profile_value("train", "model")
OPENAI_BASE_URL = _profile_value("evolution", "base_url")
OPENAI_API_KEY = _profile_value("evolution", "api_key")
OPENAI_MODEL = _profile_value("evolution", "model")
DEFAULT_PROVIDER = ""
LLM_MODEL = ""
_sync_legacy_globals()

# Temperature settings for different use cases
TEMPERATURE_CREATIVE = 0.7
TEMPERATURE_ANALYTICAL = 0.3
TEMPERATURE_DETERMINISTIC = 0.0


# ══════════════════════════════════════════════════════════
#  Client Factory
# ══════════════════════════════════════════════════════════



def resolve_llm_config(
    profile: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> LLMConfig:
    """Resolve one call strictly from the selected ``LLM_PROFILES`` entry.

    Benchmark runners may load their own ``OPENAI_*`` or ``ANTHROPIC_*``
    variables for task agents. Those process-wide variables must not replace
    the host-side train/evolution/test profile selected for this call.
    Environment-backed secrets can still be configured explicitly inside the
    profile definition with ``os.getenv(...)``.
    """
    profile_name = profile or ACTIVE_PROFILE
    p = _require_profile(profile_name)
    resolved_provider = provider or p["provider"]

    return LLMConfig(
        profile=profile_name,
        provider=resolved_provider,
        model=model or p["model"],
        base_url=p["base_url"],
        api_key=p["api_key"],
    )


def get_llm_client(
    config: LLMConfig | None = None,
    profile: str | None = None,
):
    """
    Get an LLM client instance (supports Anthropic and OpenAI).

    Args:
        config: Resolved LLMConfig. If omitted, resolves from profile.
        profile: Named profile to use ("train", "evolution", "test")

    Returns:
        Anthropic or OpenAI client instance
    """
    config = config or resolve_llm_config(profile=profile)
    if config.provider == "anthropic":
        import anthropic

        return anthropic.Anthropic(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )

    elif config.provider == "openai":
        from openai import OpenAI

        return OpenAI(
            base_url=config.base_url,
            api_key=config.api_key or "dummy",
            timeout=DEFAULT_REQUEST_TIMEOUT,
        )
    raise ValueError(f"Unsupported provider: {config.provider}. Use 'anthropic' or 'openai'.")


# ══════════════════════════════════════════════════════════
#  Retry helpers
# ══════════════════════════════════════════════════════════


def _is_retryable_error(exc: Exception) -> bool:
    """Return True for transient errors worth retrying (network, rate-limit, server)."""
    # HTTP status code on the exception itself (SDK-style)
    status_code = getattr(exc, "status_code", None)
    if status_code is not None and isinstance(status_code, int):
        return status_code == 429 or status_code >= 500

    # Nested response object
    for attr in ("response", "http_response"):
        resp = getattr(exc, attr, None)
        if resp is not None:
            sc = getattr(resp, "status_code", None)
            if sc is not None and isinstance(sc, int):
                return sc == 429 or sc >= 500

    # httpx transport errors
    if isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.WriteError,
            httpx.RemoteProtocolError,
            httpx.TimeoutException,
        ),
    ):
        return True

    # Keyword fallback — catches SDK-specific error types that stringify usefully
    msg = str(exc).lower()
    retry_keywords = (
        "rate limit",
        "server error",
        "overloaded",
        "timeout",
        "connection",
        "internal error",
        "too many requests",
        "service unavailable",
        "503",
        "502",
        "504",
        "429",
    )
    return any(kw in msg for kw in retry_keywords)


def _call_with_retry(
    fn,
    max_retries: int = MAX_RETRIES,
    base_delay: float = RETRY_BASE_DELAY,
):
    """Call *fn* with exponential backoff (up to *max_retries* attempts)."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt == max_retries - 1:
                raise
            if not _is_retryable_error(exc):
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "LLM call transient error (attempt %d/%d), retrying in %.1fs: %s",
                attempt + 1,
                max_retries,
                delay,
                exc,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


def _extract_anthropic_text(response: object) -> str:
    for block in response.content:
        if getattr(block, "type", "") == "text":
            return block.text
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    raise RuntimeError(f"No text block in response: {[getattr(b, 'type', '?') for b in response.content]}")


def _extract_openai_text(response: object, config: LLMConfig) -> str:
    choices = _response_value(response, "choices")
    if not choices:
        detail = _format_openai_error(response)
        raise RuntimeError(
            "OpenAI-compatible response did not include choices "
            f"(profile={config.profile}, model={config.model}, "
            f"base_url={config.base_url}). {detail}"
        )

    message = _response_value(choices[0], "message")
    content = _response_value(message, "content") if message is not None else None
    if isinstance(content, list):
        text_parts: list[str] = []
        for block in content:
            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
            if text:
                text_parts.append(str(text))
        content = "".join(text_parts)

    if not content and message is not None:
        reasoning = _response_value(message, "reasoning_content")
        if reasoning and str(reasoning).strip():
            content = str(reasoning).strip()

    if not content:
        raise RuntimeError(
            "OpenAI-compatible response choice did not include message content "
            f"(profile={config.profile}, model={config.model}, "
            f"base_url={config.base_url})."
        )
    return str(content)


def _call_anthropic(
    client: object,
    config: LLMConfig,
    messages: list,
    temperature: float,
    max_tokens: int,
    system: str | None,
) -> str:
    kwargs = {
        "model": config.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if system:
        kwargs["system"] = system

    response = _call_with_retry(lambda: client.messages.create(**kwargs))
    return _extract_anthropic_text(response)


def _call_openai(
    client: object,
    config: LLMConfig,
    messages: list,
    temperature: float,
    max_tokens: int,
    system: str | None,
) -> str:
    openai_messages = list(messages)
    if system:
        openai_messages.insert(0, {"role": "system", "content": system})

    response = _call_with_retry(
        lambda: client.chat.completions.create(
            model=config.model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    )
    return _extract_openai_text(response, config)


# ══════════════════════════════════════════════════════════
#  Convenience Functions
# ══════════════════════════════════════════════════════════

def call_llm(
    messages: list,
    model: str | None = None,
    temperature: float = TEMPERATURE_ANALYTICAL,
    max_tokens: int = 32000,
    system: str | None = None,
    provider: str | None = None,
    profile: str | None = None,
) -> str:
    """
    Unified LLM call function (supports Anthropic and OpenAI).

    Args:
        messages: Message list, format [{"role": "user", "content": "..."}]
        model: Model name (default from profile)
        temperature: Sampling temperature
        max_tokens: Maximum tokens
        system: System prompt (optional)
        provider: "anthropic" or "openai" (default from profile)
        profile: Named profile — "train", "evolution", or "test" (default: ACTIVE_PROFILE)

    Returns:
        LLM response text
    """
    config = resolve_llm_config(profile=profile, provider=provider, model=model)
    client = get_llm_client(config)

    if config.provider == "anthropic":
        return _call_anthropic(client, config, messages, temperature, max_tokens, system)
    if config.provider == "openai":
        return _call_openai(client, config, messages, temperature, max_tokens, system)
    raise ValueError(f"Unsupported provider: {config.provider}")
