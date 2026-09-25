You are an Industrial Engineer supporting the Brightland Processing Center.

Use `/root/process_capability_data.xlsx` (3 sheets: `Task Duration`, `Failure Rate`, `System Errors`) to produce a deterministic process capability and stability assessment.

Create **both** files:

1. `/root/process_capability_report.json`
2. `/root/process_capability_brief.md`

## Required Analysis Rules

Use these exact formulas:

- Mean: arithmetic average
- Sample standard deviation: denominator `n-1`
- Coefficient of variation (CV): `sample_std / mean`
- Failure-rate point value: `Failures / Units processed` (proportion)
- Failure overall rate percent: `100 * sum(Failures) / sum(Units processed)`
- Wilson 95% CI for overall failure rate with:
  - `z = 1.959963984540054`
  - `denom = 1 + z^2 / n`
  - `center = (p + z^2/(2n)) / denom`
  - `half = z * sqrt((p*(1-p) + z^2/(4n))/n) / denom`
- CI bounds in percent: `100 * (center +/- half)`
  - where `p = sum(Failures)/sum(Units processed)` and `n = sum(Units processed)`
- Trend test for each process series:
  - Fit linear regression with `x = 1..N`
  - Compute slope and t-statistic for slope
  - Stability rule: `Stable` iff `abs(t_stat) < 2.0`, else `Unstable`

Series for trend test:

- Task Duration: `Process Duration (min)`
- Failure Rate: per-point failure proportions (`Failures / Units processed`)
- System Errors: `Error Rate`

Variability ranking must compare CV values of:

- Task Duration series
- Failure-rate per-point series
- System Errors `Error Rate` series

## Required JSON Schema

`/root/process_capability_report.json` must contain:

- `task_duration`
- `failure_rate`
- `system_errors`
- `variability_ranking` (sorted highest CV to lowest)
- `highest_variability_process`
- `highest_risk_statement`
- `extended_analysis`
- `monitoring_plan`

### Additional JSON constraints

- `highest_variability_process` must be the top-ranked process by CV.
- `highest_risk_statement` must contain this exact sentence:
  - `System Errors is the highest-risk process.`
- `failure_rate` must include:
  - `uses_varying_denominators` (boolean)
  - `target_rate_pct` set to `1.0`
  - `capability_vs_target` (`Capable` or `Not Capable`)
- `monitoring_plan` must include these keys:
  - `process_to_be_monitored`
  - `inputs`
  - `outputs`
  - `key_performance_indicators`
  - `frequency_of_monitoring`
  - `observation_format`
  - `roles`
  - `reporting_format`
  - `corrective_action_process`
  - `benchmarks`
  - `prioritized_actions`
  - `checklist`
  - `momentum_plan_30_60_90`
  - `project_codename`
- `checklist` must have 5-9 items.

## Required Markdown Brief

`/root/process_capability_brief.md` must include these section headings:

- `Summary of Findings`
- `Most Significant Risks`
- `Prioritized Corrective Actions`
- `Monitoring Plan`

Inside `Monitoring Plan`, include these subsection headings:

- `Process to be Monitored`
- `Inputs`
- `Outputs`
- `Key Performance Indicators (KPIs)`
- `Frequency of Monitoring`
- `Observation Format`
- `Roles`
- `Reporting Format`
- `Corrective Action Process`
- `Benchmarks`

The markdown brief must also include:

- The exact sentence: `System Errors is the highest-risk process.`
- A project codename line
- 30/60/90-day momentum milestones
