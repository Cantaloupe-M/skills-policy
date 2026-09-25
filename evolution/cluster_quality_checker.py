"""Assess cluster quality before policy generation.

Filters out low-quality clusters caused by template intent/obstacle or
overly broad groupings that mix unrelated problems.
"""

from __future__ import annotations

import json
import re

from evolution.types import CapabilityCluster
from llm_config import TEMPERATURE_DETERMINISTIC, call_llm

CLUSTER_QUALITY_SYSTEM = """You are a cluster quality assessor for skill evolution systems.

Your job: determine whether a capability cluster is high-quality enough to generate a reusable skill policy.

A **high-quality cluster** has:
1. Specific, semantic intent - describes the actual problem or goal, not a generic template
2. Clear obstacle description - explains the root cause, not just an error type
3. Coherent grouping - all candidates address the same underlying problem pattern
4. Actionable resolution - provides concrete guidance that can be turned into a skill

A **low-quality cluster** shows:
1. Template intent - generic phrases like "resolve processing obstacle with X" or "diagnose artifact"
2. Error-type obstacle - just classifications like "not_found" or "runtime" without context
3. Mixed problems - unrelated failures grouped together because of similar error types
4. Vague resolution - generic advice that doesn't address the specific problem

Examples:

HIGH QUALITY:
{
  "intent": "Materialize Git LFS tracked binary files before processing",
  "obstacle": "Input file is a Git LFS pointer stub instead of actual content",
  "candidate_count": 3,
  "tasks": ["task-a", "task-b", "task-c"]
}
→ PASS: Specific problem (Git LFS), clear cause, candidates likely coherent

LOW QUALITY:
{
  "intent": "resolve processing obstacle with Bash",
  "obstacle": "not_found",
  "candidate_count": 8,
  "tasks": ["task-a", "task-b", "task-c", "task-d", "task-e", "task-f", "task-g", "task-h"]
}
→ REJECT: Template intent, error-type obstacle, suspiciously large group (likely mixing unrelated problems)

LOW QUALITY:
{
  "intent": "diagnose a verifier-rejected artifact against the task contract",
  "obstacle": "unexplained verifier rejection",
  "candidate_count": 9,
  "tasks": ["task-1", "task-2", "task-3", "task-4", "task-5", "task-6", "task-7", "task-8", "task-9"]
}
→ REJECT: Generic "verifier rejection" - too broad, likely a catch-all for unrelated failures

Return JSON only:
{
  "assessments": [
    {
      "cluster_id": "...",
      "quality": "high" | "low",
      "reason": "one-sentence explanation",
      "confidence": 0.0-1.0
    }
  ]
}

Be strict: when in doubt, mark as low quality. It's better to skip a cluster than to generate a bad policy.
"""


def assess_cluster_quality(
    clusters: list[CapabilityCluster],
    *,
    min_confidence: float = 0.7,
) -> tuple[list[CapabilityCluster], list[dict]]:
    """Filter clusters by LLM-assessed quality.

    Args:
        clusters: Capability clusters to assess
        min_confidence: Minimum confidence threshold for high-quality clusters

    Returns:
        (high_quality_clusters, quality_report)
    """
    if not clusters:
        return [], []

    # Build assessment payload
    payload = [
        {
            "cluster_id": cluster.capability_id,
            "intent": cluster.intent,
            "obstacle": cluster.obstacle,
            "candidate_count": len(cluster.candidates),
            "tasks": list({c.task_name for c in cluster.candidates}),
            "evidence_labels": list({c.evidence_label for c in cluster.candidates}),
            "evidence_sources": list({c.evidence_source for c in cluster.candidates}),
        }
        for cluster in clusters
    ]

    try:
        response = call_llm(
            messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            system=CLUSTER_QUALITY_SYSTEM,
            temperature=TEMPERATURE_DETERMINISTIC,
            profile="evolution",
        )
        match = re.search(r"\{.*\}", response, re.S)
        if not match:
            raise ValueError(f"LLM response does not contain valid JSON. Response: {response[:500]}")

        data = json.loads(match.group(0))
        assessments = data.get("assessments", [])

    except Exception as exc:
        # If quality assessment fails, log warning but don't fail the entire pipeline
        print(
            f"[evolution] WARNING: Cluster quality assessment failed: {exc}. "
            f"Proceeding with all {len(clusters)} clusters (unfiltered)."
        )
        return clusters, []

    # Build quality report and filter clusters
    quality_report = []
    high_quality_clusters = []
    cluster_by_id = {cluster.capability_id: cluster for cluster in clusters}

    for assessment in assessments:
        cluster_id = assessment.get("cluster_id")
        quality = assessment.get("quality", "low")
        reason = assessment.get("reason", "")
        confidence = float(assessment.get("confidence", 0.0))

        if cluster_id not in cluster_by_id:
            continue

        quality_report.append({
            "cluster_id": cluster_id,
            "quality": quality,
            "reason": reason,
            "confidence": confidence,
        })

        # Include cluster if high quality with sufficient confidence
        if quality == "high" and confidence >= min_confidence:
            high_quality_clusters.append(cluster_by_id[cluster_id])

    # Stats
    filtered_count = len(clusters) - len(high_quality_clusters)
    print(
        f"[evolution] Cluster quality assessment: {len(high_quality_clusters)}/{len(clusters)} "
        f"clusters passed (filtered {filtered_count} low-quality)"
    )

    if filtered_count > 0:
        print("[evolution] Filtered clusters:")
        for item in quality_report:
            if item["quality"] == "low":
                print(f"  - {item['cluster_id']}: {item['reason']}")

    return high_quality_clusters, quality_report


def _format_quality_report(quality_report: list[dict]) -> str:
    """Format quality report for logging/debugging."""
    if not quality_report:
        return "No quality assessments available."

    lines = ["Cluster Quality Report:"]
    for item in quality_report:
        status = "✅ PASS" if item["quality"] == "high" else "❌ REJECT"
        lines.append(
            f"  {status} {item['cluster_id']} "
            f"(confidence: {item['confidence']:.2f}) - {item['reason']}"
        )
    return "\n".join(lines)
