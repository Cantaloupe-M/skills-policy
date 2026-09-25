"""Claude Code artifact parsing shared by benchmark integrations."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from evolution.outcome import TaskContract

TEXT_ARTIFACT_LIMIT = 20_000
STEP_TEXT_LIMIT = 3_000
# This is a prompt-evidence budget, not a tail window.  The selector below
# retains early setup, all state-changing/error events, the final validation
# phase, and a spread of the remaining events with their original step IDs.
MAX_COMPACTED_STEPS = 120
HEAD_CONTEXT_STEPS = 8
TAIL_CONTEXT_STEPS = 24
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
CAST_EVENT_RE = re.compile(r'^\[\s*\d+(?:\.\d+)?\s*,\s*"[io]"\s*,')
PROGRESS_NOISE_RE = re.compile(
    r"^(?:[#=\-\s]{20,}(?:\s*\d+(?:\.\d+)?%)?|[⠁⠂⠄⡀⢀⠠⠐⠈⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏])$"
)


def build_task_contract(
    task_dir: Path | None,
    *,
    task_source: str = "",
) -> TaskContract:
    """Extract a generic task contract from a Harbor task directory."""
    instruction = ""
    input_artifacts: list[dict[str, Any]] = []
    verifier_checks: list[str] = []
    if task_dir is not None and task_dir.is_dir():
        instruction = _read_instruction(task_dir)
        environment_dir = task_dir / "environment"
        if environment_dir.is_dir():
            for path in sorted(environment_dir.iterdir()):
                if path.is_file() and path.name != "Dockerfile":
                    input_artifacts.append(_artifact_record(path))

        tests_dir = task_dir / "tests"
        if tests_dir.is_dir():
            for path in sorted(tests_dir.glob("test*.py")):
                verifier_checks.extend(_extract_test_names(path))

    return TaskContract(
        family=task_source,
        objective=instruction,
        input_artifacts=input_artifacts,
        output_artifacts=_extract_output_artifacts(instruction),
        required_capabilities=_infer_required_capabilities(instruction, task_source),
        constraints=_extract_constraints(instruction),
        verifier_checks=verifier_checks[:100],
    )


def compact_claude_trajectory(trial_dir: Path) -> list[dict[str, Any]]:
    """Build a causally useful, bounded trajectory from Claude Code artifacts."""
    trial_dir = Path(trial_dir)
    stream_steps = _compact_stream_json_trajectory(trial_dir)
    if stream_steps:
        return _select_reflection_steps(_renumber_steps(stream_steps))

    chunks: list[tuple[str, str]] = []
    for path in _candidate_text_files(trial_dir):
        text = _read_text(path)
        if not text:
            continue
        chunks.extend(_chunk_text(path.name, text))

    steps: list[dict[str, Any]] = []
    for idx, (source, text) in enumerate(chunks, start=1):
        steps.append(
            {
                "step": idx,
                "action": source,
                "code": text[:STEP_TEXT_LIMIT],
                "result": "",
            }
        )
    return _select_reflection_steps(steps)


def _compact_stream_json_trajectory(trial_dir: Path) -> list[dict[str, Any]]:
    """Parse Claude Code ``--output-format stream-json`` logs into trajectory steps."""
    steps: list[dict[str, Any]] = []
    for path in _stream_json_log_candidates(trial_dir):
        for event in _iter_stream_json_events(path):
            steps.extend(_event_to_steps(event, path.name))
        if steps:
            break
    return steps


def _stream_json_log_candidates(trial_dir: Path) -> list[Path]:
    candidates = [
        trial_dir / "agent" / "claude-code.txt",
        trial_dir / "agent" / "claude_code.txt",
        trial_dir / "sessions" / "agent.log",
        trial_dir / "agent.log",
        trial_dir / "claude-code.txt",
        trial_dir / "claude_code.txt",
    ]
    for subdir_name in ("agent", "sessions", "logs", "agent-logs"):
        subdir = trial_dir / subdir_name
        if subdir.is_dir():
            candidates.extend(sorted(subdir.rglob("claude-code.txt")))
            candidates.extend(sorted(subdir.rglob("claude_code.txt")))
            candidates.extend(sorted(subdir.rglob("agent.log")))
    seen: set[Path] = set()
    result: list[Path] = []
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        result.append(path)
    return result


def _iter_stream_json_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in _read_text(path).splitlines():
        stripped = ANSI_ESCAPE_RE.sub("", line).strip()
        if not stripped.startswith("{"):
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and "type" in event:
            events.append(event)
    return events


def _event_to_steps(event: dict[str, Any], source: str) -> list[dict[str, Any]]:
    event_type = event.get("type")
    if event_type == "assistant":
        return _assistant_event_steps(event, source)
    if event_type == "user":
        return _tool_result_steps(event, source)
    if event_type == "result":
        result = str(event.get("result") or "").strip()
        if result:
            return [_make_step(source, "final_result", result)]
    return []


def _assistant_event_steps(event: dict[str, Any], source: str) -> list[dict[str, Any]]:
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    content = message.get("content", [])
    if not isinstance(content, list):
        return []

    steps: list[dict[str, Any]] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "text":
            text = str(item.get("text") or "").strip()
            if text:
                steps.append(_make_step(source, "assistant_text", text))
        elif item_type == "tool_use":
            name = str(item.get("name") or "tool")
            tool_input = item.get("input", {})
            payload = {
                "function_name": name,
                "arguments": tool_input if isinstance(tool_input, dict) else {"value": tool_input},
            }
            description = ""
            if isinstance(tool_input, dict):
                description = str(tool_input.get("description") or "").strip()
            code = f"{description}\n{json.dumps(payload, ensure_ascii=False)}".strip()
            steps.append(_make_step(source, name, code, tool_use_id=str(item.get("id") or "")))
    return steps


def _tool_result_steps(event: dict[str, Any], source: str) -> list[dict[str, Any]]:
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    content = message.get("content", [])
    if not isinstance(content, list):
        return []

    steps: list[dict[str, Any]] = []
    for item in content:
        if not isinstance(item, dict) or item.get("type") != "tool_result":
            continue
        tool_use_id = str(item.get("tool_use_id") or "")
        text = _tool_result_text(item, event)
        if text:
            action = "tool_result_error" if item.get("is_error") else "tool_result"
            steps.append(_make_step(source, action, text, tool_use_id=tool_use_id))
    return steps


def _tool_result_text(item: dict[str, Any], event: dict[str, Any]) -> str:
    result = event.get("tool_use_result")
    if isinstance(result, dict):
        for key in ("stdout", "content", "stderr"):
            value = result.get(key)
            if value:
                return str(value).strip()
        if "filenames" in result:
            return "\n".join(str(name) for name in result.get("filenames") or [])
    content = item.get("content")
    if isinstance(content, str):
        return content.strip()
    return json.dumps(content, ensure_ascii=False)[:STEP_TEXT_LIMIT] if content else ""


def _make_step(
    source: str,
    action: str,
    code: str,
    *,
    tool_use_id: str = "",
) -> dict[str, Any]:
    return {
        "step": 0,
        "action": action,
        "source": source,
        "tool_use_id": tool_use_id,
        "code": code[:STEP_TEXT_LIMIT],
        "result": "",
    }


def _renumber_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for idx, step in enumerate(steps, start=1):
        step["step"] = idx
    return steps


def _select_reflection_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select evidence across a trial instead of discarding everything before its tail.

    Step numbers are assigned before selection, so a reflection can refer back to
    the original trajectory.  State-changing commands and error-bearing results
    are retained before representative read-only events are sampled.
    """
    if len(steps) <= MAX_COMPACTED_STEPS:
        return steps

    selected = set(range(min(HEAD_CONTEXT_STEPS, len(steps))))
    selected.update(range(max(0, len(steps) - TAIL_CONTEXT_STEPS), len(steps)))
    selected.update(index for index, step in enumerate(steps) if _is_critical_step(step))

    # Keep the available budget representative of the entire attempt, rather
    # than biased toward either setup or the final few commands.
    remaining = MAX_COMPACTED_STEPS - len(selected)
    if remaining > 0:
        available = [index for index in range(len(steps)) if index not in selected]
        for slot in range(remaining):
            if not available:
                break
            position = (slot + 1) * len(available) // (remaining + 1)
            selected.add(available[position])

    # Extremely long trials can have more critical events than the evidence
    # budget.  Preserve setup and closure, then sample those events uniformly.
    if len(selected) > MAX_COMPACTED_STEPS:
        protected = set(range(min(HEAD_CONTEXT_STEPS, len(steps))))
        protected.update(range(max(0, len(steps) - TAIL_CONTEXT_STEPS), len(steps)))
        candidates = sorted(selected - protected)
        budget = max(0, MAX_COMPACTED_STEPS - len(protected))
        sampled = {
            candidates[(slot + 1) * len(candidates) // (budget + 1)]
            for slot in range(budget)
        } if budget else set()
        selected = protected | sampled

    return [steps[index] for index in sorted(selected)]


def _is_critical_step(step: dict[str, Any]) -> bool:
    """Identify operations that can plausibly explain a later verifier result."""
    action = str(step.get("action") or "").lower()
    text = str(step.get("code") or step.get("result") or "").lower()
    action_markers = (
        "bash", "shell", "command", "write", "edit", "create", "patch",
        "delete", "move", "copy", "test", "pytest", "tool_result_error",
    )
    error_markers = ("traceback", "error", "failed", "exception", "assertionerror")
    return any(marker in action for marker in action_markers) or any(marker in text for marker in error_markers)


def _read_instruction(task_dir: Path) -> str:
    instruction_path = task_dir / "instruction.md"
    return _read_text(instruction_path)[:TEXT_ARTIFACT_LIMIT] if instruction_path.is_file() else ""


def _candidate_text_files(trial_dir: Path) -> list[Path]:
    names = (
        "post_agent_pane.txt",
        "panes/post-agent.txt",
    )
    candidates = [trial_dir / name for name in names]
    for subdir_name in ("agent", "agent-logs", "logs"):
        subdir = trial_dir / subdir_name
        if subdir.is_dir():
            candidates.extend(
                path
                for path in sorted(subdir.rglob("*"))
                if path.is_file() and path.suffix.lower() in {".txt", ".log"}
            )
    return [path for path in candidates if path.is_file()]


def _chunk_text(source: str, text: str) -> list[tuple[str, str]]:
    lines = [
        cleaned
        for line in text.splitlines()
        if (cleaned := _clean_artifact_line(line))
    ]
    if not lines:
        return []

    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= 25:
            chunks.append((source, "\n".join(current)))
            current = []
    if current:
        chunks.append((source, "\n".join(current)))
    return chunks


def _clean_artifact_line(line: str) -> str:
    """Drop terminal recording artifacts before they can pollute skill evidence."""
    line = ANSI_ESCAPE_RE.sub("", line).replace("\r", "").strip()
    if not line:
        return ""
    if CAST_EVENT_RE.match(line):
        return ""
    if PROGRESS_NOISE_RE.match(line):
        return ""
    if line.count("#") >= 20 and "%" in line:
        return ""
    return line


def _artifact_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "name": path.name, "extension": path.suffix.lower()}


