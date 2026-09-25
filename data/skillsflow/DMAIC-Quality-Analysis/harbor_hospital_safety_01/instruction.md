You are a Healthcare Quality Analyst supporting Clearview Regional Hospital.

Use `/root/patient_safety_data.xlsx` (3 sheets: `Wait Times`, `Medication Errors`, `Readmission Rates`) to produce a deterministic performance and risk assessment.

Create **both** files:

1. `/root/patient_safety_report.json`
2. `/root/patient_safety_brief.md`

## Required Analysis Rules

Use these exact formulas:

- Mean: arithmetic average
- Sample standard deviation: denominator `n-1`
- Coefficient of variation (CV): `sample_std / mean`
- Medication Errors point value: `Errors / Prescriptions Filled` (proportion)
- Medication Errors overall rate percent: `100 * sum(Errors) / sum(Prescriptions Filled)`
- Wilson 95% CI for overall medication errors rate with:
  - `z = 1.959963984540054`
  - `denom = 1 + z^2 / n`
  - `center = (p + z^2/(2n)) / denom`
  - `half = z * sqrt((p*(1-p) + z^2/(4n))/n) / denom`
- CI bounds in percent: `100 * (center +/- half)`
  - where `p = sum(Errors)/sum(Prescriptions Filled)` and `n = sum(Prescriptions Filled)`
- Trend test for each process series:
  - Fit linear regression with `x = 1..N`
  - Compute slope and t-statistic for slope
  - Stability rule: `Stable` iff `abs(t_stat) < 2.0`, else `Unstable`

Series for trend test:

- Wait Times: `Patient Wait Time (min)`
- Medication Errors: per-point proportions (`Errors / Prescriptions Filled`)
- Readmission Rates: `Readmission Rate`

Variability ranking must compare CV values of:

- Wait Times series
- Medication Errors per-point series
- Readmission Rates `Readmission Rate` series

## Required JSON Schema

`/root/patient_safety_report.json` must contain:

- `wait_times`
- `medication_errors`
- `readmission_rates`
- `variability_ranking` (sorted highest CV to lowest)
- `highest_variability_process`
- `highest_risk_statement`
- `extended_analysis`
- `monitoring_plan`

### Additional JSON constraints

- `highest_variability_process` must be the top-ranked process by CV.
- `highest_risk_statement` must contain this exact sentence:
  - `Readmission Rates is the highest-risk department.`
- `medication_errors` must include:
  - `uses_varying_denominators` (boolean)
  - `target_rate_pct` set to `2.0`
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
- `checklist` must have 5-9 items.

## Required Markdown Brief

`/root/patient_safety_brief.md` must include these section headings:

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

- The exact sentence: `Readmission Rates is the highest-risk department.`
