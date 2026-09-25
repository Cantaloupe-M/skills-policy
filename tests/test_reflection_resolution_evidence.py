from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import evolution.bottleneck_pipeline as bottleneck_pipeline
import evolution.exploration.capability_designer as capability_designer
from evolution.exploration.trace_parser import parse_trajectories
from evolution.trajectory_loader import load_trajectories
from evolution.types import BottleneckCandidate, CapabilityCluster, ExplorationTrace


def _candidate(
    task: str,
    *,
    label: str,
    resolution: str,
    retry_outcome: str,
) -> BottleneckCandidate:
    return BottleneckCandidate(
        candidate_id=f"{task}:1:reflection-1",
        task_name=task,
        task_family="family",
        step_range=(0, 0),
        failed_attempts=[],
        winning_command="",
        winning_tool="",
        exploration_cost=1,
        intent="artifact update was rejected",
        obstacle="the update was a no-op and post-write validation was missing",
        resolution=resolution,
        evidence_label=label,
        evidence_source="reflection",
        retry_outcome=retry_outcome,
        retry_transition={
            "from_attempt": 1,
            "to_attempt": 2,
            "retry_verifier_passed": retry_outcome == "success",
            "added_operations": [resolution],
            "removed_operations": [],
            "retained_operations": [],
        },
        candidate_kind="recovery_candidate",
    )


def _bash_step(command: str) -> dict:
    return {
        "source": "agent",
        "message": "",
        "extra": {
            "tool_use_name": "Bash",
            "raw_arguments": {"command": command},
            "tool_result_metadata": {"content": "ok", "is_error": False},
        },
    }


