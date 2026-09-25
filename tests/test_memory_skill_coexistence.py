from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import evolution.bottleneck_pipeline as bottleneck_pipeline
from evolution.bottleneck_pipeline import finalize_memory_compilation
from evolution.config import EvolutionConfig
from evolution.memory_store import (
    MEMORY_STORE_FILENAME,
    build_candidate_memory_payload,
    build_reflection_memory_payload,
    materialize_memory_runtime,
    memory_runtime_spec,
    merge_memory_store,
    prepare_runtime_skills,
    residual_memory_candidates,
)
from evolution.skill_utils import hash_skill_tree, initialize_skill_version_store
from evolution.task_instruction import prepare_task_instruction
from evolution.types import (
    BottleneckCandidate,
    CapabilityCluster,
    ExplorationReport,
    ExplorationTrace,
    ReusableSubstep,
)
from run_skillflow_evolution import _configure_memory_mcp_agents
from run_skilllearnbench_evolution import _configure_memory_mcp


def _reflection_trace(task_name: str, lesson: str) -> ExplorationTrace:
    return ExplorationTrace(
        task_name=task_name,
        task_family="spreadsheet-repair",
        attempt_id=f"{task_name}:1",
        attempt_number=1,
        verifier_passed=False,
        reflection=(
            "FAILURE OBSERVABLE: changed value was rejected\n"
            "CAUSAL STEP(S): s2\n"
            "CAUSAL EVIDENCE: verifier check and write step disagree\n"
            "DIAGNOSIS CONFIDENCE: confirmed\n"
            "ROOT CAUSE: the write was not validated after serialization\n"
            f"CORRECTIVE ACTION: {lesson}\n"
            "MISSING: post-write validation"
        ),
        reflection_files=["reflection_attempt_01.md"],
        reflection_verified_by_retry=True,
        reflection_retry_outcome="success",
        retry_transition={"from_attempt": 1, "to_attempt": 2, "retry_verifier_passed": True},
        reflection_source_attempt=1,
    )


