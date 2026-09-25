from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from evolution.bottleneck_detector import refine_candidates_with_llm
from evolution.types import BottleneckCandidate


def _candidate(candidate_id: str) -> BottleneckCandidate:
    return BottleneckCandidate(
        candidate_id=candidate_id,
        task_name="task-a",
        task_family="family-a",
        step_range=(1, 2),
        failed_attempts=[],
        winning_command="python3 process.py",
        winning_tool="Bash",
        exploration_cost=2,
        intent="resolve processing obstacle with Bash",
        obstacle="not_found",
        resolution="Use the verified Bash approach and validate its output.",
        evidence_source="trajectory",
    )


def _response(candidates: list[dict]) -> str:
    return json.dumps({"candidates": candidates})


class BottleneckRefinementRetryTests(unittest.TestCase):
    def test_retries_only_remaining_template_candidate(self) -> None:
        responses = [
            _response(
                [
                    {
                        "index": 0,
                        "intent": "normalize tabular input before aggregation",
                        "obstacle": "the input schema varies across files",
                        "resolution": "Inspect and normalize required columns before aggregation.",
                    }
                ]
            ),
            _response(
                [
                    {
                        "index": 0,
                        "intent": "validate chart data before rendering",
                        "obstacle": "the chart source contains incompatible values",
                        "resolution": "Validate and coerce chart inputs before rendering.",
                    }
                ]
            ),
        ]
        diagnostics: list[dict] = []

        with patch("evolution.bottleneck_detector.call_llm", side_effect=responses) as call:
            refined = refine_candidates_with_llm(
                [_candidate("candidate-a"), _candidate("candidate-b")],
                refinement_diagnostics=diagnostics,
            )

        self.assertEqual([candidate.candidate_id for candidate in refined], ["candidate-a", "candidate-b"])
        self.assertEqual(call.call_count, 2)
        self.assertEqual(diagnostics, [])

    def test_drops_and_records_candidate_after_three_failed_retries(self) -> None:
        unchanged = _response([])
        diagnostics: list[dict] = []

        with patch(
            "evolution.bottleneck_detector.call_llm",
            side_effect=[unchanged, unchanged, unchanged, unchanged],
        ) as call:
            refined = refine_candidates_with_llm(
                [_candidate("candidate-drop")],
                refinement_diagnostics=diagnostics,
            )

        self.assertEqual(refined, [])
        self.assertEqual(call.call_count, 4)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0]["candidate_id"], "candidate-drop")
        self.assertEqual(diagnostics[0]["max_targeted_retries"], 3)
        self.assertEqual(len(diagnostics[0]["retry_errors"]), 3)

    def test_batch_failure_falls_back_to_targeted_refinement(self) -> None:
        targeted = _response(
            [
                {
                    "index": 0,
                    "intent": "validate source files before processing",
                    "obstacle": "a required source file is unavailable",
                    "resolution": "Check required inputs and report missing files before processing.",
                }
            ]
        )
        diagnostics: list[dict] = []

        with patch(
            "evolution.bottleneck_detector.call_llm",
            side_effect=[RuntimeError("response did not include choices"), targeted],
        ) as call:
            refined = refine_candidates_with_llm(
                [_candidate("candidate-recovered")],
                refinement_diagnostics=diagnostics,
            )

        self.assertEqual([candidate.candidate_id for candidate in refined], ["candidate-recovered"])
        self.assertEqual(call.call_count, 2)
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