def _extract_test_names(path: Path) -> list[str]:
    text = _read_text(path)
    return re.findall(r"^def\s+(test_[a-zA-Z0-9_]+)\s*\(", text, re.MULTILINE)


def _extract_output_artifacts(instruction: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in re.finditer(r"(?<![\w.-])(/[^\s`'\"<>]+(?:\.[A-Za-z0-9_-]+)?)", instruction):
        value = match.group(1).rstrip(".,;:)")
        if value in seen:
            continue
        seen.add(value)
        artifacts.append({"path": value, "name": Path(value).name, "extension": Path(value).suffix.lower()})
    return artifacts


def _infer_required_capabilities(instruction: str, task_source: str) -> list[str]:
    text = f"{task_source} {instruction}".lower()
    capabilities: list[str] = []
    terms = {
        "terminal-operation": ("terminal", "shell", "command", "cli", "server"),
        "artifact-generation": ("write", "save", "export", "output", "generate", "create"),
        "input-parsing": ("read", "load", "parse", "extract"),
        "debugging": ("fix", "debug", "error", "failing", "broken"),
        "validation": ("test", "verify", "validate", "check"),
    }
    for capability, needles in terms.items():
        if any(needle in text for needle in needles):
            capabilities.append(capability)
    return capabilities


def _extract_constraints(instruction: str) -> list[str]:
    constraints: list[str] = []
    for line in instruction.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if stripped and any(term in lower for term in ("must", "exactly", "do not", "only", "required")):
            constraints.append(stripped[:300])
    return constraints[:50]


def _read_text(path: Path) -> str:
    try:
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            return json.dumps(data, ensure_ascii=False, indent=2)
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