class MemorySkillCoexistenceTests(unittest.TestCase):
    def test_default_recurrence_threshold_matches_paper(self) -> None:
        self.assertEqual(EvolutionConfig().min_occurrences, 3)

    def test_unpromoted_success_candidate_uses_the_same_memory_store(self) -> None:
        candidate = BottleneckCandidate(
            candidate_id="task-success:1:atomic-1",
            task_name="task-success",
            task_family="spreadsheet-repair",
            step_range=(2, 2),
            failed_attempts=[],
            winning_command="",
            winning_tool="Python",
            exploration_cost=1,
            intent="preserve workbook formulas during a value repair",
            obstacle="serialization can replace formulas with cached values",
            resolution="load formulas intact and validate formula cells after saving",
            evidence_label="verified_success",
            evidence_source="trajectory",
            candidate_kind="atomic_substep",
            substep=ReusableSubstep(
                step_indices=(2,),
                kind="atomic",
                action="preserve_formula_cells",
                tool_name="Python",
                signature="preserve-formulas",
            ),
        )
        trace = ExplorationTrace(task_name="task-success", task_family="spreadsheet-repair")
        payload = build_candidate_memory_payload([candidate], [trace])
        with TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / MEMORY_STORE_FILENAME
            store = merge_memory_store(store_path, payload)
            restored = residual_memory_candidates(store_path)

        self.assertEqual(store["memories"], [])
        self.assertEqual(store["counts"]["policy_candidates"], 1)
        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].candidate_kind, "atomic_substep")
        self.assertEqual(restored[0].substep.action, "preserve_formula_cells")

    def test_unpromoted_memory_persists_and_rehydrates_across_batches(self) -> None:
        payload = build_reflection_memory_payload(
            [_reflection_trace("task-a", "reopen the workbook and compare the target value")]
        )
        self.assertEqual(
            payload["fields"],
            ["context", "observation", "lesson", "rationale"],
        )
        self.assertEqual(payload["memories"][0]["observation"], "changed value was rejected")
        with TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / MEMORY_STORE_FILENAME
            store = merge_memory_store(store_path, payload)
            candidates = residual_memory_candidates(store_path)

        self.assertEqual(store["counts"]["unpromoted"], 1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].task_name, "task-a")
        self.assertIn("reopen the workbook", candidates[0].resolution)

    def test_retrieval_memory_preserves_details_policy_candidate_parameterizes_them(self) -> None:
        trace = _reflection_trace(
            "task-a",
            "reopen Summary cell C5 and verify the 3% growth formula",
        )
        payload = build_reflection_memory_payload([trace])

        memory = payload["memories"][0]
        candidate = payload["policy_candidates"][0]
        self.assertIn("C5", memory["lesson"])
        self.assertIn("3%", memory["lesson"])
        self.assertNotIn("C5", candidate["lesson"])
        self.assertIn("<cell>", candidate["lesson"])
        self.assertIn("<num>", candidate["lesson"])

    def test_later_cross_batch_compilation_factors_old_and_new_memories(self) -> None:
        first = build_reflection_memory_payload(
            [_reflection_trace("task-a", "reopen the workbook and compare the target value")]
        )
        second = build_reflection_memory_payload(
            [_reflection_trace("task-b", "reopen the workbook and compare the target value")]
        )
        with TemporaryDirectory() as temp_dir:
            store_path = Path(temp_dir) / MEMORY_STORE_FILENAME
            initial = merge_memory_store(store_path, first)
            old_memory_id = initial["memories"][0]["memory_id"]
            store = merge_memory_store(
                store_path,
                second,
                compiled_candidate_ids=[old_memory_id, second["memories"][0]["candidate_id"]],
            )

        self.assertEqual(store["counts"]["skill_factored"], 2)
        self.assertEqual(
            {item["representation"] for item in store["memories"]},
            {"memory_residual"},
        )

    def test_three_batch_pipeline_promotes_only_at_paper_threshold(self) -> None:
        def candidate(task_name: str) -> BottleneckCandidate:
            return BottleneckCandidate(
                candidate_id=f"{task_name}:1:reflection-1",
                task_name=task_name,
                task_family="spreadsheet-repair",
                step_range=(0, 0),
                failed_attempts=[],
                winning_command="",
                winning_tool="",
                exploration_cost=1,
                intent="changed value was rejected",
                obstacle="the write was not validated after serialization",
                resolution="reopen the workbook and compare the target value",
                evidence_label="verified_success",
                evidence_source="reflection",
                retry_outcome="success",
                candidate_kind="recovery_candidate",
            )

        first = candidate("task-a")
        second = candidate("task-b")
        third = candidate("task-c")
        original_group = bottleneck_pipeline.group_candidates
        original_compile = bottleneck_pipeline.compile_family_skill
        compiled_inputs: list[str] = []
        compile_call_sizes: list[int] = []

        def group(candidates: list[BottleneckCandidate]) -> list[CapabilityCluster]:
            return [
                CapabilityCluster(
                    capability_id="post-write-validation",
                    intent=first.intent,
                    obstacle=first.obstacle,
                    candidates=list(candidates),
                    candidate_kind="recovery_candidate",
                )
            ]

        def compile_skill(clusters, traces, task_family, skills_dir, **_kwargs):
            compile_call_sizes.append(len(clusters))
            if not clusters:
                raise AssertionError("singleton memory must not reach the skill compiler")
            compiled_inputs.extend(
                item.candidate_id
                for cluster in clusters
                for item in cluster.candidates
            )
            policy = Path(skills_dir) / "spreadsheet-repair" / "references" / "policies" / "post-write-validation.md"
            policy.parent.mkdir(parents=True, exist_ok=True)
            policy.write_text("# Post-write validation\n", encoding="utf-8")
            return ExplorationReport(
                task_family=task_family,
                num_capabilities=1,
                num_skills_updated=1,
                compiled_memory_ids=list(compiled_inputs),
            )

        try:
            bottleneck_pipeline.group_candidates = group
            bottleneck_pipeline.compile_family_skill = compile_skill
            with TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                store_path = root / MEMORY_STORE_FILENAME
                skills_dir = root / "skills"

                first_report = bottleneck_pipeline.run_evolution_pipeline(
                    [ExplorationTrace(task_name="task-a", task_family="spreadsheet-repair")],
                    "spreadsheet-repair",
                    skills_dir,
                    use_llm=False,
                    verbose=False,
                    discovered_candidates=[first],
                )
                self.assertEqual(first_report.publication_block_reason, "no_reusable_evidence")
                first_payload = build_candidate_memory_payload(
                    [first],
                    [ExplorationTrace(task_name="task-a", task_family="spreadsheet-repair")],
                )
                initial_store = merge_memory_store(store_path, first_payload)
                old_memory_id = initial_store["policy_candidates"][0]["memory_id"]

                second_report = bottleneck_pipeline.run_evolution_pipeline(
                    [ExplorationTrace(task_name="task-b", task_family="spreadsheet-repair")],
                    "spreadsheet-repair",
                    skills_dir,
                    use_llm=False,
                    verbose=False,
                    prior_memory_candidates=residual_memory_candidates(store_path),
                    discovered_candidates=[second],
                )
                second_payload = build_candidate_memory_payload(
                    [second],
                    [ExplorationTrace(task_name="task-b", task_family="spreadsheet-repair")],
                )
                second_store = merge_memory_store(store_path, second_payload)
                second_memory_ids = {
                    item["context"]["task_name"]: item["memory_id"]
                    for item in second_store["policy_candidates"]
                }
                self.assertEqual(second_report.publication_block_reason, "no_reusable_evidence")
                self.assertEqual(second_store["counts"]["pending_policy_candidates"], 2)

                third_report = bottleneck_pipeline.run_evolution_pipeline(
                    [ExplorationTrace(task_name="task-c", task_family="spreadsheet-repair")],
                    "spreadsheet-repair",
                    skills_dir,
                    use_llm=False,
                    verbose=False,
                    prior_memory_candidates=residual_memory_candidates(store_path),
                    discovered_candidates=[third],
                )
                third_payload = build_candidate_memory_payload(
                    [third],
                    [ExplorationTrace(task_name="task-c", task_family="spreadsheet-repair")],
                )
                pending_store = merge_memory_store(store_path, third_payload)
                final_store = finalize_memory_compilation(
                    store_path,
                    root,
                    third_report.compiled_memory_ids,
                )
                policy_exists = (
                    skills_dir
                    / "spreadsheet-repair"
                    / "references"
                    / "policies"
                    / "post-write-validation.md"
                ).is_file()
                remaining_candidates = residual_memory_candidates(store_path)
        finally:
            bottleneck_pipeline.group_candidates = original_group
            bottleneck_pipeline.compile_family_skill = original_compile

        self.assertTrue(policy_exists)
        self.assertEqual(compile_call_sizes, [1])
        self.assertEqual(
            set(compiled_inputs),
            {old_memory_id, second_memory_ids["task-b"], third.candidate_id},
        )
        self.assertEqual(pending_store["counts"]["pending_policy_candidates"], 3)
        self.assertEqual(final_store["counts"]["compiled_policy_candidates"], 3)
        self.assertEqual(final_store["counts"]["retrievable"], 0)
        self.assertEqual(remaining_candidates, [])

    def test_compilation_keeps_instance_residual_without_duplicate_procedure(self) -> None:
        original_lesson = "reopen the workbook and compare the target value"
        payload = build_reflection_memory_payload([_reflection_trace("task-a", original_lesson)])
        record = payload["memories"][0]
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store_path = root / MEMORY_STORE_FILENAME
            store = merge_memory_store(
                store_path,
                payload,
                compiled_candidate_ids=[record["candidate_id"]],
            )
            version = initialize_skill_version_store(root / "versions", task_family="spreadsheet-repair")
            runtime = materialize_memory_runtime(version.skills_dir, store_path)
            runtime_payload = json.loads((runtime / "records.json").read_text(encoding="utf-8"))
            remaining_candidates = residual_memory_candidates(store_path)

        self.assertEqual(store["memories"][0]["representation"], "memory_residual")
        self.assertEqual(remaining_candidates, [])
        exposed = runtime_payload["memories"][0]
        self.assertNotIn(original_lesson, exposed["lesson"])
        self.assertIn("compiled into the family skill", exposed["lesson"])
        self.assertIn("serialization", exposed["rationale"])
        self.assertNotIn("cluster_input", exposed)
        self.assertNotIn("substep", exposed)

    def test_materialized_server_supports_read_only_mcp_tools(self) -> None:
        payload = build_reflection_memory_payload(
            [_reflection_trace("task-a", "reopen the workbook and compare the target value")]
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store_path = root / MEMORY_STORE_FILENAME
            merge_memory_store(store_path, payload)
            version = initialize_skill_version_store(root / "versions", task_family="spreadsheet-repair")
            runtime = materialize_memory_runtime(version.skills_dir, store_path)
            spec = memory_runtime_spec(version.skills_dir)
            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "search_memories",
                        "arguments": {"query": "changed value rejected"},
                    },
                },
            ]
            result = subprocess.run(
                [sys.executable, str(runtime / "server.py"), "--store", str(runtime / "records.json")],
                input="\n".join(json.dumps(item) for item in requests) + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([item["name"] for item in responses[1]["result"]["tools"]], ["search_memories", "get_memory"])
        self.assertEqual(responses[2]["result"]["structuredContent"]["count"], 1)
        memory = responses[2]["result"]["structuredContent"]["memories"][0]
        self.assertEqual(memory["observation"], "changed value was rejected")
        self.assertIn("verifier check", memory["causal_evidence"])
        self.assertEqual(spec["name"], "experience_memory")

    def test_runtime_memory_copy_does_not_change_frozen_skill_hash(self) -> None:
        payload = build_reflection_memory_payload(
            [_reflection_trace("task-a", "reopen the workbook and compare the target value")]
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store_path = root / MEMORY_STORE_FILENAME
            merge_memory_store(store_path, payload)
            version = initialize_skill_version_store(root / "versions", task_family="spreadsheet-repair")
            frozen_hash = hash_skill_tree(version.skills_dir)
            runtime_skills = prepare_runtime_skills(
                version.skills_dir,
                root / "runtime-skills",
                store_path,
            )

            self.assertEqual(hash_skill_tree(version.skills_dir), frozen_hash)
            self.assertIsNotNone(memory_runtime_spec(runtime_skills))

    def test_task_instruction_explains_memory_skill_boundary(self) -> None:
        instruction = prepare_task_instruction(
            "Repair the supplied artifact.",
            ["spreadsheet-repair"],
            memory_available=True,
        )
        self.assertIn("invoke the `/spreadsheet-repair` skill", instruction)
        self.assertIn("contextual hypotheses", instruction)
        self.assertIn("skill remains authoritative", instruction)

    def test_benchmark_runners_attach_the_materialized_mcp(self) -> None:
        payload = build_reflection_memory_payload(
            [_reflection_trace("task-a", "reopen the workbook and compare the target value")]
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store_path = root / MEMORY_STORE_FILENAME
            merge_memory_store(store_path, payload)
            version = initialize_skill_version_store(root / "versions", task_family="spreadsheet-repair")
            materialize_memory_runtime(version.skills_dir, store_path)

            skillflow_config = {"agents": [{"mcp_servers": []}]}
            attached = _configure_memory_mcp_agents(skillflow_config, version.skills_dir)

            agent = {"run": "claude --print", "default_tools": ["Read"]}

            class FakeRunner:
                @staticmethod
                def get_agent(agent_id: str):
                    return agent if agent_id == "claude-code" else None

            _configure_memory_mcp(FakeRunner(), "claude-code", version.skills_dir)

        self.assertTrue(attached)
        self.assertEqual(skillflow_config["agents"][0]["mcp_servers"][0]["name"], "experience_memory")
        self.assertIn("--mcp-config", agent["run"])
        self.assertIn("mcp__experience_memory__search_memories", agent["default_tools"])


if __name__ == "__main__":
    unittest.main()
