"""Skill discovery and immutable version-store utilities."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

SKILL_MD_FILENAME = "SKILL.md"
CLAUDE_SKILLS_SUBPATH = Path(".claude") / "skills"
_FRONTMATTER_NAME_RE = re.compile(
    r"(?ms)^---\s*\n.*?^name:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*$.*?^---\s*$"
)


@dataclass(frozen=True)
class SkillVersionInfo:
    version_label: str
    root_dir: Path
    skills_dir: Path
    content_hash: str
    parent_version: str | None = None


@dataclass(frozen=True)
class BatchSnapshotInfo:
    batch_index: int
    version_label: str
    root_dir: Path
    skills_dir: Path
    content_hash: str


def sanitize_name(name: str) -> str:
    return name.replace("/", "-").replace(" ", "_").strip("-_")


def read_skill_name(skill_dir: Path) -> str:
    path = skill_dir / SKILL_MD_FILENAME
    if not path.is_file():
        return skill_dir.name
    match = _FRONTMATTER_NAME_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    return match.group(1).strip() if match else skill_dir.name


def find_skill_package_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if (root / SKILL_MD_FILENAME).is_file():
        return [root]
    return [
        child
        for child in sorted(root.iterdir())
        if child.is_dir() and (child / SKILL_MD_FILENAME).is_file()
    ]


def infer_primary_skill_slug(root: Path) -> str | None:
    packages = find_skill_package_dirs(root)
    return read_skill_name(packages[0]) if len(packages) == 1 else None


def make_skill_invocation_instruction(slug: str) -> str:
    return (
        f"Before starting, invoke the `/{slug}` skill and follow its operational workflow.\n"
    )


def copy_skill_library(source_root: Path, destination_root: Path) -> list[Path]:
    destination_root.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    packages = find_skill_package_dirs(source_root)
    if packages:
        for package in packages:
            destination = destination_root / read_skill_name(package)
            if destination.exists():
                continue
            shutil.copytree(package, destination)
            copied.append(destination)
        return copied

    if not source_root.exists():
        return copied
    for item in source_root.iterdir():
        destination = destination_root / item.name
        if destination.exists():
            continue
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)
        copied.append(destination)
    return copied


def ensure_claude_skills_root(path: Path) -> Path:
    path = Path(path)
    if path.name == "skills" and path.parent.name == ".claude":
        return path
    nested = path / CLAUDE_SKILLS_SUBPATH
    if nested.exists() or path.name.startswith("v") or path.name in {
        "final",
        "candidate",
        "skills_snapshot",
    }:
        return nested
    return path


def evolution_metadata_dir(skills_dir: Path) -> Path:
    """Return private evolution state stored beside, never inside, mounted skills."""
    skills_dir = ensure_claude_skills_root(Path(skills_dir))
    if skills_dir.name == "skills" and skills_dir.parent.name == ".claude":
        return skills_dir.parent.parent / ".evolution"
    return skills_dir / ".evolution"


def _copy_evolution_metadata(source_skills_dir: Path, destination_skills_dir: Path) -> None:
    source = evolution_metadata_dir(source_skills_dir)
    if not source.exists():
        return
    _copy_tree_replace(source, evolution_metadata_dir(destination_skills_dir))


def hash_skill_tree(skills_dir: Path) -> str:
    root = ensure_claude_skills_root(skills_dir)
    hasher = hashlib.sha256()
    if not root.exists():
        hasher.update(b"missing")
        return hasher.hexdigest()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        hasher.update(path.relative_to(root).as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def build_skill_version_info(
    version_label: str,
    root_dir: Path,
    *,
    parent_version: str | None = None,
) -> SkillVersionInfo:
    root_dir = Path(root_dir)
    skills_dir = ensure_claude_skills_root(root_dir)
    return SkillVersionInfo(
        version_label=version_label,
        root_dir=root_dir,
        skills_dir=skills_dir,
        content_hash=hash_skill_tree(skills_dir),
        parent_version=parent_version,
    )


def _copy_tree_replace(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def _write_manifest(info: SkillVersionInfo) -> None:
    (info.root_dir / "manifest.json").write_text(
        json.dumps(
            {
                "version": info.version_label,
                "parent_version": info.parent_version,
                "skills_dir": str(info.skills_dir.relative_to(info.root_dir)),
                "content_hash": info.content_hash,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def list_skill_versions(store_dir: Path) -> list[SkillVersionInfo]:
    versions: list[SkillVersionInfo] = []
    if not store_dir.exists():
        return versions
    for child in sorted(store_dir.iterdir()):
        if not child.is_dir() or not re.fullmatch(r"v\d+", child.name):
            continue
        parent = None
        manifest = child / "manifest.json"
        if manifest.is_file():
            try:
                parent = json.loads(manifest.read_text(encoding="utf-8")).get("parent_version")
            except (OSError, json.JSONDecodeError):
                pass
        versions.append(build_skill_version_info(child.name, child, parent_version=parent))
    return versions


def initialize_skill_version_store(
    store_dir: Path,
    seed_source: Path | None = None,
    *,
    task_family: str | None = None,
) -> SkillVersionInfo:
    store_dir.mkdir(parents=True, exist_ok=True)
    existing = list_skill_versions(store_dir)
    if existing:
        return existing[-1]
    root = store_dir / "v000"
    skills = ensure_claude_skills_root(root)
    skills.mkdir(parents=True, exist_ok=True)
    if task_family:
        family_dir = _initialize_family_skill(skills, task_family)
        _initialize_evolution_metadata(root, task_family, read_skill_name(family_dir))
    elif seed_source is not None and Path(seed_source).exists():
        copy_skill_library(ensure_claude_skills_root(seed_source), skills)
    info = build_skill_version_info("v000", root)
    _write_manifest(info)
    return info


def _family_slug(task_family: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", task_family.casefold()).strip("-")[:60] or "family-skill"


def family_workflow_steps(task_family: str) -> list[str]:
    """Return the generic family-level workflow used by v000 and the compiler.

    Initialization deliberately stays domain-agnostic.  Family-specific details
    belong in the task contract and later evidence-grounded policy cards rather
    than being selected from the family name.
    """
    del task_family  # Kept in the signature for compatibility with callers.
    return [
        "Read the task contract and identify the required inputs and outputs.",
        "Inspect the workspace and choose tools appropriate to the input artifacts.",
        "Validate input structure and constraints before transforming or creating artifacts.",
        "Execute the task incrementally while preserving unrelated user data.",
        "Validate the final artifact deterministically against the contract and verifier.",
        "Report produced artifacts, checks performed, and unresolved risks.",
    ]


def _initialize_family_skill(skills_dir: Path, task_family: str) -> Path:
    """Create the stable, domain-agnostic v000 family skill contract."""
    slug = _family_slug(task_family)
    skill_dir = skills_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "references" / "policies").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts" / "experimental").mkdir(parents=True, exist_ok=True)
    (skill_dir / "scripts" / "capabilities").mkdir(parents=True, exist_ok=True)
    skill = f'''---
name: {slug}
description: >
  Use for tasks in {task_family} that require multi-step execution,
  artifact creation, constraint checking, or recovery from failures.
---

# {task_family}

## Scope

This skill provides reusable procedures for {task_family}.
It does not contain task-specific answers, credentials, absolute paths,
or instance-specific constants.

## When to use

Use this skill when the task involves:

- multi-step execution;
- creating or modifying a requested artifact;
- checking explicit constraints or recovering from a failure.

Do not use it for explanation-only requests or unrelated task families.

## Operating procedure

{chr(10).join(f"{index}. {step}" for index, step in enumerate(family_workflow_steps(task_family), start=1))}

After selecting the smallest matching policy card from `references/policies/`,
apply it within this family workflow.

## Invariants

Always preserve:

- required output format and location;
- user-provided data and unrelated files;
- reproducibility of deterministic steps;
- explicit validation before completion;
- safety and permission boundaries.

## Recovery

When an operation fails, distinguish environment, input, procedure, and
verifier failures. Apply a matching recovery policy when one exists; otherwise
record a diagnostic and continue conservatively.

## Reusable implementations

Use a helper only when its metadata and applicability match the task. Helpers
must accept task-specific values as arguments, expose explicit input and output
behavior, avoid hidden writes, network access, credentials, and destructive
operations, and provide a deterministic validation path.

## Policy cards

Load only the relevant policy card from `references/policies/`. Each card must
specify `When`, `Do`, `Keep`, `Recover`, and `Validation`.
'''
    (skill_dir / "SKILL.md").write_text(skill, encoding="utf-8")
    return skill_dir


def _initialize_evolution_metadata(root: Path, task_family: str, slug: str) -> None:
    metadata = root / ".evolution"
    metadata.mkdir(parents=True, exist_ok=True)
    files = {
        "manifest.json": {"schema_version": 1, "task_family": task_family, "skill_slug": slug, "version": "v000", "parent_version": None},
        "lineage.json": {"schema_version": 1, "task_family": task_family, "policies": {}},
        "metrics.json": {"schema_version": 1, "task_family": task_family, "versions": []},
    }
    for name, payload in files.items():
        path = metadata / name
        if not path.exists():
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    evidence = metadata / "evidence.jsonl"
    evidence.touch(exist_ok=True)


def get_latest_skill_version(store_dir: Path) -> SkillVersionInfo:
    versions = list_skill_versions(store_dir)
    if not versions:
        raise FileNotFoundError(f"No skill versions under {store_dir}")
    return versions[-1]


def create_batch_snapshot(
    version: SkillVersionInfo,
    batch_dir: Path,
    *,
    batch_index: int,
) -> BatchSnapshotInfo:
    root = Path(batch_dir) / "skills_snapshot"
    skills = ensure_claude_skills_root(root)
    _copy_tree_replace(version.skills_dir, skills)
    _copy_evolution_metadata(version.skills_dir, skills)
    content_hash = hash_skill_tree(skills)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "batch_index": batch_index,
                "version_label": version.version_label,
                "content_hash": content_hash,
                "source_version_root": str(version.root_dir),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return BatchSnapshotInfo(batch_index, version.version_label, root, skills, content_hash)


def create_candidate_from_version(
    version: SkillVersionInfo,
    candidate_root: Path,
) -> SkillVersionInfo:
    skills = ensure_claude_skills_root(candidate_root)
    _copy_tree_replace(version.skills_dir, skills)
    _copy_evolution_metadata(version.skills_dir, skills)
    return build_skill_version_info(
        "candidate",
        Path(candidate_root),
        parent_version=version.version_label,
    )


def promote_candidate_version(
    store_dir: Path,
    candidate_skills_dir: Path,
    *,
    parent_version: str | None,
) -> SkillVersionInfo:
    label = f"v{len(list_skill_versions(store_dir)):03d}"
    root = Path(store_dir) / label
    skills = ensure_claude_skills_root(root)
    _copy_tree_replace(ensure_claude_skills_root(candidate_skills_dir), skills)
    _copy_evolution_metadata(candidate_skills_dir, skills)
    info = build_skill_version_info(label, root, parent_version=parent_version)
    _write_manifest(info)
    return info


def freeze_final_version(
    store_dir: Path,
    source_version: SkillVersionInfo,
) -> SkillVersionInfo:
    root = Path(store_dir) / "final"
    skills = ensure_claude_skills_root(root)
    _copy_tree_replace(source_version.skills_dir, skills)
    _copy_evolution_metadata(source_version.skills_dir, skills)
    info = build_skill_version_info(
        "final",
        root,
        parent_version=source_version.version_label,
    )
    _write_manifest(info)
    return info
