# SkillFlow mechanism ablations

This directory runs the SkillFlow ablation matrix from the paper. Each variant
has an isolated output directory under `--output-root`.

Implemented variants:

- `full`: `m=2`, strict cross-task explicit-use qualification, delayed promotion.
- `m1`: support threshold `m=1`.
- `success_only`: disable unresolved-failure evidence.
- `immediate_promotion`: activate induced policies immediately.
- `outcome_only`: qualify from a later successful outcome without requiring explicit policy use.

## List variants

```bash
python experiments/skillflow_ablation/run.py \
  --list
```

## Dry-run

Inspect the commands without executing them:

```bash
python experiments/skillflow_ablation/run.py \
  --output-root runs/skillflow-ablation \
  --dry-run
```

## Run experiments

Run one representative family first:

```bash
python experiments/skillflow_ablation/run.py \
  --dataset-path data/skillsflow/Cross-Format-Data-Reconciliation \
  --only-family Cross-Format-Data-Reconciliation \
  --output-root runs/skillflow-ablation
```

Run all families from the configured `datasets` list (the default):

```bash
python experiments/skillflow_ablation/run.py --output-root runs/skillflow-ablation
```

`--dataset-path` is optional. It is only needed together with
`--only-family` when you want to run one family directly. The wrapper launches
one child run per implemented ablation variant, and each child run processes
all families in `configs/myevolution.yaml`.

Run selected variants:

```bash
python experiments/skillflow_ablation/run.py \
  --variant m1 \
  --variant immediate_promotion \
  --output-root runs/skillflow-ablation
```

The runner uses `uv run python` by default. Add `--launcher python` when all
dependencies are already installed in the active interpreter.


## Summarize results

```bash
python experiments/skillflow_ablation/summarize.py \
  --root runs/skillflow-ablation \
  --output runs/skillflow-ablation/summary.json0
```

The summary includes held-out accuracy, reuse success, false-promotion rate,
and same-batch exposure. Outputs are stored as
`<output-root>/<variant>/<job>/`.
