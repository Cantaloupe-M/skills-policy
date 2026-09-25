"""Compile policy records and bottleneck-targeted edits to family skills.

The private registry owns policies and optional implementations. A family skill
is edited in place: each cluster retrieves relevant Markdown sections and may
replace one section without regenerating unrelated instructions.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from evolution.exploration.capability_designer import (
    PolicyProposal,
    design_policy_proposal,
    design_skill_patch,
    design_workflow_update,
    validate_experimental_source,
)
from evolution.exploration.skill_patcher import replace_skill_section, retrieve_skill_sections
from evolution.exploration.trace_parser import is_public_substep_action
from evolution.skill_compaction import compact_skill_text
from evolution.types import (
    CapabilityCluster,
    ExplorationReport,
    ExplorationTrace,
)

REGISTRY_SCHEMA_VERSION = 1
FAMILY_STATE_SCHEMA_VERSION = 1
EVOLUTION_METADATA_DIRNAME = ".evolution"


def _slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:60] or "skill-policy"


def _task_fingerprint(task_name: str) -> str:
    return hashlib.sha256(task_name.encode("utf-8")).hexdigest()[:16]


def _metadata_dir(skills_dir: Path) -> Path:
    skills_dir = Path(skills_dir)
    if skills_dir.name == "skills" and skills_dir.parent.name == ".claude":
        return skills_dir.parent.parent / EVOLUTION_METADATA_DIRNAME
    return skills_dir / EVOLUTION_METADATA_DIRNAME


def _state_path(skills_dir: Path, slug: str) -> Path:
    return _metadata_dir(skills_dir) / "manifest.json"


def _registry_path(skills_dir: Path) -> Path:
    return _metadata_dir(skills_dir) / "lineage.json"


def _read_binding(skills_dir: Path, family: str) -> str | None:
    path = _metadata_dir(skills_dir) / "manifest.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    bound_family = data.get("task_family", data.get("family_name"))
    slug = data.get("skill_slug", data.get("canonical_skill_slug")) if bound_family == family else None
    return str(slug) if slug else _slugify(family)


def resolve_family_skill_slug(skills_dir: Path, family: str) -> str | None:
    """Return the skill-package view associated with a task family."""
    return _read_binding(Path(skills_dir), family)


def _write_binding(skills_dir: Path, family: str, slug: str) -> None:
    directory = _metadata_dir(skills_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "manifest.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    payload.update({"schema_version": 1, "task_family": family, "skill_slug": slug})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_family_state(skills_dir: Path, family: str, slug: str) -> dict[str, Any]:
    path = _state_path(skills_dir, slug)
    try:
        state = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        state = {}
    if state.get("schema_version") == FAMILY_STATE_SCHEMA_VERSION and isinstance(state.get("policy_ids"), list):
        return state
    return {
        "schema_version": FAMILY_STATE_SCHEMA_VERSION,
        "skill_slug": slug,
        "task_family": family,
        "policy_ids": [],
    }


def _write_family_state(skills_dir: Path, slug: str, state: dict[str, Any]) -> None:
    path = _state_path(skills_dir, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        payload = {}
    payload.update({"schema_version": FAMILY_STATE_SCHEMA_VERSION, "policy_ids": state.get("policy_ids", [])})
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_registry(skills_dir: Path) -> dict[str, Any]:
    path = _registry_path(skills_dir)
    try:
        registry = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        registry = {}
    if registry.get("schema_version") == REGISTRY_SCHEMA_VERSION and isinstance(registry.get("policies"), dict):
        return registry
    return {"schema_version": REGISTRY_SCHEMA_VERSION, "policies": {}}


def _write_registry(skills_dir: Path, registry: dict[str, Any]) -> None:
    path = _registry_path(skills_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_id(prefix: str, value: str) -> str:
    return f"{prefix}-{_slugify(value)[:32]}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]}"


def _origin_observations(cluster: CapabilityCluster) -> list[dict[str, str]]:
    observations: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in cluster.candidates:
        item = (_task_fingerprint(candidate.task_name), candidate.evidence_label)
        if item not in seen:
            seen.add(item)
            observations.append({"task_fingerprint": item[0], "label": item[1]})
    return observations


def _resolution_observations(cluster: CapabilityCluster) -> list[dict[str, Any]]:
    """Persist each proposed method with its outcome instead of flattening it."""
    observations: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str, str]] = set()
    for candidate in cluster.candidates:
        if not candidate.resolution:
            continue
        item = (
            _task_fingerprint(candidate.task_name),
            candidate.evidence_source,
            candidate.evidence_label,
            candidate.retry_outcome or "",
            candidate.resolution,
            json.dumps(candidate.retry_transition, ensure_ascii=False, sort_keys=True),
        )
        if item in seen:
            continue
        seen.add(item)
        observations.append(
            {
                "task_fingerprint": item[0],
                "source": item[1],
                "label": item[2],
                "retry_outcome": item[3] or None,
                "resolution": item[4],
                "retry_transition": candidate.retry_transition,
            }
        )
    return observations


def _policy_catalog(registry: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "policy_id": policy_id,
            "purpose": str(policy.get("purpose", "")),
            "trigger": str(policy.get("trigger", "")),
            "invariants": "; ".join(str(value) for value in policy.get("invariants", [])),
        }
        for policy_id, policy in registry["policies"].items()
    ]


def _new_policy(
    proposal: PolicyProposal,
    observations: list[dict[str, str]],
    existing_ids: set[str],
    cluster: CapabilityCluster | None = None,
) -> dict[str, Any]:
    """Create an experimental policy from verified or recurring-failure evidence."""
    signature = "\x1f".join((proposal.name, proposal.purpose, proposal.trigger, *proposal.procedure))
    policy_id = _new_id("policy", signature)
    suffix = 2
    while policy_id in existing_ids:
        policy_id = _new_id("policy", f"{signature}\x1f{suffix}")
        suffix += 1
    base_slug = _slugify(proposal.name)
    policy_slug = base_slug
    return {
        "policy_id": policy_id,
        "status": "experimental",
        "name": proposal.name,
        "slug": policy_slug,
        "purpose": proposal.purpose,
        "trigger": proposal.trigger,
        "invariants": list(proposal.invariants),
        "recovery": list(proposal.recovery),
        "families": [],
        "observations": observations,
        "resolution_evidence": _resolution_observations(cluster) if cluster else [],
        "evidence": [],
        "implementations": {},
        # Public policies are the only records eligible for SKILL rendering.
        # Raw operation observations remain in lineage for audit purposes.
        "visibility": "public",
        "observed_substeps": _observed_substeps(cluster) if cluster else [],
    }


def _observed_substeps(cluster: CapabilityCluster | None) -> list[dict[str, Any]]:
    """Persist normalized trajectory operations alongside the prose policy."""
    if cluster is None:
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in cluster.candidates:
        substep = candidate.substep
        if substep is None or substep.signature in seen:
            continue
        seen.add(substep.signature)
        result.append(
            {
                "kind": substep.kind,
                "action": substep.action,
                "tool": substep.tool_name,
                "signature": substep.signature,
                "command_shape": substep.command_shape,
                "input_formats": list(substep.input_formats),
                "output_formats": list(substep.output_formats),
            }
        )
    return result[:16]


def _implementation_id(policy_id: str, proposal: PolicyProposal) -> str:
    """Use one stable implementation slot per policy.

    Evolution is an update operation.  A revised procedure replaces the previous
    experimental implementation instead of growing an unbounded implementation log.
    """
    del proposal
    return _new_id("implementation", policy_id)


def _add_implementation(policy: dict[str, Any], proposal: PolicyProposal, observations: list[dict[str, str]]) -> bool:
    implementation_id = _implementation_id(str(policy["policy_id"]), proposal)
    existing = policy["implementations"].get(implementation_id)
    if existing and existing.get("trigger") == proposal.trigger and existing.get("procedure") == list(proposal.procedure):
        return False
    script_filename = f"helper_{hashlib.sha256(implementation_id.encode('utf-8')).hexdigest()[:12]}.py" if proposal.script_name else None
    source = proposal.script_source.rstrip() + "\n# EVOLUTION_GENERATED_HELPER\n" if proposal.script_source else None
    # Preserve adoption evidence across wording or implementation revisions.
    policy["implementations"] = {
        implementation_id: {
            "implementation_id": implementation_id,
            # A revised implementation needs its own later reuse evidence.
            "status": "experimental",
            "trigger": proposal.trigger,
            "procedure": list(proposal.procedure),
            "script_name": script_filename,
            "script_source": source,
            "observations": observations,
            "evidence": existing.get("evidence", []) if existing else [],
        }
    }
    return True


def _update_policy_contract(
    policy: dict[str, Any],
    proposal: PolicyProposal,
    observations: list[dict[str, str]],
    resolution_evidence: list[dict[str, Any]],
) -> bool:
    """Replace the reusable contract in place while retaining its identity and evidence."""
    changes = {
        "name": proposal.name,
        "purpose": proposal.purpose,
        "trigger": proposal.trigger,
        "invariants": list(proposal.invariants),
        "recovery": list(proposal.recovery),
    }
    changed = any(policy.get(key) != value for key, value in changes.items())
    policy.update(changes)
    for observation in observations:
        if observation not in policy["observations"]:
            policy["observations"].append(observation)
            changed = True
    stored_resolutions = policy.setdefault("resolution_evidence", [])
    for item in resolution_evidence:
        if item not in stored_resolutions:
            stored_resolutions.append(item)
            changed = True
    return changed


def _promote_from_evidence(
    registry: dict[str, Any],
    traces: list[ExplorationTrace],
    *,
    strict_cross_task: bool = False,
    require_policy_use: bool = True,
) -> tuple[int, int]:
    """Promote only exact, later policy and implementation adoptions."""
    policy_promoted = 0
    implementation_promoted = 0
    for policy in registry["policies"].values():
        origin_tasks = {item.get("task_fingerprint") for item in policy.get("observations", []) if isinstance(item, dict)}
        if not origin_tasks:
            # A template policy has no discovery task to validate against yet.
            continue
        for trace in traces:
            if not trace.verifier_passed:
                continue
            if strict_cross_task and _task_fingerprint(trace.task_name) in origin_tasks:
                continue
            if require_policy_use and policy["policy_id"] not in trace.used_policy_ids and policy.get("slug") not in trace.used_policy_ids:
                continue
            if policy["status"] != "active":
                policy["status"] = "active"
                policy_promoted += 1
            evidence = {
                "task_fingerprint": _task_fingerprint(trace.task_name),
                "attempt_id": trace.attempt_id,
                "label": "verified_policy_reuse",
            }
            if evidence not in policy["evidence"]:
                policy["evidence"].append(evidence)
        for implementation in policy["implementations"].values():
            origins = {item.get("task_fingerprint") for item in implementation.get("observations", []) if isinstance(item, dict)}
            if not origins:
                continue
            for trace in traces:
                if not trace.verifier_passed:
                    continue
                if strict_cross_task and _task_fingerprint(trace.task_name) in origins:
                    continue
                if require_policy_use and policy["policy_id"] not in trace.used_policy_ids and policy.get("slug") not in trace.used_policy_ids:
                    continue
                if implementation["implementation_id"] not in trace.used_implementation_ids:
                    continue
                script_name = implementation.get("script_name")
                if script_name and script_name not in trace.used_script_ids:
                    continue
                if implementation["status"] != "active":
                    implementation["status"] = "active"
                    implementation_promoted += 1
                evidence = {
                    "task_fingerprint": _task_fingerprint(trace.task_name),
                    "attempt_id": trace.attempt_id,
                    "label": "verified_implementation_reuse",
                }
                if evidence not in implementation["evidence"]:
                    implementation["evidence"].append(evidence)
    return policy_promoted, implementation_promoted


def _policy_filename(policy: dict[str, Any] | str) -> str:
    if isinstance(policy, dict):
        slug = str(policy.get("slug", ""))
        if slug:
            return f"{slug}.md"
        policy_id = str(policy.get("policy_id", "policy"))
    else:
        policy_id = policy
    return f"{policy_id}.md"


def _policy_card(policy: dict[str, Any]) -> str:
    implementation = next(iter(policy["implementations"].values()), None)
    lines = [
        f"# {policy['name']}",
        "",
        f"Purpose: {policy['purpose']}",
        "",
        f"Use this procedure when: {_clean_trigger(policy['trigger'])}",
        "",
        "## Steps",
        "",
        "Follow these steps in order:",
        "",
        *(
            [f"{index}. {step}" for index, step in enumerate(implementation["procedure"], start=1)]
            if implementation
            else ["1. Apply the task-specific procedure while preserving the constraints below."]
        ),
        "",
        "## Constraints",
        "",
        *[f"- {item}" for item in policy["invariants"]],
        "",
        "## Recovery",
        "",
        *[f"- {item}" for item in policy["recovery"]],
        "",
        "## Validation",
        "",
        "- Validate the produced artifact against the task contract and the supplied verifier before completion.",
        "",
    ]
    # Observed action names are internal evidence, not runtime instructions.
    # Keep them in lineage.json but never copy them into the mounted skill.
    if implementation and implementation.get("script_name"):
        directory = "capabilities" if implementation["status"] == "active" else "experimental"
        lines.extend([f"For the deterministic portion, run: `python scripts/{directory}/{implementation['script_name']} --help`", ""])
    return "\n".join(lines).strip() + "\n"


def _policy_files(policies: list[dict[str, Any]]) -> dict[str, str]:
    return {_policy_filename(policy): _policy_card(policy) for policy in policies}


def _policy_tokens(policy: dict[str, Any]) -> set[str]:
    text = " ".join(
        [
            str(policy.get("name", "")),
            str(policy.get("purpose", "")),
            str(policy.get("trigger", "")),
            *[str(item) for item in policy.get("invariants", [])],
            *[str(item) for item in policy.get("recovery", [])],
        ]
    ).casefold()
    return set(re.findall(r"[a-z][a-z0-9_-]{2,}", text))


def _compact_policies(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop near-duplicate policy cards before exposing them to the runtime.

    The lineage registry keeps all evidence, but the mounted skill should only
    expose one card for one reusable contract.  This prevents small wording
    changes across batches from becoming several copies of the same operation.
    """
    selected: list[dict[str, Any]] = []
    for policy in policies:
        if not _policy_is_public(policy):
            continue
        tokens = _policy_tokens(policy)
        if not tokens:
            continue
        duplicate = False
        for existing in selected:
            other = _policy_tokens(existing)
            overlap = len(tokens & other) / max(1, min(len(tokens), len(other)))
            same_trigger = str(policy.get("trigger", "")).casefold() == str(existing.get("trigger", "")).casefold()
            if same_trigger or overlap >= 0.72:
                # Prefer verified/active and better-supported cards.
                score = (policy.get("status") == "active", len(policy.get("observations", [])))
                old_score = (existing.get("status") == "active", len(existing.get("observations", [])))
                if score > old_score:
                    selected[selected.index(existing)] = policy
                duplicate = True
                break
        if not duplicate:
            selected.append(policy)
    return selected


