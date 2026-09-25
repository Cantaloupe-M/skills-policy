from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from evolution.memory_backfill import backfill_memory_store, prepare_test_memory_store
from evolution.memory_store import MEMORY_STORE_FILENAME, merge_memory_store
from evolution.types import BottleneckCandidate, ExplorationTrace


def _candidate(task_name: str, resolution: str) -> BottleneckCandidate:
    return BottleneckCandidate(
        candidate_id=f"{task_name}:1:reflection-1",
        task_name=task_name,
        task_family="family-a",
        step_range=(0, 0),
        failed_attempts=[],
        winning_command="",
        winning_tool="",
        exploration_cost=1,
        intent="repair a rejected artifact",
        obstacle="the artifact was not validated",
        resolution=resolution,
        evidence_label="verified_success",
        evidence_source="reflection",
        retry_outcome="success",
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


class MemoryBackfillTests(unittest.TestCase):
    def test_backfill_reads_train_only_and_marks_exact_lineage_match(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source-family"
            train_stage = source / "train/epoch_001/batch_001/evolution/staged_batch"
            test_stage = source / "test/round_001/evolution/staged_batch"
            train_stage.mkdir(parents=True)
            test_stage.mkdir(parents=True)
            (train_stage / "train-marker.json").write_text("{}", encoding="utf-8")
            (test_stage / "test-marker.json").write_text("{}", encoding="utf-8")

            compiled = _candidate("task-a", "reopen and validate the artifact")
            unpromoted = _candidate("task-b", "inspect the rejected field")
            fingerprint = hashlib.sha256(b"task-a").hexdigest()[:16]
            lineage_path = source / "skill_versions/final/.evolution/lineage.json"
            lineage_path.parent.mkdir(parents=True)
            lineage_path.write_text(
                json.dumps(
                    {
                        "policies": {
                            "policy-a": {
                                "resolution_evidence": [
                                    {
                                        "task_fingerprint": fingerprint,
                                        "source": "reflection",
                                        "label": "verified_success",
                                        "retry_outcome": "success",
                                        "resolution": compiled.resolution,
                                    }
                                ]
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            before = _snapshot(source)
            destination = root / "output/skill_versions" / MEMORY_STORE_FILENAME
            traces = [ExplorationTrace(task_name="task-a", task_family="family-a")]

            with (
                patch("evolution.memory_backfill.load_trajectories", return_value=[{}]) as load,
                patch("evolution.memory_backfill.parse_trajectories", return_value=traces),
                patch(
                    "evolution.memory_backfill.discover_candidates_cross_trial",
                    return_value=[compiled, unpromoted],
                ),
            ):
                report = backfill_memory_store(
                    source,
                    destination,
                    task_family="family-a",
                )

            self.assertEqual(load.call_count, 1)
            self.assertEqual(load.call_args.args[0], train_stage)
            self.assertEqual(_snapshot(source), before)
            self.assertTrue(all(path.startswith("train/") for path in report["source_files"]))
            self.assertEqual(report["counts"]["retrievable"], 0)
            self.assertEqual(report["counts"]["compiled_policy_candidates"], 1)
            self.assertEqual(report["counts"]["pending_policy_candidates"], 1)
            store = json.loads(destination.read_text(encoding="utf-8"))
            representations = {
                item["context"]["task_name"]: item["representation"]
                for item in store["policy_candidates"]
            }
            self.assertEqual(representations["task-a"], "skill_factored")
            self.assertEqual(representations["task-b"], "candidate")

    def test_native_store_is_copied_without_mutating_source(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source-family"
            native = source / "skill_versions" / MEMORY_STORE_FILENAME
            payload = {
                "task_family": "family-a",
                "memories": [],
            }
            merge_memory_store(native, payload)
            before = native.read_bytes()
            destination = root / "output" / MEMORY_STORE_FILENAME

            report = prepare_test_memory_store(
                source,
                destination,
                task_family="family-a",
            )

            self.assertEqual(report["source"], "native_training_store")
            self.assertEqual(destination.read_bytes(), before)
            self.assertEqual(native.read_bytes(), before)

    def test_native_v1_store_hides_workflows_from_retrieval(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source-family"
            native = source / "skill_versions" / MEMORY_STORE_FILENAME
            native.parent.mkdir(parents=True)
            native.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "task_family": "family-a",
                        "memories": [
                            {
                                "memory_id": "memory-reflection",
                                "candidate_id": "task-a:1:reflection-1",
                                "context": {
                                    "task_name": "task-a",
                                    "task_family": "family-a",
                                    "reflection_files": ["reflection_attempt_01.md"],
                                },
                                "lesson": "inspect cell C5",
                                "representation": "memory",
                            },
                            {
                                "memory_id": "memory-workflow",
                                "candidate_id": "task-a:1:substep-2",
                                "context": {
                                    "task_name": "task-a",
                                    "task_family": "family-a",
                                    "candidate_kind": "workflow",
                                    "evidence_source": "trajectory",
                                },
                                "candidate_kind": "workflow",
                                "lesson": "apply a parameterized workflow",
                                "representation": "memory",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            source_before = native.read_bytes()
            destination = root / "output" / MEMORY_STORE_FILENAME

            prepare_test_memory_store(
                source,
                destination,
                task_family="family-a",
            )
            migrated = json.loads(destination.read_text(encoding="utf-8"))
            source_after = native.read_bytes()

        self.assertEqual(source_after, source_before)
        self.assertEqual([item["memory_id"] for item in migrated["memories"]], ["memory-reflection"])
        self.assertEqual(len(migrated["policy_candidates"]), 2)


if __name__ == "__main__":
    unittest.main()
