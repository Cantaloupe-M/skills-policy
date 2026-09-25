You are a DevOps Performance Engineer supporting NovaCraft Engineering's CI/CD platform.

Use `/root/pipeline_performance_data.xlsx` (3 sheets: `Build Duration`, `Bug Rate`, `Deployment Failures`) to produce a deterministic performance and risk assessment.

Create **both** files:

1. `/root/pipeline_performance_report.json`
2. `/root/pipeline_performance_brief.md`

## Required Analysis Rules

Use these exact formulas:

- Mean: arithmetic average
- Sample standard deviation: denominator `n-1`
- Coefficient of variation (CV): `sample_std / mean`
- Bug Rate point value: `Bugs Found / Lines Reviewed` (proportion)
- Bug Rate overall rate percent: `100 * sum(Bugs Found) / sum(Lines Reviewed)`
- Wilson 95% CI for overall bug rate rate with:
  - `z = 1.959963984540054`
  - `denom = 1 + z^2 / n`
  - `center = (p + z^2/(2n)) / denom`
  - `half = z * sqrt((p*(1-p) + z^2/(4n))/n) / denom`
- CI bounds in percent: `100 * (center +/- half)`
  - where `p = sum(Bugs Found)/sum(Lines Reviewed)` and `n = sum(Lines Reviewed)`
- Trend test for each process series:
  - Fit linear regression with `x = 1..N`
  - Compute slope and t-statistic for slope
  - Stability rule: `Stable` iff `abs(t_stat) < 2.0`, else `Unstable`

Series for trend test:

- Build Duration: `Build Duration (sec)`
- Bug Rate: per-point proportions (`Bugs Found / Lines Reviewed`)
- Deployment Failures: `Failure Rate`

Variability ranking must compare CV values of:

- Build Duration series
- Bug Rate per-point series
- Deployment Failures `Failure Rate` series

## Required JSON Schema

`/root/pipeline_performance_report.json` must contain:

- `build_duration`
- `bug_rate`
- `deployment_failures`
- `variability_ranking` (sorted highest CV to lowest)
- `highest_variability_process`
- `highest_risk_statement`
- `extended_analysis`
- `improvement_plan`

### Additional JSON constraints

- `highest_variability_process` must be the top-ranked process by CV.
- `highest_risk_statement` must contain this exact sentence:
  - `Deployment Failures is the highest-risk stage.`
- `bug_rate` must include:
  - `uses_varying_denominators` (boolean)
  - `target_rate_pct` set to `3.0`
  - `capability_vs_target` (`Capable` or `Not Capable`)
- `improvement_plan` must include these keys:
  - `process`
  - `methodology`
  - `root_cause_approach`
  - `incident_response_plan`
  - `technical_debt_assessment`
  - `prioritized_actions`
  - `project_codename`
  - `momentum_plan_30_60_90`

## Required Markdown Brief

`/root/pipeline_performance_brief.md` must include these section headings:

- `Summary of Findings`
- `Most Significant Risks`
- `Prioritized Corrective Actions`
- `Improvement Plan`

Inside `Improvement Plan`, include these subsection headings:

- `Process Under Review`
- `Methodology`
- `Root Cause Approach`
- `Incident Response Plan`
- `Technical Debt Assessment`

The markdown brief must also include:

- The exact sentence: `Deployment Failures is the highest-risk stage.`
- A project codename line
- 30/60/90-day momentum milestones
