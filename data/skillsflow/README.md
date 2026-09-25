---
pretty_name: SkillFlow Test Tasks
language:
- en
license: other
task_categories:
- question-answering
- text-generation
- summarization
- other
tags:
- arxiv:2604.17308
- agents
- benchmark
- lifelong-learning
- skill-evolution
- office-automation
- spreadsheets
- docker
- harbor
size_categories:
- 100<n<1K
configs:
- config_name: default
  data_files:
  - split: train
    path: "**/*"
---

# Dataset Card for SkillFlow Test Tasks

## Dataset Summary

`SkillFlow Test Tasks` is the task repository used in the `SkillFlow` benchmark for evaluating lifelong skill discovery, skill revision, and cross-task procedural transfer in autonomous agents.

The dataset contains **166 runnable tasks** organized into **20 workflow families** spanning **five broad domains**:

- Finance & Economics
- Operations & Supply Chain
- Healthcare & Life Sciences
- Governance & Strategy
- Data & Document Intelligence

Each workflow family contains **8-9 tasks** that share a common **Domain-Agnostic Execution Flow (DAEF)** while varying in domain entities, files, business semantics, and grounded instructions. Tasks are intended for agentic execution in a containerized environment rather than for static text-only modeling.

This release is best viewed as a **benchmark task repository** rather than a conventional tabular dataset.

## Supported Tasks and Leaderboards

This dataset is designed for evaluating:

- lifelong skill discovery and externalization
- skill reuse across related tasks in a workflow family
- skill revision / patching after failures
- procedural transfer under shared DAEF structure
- end-to-end agent performance in executable office and data workflows

Typical evaluation metrics include:

- task completion rate
- interaction turns
- monetary cost
- output tokens
- number of evolved skills
- skill usage rate

## Languages

The benchmark instructions and file artifacts are primarily in **English**, although some repository metadata and supporting analysis files may include **Chinese** annotations.

## Dataset Structure

The root directory is organized by workflow family:

```text
<family_name>/
  ALL_TASK_DIFFICULTY_RANKING.json
  <task_name>/
    instruction.md
    task.toml
    environment/
      Dockerfile
      ... task-specific input artifacts ...
    tests/
      test.sh
      test_output.py
      test_outputs.py
    solution/
      solve.sh
      solve.py (optional)
      tools/...
```

### Workflow Families

The 20 workflow families map to the following benchmark definitions:

- `econ-detrending-correlation` → Industry Correlation Analysis
- `harbor_gdpval_20` → Financial Statement Rolling
- `sec-financial-report` → SEC 13F Financial Analysis
- `harbor_gdpval_21` → Supply Chain Replenishment
- `harbor_gdpval_36` → Production Capacity Planning
- `merge_20_21` → Inventory & Finance Integration
- `merge_35_37` → DMAIC Quality Analysis
- `merge_36_41` → Operational Recovery Planning
- `harbor_gdpval_42` → Healthcare Cost-Benefit Analysis
- `lab-unit-harmonization` → Medical Data Standardization
- `harbor_gdpval_3` → Distribution Center Auditing
- `harbor_gdpval_33` → Compensation Scenario Modeling
- `invoice-fraud-detection` → Document Fraud Detection
- `exceltable-in-ppt` → Embedded Data Repair
- `jpg-ocr-stat` → OCR Data Extraction
- `merge_court_offer` → HWPX Document Automation
- `merge_pdf_xlsx` → Cross-Format Data Reconciliation
- `merge_weight_reserves` → Weighted Risk Assessment
- `pptx-reference-formatting` → PPT Formatting Optimization
- `sales-pivot-analysis` → Sales Pivot Analysis

## Data Instances

A single data instance is a **task directory**.

Examples of task instances include:

- `econ-detrending-correlation/econ-broadcasting-advertising-correlation`
- `exceltable-in-ppt/fx-spot-matrix-refresh`
- `harbor_gdpval_20/atlas_refund_reserve_template_merge`

Each task instance includes:

- a natural-language task instruction in `instruction.md`
- execution and verifier configuration in `task.toml`
- a Docker-based runtime under `environment/`
- task-specific input files such as `xlsx`, `pptx`, `json`, `csv`, images, or PDFs
- programmatic tests under `tests/`
- an oracle or reference solution under `solution/`

## Data Fields

Because this is an executable benchmark, the main fields are file-based rather than row-based.

### Per-family files

- `ALL_TASK_DIFFICULTY_RANKING.json`: ordered list of task names inside a family, used for fixed within-family evaluation and rank-based train/test style splits in lifelong-skill experiments.

### Per-task files

- `instruction.md`: the user-facing task description to be solved by an agent
- `task.toml`: structured task metadata and runtime specification
- `environment/Dockerfile`: task environment definition
- `environment/*`: task inputs and runtime assets
- `tests/test.sh`: entrypoint for verification
- `tests/test_output.py`, `tests/test_outputs.py`: programmatic checkers
- `solution/solve.sh`, `solution/solve.py`: oracle/reference solver assets
- `solution/tools/*`: helper utilities used by the reference solution

