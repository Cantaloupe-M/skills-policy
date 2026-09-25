"""Group discoveries by semantic similarity of their problem descriptions."""

from __future__ import annotations

import hashlib
import os
import re

import numpy as np

from evolution.semantic_embeddings import embed_texts
from evolution.types import BottleneckCandidate, CandidateKind, CapabilityCluster

GROUPING_ALGORITHM = "semantic-v2-kind-partitioned"
SIMILARITY_THRESHOLD = 0.75
CANDIDATE_KINDS: tuple[CandidateKind, ...] = ("recovery_candidate", "atomic_substep", "workflow")


def _normalize(value: str) -> str:
    value = (value or "").casefold().strip()
    value = re.sub(r"[/\\][\w./\\-]+", "<path>", value)
    value = re.sub(r"\b[\w.-]+\.(xlsx|xls|csv|json|pdf|png|jpg|xml|ya?ml|py|txt)\b", r"<\1>", value)
    return re.sub(r"\s+", " ", value)[:320]


def _embedding_text(candidate: BottleneckCandidate) -> str:
    return f"intent: {_normalize(candidate.intent)}\nobstacle: {_normalize(candidate.obstacle)}"


def _fingerprint(candidate: BottleneckCandidate) -> str:
    text = "\x1f".join((_normalize(candidate.intent), _normalize(candidate.obstacle)))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _representative(members: list[int], vectors: np.ndarray, candidates: list[BottleneckCandidate]) -> int:
    if len(members) == 1:
        return members[0]
    scores = {
        index: float(np.mean([float(vectors[index] @ vectors[other]) for other in members if other != index]))
        for index in members
    }
    return min(members, key=lambda index: (-scores[index], _fingerprint(candidates[index])))


def _capability_id(candidate: BottleneckCandidate) -> str:
    key = "\x1f".join(
        (candidate.candidate_kind, _normalize(candidate.intent), _normalize(candidate.obstacle), GROUPING_ALGORITHM)
    )
    return f"cap-semantic-v2-{hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]}"


def _group_candidate_pool(candidates: list[BottleneckCandidate], candidate_kind: CandidateKind) -> list[CapabilityCluster]:
    """Cluster one homogeneous candidate kind."""
    model_name = os.environ.get("SKILLFLOW_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    ordered = sorted(candidates, key=_fingerprint)
    vectors = embed_texts([_embedding_text(candidate) for candidate in ordered], model_name=model_name)
    clusters: list[list[int]] = []
    for index, _candidate in enumerate(ordered):
        selected: list[int] = []
        for cluster_index, members in enumerate(clusters):
            if all(
                float(vectors[index] @ vectors[member]) >= SIMILARITY_THRESHOLD
                for member in members
            ):
                selected.append(cluster_index)
        if selected:
            clusters[selected[0]].append(index)
        else:
            clusters.append([index])

    result: list[CapabilityCluster] = []
    for members in clusters:
        representative_index = _representative(members, vectors, ordered)
        representative = ordered[representative_index]
        result.append(
            CapabilityCluster(
                capability_id=_capability_id(representative),
                intent=representative.intent,
                obstacle=representative.obstacle,
                candidates=[ordered[index] for index in members],
                grouping_algorithm=GROUPING_ALGORITHM,
                candidate_kind=candidate_kind,
            )
        )
    return result


def group_candidates(candidates: list[BottleneckCandidate]) -> list[CapabilityCluster]:
    """Cluster candidates by semantic similarity without mixing evidence granularity."""
    if not candidates:
        return []
    invalid = sorted({candidate.candidate_kind for candidate in candidates} - set(CANDIDATE_KINDS))
    if invalid:
        raise ValueError(f"unsupported candidate kind(s): {', '.join(invalid)}")
    result: list[CapabilityCluster] = []
    for candidate_kind in CANDIDATE_KINDS:
        pool = [candidate for candidate in candidates if candidate.candidate_kind == candidate_kind]
        if pool:
            result.extend(_group_candidate_pool(pool, candidate_kind))
    return sorted(result, key=lambda cluster: cluster.capability_id)
