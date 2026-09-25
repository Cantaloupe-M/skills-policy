"""Retrieve and apply bounded edits to Markdown skill documents.

Every section of a skill is eligible for revision.  The editor limits a single
evolution step to a section selected from the current document, which keeps a
new bottleneck from rewriting unrelated instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_TOKEN = re.compile(r"[a-z0-9][a-z0-9_-]{2,}", re.I)
_STOP_WORDS = {
    "and",
    "are",
    "artifact",
    "before",
    "check",
    "current",
    "from",
    "into",
    "must",
    "not",
    "or",
    "output",
    "skill",
    "task",
    "that",
    "the",
    "this",
    "when",
    "with",
}


@dataclass(frozen=True)
class SkillSection:
    """One editable heading-delimited Markdown section."""

    section_id: str
    heading: str
    level: int
    start: int
    end: int
    content: str


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value[:64] or "section"


def parse_skill_sections(skill_text: str) -> list[SkillSection]:
    """Split a skill into heading-delimited, independently replaceable sections."""
    headings = list(_HEADING.finditer(skill_text))
    sections: list[SkillSection] = []
    seen: dict[str, int] = {}
    for index, match in enumerate(headings):
        level = len(match.group(1))
        heading = match.group(2).strip()
        end = len(skill_text)
        for following in headings[index + 1 :]:
            if len(following.group(1)) <= level:
                end = following.start()
                break
        base_id = _slug(heading)
        seen[base_id] = seen.get(base_id, 0) + 1
        suffix = "" if seen[base_id] == 1 else f"-{seen[base_id]}"
        sections.append(
            SkillSection(
                section_id=f"{base_id}{suffix}",
                heading=heading,
                level=level,
                start=match.start(),
                end=end,
                content=skill_text[match.start() : end],
            )
        )
    return sections


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in _TOKEN.findall(value) if token.casefold() not in _STOP_WORDS}


def retrieve_skill_sections(skill_text: str, query: str, *, limit: int = 4) -> list[SkillSection]:
    """Return the most relevant current sections using deterministic lexical ranking."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    sections = parse_skill_sections(skill_text)
    child_starts = {
        section.section_id
        for section in sections
        if any(
            section.start < child.start < section.end and child.level > section.level
            for child in sections
        )
    }
    scored: list[tuple[int, int, SkillSection]] = []
    for index, section in enumerate(sections):
        heading_overlap = len(query_tokens & _tokens(section.heading))
        body_overlap = len(query_tokens & _tokens(section.content))
        score = heading_overlap * 4 + body_overlap
        if score:
            scored.append((score, -index, section))
    leaf_scored = [item for item in scored if item[2].section_id not in child_starts]
    selected = sorted(leaf_scored or scored, reverse=True)
    best_score = selected[0][0] if selected else 0
    minimum_score = max(2, (best_score + 1) // 2)
    return [
        section
        for score, _, section in selected
        if score >= minimum_score
    ][:limit]


def replace_skill_section(skill_text: str, section: SkillSection, replacement: str) -> str | None:
    """Replace a retrieved section only when the replacement preserves its heading."""
    replacement = replacement.strip() + "\n"
    first_heading = _HEADING.match(replacement)
    if first_heading is None:
        return None
    if len(first_heading.group(1)) != section.level or first_heading.group(2).strip() != section.heading:
        return None
    if len(replacement) > 8_000 or replacement == section.content:
        return None
    return skill_text[: section.start] + replacement + skill_text[section.end :]
