from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from evolution.memory_mcp_server import _query_embedding, _search


def _memory(
    memory_id: str,
    task_name: str,
    lesson: str,
    embedding: list[float] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "memory_id": memory_id,
        "outcome": "verified_success",
        "context": {"task_name": task_name, "task_family": "productivity-tools"},
        "observation": "The verifier rejected the generated artifact.",
        "lesson": lesson,
        "rationale": "The output was not validated against the task contract.",
    }
    if embedding is not None:
        record["retrieval_embedding"] = embedding
    return record


class MemoryRetrievalTests(unittest.TestCase):
    def test_query_embedding_rejects_a_different_model_space(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            @staticmethod
            def read() -> bytes:
                return json.dumps({"model": "other-model", "embedding": [1.0, 0.0]}).encode()

        retrieval = {"semantic_available": True, "embedding_model": "snapshot-model"}
        environment = {
            "SKILLFLOW_MEMORY_EMBEDDING_ENDPOINT": "http://embedding.invalid/embed",
            "SKILLFLOW_MEMORY_EMBEDDING_TOKEN": "test-token",
        }
        with patch.dict("os.environ", environment, clear=False), patch(
            "urllib.request.urlopen",
            return_value=Response(),
        ):
            result = _query_embedding("query", retrieval)

        self.assertIsNone(result)

    def test_strict_lexical_fallback_rejects_single_generic_overlap(self) -> None:
        records = [
            _memory(
                "schedule",
                "schedule-planning-1",
                "Validate timezone constraints and persist the corrected meeting schedule.",
            )
        ]

        result = _search(
            records,
            "DOCX template placeholder replacement conditional section formatting validation",
            5,
            None,
        )

        self.assertEqual(result, [])

    def test_strict_lexical_fallback_keeps_high_coverage_exact_match(self) -> None:
        records = [
            _memory(
                "schedule",
                "schedule-planning-1",
                "Validate timezone constraints and persist the corrected meeting schedule.",
            )
        ]

        result = _search(records, "timezone meeting schedule", 5, None)

        self.assertEqual([item["memory_id"] for item in result], ["schedule"])
        self.assertEqual(result[0]["match_mode"], "lexical_exact")

    def test_semantic_embedding_can_retrieve_without_lexical_overlap(self) -> None:
        records = [
            _memory(
                "schedule",
                "schedule-planning-1",
                "Validate timezone constraints and persist the corrected meeting schedule.",
                [1.0, 0.0],
            ),
            _memory(
                "offer",
                "offer-letter-generator-2",
                "Inspect every document part and remove all unreplaced template markers.",
                [0.0, 1.0],
            ),
        ]

        result = _search(
            records,
            "prepare a candidate employment document",
            5,
            None,
            retrieval={"semantic_available": True},
            query_embedding=[0.0, 1.0],
        )

        self.assertEqual([item["memory_id"] for item in result], ["offer"])
        self.assertEqual(result[0]["match_mode"], "hybrid")
        self.assertEqual(result[0]["semantic_score"], 1.0)

    def test_low_semantic_and_lexical_scores_return_empty(self) -> None:
        records = [
            _memory(
                "schedule",
                "schedule-planning-1",
                "Validate timezone constraints and persist the corrected meeting schedule.",
                [1.0, 0.0],
            )
        ]

        result = _search(
            records,
            "replace placeholders in a word processing file",
            5,
            None,
            retrieval={"semantic_available": True},
            query_embedding=[0.0, 1.0],
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
