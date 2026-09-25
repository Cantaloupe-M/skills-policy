"""Create an editable v000 family skill before task execution."""

from __future__ import annotations

from pathlib import Path

from evolution.skill_utils import (
    SkillVersionInfo,
    get_latest_skill_version,
    hash_skill_tree,
    initialize_skill_version_store,
    list_skill_versions,
)
from llm_config import call_llm

_SYSTEM = """You write a compact initial reusable family skill for an execution
agent. This is an initial skill for a task family, not a solution for any one task
and not a generic textbook chapter.

First compare the supplied training tasks. Separate stable family patterns
(present in multiple tasks or inherent to the family) from task-specific
variables (paths, filenames, values, exact coordinates, schemas, row counts,
and one-off acceptance criteria). Include only stable patterns in the skill.
The skill must tell an agent how to derive the variables from each future task
at runtime; it must never invent them or bake them in.

Return Markdown only, beginning with YAML frontmatter containing exactly a
lowercase name and a concise description. Use clear Markdown headings. Every
section may later be revised by a bounded, evidence-grounded local edit; do not
introduce immutable zones or compiler-managed placeholders.

The skill must contain these sections:

- Trigger and boundaries: what belongs to this family and what does not.
- Family patterns: stable inputs, outputs, transformations, and invariants.
- Stable decision rules: reusable criteria for inspecting the current task and
  deriving its task contract before implementation.
- Tool compatibility and reliability constraints that remain valid across tasks.
- Family-specific validation and recovery: checks that generalize across this
  family, plus diagnosis paths for common failure modes.

Include an executable runtime workflow, tool choices, policy links, and a
recovery checklist. Keep each concern in a focused heading-delimited section so
later evolution can retrieve and revise only the relevant content.

Do not repeat universal agent advice, generic project-management prose, or
background explanations. Do not assume a file format, library, command,
schema, path, or verifier unless it is a stable family pattern supported by
multiple supplied tasks. Do not include task-specific answers, secrets,
absolute paths, fabricated facts, or instructions to bypass verification.

Use only the supplied task evidence. Do not browse, cite external sources, or
infer industry background. Express compatibility and reliability caveats only
when they are supported by the supplied tasks.

Prefer checklists, small schemas, decision tables, and pseudocode over prose.
Keep the skill under 1,500 words."""

INITIALIZATION_TASK_DERIVED = "task-derived"
INITIALIZATION_SCAFFOLD = "scaffold"
INITIALIZATION_MODES = (INITIALIZATION_TASK_DERIVED, INITIALIZATION_SCAFFOLD)


def generate_initial_family_skill(
    task_family: str,
    train_tasks: list[Path],
    skill_dir: Path,
) -> bool:
    """Generate and write the family skill from the supplied task definitions."""
    prompts: list[str] = []
    for task in train_tasks:
        for filename in ("instruction.md", "task.toml"):
            path = task / filename
            if path.is_file():
                content = path.read_text(encoding="utf-8", errors="replace")
                prompts.append(f"### {task.name}/{filename}\n{content[:12000]}")
                break
    if not prompts:
        return False

    joined = "\n\n".join(prompts)
    user_prompt = (
        f"Family: {task_family}\n\nTRAIN TASK PROMPTS:\n{joined}\n\n"
        "Generate the initial family skill described in the system prompt. Treat the "
        "prompts as evidence, not as templates to copy. First infer the shared "
        "family capability and explicitly keep per-task details as runtime "
        "variables. The resulting skill must help a future agent adapt to an "
        "unseen task in this family, even when its artifact type, inputs, and "
        "acceptance criteria differ from these training tasks."
    )
    try:
        generated = call_llm(
            [{"role": "user", "content": user_prompt}],
            profile="evolution",
            temperature=0.2,
            max_tokens=12000,
            system=_SYSTEM,
        )
        # Keep the model's content as an ordinary, fully editable Markdown skill.
        skill = str(generated) if generated is not None else ""
        if not skill.strip():
            raise ValueError("model returned no usable Markdown")
        skill = _normalize_skill(skill)
    except Exception as exc:
        # Do not silently replace model synthesis with a low-quality template.
        raise RuntimeError(f"Initial skill generation failed for family '{task_family}'; the evolution model is unavailable") from exc

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(skill, encoding="utf-8")
        return True
    except Exception as exc:
        print(f"[SkillFlow] Initial skill write unavailable: {exc}")
        return False


def _normalize_skill(skill: str) -> str:
    """Normalize whitespace without imposing an evolution-specific document shape."""
    return skill.strip() + "\n"


def prepare_initial_family_skill_store(
    store_dir: Path,
    task_family: str,
    train_tasks: list[Path],
    *,
    initialization: str = INITIALIZATION_TASK_DERIVED,
) -> SkillVersionInfo:
    """Create v000 using either task-derived initialization or a fixed scaffold.

    ``scaffold`` never reads training task files and never calls the evolution
    model during initialization.  Training tasks are used only after v000 is
    frozen, by the ordinary batch evolution loop.
    """
    if initialization not in INITIALIZATION_MODES:
        raise ValueError(
            f"Unsupported initialization mode {initialization!r}; "
            f"expected one of {INITIALIZATION_MODES}"
        )

    existing = list_skill_versions(store_dir)
    initial = initialize_skill_version_store(store_dir, task_family=task_family)
    manifest_path = initial.root_dir / "manifest.json"
    try:
        import json

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}

    recorded_mode = manifest.get("initialization_mode")
    if existing and recorded_mode is not None and recorded_mode != initialization:
        raise RuntimeError(
            f"Skill store {store_dir} was initialized as {recorded_mode!r}, "
            f"not {initialization!r}; use a fresh run directory"
        )
    if existing and recorded_mode is None and initialization == INITIALIZATION_SCAFFOLD:
        raise RuntimeError(
            f"Existing skill store {store_dir} has no initialization provenance; "
            "use a fresh run directory for the scaffold experiment"
        )

    if (
        initialization == INITIALIZATION_TASK_DERIVED
        and train_tasks
        and not existing
        and initial.version_label == "v000"
    ):
        from evolution.exploration.skill_compiler import resolve_family_skill_slug

        slug = resolve_family_skill_slug(initial.skills_dir, task_family) or ""
        skill_dir = initial.skills_dir / slug
        if not generate_initial_family_skill(task_family, train_tasks, skill_dir):
            raise RuntimeError(
                f"Initial skill generation produced no skill for family '{task_family}'"
            )
    manifest["initialization_mode"] = initialization
    manifest["initialization_uses_train_task_content"] = (
        initialization == INITIALIZATION_TASK_DERIVED
    )
    manifest["initialization_source"] = (
        "fixed_generic_scaffold_v1"
        if initialization == INITIALIZATION_SCAFFOLD
        else "train_task_contract_synthesis"
    )
    manifest["content_hash"] = hash_skill_tree(initial.skills_dir)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return get_latest_skill_version(store_dir)