class ReflectionRetryEvidenceTests(unittest.TestCase):
    @staticmethod
    def _retry_chain() -> list[dict]:
        return [
            {
                "task_name": "task-a",
                "attempt_id": "task-a:1",
                "attempt_number": 1,
                "raw_steps": [_bash_step("python edit.py input.xlsx")],
                "reflection": "ROOT CAUSE: first method failed",
                "reflection_files": ["reflection_attempt_01.md"],
                "verifier_passed": False,
            },
            {
                "task_name": "task-a",
                "attempt_id": "task-a:2",
                "attempt_number": 2,
                "raw_steps": [
                    _bash_step("python edit.py input.xlsx"),
                    _bash_step("python validate.py output.xlsx"),
                ],
                "reflection": "ROOT CAUSE: second method found the missing check",
                "reflection_files": ["reflection_attempt_02.md"],
                "verifier_passed": False,
            },
            {
                "task_name": "task-a",
                "attempt_id": "task-a:3",
                "attempt_number": 3,
                "raw_steps": [
                    _bash_step("python edit.py input.xlsx"),
                    _bash_step("python validate.py output.xlsx"),
                    _bash_step("python repair.py output.xlsx"),
                ],
                "reflection": "",
                "reflection_files": [],
                "verifier_passed": True,
            },
        ]

    def test_only_immediate_retry_validates_reflection(self) -> None:
        traces = parse_trajectories(self._retry_chain(), "family")

        self.assertEqual(traces[0].reflection_retry_outcome, "failure")
        self.assertFalse(traces[0].reflection_verified_by_retry)
        self.assertTrue(any("validate.py" in item for item in traces[0].retry_transition["added_operations"]))
        self.assertEqual(traces[1].reflection_retry_outcome, "success")
        self.assertTrue(traces[1].reflection_verified_by_retry)
        self.assertTrue(any("repair.py" in item for item in traces[1].retry_transition["added_operations"]))

    def test_staged_loader_keeps_all_attempts_and_reflections(self) -> None:
        trials = self._retry_chain()
        with TemporaryDirectory() as temp_dir:
            job_dir = Path(temp_dir)
            task_dir = job_dir / "task-a"
            attempts_dir = task_dir / "attempts"
            attempts_dir.mkdir(parents=True)
            manifest_attempts = []
            for trial in trials:
                number = trial["attempt_number"]
                attempt_dir = attempts_dir / f"attempt_{number:02d}"
                agent_dir = attempt_dir / "agent"
                agent_dir.mkdir(parents=True)
                (agent_dir / "trajectory.json").write_text(
                    json.dumps({"steps": trial["raw_steps"]}),
                    encoding="utf-8",
                )
                reflection_files = trial["reflection_files"]
                if reflection_files:
                    (attempt_dir / reflection_files[0]).write_text(
                        trial["reflection"],
                        encoding="utf-8",
                    )
                manifest_attempts.append(
                    {
                        "number": number,
                        "success": trial["verifier_passed"],
                        "reflection_files": reflection_files,
                    }
                )
            (task_dir / "attempt_manifest.json").write_text(
                json.dumps({"task_name": "task-a", "attempts": manifest_attempts}),
                encoding="utf-8",
            )

            loaded = load_trajectories(job_dir)
            traces = parse_trajectories(loaded, "family")

        self.assertEqual([trace.attempt_number for trace in traces], [1, 2, 3])
        self.assertEqual([trace.reflection_retry_outcome for trace in traces[:2]], ["failure", "success"])

    def test_reflection_memory_preserves_the_complete_retry_episode(self) -> None:
        traces = parse_trajectories(self._retry_chain(), "family")
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            bottleneck_pipeline._write_reflection_memories(output_dir, traces)
            payload = json.loads((output_dir / "reflection_memories.json").read_text(encoding="utf-8"))

        self.assertEqual(len(payload["memories"]), 2)
        self.assertEqual(
            [(item["outcome"], item["retry_outcome"]) for item in payload["memories"]],
            [("unresolved_failure", "failure"), ("verified_success", "success")],
        )
        episode = payload["task_retry_episodes"][0]
        self.assertEqual(len(episode["attempts"]), 3)
        self.assertFalse(episode["attempts"][0]["retry_transition"]["retry_verifier_passed"])
        self.assertTrue(episode["attempts"][1]["retry_transition"]["retry_verifier_passed"])
        self.assertIsNone(episode["attempts"][2]["reflection_memory_id"])

    def test_mixed_resolution_outcomes_share_problem_cluster(self) -> None:
        successful = _candidate(
            "task-a",
            label="verified_success",
            retry_outcome="success",
            resolution="reopen the artifact and compare the target value",
        )
        failed = _candidate(
            "task-b",
            label="unresolved_failure",
            retry_outcome="failure",
            resolution="check only that the artifact can be opened",
        )
        original_discover = bottleneck_pipeline.discover_candidates_cross_trial
        original_group = bottleneck_pipeline.group_candidates
        try:
            bottleneck_pipeline.discover_candidates_cross_trial = lambda *args, **kwargs: [successful, failed]

            def group(candidates: list[BottleneckCandidate]) -> list[CapabilityCluster]:
                self.assertEqual(candidates, [successful, failed])
                return [
                    CapabilityCluster(
                        capability_id="shared-problem",
                        intent=successful.intent,
                        obstacle=successful.obstacle,
                        candidates=candidates,
                        candidate_kind="recovery_candidate",
                    )
                ]

            bottleneck_pipeline.group_candidates = group
            report = bottleneck_pipeline.run_evolution_pipeline(
                [ExplorationTrace(task_name="task-a"), ExplorationTrace(task_name="task-b")],
                "family",
                Path("/tmp/unused-skills"),
                use_llm=False,
                min_occurrences=2,
                dry_run=True,
                verbose=False,
            )
        finally:
            bottleneck_pipeline.discover_candidates_cross_trial = original_discover
            bottleneck_pipeline.group_candidates = original_group

        self.assertEqual(report.num_capabilities, 1)
        self.assertIn("verified candidate", report.summary)

    def test_policy_designer_receives_outcome_labeled_resolutions(self) -> None:
        successful = _candidate(
            "task-a",
            label="verified_success",
            retry_outcome="success",
            resolution="reopen the artifact and compare the target value",
        )
        failed = _candidate(
            "task-b",
            label="unresolved_failure",
            retry_outcome="failure",
            resolution="check only that the artifact can be opened",
        )
        cluster = CapabilityCluster(
            capability_id="shared-problem",
            intent=successful.intent,
            obstacle=successful.obstacle,
            candidates=[successful, failed],
            candidate_kind="recovery_candidate",
        )
        captured: dict = {}
        original_call = capability_designer.call_llm
        try:
            def fake_call_llm(*, messages, **kwargs):
                captured.update(json.loads(messages[0]["content"]))
                return json.dumps(
                    {
                        "existing_policy_id": None,
                        "name": "post-write-validation",
                        "purpose": "Ensure requested updates are materially applied.",
                        "trigger": "when modifying an existing artifact",
                        "procedure": ["Reopen the artifact and compare the target value."],
                        "invariants": ["Do not accept a no-op update."],
                        "recovery": ["If unchanged, inspect the authoritative field and retry."],
                        "script": None,
                    }
                )

            capability_designer.call_llm = fake_call_llm
            proposal = capability_designer.design_policy_proposal(cluster)
        finally:
            capability_designer.call_llm = original_call

        self.assertIsNotNone(proposal)
        outcomes = {
            (item["outcome"], item["retry_outcome"])
            for item in captured["resolution_evidence"]
        }
        self.assertEqual(outcomes, {("verified_success", "success"), ("unresolved_failure", "failure")})
        transitions = [item["retry_transition"] for item in captured["resolution_evidence"]]
        self.assertTrue(all(item["added_operations"] for item in transitions))

    def test_tool_recovery_does_not_satisfy_publication_support(self) -> None:
        first = _candidate(
            "task-a",
            label="tool_recovery",
            retry_outcome="missing",
            resolution="switch to a different local command",
        )
        second = _candidate(
            "task-b",
            label="tool_recovery",
            retry_outcome="missing",
            resolution="switch to another local command",
        )
        original_discover = bottleneck_pipeline.discover_candidates_cross_trial
        original_group = bottleneck_pipeline.group_candidates
        try:
            bottleneck_pipeline.discover_candidates_cross_trial = lambda *args, **kwargs: [first, second]
            bottleneck_pipeline.group_candidates = lambda candidates: [
                CapabilityCluster(
                    capability_id="local-recovery-only",
                    intent=first.intent,
                    obstacle=first.obstacle,
                    candidates=candidates,
                    candidate_kind="recovery_candidate",
                )
            ]
            report = bottleneck_pipeline.run_evolution_pipeline(
                [ExplorationTrace(task_name="task-a"), ExplorationTrace(task_name="task-b")],
                "family",
                Path("/tmp/unused-skills"),
                use_llm=False,
                min_occurrences=2,
                dry_run=True,
                verbose=False,
            )
        finally:
            bottleneck_pipeline.discover_candidates_cross_trial = original_discover
            bottleneck_pipeline.group_candidates = original_group

        self.assertEqual(report.num_capabilities, 0)
        self.assertEqual(report.publication_block_reason, "no_reusable_evidence")


if __name__ == "__main__":
    unittest.main()
