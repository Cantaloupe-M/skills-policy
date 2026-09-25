"""Dependency-free, read-only MCP server for reflective experience memory."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

SERVER_NAME = "experience-memory"
EMBEDDING_ENDPOINT_ENV = "SKILLFLOW_MEMORY_EMBEDDING_ENDPOINT"
EMBEDDING_TOKEN_ENV = "SKILLFLOW_MEMORY_EMBEDDING_TOKEN"

DEFAULT_RETRIEVAL_CONFIG: dict[str, float] = {
    "semantic_weight": 0.75,
    "lexical_weight": 0.25,
    "min_semantic_similarity": 0.38,
    "min_hybrid_score": 0.34,
    "min_lexical_coverage": 0.5,
    "min_lexical_score": 0.2,
}

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def _tokens(text: str) -> list[str]:
    normalized = str(text or "").casefold()
    words = re.findall(r"[a-z0-9_]+|[\u3400-\u9fff]", normalized)
    chinese = [item for item in words if len(item) == 1 and "\u3400" <= item <= "\u9fff"]
    return words + ["".join(chinese[index : index + 2]) for index in range(len(chinese) - 1)]


def _content_tokens(text: str) -> list[str]:
    return [token for token in _tokens(text) if token not in _STOPWORDS]


def _document_text(item: dict[str, Any]) -> str:
    context = item.get("context") if isinstance(item.get("context"), dict) else {}
    cluster_input = item.get("cluster_input") if isinstance(item.get("cluster_input"), dict) else {}
    return " ".join(
        str(value or "")
        for value in (
            item.get("observation"),
            item.get("lesson"),
            item.get("rationale"),
            item.get("causal_evidence"),
            item.get("missing"),
            cluster_input.get("intent"),
            cluster_input.get("obstacle"),
            context.get("task_family"),
            context.get("task_name"),
        )
    )


def _float_setting(config: dict[str, Any], name: str) -> float:
    try:
        return float(config.get(name, DEFAULT_RETRIEVAL_CONFIG[name]))
    except (TypeError, ValueError):
        return DEFAULT_RETRIEVAL_CONFIG[name]


def _normalize(vector: Any) -> list[float] | None:
    if not isinstance(vector, list) or not vector:
        return None
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError):
        return None
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude <= 0 or not math.isfinite(magnitude):
        return None
    return [value / magnitude for value in values]


def _semantic_similarity(query_embedding: list[float] | None, item: dict[str, Any]) -> float | None:
    query_vector = _normalize(query_embedding)
    document_vector = _normalize(item.get("retrieval_embedding"))
    if query_vector is None or document_vector is None or len(query_vector) != len(document_vector):
        return None
    score = sum(left * right for left, right in zip(query_vector, document_vector))
    return max(-1.0, min(1.0, score))


def _query_embedding(query: str, retrieval: dict[str, Any]) -> list[float] | None:
    if not retrieval.get("semantic_available"):
        return None
    endpoint = os.environ.get(EMBEDDING_ENDPOINT_ENV, "").strip()
    token = os.environ.get(EMBEDDING_TOKEN_ENV, "").strip()
    if not endpoint or not token:
        return None
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"text": query}, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read())
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("model") != retrieval.get("embedding_model"):
        return None
    return _normalize(payload.get("embedding"))


def _search(
    records: list[dict[str, Any]],
    query: str,
    limit: int,
    outcome: str | None,
    *,
    retrieval: dict[str, Any] | None = None,
    query_embedding: list[float] | None = None,
) -> list[dict[str, Any]]:
    retrieval = retrieval if isinstance(retrieval, dict) else {}
    eligible = [item for item in records if not outcome or item.get("outcome") == outcome]
    if not eligible:
        return []
    documents = [_content_tokens(_document_text(item)) for item in eligible]
    query_tokens = _content_tokens(query)
    if not query_tokens:
        return []
    unique_query_tokens = set(query_tokens)
    document_frequency = Counter(token for tokens in documents for token in set(tokens))
    average_length = sum(map(len, documents)) / max(1, len(documents))
    semantic_weight = _float_setting(retrieval, "semantic_weight")
    lexical_weight = _float_setting(retrieval, "lexical_weight")
    min_semantic = _float_setting(retrieval, "min_semantic_similarity")
    min_hybrid = _float_setting(retrieval, "min_hybrid_score")
    min_lexical_coverage = _float_setting(retrieval, "min_lexical_coverage")
    min_lexical_score = _float_setting(retrieval, "min_lexical_score")
    scored: list[tuple[float, str, dict[str, Any], float | None, float, float, str]] = []
    for item, tokens in zip(eligible, documents):
        frequency = Counter(tokens)
        raw_lexical_score = 0.0
        for token in query_tokens:
            if not frequency[token]:
                continue
            inverse = math.log(1 + (len(documents) - document_frequency[token] + 0.5) / (document_frequency[token] + 0.5))
            denominator = frequency[token] + 1.2 * (0.25 + 0.75 * len(tokens) / max(1.0, average_length))
            raw_lexical_score += inverse * frequency[token] * 2.2 / denominator
        lexical_score = raw_lexical_score / (raw_lexical_score + 2.0) if raw_lexical_score > 0 else 0.0
        matched_tokens = unique_query_tokens.intersection(frequency)
        lexical_coverage = len(matched_tokens) / max(1, len(unique_query_tokens))
        required_terms = 1 if len(unique_query_tokens) <= 2 else 2
        lexical_pass = (
            lexical_score >= min_lexical_score
            and lexical_coverage >= min_lexical_coverage
            and len(matched_tokens) >= required_terms
        )
        semantic_score = _semantic_similarity(query_embedding, item)
        hybrid_score = lexical_weight * lexical_score
        if semantic_score is not None:
            hybrid_score += semantic_weight * max(0.0, semantic_score)
        semantic_pass = (
            semantic_score is not None
            and semantic_score >= min_semantic
            and hybrid_score >= min_hybrid
        )
        if not semantic_pass and not lexical_pass:
            continue
        match_mode = "hybrid" if semantic_pass else "lexical_exact"
        scored.append(
            (
                hybrid_score,
                str(item.get("memory_id") or ""),
                item,
                semantic_score,
                lexical_score,
                lexical_coverage,
                match_mode,
            )
        )
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [
        {
            "memory_id": item.get("memory_id"),
            "score": round(score, 6),
            "semantic_score": round(semantic_score, 6) if semantic_score is not None else None,
            "lexical_score": round(lexical_score, 6),
            "lexical_coverage": round(lexical_coverage, 6),
            "match_mode": match_mode,
            "outcome": item.get("outcome"),
            "verified_by_retry": item.get("verified_by_retry"),
            "context": item.get("context"),
            "observation": item.get("observation"),
            "lesson": item.get("lesson"),
            "rationale": item.get("rationale"),
            "causal_evidence": item.get("causal_evidence"),
            "missing": item.get("missing"),
            "diagnosis_confidence": item.get("diagnosis_confidence"),
        }
        for score, _memory_id, item, semantic_score, lexical_score, lexical_coverage, match_mode in scored[:limit]
    ]


class MemoryServer:
    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path

    def _store(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"memories": [], "retrieval": {}}
        if not isinstance(payload, dict):
            return {"memories": [], "retrieval": {}}
        return {
            "memories": [item for item in payload.get("memories", []) if isinstance(item, dict)],
            "retrieval": payload.get("retrieval") if isinstance(payload.get("retrieval"), dict) else {},
        }

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        return [
            {
                "name": "search_memories",
                "description": (
                    "Search instance-specific experience memories from prior tasks. "
                    "Use these records as contextual hypotheses, not mandatory procedures; "
                    "reusable procedures are provided separately by skills."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Current obstacle, context, or intended operation."},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
                        "outcome": {
                            "type": "string",
                            "enum": ["verified_success", "unresolved_failure", "tool_recovery"],
                            "description": "Optional evidence-outcome filter.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
            },
            {
                "name": "get_memory",
                "description": "Read one residual experience memory by its exact memory_id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"memory_id": {"type": "string"}},
                    "required": ["memory_id"],
                    "additionalProperties": False,
                },
                "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True},
            },
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        store = self._store()
        records = store["memories"]
        retrieval = store["retrieval"]
        if name == "search_memories":
            query = str(arguments.get("query") or "").strip()
            limit = max(1, min(int(arguments.get("limit", 5)), 10))
            outcome = str(arguments.get("outcome") or "").strip() or None
            query_embedding = _query_embedding(query, retrieval) if query else None
            retrieval_mode = "hybrid" if query_embedding is not None else "strict_lexical_fallback"
            value: Any = {
                "query": query,
                "count": 0,
                "retrieval_mode": retrieval_mode,
                "memories": [],
            }
            if query:
                value["memories"] = _search(
                    records,
                    query,
                    limit,
                    outcome,
                    retrieval=retrieval,
                    query_embedding=query_embedding,
                )
                value["count"] = len(value["memories"])
        elif name == "get_memory":
            memory_id = str(arguments.get("memory_id") or "")
            value = next((item for item in records if item.get("memory_id") == memory_id), None)
            if value is None:
                return {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Memory not found: {memory_id}"}],
                }
            value = {key: item for key, item in value.items() if key != "retrieval_embedding"}
        else:
            return {"isError": True, "content": [{"type": "text", "text": f"Unknown tool: {name}"}]}
        return {
            "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}],
            "structuredContent": value,
        }

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any] | None:
        request_id = request.get("id")
        method = request.get("method")
        if request_id is None:
            return None
        if method == "initialize":
            requested = (request.get("params") or {}).get("protocolVersion")
            result = {
                "protocolVersion": requested or "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": "1.1.0"},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": self.tools()}
        elif method == "tools/call":
            params = request.get("params") or {}
            result = self.call(str(params.get("name") or ""), dict(params.get("arguments") or {}))
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def run(self) -> None:
        for line in sys.stdin:
            try:
                request = json.loads(line)
                response = self.dispatch(request)
            except Exception as exc:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(exc)},
                }
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only reflective memory MCP server")
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    MemoryServer(args.store).run()


if __name__ == "__main__":
    main()
