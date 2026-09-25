You are supporting a regional diagnostics network that is reviewing whether certain panels should stay on the 14-day replenishment cadence or move to the 28-day cadence.

Evaluate the retained panels and compare the 14-day policy versus the 28-day policy.

Use these machine-readable input files:
- `/root/panel_manifest.json`
- `/root/shipper_cost.csv`
- `/root/contract_terms.csv`
- `/root/network_adjustments.csv`
- `/root/lab_capacity_overrides.csv`
- `/root/holdouts.json`
- `/root/report_template.json`

Assumptions and rules:
- Evaluate only panels whose manifest field `analysis_mode` equals `review`.
- Exclude any panel listed in `/root/holdouts.json` with `holdout_state` equal to `exclude`.
- Resolve `contract_terms.csv` rows by matching `panel_ref` to either `panel_name` or any entry in `alias_labels` from `panel_manifest.json`.
- Use only contract rows where `status_flag` is `current`.
- If multiple current contract rows map to the same retained panel, keep the one with the latest `effective_week`.
- Revenue per run per lab is:
  - retained `base_payment_per_run_per_lab_usd` from `contract_terms.csv`
  - plus `network_adjustment_per_run_per_lab_usd` from `network_adjustments.csv`, matched by `network_tier`
- If a retained panel's `network_tier` does not appear in `network_adjustments.csv`, use `0.0` as the network adjustment.
- Active lab count comes from `lab_capacity_overrides.csv`.
- In `lab_capacity_overrides.csv`, use only rows where `approval` is `approved`.
- Ignore approved rows whose `rev` is blank or whose `active_labs` is blank.
- If multiple approved valid rows exist for the same `panel_code`, keep the one with the highest numeric `rev`.
- If a retained panel has no approved valid override row, use `default_active_labs` from `panel_manifest.json`.
- 14-day model: `26 runs/year`, use `tests_per_lab_per_run_14_day` from `panel_manifest.json`.
- 28-day model: `13 runs/year`, use `tests_per_lab_per_run_28_day` from `panel_manifest.json`.
- Reagent cost uses `reagent_cost_per_1000_tests_usd` from `panel_manifest.json`.
- Shipper cost uses `shipper_cost_usd` from `shipper_cost.csv`, matched by `shipper_class`.
- Annual revenue formula: `(base_payment_per_run_per_lab_usd + network_adjustment_per_run_per_lab_usd) * active_labs * runs_per_year`
- Annual reagent cost formula: `reagent_cost_per_1000_tests_usd * active_labs * tests_per_lab_per_run * runs_per_year / 1000`
- Annual margin formula: `annual_revenue - annual_reagent_cost - annual_shipper_cost`
- Per-panel difference: `annual_margin_28_day_usd - annual_margin_14_day_usd`
- Total difference: the sum of all per-panel differences.
- Decision rule:
  - If `abs(total_difference) < 6000`, recommend `adopt_28_day`.
  - Otherwise, recommend `keep_14_day`.
- Round all currency outputs to 2 decimals.
- Sort `analysis.panels` by `panel_code` ascending.
- Preserve `metadata` and `audit_notes` from `/root/report_template.json` exactly as-is in the final JSON output.

Create exactly these output files:

1) `/root/diagpanel_policy_report.json`

Use this JSON schema:
```json
{
  "metadata": {
    "request_id": "string",
    "requested_by": "string"
  },
  "audit_notes": [
    "string"
  ],
  "analysis": {
    "assumptions": {
      "runs_per_year_14_day": 26,
      "runs_per_year_28_day": 13,
      "switch_threshold_usd": 6000,
      "override_rule": "highest numeric approved rev with non-empty active_labs, else default_active_labs",
      "holdout_rule": "exclude holdout_state=exclude",
      "adjustment_rule": "missing network_tier adjustment defaults to 0.0"
    },
    "panels": [
      {
        "panel_code": "string",
        "panel_name": "string",
        "active_labs": 0,
        "reagent_cost_per_1000_tests_usd": 0.0,
        "network_tier": "string",
        "network_adjustment_per_run_per_lab_usd": 0.0,
        "shipper_class": "string",
        "shipper_cost_usd": 0.0,
        "base_payment_per_run_per_lab_usd": 0.0,
        "total_payment_per_run_per_lab_usd": 0.0,
        "tests_per_lab_per_run_14_day": 0,
        "tests_per_lab_per_run_28_day": 0,
        "annual_reagent_cost_14_day_usd": 0.0,
        "annual_reagent_cost_28_day_usd": 0.0,
        "annual_shipper_cost_14_day_usd": 0.0,
        "annual_shipper_cost_28_day_usd": 0.0,
        "annual_revenue_14_day_usd": 0.0,
        "annual_revenue_28_day_usd": 0.0,
        "annual_margin_14_day_usd": 0.0,
        "annual_margin_28_day_usd": 0.0,
        "annual_margin_difference_28_minus_14_usd": 0.0
      }
    ],
    "totals": {
      "total_annual_margin_14_day_usd": 0.0,
      "total_annual_margin_28_day_usd": 0.0,
      "total_annual_margin_difference_28_minus_14_usd": 0.0,
      "absolute_total_margin_difference_usd": 0.0
    },
    "recommendation": {
      "decision": "adopt_28_day | keep_14_day",
      "justification": "string"
    }
  }
}
```

2) `/root/diagpanel_policy_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 14-day margin (USD),
  - total 28-day margin (USD),
  - absolute difference (USD),
  - final decision (`adopt_28_day` or `keep_14_day`). Use the exact slug in the summary.