### Common `task.toml` metadata

The `task.toml` files commonly expose fields such as:

- `version`
- `metadata.author_name`
- `metadata.author_email`
- `metadata.difficulty`
- `metadata.category`
- `metadata.tags`
- `verifier.timeout_sec`
- `agent.timeout_sec`
- `environment.build_timeout_sec`
- `environment.cpus`
- `environment.memory_mb`
- `environment.storage_mb`
- `environment.docker_image`
- optional flags such as `environment.allow_internet` or `environment.gpus`

## Data Splits

This release does not define conventional ML splits such as `train`, `validation`, and `test`.

Instead, evaluation is organized by **workflow family** and **within-family difficulty order**:

- each family contains a fixed ranked sequence of tasks
- agents are typically evaluated sequentially within a family
- some experimental protocols split each family into a **reference set** and a **test set** using `ALL_TASK_DIFFICULTY_RANKING.json`

## Dataset Creation

### Curation Rationale

`SkillFlow` is built to evaluate whether agents can:

1. solve executable tasks without pre-provided skills,
2. externalize reusable procedural knowledge from trajectories,
3. revise skills after failures, and
4. transfer those skills to later tasks that share the same DAEF.

The benchmark focuses on realistic workplace-style tasks such as spreadsheet planning, document editing, OCR extraction, reconciliation, auditing, and structured analysis.

### Source Data

According to the accompanying paper, the benchmark construction process starts from seed tasks collected from **SkillsBench** and **GDPval**, then expands them into cross-domain task families under fixed DAEF constraints. The final benchmark contains **20 workflow families and 166 tasks** after filtering candidate tasks for environment validity, logical soundness, difficulty ordering, and workflow consistency.

### Annotation Process

The benchmark construction follows a hybrid process described in the paper:

- human annotators extract and standardize DAEFs from seed tasks
- an architect agent performs cross-domain task-family generation
- a critic agent reviews execution reliability and DAEF consistency
- human reviewers filter families for robustness, leakage risk, and difficulty calibration

### Personal and Sensitive Information

The benchmark is intended to contain task artifacts for executable evaluation rather than personal user data. However, because some tasks mimic workplace documents and structured business scenarios, users should still review task assets carefully before redistribution or downstream commercial use.

## Considerations for Using the Data

### Social Impact

This dataset supports research on lifelong learning, external memory, skill discovery, and procedural transfer in autonomous agents. It may be useful for studying when skill reuse helps, when it fails, and how agent systems can maintain reusable skill libraries over time.

### Limitations

- This is not a plain text benchmark; many tasks require Docker, local file manipulation, and task-specific runtimes.
- The benchmark is designed for agentic execution, not direct single-shot language modeling.
- Some tasks depend on office documents, scripts, or file formats that are awkward to preview directly in the Hugging Face dataset viewer.
- Difficulty ranking is family-local rather than globally calibrated across all tasks.
- The benchmark evaluates one concrete style of external skill mechanism and does not exhaust all possible lifelong-learning designs.

### Recommendations

Users should:

- treat each task as an executable benchmark instance, not as a text example
- preserve directory structure when mirroring the dataset
- run tasks inside isolated container environments
- review included assets and licenses before wide redistribution

## How to Use

A typical workflow is:

1. choose a workflow family under `test_tasks/`
2. read `ALL_TASK_DIFFICULTY_RANKING.json` to obtain task order
3. select a task directory
4. read `instruction.md`
5. build or reuse the Docker environment from `environment/Dockerfile`
6. let an agent solve the task
7. run the verifier under `tests/`

Within the original repository, this dataset is commonly used together with Harbor-based runners such as:

- `family_job_runner.py`
- `iterative_shared_skills_runner.py`
- `rank_split_shared_skills_runner.py`

## Repository-Level Notes

This dataset card describes the `test_tasks/` release from the `SkillFlow` benchmark repository. In the original project, `test_tasks/` is the recommended task root for benchmark execution.

## Citation

If you use this dataset, please cite the SkillFlow paper.

```bibtex
@misc{skillflow2026,
  title={SkillFlow: A Benchmark for Lifelong Skill Discovery and Evolution in Autonomous Agents},
  author={Anonymous},
  year={2026},
  note={EMNLP 2026 submission / preprint metadata to be updated}
}
```

## Licensing Information

A standalone dataset license has not been clearly specified in the current repository materials used to prepare this card. The Hugging Face metadata is therefore marked as `other`.

Before public release, you should verify:

- the repository license
- redistribution rights for included task artifacts
- whether any embedded office or document assets require additional attribution or replacement

## Contact

For questions about the benchmark, please refer to the main repository and accompanying paper materials.