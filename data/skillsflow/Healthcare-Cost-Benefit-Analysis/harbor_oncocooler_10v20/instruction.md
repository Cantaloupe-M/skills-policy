You are supporting an oncology supportive-care program that is reviewing whether to keep frequent cooler dispatches or move to larger, less frequent dispatches.

Evaluate the in-scope programs and compare keeping 10-day dispatches versus moving to 20-day dispatches.

Use these machine-readable input files:
- `/root/program_catalog.json`
- `/root/cooler_cost.csv`
- `/root/contract_payment.csv`
- `/root/site_overrides.csv`

Assumptions and rules:
- Evaluate only programs whose catalog field `review_flag` equals `review`.
- Resolve `contract_payment.csv` rows by matching `program_label` to either `program_name` or any entry in `known_labels` from `program_catalog.json`.
- Ignore payment rows that do not map to an in-scope program.
- Active site count comes from `site_overrides.csv`.
- In `site_overrides.csv`, use only rows where `approval_state` is `approved`.
- If multiple approved rows exist for the same `program_code`, keep the one with the highest `version_no`.
- If an in-scope program has no approved override row, use `default_active_sites` from `program_catalog.json`.
- 10-day model: `10 days/dispatch`, `36 dispatches/year`
- 20-day model: `20 days/dispatch`, `18 dispatches/year`
- Drug cost uses `acquisition_cost_per_1000_units_usd` and `units_per_day` from `program_catalog.json`.
- Cooler cost uses `cooler_cost_usd` from `cooler_cost.csv`, matched by `cooler_type`.
- Revenue uses `payment_per_dispatch_per_site_usd` from `contract_payment.csv`.
- Annual revenue formula: `payment_per_dispatch_per_site_usd * active_sites * dispatches_per_year`
- Annual drug cost formula: `acquisition_cost_per_1000_units_usd * active_sites * units_per_day * days_per_dispatch * dispatches_per_year / 1000`
- Annual margin formula: `annual_revenue - annual_drug_cost - annual_cooler_cost`
- Per-program difference: `annual_margin_20_day_usd - annual_margin_10_day_usd`
- Total difference: the sum of all per-program differences.
- Decision rule:
  - If `abs(total_difference) < 10000`, recommend `move_to_20_day`.
  - Otherwise, recommend `keep_10_day`.
- Round all currency outputs to 2 decimals.
- Sort the `programs` array by `program_code` ascending.

Create exactly these output files:

1) `/root/oncocooler_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "dispatches_per_year_10_day": 36,
    "dispatches_per_year_20_day": 18,
    "days_per_dispatch_10_day": 10,
    "days_per_dispatch_20_day": 20,
    "switch_threshold_usd": 10000,
    "site_override_rule": "highest approved version_no per program_code, else default_active_sites"
  },
  "programs": [
    {
      "program_code": "string",
      "program_name": "string",
      "active_sites": 0,
      "acquisition_cost_per_1000_units_usd": 0.0,
      "units_per_day": 0.0,
      "cooler_type": "string",
      "cooler_cost_usd": 0.0,
      "payment_per_dispatch_per_site_usd": 0.0,
      "annual_drug_cost_10_day_usd": 0.0,
      "annual_drug_cost_20_day_usd": 0.0,
      "annual_cooler_cost_10_day_usd": 0.0,
      "annual_cooler_cost_20_day_usd": 0.0,
      "annual_revenue_10_day_usd": 0.0,
      "annual_revenue_20_day_usd": 0.0,
      "annual_margin_10_day_usd": 0.0,
      "annual_margin_20_day_usd": 0.0,
      "annual_margin_difference_20_minus_10_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_10_day_usd": 0.0,
    "total_annual_margin_20_day_usd": 0.0,
    "total_annual_margin_difference_20_minus_10_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "move_to_20_day | keep_10_day",
    "justification": "string"
  }
}
```

2) `/root/oncocooler_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 10-day margin (USD),
  - total 20-day margin (USD),
  - absolute difference (USD),
  - final decision (`move_to_20_day` or `keep_10_day`). Use the exact slug in the summary.