def _policy_is_public(policy: dict[str, Any]) -> bool:
    """Filter internal observations before rendering a runtime skill.

    The lineage registry intentionally keeps historical observations, including
    old versions that predate the visibility field.  This compatibility check
    prevents those records from reintroducing ``write_json``-style instructions.
    """
    if str(policy.get("visibility", "public")) != "public":
        return False
    observations = policy.get("observed_substeps", [])
    if not isinstance(observations, list):
        return True
    actions = [
        str(item.get("action", ""))
        for item in observations
        if isinstance(item, dict) and item.get("action")
    ]
    return all(is_public_substep_action(action) for action in actions)


def _clean_trigger(value: object) -> str:
    text = " ".join(str(value or "").split())
    text = re.sub(r"^(?:use when|when)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"^(?:use when|when)\s+", "", text, flags=re.I)
    return text[:400] or "the task's inputs and output contract require this procedure"


def _remove_central_policy_links(skill_text: str) -> str:
    """Remove the legacy catch-all policy index from model-authored Markdown."""
    match = re.search(r"(?ms)^#\s+Policy links\s*$.*?(?=^#{1,6}\s+|\Z)", skill_text, re.I)
    if match:
        skill_text = skill_text[: match.start()] + skill_text[match.end() :]
    # Rebuild compiler-owned link groups on every batch so stale links cannot
    # accumulate after policy deduplication.
    skill_text = re.sub(
        r"(?ms)^###\s+Related policies\s*$.*?(?=^#{1,3}\s+|\Z)",
        "",
        skill_text,
        flags=re.I,
    )
    return skill_text.strip() + "\n"


def _distributed_policy_links(
    skill_text: str,
    policies: list[dict[str, Any]],
    section_bindings: dict[str, str] | None = None,
) -> str:
    """Place real policy-file links beside the sections they support.

    Links are intentionally attached to relevant leaf sections instead of a
    single generated index.  The target files are written by ``_write_package``
    in the same package, so every emitted link is resolvable at runtime.
    """
    from evolution.exploration.skill_patcher import parse_skill_sections

    skill_text = _remove_central_policy_links(skill_text)
    sections = parse_skill_sections(skill_text)
    candidates = [section for section in sections if section.level >= 2]
    if not candidates:
        candidates = sections
    if not candidates:
        return skill_text
    used: set[str] = set()
    additions: dict[str, list[str]] = {}
    section_bindings = section_bindings or {}
    section_by_id = {section.section_id: section for section in candidates}
    for policy in policies:
        tokens = _policy_tokens(policy)
        bound_section = section_by_id.get(str(section_bindings.get(str(policy.get("policy_id", "")), "")))
        if bound_section is not None:
            section = bound_section
        else:
            scored = []
            for index, candidate in enumerate(candidates):
                section_tokens = set(re.findall(r"[a-z][a-z0-9_-]{2,}", candidate.content.casefold()))
                score = len(tokens & section_tokens)
                scored.append((score, -len(additions.get(candidate.section_id, [])), -index, candidate))
            _, _, _, section = max(scored, key=lambda item: (item[0], item[1], item[2]))
        filename = _policy_filename(policy)
        if filename in used:
            continue
        used.add(filename)
        additions.setdefault(section.section_id, []).append(
            f"- Policy: [{policy.get('name', filename)}](references/policies/{filename})"
        )
    for section in sorted(candidates, key=lambda item: item.start, reverse=True):
        links = additions.get(section.section_id)
        if not links:
            continue
        marker = "\n\n### Related policies\n\n" + "\n".join(links) + "\n"
        body = skill_text[section.start : section.end].rstrip() + marker
        skill_text = skill_text[: section.start] + body + skill_text[section.end :]
    return skill_text.strip() + "\n"


def _skill_quality_metrics(skill_text: str) -> dict[str, int]:
    """Return cheap guardrail metrics for redundancy and link integrity."""
    lines = [line.strip() for line in skill_text.splitlines() if line.strip()]
    duplicate_lines = len(lines) - len(set(lines))
    policy_links = re.findall(r"\]\((references/policies/[^)#]+\.md)\)", skill_text)
    return {
        "word_count": len(skill_text.split()),
        "nonempty_lines": len(lines),
        "duplicate_nonempty_lines": duplicate_lines,
        "policy_links": len(policy_links),
    }


def _skill_patch_query(cluster: CapabilityCluster, proposal: PolicyProposal) -> str:
    """Use only reusable bottleneck facts when retrieving editable sections."""
    return " ".join(
        (
            cluster.intent,
            cluster.obstacle,
            proposal.purpose,
            proposal.trigger,
            *proposal.procedure,
            *proposal.invariants,
        )
    )


def _script_files(policies: list[dict[str, Any]], status: str) -> dict[str, str]:
    files: dict[str, str] = {}
    for policy in policies:
        for implementation in policy["implementations"].values():
            if implementation["status"] == status and implementation.get("script_name") and implementation.get("script_source"):
                files[str(implementation["script_name"])] = str(implementation["script_source"])
    return files


def _write_package(
    skill_dir: Path,
    *,
    skill_md: str,
    policy_files: dict[str, str],
    script_files: dict[str, str],
    experimental_script_files: dict[str, str],
) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    references_dir = skill_dir / "references" / "policies"
    references_dir.mkdir(parents=True, exist_ok=True)
    expected = set(policy_files)
    if references_dir.is_dir():
        for path in references_dir.glob("*.md"):
            if path.name not in expected:
                path.unlink()
    if policy_files:
        references_dir.mkdir(parents=True, exist_ok=True)
        for name, content in policy_files.items():
            (references_dir / name).write_text(content, encoding="utf-8")
    for directory, files in (("capabilities", script_files), ("experimental", experimental_script_files)):
        target = skill_dir / "scripts" / directory
        target.mkdir(parents=True, exist_ok=True)
        if target.is_dir():
            for path in target.glob("*.py"):
                if path.name not in files:
                    path.unlink()
        if files:
            target.mkdir(parents=True, exist_ok=True)
            for name, source in files.items():
                validate_experimental_source(name, source)
                path = target / name
                path.write_text(source, encoding="utf-8")
                path.chmod(0o755)
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    cache = scripts_dir / "__pycache__"
    if cache.is_dir():
        shutil.rmtree(cache)
    _validate_policy_links(skill_dir)


def _validate_policy_links(skill_dir: Path) -> None:
    """Reject mounted skills containing a reference to a missing policy card."""
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.is_file():
        return
    text = skill_path.read_text(encoding="utf-8", errors="replace")
    for target in re.findall(r"\]\((references/policies/[^)#]+\.md)\)", text):
        if not (skill_dir / target).is_file():
            raise ValueError(f"Skill contains an unresolved policy link: {target}")


def compile_family_skill(
    update_clusters: list[CapabilityCluster],
    traces: list[ExplorationTrace],
    task_family: str,
    skills_dir: Path,
    *,
    workflow_traces: list[ExplorationTrace] | None = None,
    strict_cross_task: bool = True,
    require_policy_use: bool = True,
    immediate_promotion: bool = False,
) -> ExplorationReport:
    """Record discoveries and apply bounded edits to matching skill sections."""
    skills_dir = Path(skills_dir)
    slug = _read_binding(skills_dir, task_family) or _slugify(task_family)
    skill_dir = skills_dir / slug
    skill_path = skill_dir / "SKILL.md"
    if not skill_path.is_file():
        raise FileNotFoundError(f"Family skill is missing; initialize it before evolution: {skill_path}")
    skill_text = skill_path.read_text(encoding="utf-8")
    family_state = _load_family_state(skills_dir, task_family, slug)
    registry = _load_registry(skills_dir)
    policy_promoted, implementation_promoted = _promote_from_evidence(
        registry,
        traces,
        strict_cross_task=strict_cross_task,
        require_policy_use=require_policy_use,
    )
    catalog = _policy_catalog(registry)

    # Direct callers can still request batch-level workflow synthesis. The
    # paper-aligned memory-to-skill pipeline passes an empty list so instance
    # traces cannot bypass recurrence-gated policy compilation.
    workflow_updated = False
    workflow_update_reason = ""
    workflow_evidence = traces if workflow_traces is None else workflow_traces
    workflow_update = (
        design_workflow_update(skill_text, workflow_evidence, task_family)
        if workflow_evidence
        else None
    )
    if workflow_update is not None:
        candidate_text, workflow_update_reason = workflow_update
        if candidate_text != skill_text:
            skill_text = candidate_text
            workflow_updated = True

    updated = 0
    created = 0
    compiled_memory_ids: list[str] = []
    patch_inputs: list[tuple[CapabilityCluster, PolicyProposal, str]] = []
    for cluster in update_clusters:
        observed_actions = [
            candidate.substep.action
            for candidate in cluster.candidates
            if candidate.substep is not None and candidate.substep.action
        ]
        if observed_actions and not all(is_public_substep_action(action) for action in observed_actions):
            # A manually supplied or legacy cluster may bypass the pipeline's
            # candidate filter.  Keep its evidence in the registry only when it
            # is already represented there; never synthesize a public policy
            # from an internal primitive at compile time.
            continue
        proposal = design_policy_proposal(
            cluster,
            traces,
            catalog,
        )
        if proposal is None:
            continue
        compiled_memory_ids.extend(
            candidate.candidate_id
            for candidate in cluster.candidates
        )
        observations = _origin_observations(cluster)
        resolution_evidence = _resolution_observations(cluster)
        policy = registry["policies"].get(proposal.existing_policy_id or "")
        if policy is None:
            policy = _new_policy(proposal, observations, set(registry["policies"]), cluster)
            if immediate_promotion:
                policy["status"] = "active"
            registry["policies"][policy["policy_id"]] = policy
            created += 1
        observed = _observed_substeps(cluster)
        existing_observed = policy.setdefault("observed_substeps", [])
        known_signatures = {item.get("signature") for item in existing_observed if isinstance(item, dict)}
        for item in observed:
            if item.get("signature") not in known_signatures:
                existing_observed.append(item)
                known_signatures.add(item.get("signature"))
        if task_family not in policy["families"]:
            policy["families"].append(task_family)
        contract_updated = (
            _update_policy_contract(policy, proposal, observations, resolution_evidence)
            if proposal.existing_policy_id
            else False
        )
        implementation_updated = _add_implementation(policy, proposal, observations)
        if immediate_promotion:
            for implementation in policy.get("implementations", {}).values():
                implementation["status"] = "active"
        if proposal.existing_policy_id:
            updated += int(contract_updated or implementation_updated)
        policy_id = str(policy["policy_id"])
        if policy_id not in family_state["policy_ids"]:
            family_state["policy_ids"].append(policy_id)

        patch_inputs.append((cluster, proposal, policy_id))
        # Later clusters in the same batch must be able to reuse or update a
        # policy created by an earlier cluster, not only policies from the
        # previous published version.
        catalog = _policy_catalog(registry)

    applied_patches: list[dict[str, str]] = []
    section_bindings: dict[str, str] = {}
    for cluster, proposal, policy_id in patch_inputs:
        sections = retrieve_skill_sections(skill_text, _skill_patch_query(cluster, proposal))
        patch = design_skill_patch(cluster, sections, proposal)
        if patch is None:
            continue
        section = next(
            (item for item in sections if item.section_id == patch.target_section_id),
            None,
        )
        if section is None:
            continue
        patched_text = replace_skill_section(skill_text, section, patch.replacement)
        if patched_text is None:
            continue
        # A patch is allowed to improve coverage, but never to grow the skill
        # into an unbounded transcript of observed commands.
        if len(patched_text.split()) > 1_800:
            continue
        skill_text = patched_text
        applied_patches.append(
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "reason": patch.reason,
                "cluster_id": cluster.capability_id,
            }
        )
        # Preserve the cluster -> retrieved section relationship.  The policy
        # link is rendered beside this exact section after all patches finish.
        section_bindings[policy_id] = section.section_id

    # Apply the same deterministic pass after model workflow synthesis and local
    # section patches.  This is where duplicate planning/checking/validation
    # bullets from different sections are collapsed before runtime exposure.
    skill_text, compacted_items = compact_skill_text(skill_text)

    visible_ids = set(family_state["policy_ids"])
    policies = _compact_policies(
        [policy for policy_id, policy in registry["policies"].items() if policy_id in visible_ids]
    )
    # Policy cards remain separately inspectable, while their links are placed
    # next to the workflow/validation/recovery section they support.
    skill_text = _distributed_policy_links(skill_text, policies, section_bindings)
    _write_package(
        skill_dir,
        skill_md=skill_text,
        policy_files=_policy_files(policies),
        script_files=_script_files(policies, "active"),
        experimental_script_files=_script_files(policies, "experimental"),
    )
    _write_family_state(skills_dir, slug, family_state)
    _write_registry(skills_dir, registry)
    _write_binding(skills_dir, task_family, slug)

    metadata = _metadata_dir(skills_dir)
    metadata.mkdir(parents=True, exist_ok=True)
    if applied_patches:
        patch_log = metadata / "skill_patches.jsonl"
        with patch_log.open("a", encoding="utf-8") as handle:
            for item in applied_patches:
                handle.write(json.dumps({"task_family": task_family, **item}, ensure_ascii=False) + "\n")
    if workflow_updated:
        workflow_log = metadata / "workflow_updates.jsonl"
        with workflow_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "task_family": task_family,
                        "trials": len(traces),
                        "verifier_passed": sum(trace.verifier_passed for trace in traces),
                        "reason": workflow_update_reason,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    evidence_path = metadata / "evidence.jsonl"
    with evidence_path.open("a", encoding="utf-8") as handle:
        for trace in traces:
            if trace.verifier_passed:
                handle.write(
                    json.dumps(
                        {
                            "task_family": task_family,
                            "task_fingerprint": _task_fingerprint(trace.task_name),
                            "attempt_id": trace.attempt_id,
                            "reward": trace.reward,
                            "used_policies": trace.used_policy_ids,
                            "used_memories": trace.used_memory_ids,
                            "memory_query_count": trace.memory_query_count,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    metrics_path = metadata / "metrics.json"
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        metrics = {}
    metrics.setdefault("schema_version", 1)
    metrics.setdefault("task_family", task_family)
    metrics.setdefault("batches", [])
    metrics["batches"].append(
        {
            "trials": len(traces),
            "verifier_passed": sum(trace.verifier_passed for trace in traces),
            "verifier_failed": sum(not trace.verifier_passed for trace in traces),
            "policies": len(registry["policies"]),
            "experimental_policies": sum(policy["status"] == "experimental" for policy in registry["policies"].values()),
            "active_policies": sum(policy["status"] == "active" for policy in registry["policies"].values()),
            "skill_patches_applied": len(applied_patches),
            "workflow_updated": workflow_updated,
            "workflow_update_reason": workflow_update_reason,
            "redundant_items_removed": compacted_items,
            "skill_quality": _skill_quality_metrics(skill_text),
        }
    )
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    active = sum(policy["status"] == "active" for policy in registry["policies"].values())
    return ExplorationReport(
        task_family=task_family,
        num_trials=len(traces),
        num_bottlenecks_detected=sum(len(cluster.candidates) for cluster in update_clusters),
        num_capabilities=len(registry["policies"]),
        num_active_capabilities=active,
        num_skills_updated=len(applied_patches) + int(workflow_updated),
        skill_dir=str(skill_dir),
        skill_md_path=str(skill_dir / "SKILL.md"),
        summary=(
            f"{created} experimental SkillPolicy(s) created; {updated} existing SkillPolicy update(s); "
            f"{policy_promoted} policy and {implementation_promoted} implementation promotion(s); "
            f"{int(workflow_updated)} batch workflow update(s) and "
            f"{len(applied_patches)} bottleneck-targeted skill patch(es) applied; "
            "active status requires later verified explicit adoption."
        ),
        compiled_memory_ids=list(dict.fromkeys(compiled_memory_ids)),
    )
