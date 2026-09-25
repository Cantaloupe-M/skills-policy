# Behavioral-delta audit

This is a read-only first-stage audit of already-produced evolution artifacts.
It selects up to 30 policies from `skill_versions/final/.evolution/lineage.json`,
matches their origin fingerprints to all staged attempts, and emits a CSV with a
heuristic label (`spontaneous`, `exploration-induced`, `task-specific`, or
`ambiguous`). The `human_label` and `review_notes` columns are intentionally blank.

Run it against one family/run directory:

```bash
python experiments/behavioral_delta_audit/audit.py \
  --run-dir runs/skilllearnbench-evolution/information-retrieval
```

To select policies across all recorded runs (up to 30 total):

```bash
python experiments/behavioral_delta_audit/audit.py --runs-root runs --limit 30
```

Outputs are written under `<run-dir>/behavioral_delta_audit/` unless `--output`
is supplied. `audit_summary.json` reports per-label adoption, success, and retry
statistics. `candidate_audit.json` retains evidence fields for programmatic review.

The workflow section is an estimate: a workflow update is considered
“workflow-only” when the version has no policy/script runtime diff relative to its
parent. Inspect the version diff before using that number as a publication-bypass
claim. No LLM, network call, skill mutation, or trajectory mutation is performed.
