"""Deterministic compaction for repeated workflow instructions.

Generated skills often describe the same planning, checking, or validation gate
in both the workflow and a later checklist.  This module removes only highly
similar actionable list items, keeping the more specific wording.  Headings,
tables, prose, and fenced examples are left untouched.
"""

from __future__ import annotations

import re

_LIST_ITEM = re.compile(r"^(\s*(?:[-*+]\s+|\d+[.)]\s+|[-*+]\s+\[[ xX]\]\s+))(.*\S)\s*$")
_TOKEN = re.compile(r"[a-z][a-z0-9_-]{2,}")
_STOP_WORDS = {
    "and", "are", "before", "current", "each", "every", "from", "into",
    "must", "only", "required", "the", "this", "when", "with", "your",
    "then", "that", "after", "task", "output", "artifact", "source",
}
_PLAN_TERMS = (
    "plan", "planning", "derive", "contract", "inventory", "manifest",
    "before editing", "before mutation", "before writing", "identify",
)
_VALIDATE_TERMS = (
    "validat", "verif", "reopen", "integrity", "completion", "final scan",
    "acceptance", "well-formed", "parse successfully",
)
_CHECK_TERMS = (
    "check", "confirm", "compare", "ensure", "inspect", "count", "preserve",
    "review", "assert",
)


def _kind(text: str) -> str | None:
    lowered = text.casefold()
    if any(term in lowered for term in _VALIDATE_TERMS):
        return "validation"
    if any(term in lowered for term in _PLAN_TERMS):
        return "planning"
    if any(term in lowered for term in _CHECK_TERMS):
        return "checking"
    return None


def _tokens(text: str) -> set[str]:
    text = re.sub(r"[`*_~]", " ", text.casefold())
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<n>", text)
    return {
        token
        for token in _TOKEN.findall(text)
        if token not in _STOP_WORDS and not token.startswith("http")
    }


def _is_duplicate(left: str, right: str) -> bool:
    left_kind = _kind(left)
    if left_kind is None or left_kind != _kind(right):
        return False
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    shared = left_tokens & right_tokens
    if len(shared) < 3:
        return False
    similarity = len(shared) / max(1, min(len(left_tokens), len(right_tokens)))
    return similarity >= 0.72


def compact_skill_text(skill_text: str) -> tuple[str, int]:
    """Remove redundant planning/checking/validation list items.

    The first occurrence keeps its location.  If a later item is more specific,
    its text replaces the first one; this preserves workflow ordering while
    retaining the stronger contract.  At most one duplicate item is removed for
    a given surviving item, so unrelated detailed checklist entries remain.
    """
    lines = skill_text.splitlines()
    kept: list[str] = []
    kept_bodies: list[tuple[int, str]] = []
    removed = 0
    in_fence = False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            kept.append(line)
            continue
        match = _LIST_ITEM.match(line) if not in_fence and "|" not in line else None
        if match is None or len(match.group(2)) < 24 or _kind(match.group(2)) is None:
            kept.append(line)
            continue
        body = match.group(2)
        duplicate_index = next(
            (index for index, (_, previous) in enumerate(kept_bodies) if _is_duplicate(previous, body)),
            None,
        )
        if duplicate_index is None:
            kept_bodies.append((len(kept), body))
            kept.append(line)
            continue
        previous_line_index, previous_body = kept_bodies[duplicate_index]
        if len(_tokens(body)) > len(_tokens(previous_body)):
            # Keep the original bullet/number marker so removing a later item
            # cannot create a broken sequence such as ``2.`` followed by ``3.``.
            previous_match = _LIST_ITEM.match(kept[previous_line_index])
            prefix = previous_match.group(1) if previous_match else match.group(1)
            kept[previous_line_index] = prefix + body
            kept_bodies[duplicate_index] = (previous_line_index, body)
        removed += 1
    result = "\n".join(kept)
    if skill_text.endswith("\n"):
        result += "\n"
    return result, removed
