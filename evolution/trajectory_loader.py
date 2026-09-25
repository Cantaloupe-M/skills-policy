"""Trajectory loading and compaction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def load_trajectories(job_dir: Path) -> list[dict[str, Any]]:
    """Load every staged attempt, or every direct trial, with verifier outcomes."""
    trials: list[dict[str, Any]] = []
    for child in sorted(job_dir.iterdir()):
        if not child.is_dir():
            continue
        manifest = child / "attempt_manifest.json"
        attempts_dir = child / "attempts"
        if manifest.is_file() and attempts_dir.is_dir():
            for attempt in _load_staged_attempts(child, manifest):
                trials.append(attempt)
            continue
        trial = _load_trial(child, task_name=child.name, attempt_id=child.name, attempt_number=1)
        if trial:
            trials.append(trial)
    return trials


def _load_staged_attempts(task_dir: Path, manifest_path: Path) -> list[dict[str, Any]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    task_name = str(manifest.get("task_name") or task_dir.name)
    attempts = manifest.get("attempts", [])
    if not isinstance(attempts, list):
        return []
    result: list[dict[str, Any]] = []
    for item in attempts:
        if not isinstance(item, dict):
            continue
        number = int(item.get("number", 0) or 0)
        attempt_dir = task_dir / "attempts" / f"attempt_{number:02d}"
        trial = _load_trial(
            attempt_dir,
            task_name=task_name,
            attempt_id=f"{task_name}:{number}",
            attempt_number=number,
            outcome={
                "verifier_passed": bool(item.get("success", False)),
                "reward": item.get("reward"),
                "exception_info": item.get("exception_info"),
                "outcome": item.get("outcome"),
                "trajectory_available": item.get("trajectory_available"),
            },
            reflection_files=item.get("reflection_files", []),
        )
        if trial:
            result.append(trial)
    return result


def _load_trial(
    trial_dir: Path,
    *,
    task_name: str,
    attempt_id: str,
    attempt_number: int,
    outcome: dict[str, Any] | None = None,
    reflection_files: list[str] | None = None,
) -> dict[str, Any] | None:
    raw = _load_raw_steps(trial_dir)
    files, reflection = _load_reflection(trial_dir, reflection_files)
    # A reflection is itself a usable instance-level memory.  Keep it even
    # when the container failed to expose the raw trajectory; the pipeline will
    # still emit a missing-trajectory diagnostic for audit purposes.
    if raw is None and not reflection:
        return None
    raw = raw or []
    return {
        "task_name": task_name,
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "raw_steps": raw,
        "compacted": _compact_steps(raw),
        "trajectory": raw,
        "reflection": reflection,
        "reflection_files": files,
        **(outcome or _load_outcome(trial_dir)),
        **_extract_skill_usage(raw),
    }


def _load_reflection(
    trial_dir: Path,
    manifest_files: list[str] | None = None,
) -> tuple[list[str], str]:
    """Load the reflection memory emitted for a failed attempt.

    Reflections are sidecars of the failed attempt (the retry itself lives in a
    sibling directory), so trajectory loading must read them explicitly rather
    than expecting them in ``trajectory.json``.
    """
    names = [
        str(name)
        for name in (manifest_files or [])
        if str(name).startswith("reflection_attempt_") and str(name).endswith(".md")
    ]
    if not names:
        names = [path.name for path in trial_dir.glob("reflection_attempt_*.md")]
    names = sorted(dict.fromkeys(names))
    parts: list[str] = []
    for name in names:
        try:
            content = (trial_dir / name).read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            continue
        if content:
            parts.append(content)
    return names, "\n\n".join(parts)


def _load_raw_steps(trial_dir: Path) -> list[dict[str, Any]] | None:
    trajectory_path = trial_dir / "agent" / "trajectory.json"
    if trajectory_path.is_file():
        try:
            return json.loads(trajectory_path.read_text(encoding="utf-8")).get("steps", [])
        except (OSError, json.JSONDecodeError):
            return None
    for log_path in (
        trial_dir / "agent" / "claude-code.txt",
        trial_dir / "agent" / "claude_code.txt",
        trial_dir / "sessions" / "agent.log",
    ):
        if log_path.is_file():
            return _parse_stream_json_trajectory(log_path)
    return None


def _load_outcome(trial_dir: Path) -> dict[str, Any]:
    reward: float | None = None
    result_path = trial_dir / "result.json"
    if result_path.is_file():
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
            rewards = result.get("verifier_result", {}).get("rewards", {})
            raw_reward = rewards.get("reward", result.get("reward"))
            if isinstance(raw_reward, (int, float)):
                reward = float(raw_reward)
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    reward_path = trial_dir / "verifier" / "reward.txt"
    if reward is None and reward_path.is_file():
        try:
            reward = float(reward_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pass
    return {"verifier_passed": reward is not None and reward >= 1.0, "reward": reward}


def _extract_skill_usage(raw_steps: list[dict[str, Any]]) -> dict[str, Any]:
    text = json.dumps(raw_steps, ensure_ascii=False)
    skill_ids = list(dict.fromkeys(match.lower() for match in re.findall(
        r"/(?:\.claude|\.codex|\.agents)/skills/([a-z0-9][a-z0-9-]*)/SKILL\.md", text, re.I
    )))
    # Policy cards are agent-facing slugs; internal registry IDs are resolved
    # privately by the compiler when evidence is evaluated.
    policy_ids = list(dict.fromkeys(re.findall(r"references/(?:policies/)?([a-z0-9][a-z0-9-]+)\.md", text, re.I)))
    implementation_ids = list(dict.fromkeys(re.findall(r"(?:implementation|impl):([a-z0-9-]+)", text, re.I)))
    script_ids = list(dict.fromkeys(re.findall(r"scripts/(?:experimental|capabilities)/([a-z0-9_.-]+\.py)", text, re.I)))
    memory_ids = list(dict.fromkeys(re.findall(r"memory-[a-f0-9]{20}", text, re.I)))
    memory_query_count = len(
        re.findall(r"mcp__experience_memory__(?:search_memories|get_memory)", text, re.I)
    )
    return {
        "used_skill_ids": skill_ids,
        "used_policy_ids": policy_ids,
        "used_implementation_ids": implementation_ids,
        "used_script_ids": script_ids,
        "used_memory_ids": memory_ids,
        "memory_query_count": memory_query_count,
    }


def _parse_stream_json_trajectory(log_path: Path) -> list[dict]:
    steps: list[dict] = []

    def push(source: str, text: str, extra: dict[str, Any], step_id: str = "") -> None:
        steps.append({"step": len(steps) + 1, "source": source, "message": text, "step_id": step_id, "extra": extra})

    def attach(tool_use_id: str, content: Any, is_error: bool) -> None:
        if not tool_use_id:
            return
        for step in reversed(steps):
            extra = step.get("extra", {})
            if extra.get("tool_use_id") == tool_use_id:
                extra["tool_result_metadata"] = {"content": str(content or "")[:2000], "is_error": is_error, "tool_use_id": tool_use_id}
                extra["is_error"] = is_error
                return

    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message", {}) or {}
        content: Any = message if isinstance(message, str) else message.get("content", "") or ""
        if event.get("type") == "user":
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        attach(str(block.get("tool_use_id", "")), block.get("content", ""), bool(block.get("is_error", False)))
                    elif isinstance(block, dict) and block.get("text"):
                        texts.append(block["text"])
                content = " ".join(texts)
            if str(content).strip():
                push("user", str(content)[:1000], {"is_sidechain": False}, event.get("step_id", ""))
        elif event.get("type") == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and str(block.get("text", "")).strip():
                    push("agent", str(block["text"])[:300], {"is_sidechain": False}, event.get("step_id", ""))
                elif block.get("type") == "tool_use":
                    push("agent", "", {"tool_use_name": block.get("name", ""), "tool_use_id": block.get("id", ""), "raw_arguments": block.get("input", {}), "is_sidechain": False}, event.get("step_id", ""))
        elif event.get("type") == "tool_result":
            attach(str(event.get("tool_use_id", "")), content, bool(event.get("is_error", False)))
    return steps


def _compact_steps(steps: list[dict]) -> list[dict]:
    out: list[dict] = []
    for i, step in enumerate(steps, 1):
        extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
        tool = extra.get("tool_use_name", "")
        raw_args = extra.get("raw_arguments", {}) or {}
        message = step.get("message", "") or ""
        if tool:
            out.append({"step": i, "type": "tool_call", "tool": tool, "description": raw_args.get("description", "")[:200], "command": (raw_args.get("command") or raw_args.get("description") or "")[:800]})
        elif step.get("source") == "agent" and message.strip():
            out.append({"step": i, "type": "thinking", "text": message[:300]})
        elif step.get("source") == "user":
            out.append({"step": i, "type": "user_prompt", "text": message[:300]})
    return out
