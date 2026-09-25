You are a Supply Chain Analyst supporting Meridian Global Logistics.

Use `/root/logistics_reliability_data.xlsx` (3 sheets: `Delivery Times`, `Damage Rates`, `Order Accuracy`) to produce a deterministic performance and risk assessment.

Create **both** files:

1. `/root/logistics_reliability_report.json`
2. `/root/logistics_reliability_brief.md`

## Required Analysis Rules

Use these exact formulas:

- Mean: arithmetic average
- Sample standard deviation: denominator `n-1`
- Coefficient of variation (CV): `sample_std / mean`
- Damage Rates point value: `Damaged / Shipments` (proportion)
- Damage Rates overall rate percent: `100 * sum(Damaged) / sum(Shipments)`
- Wilson 95% CI for overall damage rates rate with:
  - `z = 1.959963984540054`
  - `denom = 1 + z^2 / n`
  - `center = (p + z^2/(2n)) / denom`
  - `half = z * sqrt((p*(1-p) + z^2/(4n))/n) / denom`
- CI bounds in percent: `100 * (center +/- half)`
  - where `p = sum(Damaged)/sum(Shipments)` and `n = sum(Shipments)`
- Trend test for each process series:
  - Fit linear regression with `x = 1..N`
  - Compute slope and t-statistic for slope
  - Stability rule: `Stable` iff `abs(t_stat) < 2.0`, else `Unstable`

Series for trend test:

- Delivery Times: `Delivery Time (hrs)`
- Damage Rates: per-point proportions (`Damaged / Shipments`)
- Order Accuracy: `Error Rate`

Variability ranking must compare CV values of:

- Delivery Times series
- Damage Rates per-point series
- Order Accuracy `Error Rate` series

## Required JSON Schema

`/root/logistics_reliability_report.json` must contain:

- `delivery_times`
- `damage_rates`
- `order_accuracy`
- `variability_ranking` (sorted highest CV to lowest)
- `highest_variability_process`
- `highest_risk_statement`
- `extended_analysis`
- `variance_diagnostic`
- `action_plan`

### Additional JSON constraints

- `highest_variability_process` must be the top-ranked process by CV.
- `highest_risk_statement` must contain this exact sentence:
  - `Order Accuracy is the highest-risk process.`
- `damage_rates` must include:
  - `uses_varying_denominators` (boolean)
  - `target_rate_pct` set to `1.5`
  - `capability_vs_target` (`Capable` or `Not Capable`)
- `variance_diagnostic` must include these keys:
  - `process_analyzed`
  - `amplification_detected` (boolean)
  - `severity`
  - `pattern_type`
  - `origin_layer`
  - `recommended_intervention`
- `action_plan` must include these keys:
  - `prioritized_actions`
  - `checklist`
  - `project_codename`
  - `momentum_plan_30_60_90`
- `checklist` must have 5-9 items.

## Required Markdown Brief

`/root/logistics_reliability_brief.md` must include these section headings:

- `Summary of Findings`
- `Most Significant Risks`
- `Prioritized Corrective Actions`
- `Variance Diagnostic`
- `Action Plan`

The markdown brief must also include:

- The exact sentence: `Order Accuracy is the highest-risk process.`
- A project codename line
- 30/60/90-day momentum milestones
