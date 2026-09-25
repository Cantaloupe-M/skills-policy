#!/usr/bin/env python3
"""
Step 1: Exploration Trace Parsing
==================================
Parse raw agent trajectories into structured ``ExplorationTrace`` objects.

The goal is NOT to extract all operations, but to identify the agent's
exploration process: what it tried, what failed, what succeeded, and
which artifacts were involved.

We detect:
- Tool calls with their inputs/outputs
- Thinking segments (especially those suggesting retry/fix/alternative)
- Error events and whether they were recovered from
- File artifacts and their lifecycles
- Retry patterns (same tool, same artifact, same goal → multiple attempts)
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from evolution.types import (
    ErrorEvent,
    ExplorationTrace,
    FileArtifact,
    NormalizedTraceEvent,
    ReusableSubstep,
    ThinkingSegment,
    ToolCallStep,
)

# ── File path patterns ────────────────────────────────────────────────────────

_PATH_EXTENSIONS = {
    "xlsx", "xls", "csv", "tsv", "json", "jsonl", "yaml", "yml",
    "py", "sh", "md", "txt", "docx", "doc", "pdf", "html", "xml",
    "png", "jpg", "jpeg", "svg", "sql", "db", "sqlite", "parquet",
    "pkl", "pickle", "h5", "pt", "onnx", "toml", "cfg", "ini", "log",
}

# These actions are useful for auditing trajectories, but are infrastructure
# primitives rather than family-level capabilities.  Publishing them creates
# instructions such as ``write_json`` that have no runtime tool binding.
INTERNAL_PRIMITIVE_ACTIONS = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "read_json",
        "write_json",
        "search_text",
        "run_test",
        "inspect_state",
        "inspect_failure",
    }
)


def is_public_substep_action(action: str) -> bool:
    """Return whether an observed action is eligible for capability publication.

    Workflows are checked component-wise so a composite observation containing a
    generic primitive cannot smuggle that primitive into a public policy.
    """
    actions = (part.strip() for part in str(action or "").split("->"))
    return not any(part in INTERNAL_PRIMITIVE_ACTIONS for part in actions)

_EXT_PATTERN = re.compile(
    r"""[\w\-./]+\.(?:""" + "|".join(_PATH_EXTENSIONS) + r""")(?:\b|["'\s])""",
    re.IGNORECASE,
)

# Patterns that indicate a file is being written
_WRITE_PATTERNS = [
    re.compile(r"""open\(\s*['"]([^'"]+\.[\w]+)['"]\s*,\s*['"][^'"]*[wax+][^'"]*['"]""", re.IGNORECASE),
    re.compile(
        r"\.(?:save|write_text|write_bytes|to_csv|to_json|to_excel|to_parquet|to_pickle|to_markdown)"
        r"\(\s*['\"]([^'\"]+\.[\w]+)['\"]",
        re.IGNORECASE,
    ),
    re.compile(r"""Path\(\s*['"]([^'"]+\.[\w]+)['"]\s*\)\.(?:write_text|write_bytes)\(""", re.IGNORECASE),
    re.compile(r"""(?:^|[\s;])>>?\s*(['"]?[\w./-]+\.[\w]+['"]?)""", re.IGNORECASE),
    re.compile(r"""(?:^|[;&\n])\s*(?:cp|mv)\s+(?:-[^\s]+\s+)*(['"]?[\w./-]+\.[\w]+['"]?)\s+(['"]?[\w./-]+\.[\w]+['"]?)""", re.IGNORECASE),
    re.compile(r"""(?:^|[;&\n])\s*touch\s+(['"]?[\w./-]+\.[\w]+['"]?)""", re.IGNORECASE),
]

# Thinking patterns suggesting retry/strategy change
_RETRY_MARKERS = (
    "retry", "try again", "again", "fix", "correct", "adjust", "update",
    "verify", "double-check", "re-run", "rerun", "instead", "revise",
    "alternative", "different approach", "let me try", "should have",
    "failed because", "error was", "the issue is", "need to",
)
_ALTERNATIVE_MARKERS = (
    "alternative", "instead", "rather than", "different approach",
    "another way", "switch to", "use.*instead",
)


def _extract_file_paths(text: str) -> list[str]:
    """Extract plausible file paths from a text string."""
    paths: list[str] = []
    for m in _EXT_PATTERN.finditer(text):
        p = m.group(0).rstrip('"').rstrip("'").rstrip()
        if not p or p.startswith(("http://", "https://")):
            continue
        paths.append(p)
    return list(dict.fromkeys(paths))


def _extract_written_paths(command: str) -> list[str]:
    """Detect files being written in a command."""
    outputs: list[str] = []
    for pattern in _WRITE_PATTERNS:
        for match in pattern.finditer(command):
            fps = _extract_file_paths(match.group(0))
            outputs.extend(fps)
    # For cp/mv, the second path is the destination
    cp_mv = _WRITE_PATTERNS[4]
    for match in cp_mv.finditer(command):
        dest = match.group(2)
        if dest:
            outputs.extend(_extract_file_paths(dest))
    return list(dict.fromkeys(outputs))


def _classify_error(error_text: str) -> str:
    """Classify an error message into a type."""
    text = error_text.lower()
    if "traceback" in text or "syntaxerror" in text or "indentationerror" in text:
        return "syntax"
    if "modulenotfounderror" in text or "importerror" in text or "command not found" in text:
        return "not_found"
    if "keyerror" in text or "attributeerror" in text or "typeerror" in text or "valueerror" in text:
        return "runtime"
    if "assert" in text or "fail" in text:
        return "assertion"
    if "permission denied" in text or "access denied" in text:
        return "permission"
    if "filenotfounderror" in text or "no such file" in text:
        return "missing_file"
    if "exit code" in text:
        try:
            code = int(re.search(r"exit code[:\s]*(\d+)", text, re.IGNORECASE).group(1))
            if code != 0:
                return "non_zero_exit"
        except (AttributeError, ValueError):
            pass
    return "unknown"


# ── Step detection helpers ────────────────────────────────────────────────────


def _is_tool_step(step: dict) -> bool:
    extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
    return bool(extra.get("tool_use_name", ""))


def _is_thinking_step(step: dict) -> bool:
    if _is_tool_step(step):
        return False
    return step.get("source") == "agent"


def _get_tool_name(step: dict) -> str:
    extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
    return extra.get("tool_use_name", "")


def _get_tool_args(step: dict) -> dict:
    extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
    return extra.get("raw_arguments", {}) or {}


def _get_tool_result(step: dict) -> str:
    extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
    meta = extra.get("tool_result_metadata", {}) or {}
    if isinstance(meta, dict):
        # Try multiple locations for the error content
        content = meta.get("truncated") or meta.get("content")
        if content:
            return str(content)
        # Check raw_tool_result (Harbor trajectory.json format)
        raw = meta.get("raw_tool_result", {}) or {}
        if isinstance(raw, dict) and raw.get("content"):
            return str(raw["content"])
        # Check tool_use_result (stdout/stderr format)
        tool_use_result = meta.get("tool_use_result", {}) or {}
        if isinstance(tool_use_result, dict):
            stdout = str(tool_use_result.get("stdout", "") or "")
            stderr = str(tool_use_result.get("stderr", "") or "")
            return "\n".join(part for part in (stdout, stderr) if part).strip()
    return ""


def _is_error(step: dict) -> bool:
    extra = step.get("extra", {}) if isinstance(step.get("extra"), dict) else {}
    if extra.get("is_error"):
        return True
    meta = extra.get("tool_result_metadata", {}) or {}
    if isinstance(meta, dict) and meta.get("is_error"):
        return True
    result = _get_tool_result(step)
    if not result:
        return False

    # Non-zero exit code (many formats)
    lower = result.lower()
    if "exit code" in lower or "exit status" in lower or "returncode" in lower:
        for m in re.finditer(r"(?:exit code|exit status|returncode)[:\s=]*(\d+)", result, re.IGNORECASE):
            try:
                if int(m.group(1)) != 0:
                    return True
            except ValueError:
                pass

    # Hard error keywords (case-sensitive for Python exceptions)
    for marker in [
        "Traceback (most recent call last)", "Error:", "error:",
        "FAILED", "ModuleNotFoundError", "KeyError", "FileNotFoundError",
        "AttributeError", "TypeError", "ValueError", "ImportError",
        "Permission denied", "command not found", "No such file",
        "SyntaxError", "IndentationError", "NameError", "RuntimeError",
        "AssertionError", "ZeroDivisionError",
    ]:
        if marker in result:
            return True

    # Looser patterns for non-Python failures
    _LOOSE_ERROR_PATTERNS = [
        r"\bfailed\b",                           # "task failed", "build failed"
        r"\bfailure\b",
        r"not found",
        r"cannot (?:find|open|read|write|parse|import)",
        r"unable to",
        r"invalid (?:file|path|argument|value|format|syntax|option)",
        r"no (?:module|file|such|attribute)",
        r"unexpected (?:error|exception|token|indent)",
        r"exception (?:raised|occurred|thrown)",
    ]
    for pat in _LOOSE_ERROR_PATTERNS:
        if re.search(pat, lower):
            return True

    # assert without capital (shell test failures, pytest output)
    if "assert " in lower and ("false" in lower or "fail" in lower):
        return True

    return False


# ── Main parsing function ─────────────────────────────────────────────────────


def parse_exploration_trace(
    raw_steps: list[dict],
    task_name: str = "",
    task_family: str = "",
) -> ExplorationTrace:
    """Parse a raw trajectory into an ExplorationTrace.

    Extracts: tool calls, thinking segments, errors, file artifacts, and
    summary statistics about the exploration process.
    """
    trace = ExplorationTrace(
        task_name=task_name,
        task_family=task_family,
        raw_steps=raw_steps,
    )

    if not raw_steps:
        return trace

    # Track seen artifacts across the trajectory
    artifact_registry: dict[str, FileArtifact] = {}
    consecutive_thinking: list[dict] = []
    thinking_start_idx = -1

    for i, step in enumerate(raw_steps):
        step_idx = i + 1  # 1-indexed

        if _is_tool_step(step):
            # Flush pending thinking
            if consecutive_thinking:
                seg = _build_thinking_segment(consecutive_thinking, thinking_start_idx, step_idx - 1)
                trace.thinking_segments.append(seg)
                consecutive_thinking = []
                thinking_start_idx = -1

            # Parse tool call
            tc = _parse_tool_call(step, step_idx)
            trace.tool_calls.append(tc)

            if tc.success is False:
                trace.errors.append(ErrorEvent(
                    step_index=step_idx,
                    tool_name=tc.tool_name,
                    error_message=tc.error_message,
                    error_type=_classify_error(tc.error_message),
                ))

            # Track artifacts
            for fp in tc.input_files + tc.output_files:
                key = Path(fp).name.lower()
                if key in artifact_registry:
                    art = artifact_registry[key]
                    art.last_seen_at_step = step_idx
                    if fp in tc.output_files:
                        art.produced_by_steps.append(step_idx)
                    if fp in tc.input_files:
                        art.consumed_by_steps.append(step_idx)
                else:
                    art = FileArtifact(
                        path=fp,
                        ext=Path(fp).suffix.lstrip(".").lower(),
                        first_seen_at_step=step_idx,
                        last_seen_at_step=step_idx,
                        produced_by_steps=[step_idx] if fp in tc.output_files else [],
                        consumed_by_steps=[step_idx] if fp in tc.input_files else [],
                    )
                    artifact_registry[key] = art

        elif _is_thinking_step(step):
            if thinking_start_idx < 0:
                thinking_start_idx = step_idx
            consecutive_thinking.append(step)

    # Flush final thinking
    if consecutive_thinking:
        seg = _build_thinking_segment(consecutive_thinking, thinking_start_idx, len(raw_steps))
        trace.thinking_segments.append(seg)

    # Finalize artifacts
    trace.file_artifacts = list(artifact_registry.values())
    for art in trace.file_artifacts:
        if art.produced_by_steps and not art.consumed_by_steps:
            art.role = "output"
        elif art.consumed_by_steps and not art.produced_by_steps:
            art.role = "input"
        else:
            art.role = "intermediate"

    return trace


def _parse_tool_call(step: dict, step_idx: int) -> ToolCallStep:
    """Parse one tool-use step into a ToolCallStep."""
    tool = _get_tool_name(step)
    args = _get_tool_args(step)
    error_text = _get_tool_result(step) if _is_error(step) else ""

    # Extract command
    cmd = ""
    desc = ""
    input_files: list[str] = []
    output_files: list[str] = []

    if tool in ("Bash",):
        cmd = args.get("command", "")
        desc = args.get("description", "")
        all_paths = _extract_file_paths(cmd)
        written = set(_extract_written_paths(cmd))
        output_files = [p for p in all_paths if p in written]
        input_files = [p for p in all_paths if p not in written]
    elif tool in ("Read",):
        fp = args.get("file_path", "")
        desc = f"Read {fp}"
        input_files = [fp] if fp else []
    elif tool in ("Write",):
        fp = args.get("file_path", "")
        content = args.get("content", "")
        desc = f"Write → {fp}"
        cmd = content if content else ""
        output_files = [fp] if fp else []
    elif tool in ("Edit",):
        fp = args.get("file_path", "")
        desc = f"Edit {fp}"
        input_files = [fp] if fp else []
        output_files = [fp] if fp else []
    else:
        desc = args.get("description", args.get("command", ""))
        fp = args.get("file_path", args.get("path", ""))
        if fp:
            input_files = [fp]

    return ToolCallStep(
        step_index=step_idx,
        tool_name=tool,
        command=cmd if cmd else "",
        description=desc if desc else "",
        input_files=list(dict.fromkeys(input_files)),
        output_files=list(dict.fromkeys(output_files)),
        success=not _is_error(step),
        error_message=error_text if error_text else "",
    )


def _build_thinking_segment(
    steps: list[dict],
    start_idx: int,
    end_idx: int,
) -> ThinkingSegment:
    """Build a ThinkingSegment from consecutive thinking steps."""
    texts = [
        str(step.get("message", "")).strip()
        for step in steps
        if str(step.get("message", "")).strip()
    ]
    combined = " ".join(texts)
    lower = combined.lower()

    return ThinkingSegment(
        step_indices=(start_idx, end_idx),
        text=combined[:2000],
        suggests_retry=any(marker in lower for marker in _RETRY_MARKERS),
        mentions_fix=any(m in lower for m in ("fix", "correct", "adjust", "debug")),
        mentions_alternative=any(
            re.search(pat, lower) for pat in _ALTERNATIVE_MARKERS
        ),
    )


# ── Normalized event extraction ───────────────────────────────────────────────


def _normalize_target(paths: list[str], fallback: str = "") -> str | None:
    """Return a stable target token from files or command text."""
    if paths:
        suffixes = [Path(p).suffix.lower().lstrip(".") for p in paths if Path(p).suffix]
        if suffixes:
            return f"*.{suffixes[0]}"
        return Path(paths[0]).name.lower()[:80]
    text = (fallback or "").strip().lower()
    if not text:
        return None
    text = re.sub(r"['\"][^'\"]{1,120}['\"]", "<quoted>", text)
    text = re.sub(r"\b\d+\b", "<num>", text)
    text = re.sub(r"\s+", " ", text)
    return text[:80]


def _normalize_bash_action(command: str, description: str = "") -> tuple[str, str | None]:
    """Collapse shell commands into action families used by opportunity mining."""
    cmd = (command or "").strip()
    lower = cmd.lower()
    paths = _extract_file_paths(cmd)
    first = lower.split(maxsplit=1)[0] if lower.split() else ""

    if re.search(r"(^|[;&|]\s*)(rg|grep|find)\b", lower):
        return "search_text", _normalize_target(paths, lower)
    if first in {"cat", "less", "more", "head", "tail", "nl"} or re.search(r"(^|[;&|]\s*)sed\s+-n\b", lower):
        return "read_file", _normalize_target(paths, lower)

    # Prefer semantic library operations over the generic write/edit bucket.
    if re.search(r"\b(openpyxl|xlrd|xlwt|xlwings|xlsxwriter)\b", lower):
        if _extract_written_paths(cmd):
            return "write_spreadsheet", _normalize_target(_extract_written_paths(cmd), lower)
        return "read_spreadsheet", _normalize_target(paths, lower)
    if re.search(r"\b(pdfplumber|pypdf|pdfminer|fitz\b|pikepdf|camelot)\b", lower):
        return "extract_pdf", _normalize_target(paths, lower)
    if re.search(r"\bjson\.(dump|dumps)\b", lower):
        return "write_json", _normalize_target(paths, lower)
    if re.search(r"\bjson\.(load|loads)\b", lower):
        return "read_json", _normalize_target(paths, lower)
    if re.search(r"\bpd\.read_\w+\b", lower):
        return "read_dataframe", _normalize_target(paths, lower)
    if re.search(r"\bpd\.to_\w+\b|\.to_csv\(|\.to_excel\(|\.to_json\(|\.to_parquet\(", lower):
        return "write_dataframe", _normalize_target(paths, lower)
    if "apply_patch" in lower or re.search(r"(^|[;&|]\s*)(python|python3)\b.*\b(write_text|write_bytes|open\()", lower, re.S):
        return "edit_file", _normalize_target(paths, lower)
    if _extract_written_paths(cmd):
        return "write_file", _normalize_target(_extract_written_paths(cmd), lower)
    if re.search(r"(^|[;&|]\s*)(pytest|python\s+-m\s+pytest|npm\s+test|pnpm\s+test|yarn\s+test|cargo\s+test|go\s+test)\b", lower):
        return "run_test", _normalize_target(paths, lower)
    if re.search(r"(^|[;&|]\s*)(git\s+diff|git\s+status|git\s+show)\b", lower):
        return "inspect_state", _normalize_target(paths, lower)
    if any(marker in lower for marker in ("traceback", "failed", "error", "assert")):
        return "inspect_failure", _normalize_target(paths, lower)

    # Other deterministic operations remain useful fine-grained substeps.
    if re.search(r"\b(plt\.\w+|sns\.\w+|\.plot\(|\.scatter\(|\.bar\(|\.hist\()", lower):
        return "generate_plot", _normalize_target(paths, lower)
    if re.search(r"\b(requests\.\w+|urllib\.request|httpx\.\w+|curl\b)", lower):
        return "http_request", _normalize_target(paths, lower)
    if re.search(r"\b(BeautifulSoup|bs4|\.select\(|\.find_all\(|lxml|html\.parser)", lower):
        return "parse_html", _normalize_target(paths, lower)

    return "other_command", (_normalize_target(paths, description or lower) if paths else None)


def _event_cost(action: str, success: bool | None) -> float:
    base = {
        "search_text": 0.8,
        "read_file": 0.6,
        "edit_file": 1.2,
        "write_file": 1.1,
        "run_test": 1.4,
        "inspect_failure": 0.9,
        "inspect_state": 0.5,
        # Fine-grained operations — cost proportional to complexity
        "read_spreadsheet": 0.9,
        "write_spreadsheet": 1.2,
        "extract_pdf": 1.0,
        "read_json": 0.6,
        "write_json": 0.9,
        "read_dataframe": 0.8,
        "write_dataframe": 1.0,
        "generate_plot": 1.1,
        "http_request": 0.7,
        "parse_html": 0.9,
    }.get(action, 0.4)
    if success is False:
        base += 0.8
    return base


def normalize_trace_events(trace: ExplorationTrace, trace_index: int = 0) -> list[NormalizedTraceEvent]:
    """Normalize parsed trace tool calls into stable action tokens.

    This stage is deliberately deterministic: it prepares evidence for skill
    opportunity mining but does not decide whether an opportunity exists.
    """
    events: list[NormalizedTraceEvent] = []
    for tc in trace.tool_calls:
        tool = (tc.tool_name or "").strip()
        command_text = tc.command or tc.description or ""
        if tool == "Bash":
            action, target = _normalize_bash_action(tc.command, tc.description)
        elif tool in {"Read", "NotebookRead"}:
            action, target = "read_file", _normalize_target(tc.input_files, tc.description)
        elif tool == "Edit":
            action, target = "edit_file", _normalize_target(tc.output_files or tc.input_files, tc.description)
        elif tool in {"Write", "NotebookEdit"}:
            action, target = "write_file", _normalize_target(tc.output_files or tc.input_files, tc.description)
        elif tool in {"Grep", "Glob"}:
            action, target = "search_text", _normalize_target(tc.input_files, tc.description)
        else:
            action, target = "other_tool", _normalize_target(tc.input_files + tc.output_files, tc.description)

        if tc.success is False and action in {"run_test", "other_command", "other_tool"}:
            action = "inspect_failure" if action != "run_test" else action

        signature_target = target or "any"
        events.append(NormalizedTraceEvent(
            idx=tc.step_index,
            trace_index=trace_index,
            role="tool",
            event_type="tool_call",
            tool_name=tool,
            raw_text=command_text[:1000],
            normalized_action=action,
            target=target,
            signature_token=f"{action}:{signature_target}",
            success=tc.success,
            error_type=_classify_error(tc.error_message) if tc.error_message else "",
            cost=_event_cost(action, tc.success),
        ))
    return events


def _parameterize_command(text: str) -> str:
    """Remove task-instance values while retaining an executable operation shape."""
    value = str(text or "").strip()
    if not value:
        return ""
    value = re.sub(
        r"(?P<quote>['\"])(?P<path>[^'\"]+\.(?:xlsx?|csv|tsv|jsonl?|pdf|docx?|py|txt|ya?ml|xml))(?P=quote)",
        r"<artifact>",
        value,
        flags=re.IGNORECASE,
    )
    value = re.sub(r"(?:^|[\s=(])(/[^\s'\")]+)", r" <path>", value)
    value = re.sub(r"\b[A-Z]{2,}[A-Z0-9_-]*\d{3,}\b", "<id>", value)
    value = re.sub(r"\b\d+(?:\.\d+)?\b", "<num>", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:320]


def extract_reusable_substeps(trace: ExplorationTrace) -> list[ReusableSubstep]:
    """Decompose a trace into atomic operations and short verified workflows.

    The decomposition is deterministic; semantic clustering happens later.  Only
    successful tool calls are eligible here, so a policy cannot be created from a
    command merely observed in a failed attempt.
    """
    events = normalize_trace_events(trace)
    calls = trace.tool_calls
    atoms: list[ReusableSubstep] = []
    ignored = {"other_command", "other_tool"}
    for event, call in zip(events, calls):
        if call.success is not True or event.normalized_action in ignored:
            continue
        inputs = tuple(sorted({Path(path).suffix.lower().lstrip(".") for path in call.input_files if Path(path).suffix}))
        outputs = tuple(sorted({Path(path).suffix.lower().lstrip(".") for path in call.output_files if Path(path).suffix}))
        command = _parameterize_command(call.command or call.description)
        signature = f"{event.normalized_action}:{event.target or 'any'}:{','.join(inputs)}->{','.join(outputs)}"
        atoms.append(
            ReusableSubstep(
                step_indices=(event.idx,),
                action=event.normalized_action,
                tool_name=event.tool_name,
                target=event.target,
                signature=signature,
                command_shape=command,
                input_formats=inputs,
                output_formats=outputs,
            )
        )

    # Preserve short workflows as first-class patterns.  A gap of a few
    # transcript steps is allowed because assistant text and tool results sit
    # between consecutive tool calls in stream-json trajectories.
    workflows: list[ReusableSubstep] = []
    for left, right in zip(atoms, atoms[1:]):
        if right.step_indices[0] - left.step_indices[0] > 4 or left.action == right.action:
            continue
        actions = (left.action, right.action)
        workflows.append(
            ReusableSubstep(
                step_indices=left.step_indices + right.step_indices,
                kind="workflow",
                action=" -> ".join(actions),
                tool_name=f"{left.tool_name}+{right.tool_name}",
                target=right.target or left.target,
                signature="workflow:" + "->".join(
                    (left.signature, right.signature)
                ),
                command_shape=" -> ".join(
                    item for item in (left.command_shape, right.command_shape) if item
                ),
                input_formats=tuple(sorted(set(left.input_formats + right.input_formats))),
                output_formats=tuple(sorted(set(left.output_formats + right.output_formats))),
            )
        )
    trace.reusable_substeps = [*atoms, *workflows]
    return trace.reusable_substeps


def _operation_shapes(trace: ExplorationTrace) -> list[str]:
    """Return bounded, parameterized operations for cross-attempt comparison."""
    operations: list[str] = []
    for event in normalize_trace_events(trace):
        shape = _parameterize_command(event.raw_text)
        status = "failed" if event.success is False else "succeeded"
        detail = f"{event.signature_token} [{status}]"
        if shape:
            detail += f" {shape}"
        operations.append(detail[:500])
    return operations[:60]


def _ordered_difference(items: list[str], subtract: list[str]) -> list[str]:
    remaining = Counter(subtract)
    result: list[str] = []
    for item in items:
        if remaining[item] > 0:
            remaining[item] -= 1
        else:
            result.append(item)
    return result


def _build_retry_transition(
    source: ExplorationTrace,
    retry: ExplorationTrace,
) -> dict[str, object]:
    """Describe what changed between one failed attempt and its direct retry."""
    source_operations = _operation_shapes(source)
    retry_operations = _operation_shapes(retry)
    source_counts = Counter(source_operations)
    retained: list[str] = []
    for operation in retry_operations:
        if source_counts[operation] > 0:
            retained.append(operation)
            source_counts[operation] -= 1
    return {
        "from_attempt": source.attempt_number,
        "to_attempt": retry.attempt_number,
        "retry_verifier_passed": retry.verifier_passed,
        "source_operations": source_operations,
        "retry_operations": retry_operations,
        "retained_operations": retained[:30],
        "added_operations": _ordered_difference(retry_operations, source_operations)[:30],
        "removed_operations": _ordered_difference(source_operations, retry_operations)[:30],
    }


# ── Batch parsing ─────────────────────────────────────────────────────────────


def parse_trajectories(
    trial_data: list[dict],
    task_family: str = "",
) -> list[ExplorationTrace]:
    """Parse multiple trial trajectories into ExplorationTrace objects."""
    traces: list[ExplorationTrace] = []
    for trial in trial_data:
        raw_steps = trial.get("raw_steps", trial.get("trajectory", []))
        task_name = trial.get("task_name", "")
        trace = parse_exploration_trace(raw_steps, task_name, task_family)
        trace.attempt_id = str(trial.get("attempt_id", task_name))
        trace.attempt_number = int(trial.get("attempt_number", 1) or 1)
        trace.verifier_passed = bool(trial.get("verifier_passed", False))
        trace.reward = trial.get("reward")
        trace.reflection = str(trial.get("reflection") or "")
        trace.reflection_files = [str(item) for item in trial.get("reflection_files", []) if item]
        trace.reflection_source_attempt = trace.attempt_number if trace.reflection else None
        trace.used_skill_ids = list(trial.get("used_skill_ids", []))
        trace.used_policy_ids = list(trial.get("used_policy_ids", []))
        trace.used_implementation_ids = list(trial.get("used_implementation_ids", []))
        trace.used_script_ids = list(trial.get("used_script_ids", []))
        trace.used_memory_ids = list(trial.get("used_memory_ids", []))
        trace.memory_query_count = int(trial.get("memory_query_count", 0) or 0)
        extract_reusable_substeps(trace)
        traces.append(trace)
    # A reflection belongs to the failed attempt that produced it and directly
    # guides only the immediately following retry.  Do not let a later success
    # retroactively validate an earlier reflection whose own retry failed.
    by_task: dict[str, list[ExplorationTrace]] = {}
    for trace in traces:
        by_task.setdefault(trace.task_name, []).append(trace)
    for task_traces in by_task.values():
        task_traces.sort(key=lambda item: item.attempt_number)
        by_attempt = {trace.attempt_number: trace for trace in task_traces}
        for trace in task_traces:
            if not trace.reflection:
                continue
            retry = by_attempt.get(trace.attempt_number + 1)
            if retry is None:
                trace.reflection_retry_outcome = "missing"
                trace.reflection_verified_by_retry = False
                trace.retry_transition = {
                    "from_attempt": trace.attempt_number,
                    "to_attempt": trace.attempt_number + 1,
                    "retry_verifier_passed": None,
                    "source_operations": _operation_shapes(trace),
                    "retry_operations": [],
                    "retained_operations": [],
                    "added_operations": [],
                    "removed_operations": [],
                    "artifact_missing": True,
                }
            elif retry.verifier_passed:
                trace.reflection_retry_outcome = "success"
                trace.reflection_verified_by_retry = True
                trace.retry_transition = _build_retry_transition(trace, retry)
            else:
                trace.reflection_retry_outcome = "failure"
                trace.reflection_verified_by_retry = False
                trace.retry_transition = _build_retry_transition(trace, retry)
    return traces
