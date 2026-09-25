"""Shared task-instruction composition for benchmark runners.

Both benchmark entrypoints must present the same Skill invocation and retry
reflection contract to the agent.  The task runners remain responsible for
copying/writing the benchmark-specific instruction file.
"""

from __future__ import annotations

from collections.abc import Iterable

from evolution.skill_utils import make_skill_invocation_instruction


def prepare_task_instruction(
    original: str | None,
    skill_slugs: Iterable[str] = (),
    reflection: str | None = None,
    memory_available: bool = False,
) -> str | None:
    """Compose the canonical Skill prefix, retry reflection, and task body."""
    slugs = list(dict.fromkeys(str(slug).strip() for slug in skill_slugs if str(slug).strip()))
    body = (original or "").lstrip()
    prefix = "".join(make_skill_invocation_instruction(slug) for slug in slugs)
    if memory_available:
        prefix += (
            "A read-only `experience_memory` MCP server contains instance-specific "
            "lessons from prior tasks. Search it only when the current task or an "
            "obstacle could benefit from analogous experience; treat returned "
            "memories as contextual hypotheses and validate them against this task. "
            "The invoked skill remains authoritative for reusable procedures.\n"
        )

    # Avoid duplicating the canonical prefix when a prepared task is retried.
    for slug in slugs:
        marker = make_skill_invocation_instruction(slug).strip()
        if body.startswith(marker):
            body = body[len(marker):].lstrip("\n")
        shorthand = f"/{slug}"
        if body.startswith(shorthand):
            body = body[len(shorthand):].lstrip("\n")
    instructions = prefix + body if prefix else (body or None)

    if not reflection:
        return instructions
    if instructions is None:
        instructions = "Follow the task instructions provided by the benchmark.\n"
    return (
        "## Previous Attempt Reflection\n\n"
        "The previous attempt at this task failed. Use this analysis "
        "to change your approach and explicitly address its corrective actions.\n\n"
        f"{reflection.strip()}\n\n"
        "## Task Instructions\n\n"
        f"{instructions}"
    )
