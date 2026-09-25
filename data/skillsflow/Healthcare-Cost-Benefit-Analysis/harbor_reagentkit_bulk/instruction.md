You are supporting a regional pathology operations team that is reviewing whether certain assays should stay on the small-kit cadence or move to bulk-kit restocking.

Evaluate the in-scope assays and compare the small-kit policy versus the bulk-kit policy.

Use these machine-readable input files:
- `/root/assay_manifest.json`
- `/root/carrier_cost.csv`
- `/root/billing.csv`
- `/root/lab_overrides.csv`
- `/root/report_template.json`

Assumptions and rules:
- Evaluate only assays whose manifest entry has `in_scope` set to `true`.
- Resolve `billing.csv` rows by matching `assay_label` to either `assay_name` or any alias listed for that assay in `assay_manifest.json`.
- Use only billing rows where `is_active` is `true`.
- If multiple active billing rows map to the same assay, keep the row with the latest `effective_month`.
- Active lab count comes from `lab_overrides.csv`.
- In `lab_overrides.csv`, use only rows where `status` is `approved`.
- If multiple approved rows exist for the same `assay_id`, keep the one with the highest `revision`.
- If an in-scope assay has no approved override row, use `default_active_labs` from `assay_manifest.json`.
- Small-kit model: `24 runs/year`, use `tests_per_lab_per_run_small` from `assay_manifest.json`.
- Bulk-kit model: `12 runs/year`, use `tests_per_lab_per_run_bulk` from `assay_manifest.json`.
- Reagent cost uses `reagent_price_per_1000_tests_usd` from `assay_manifest.json`.
- Carrier cost uses `carrier_cost_usd` from `carrier_cost.csv`, matched by `carrier_type`.
- Revenue uses `payment_per_run_per_lab_usd` from the retained billing row.
- Annual revenue formula: `payment_per_run_per_lab_usd * active_labs * runs_per_year`
- Annual reagent cost formula: `reagent_price_per_1000_tests_usd * active_labs * tests_per_lab_per_run * runs_per_year / 1000`
- Annual margin formula: `annual_revenue - annual_reagent_cost - annual_carrier_cost`
- Per-assay difference: `annual_margin_bulk_kit_usd - annual_margin_small_kit_usd`
- Total difference: the sum of all per-assay differences.
- Decision rule:
  - If `abs(total_difference) < 7000`, recommend `adopt_bulk_kit`.
  - Otherwise, recommend `keep_small_kit`.
- Round all currency outputs to 2 decimals.
- Sort `analysis.assays` by `assay_id` ascending.
- Preserve the `metadata` object from `/root/report_template.json` exactly as-is in the final JSON output.

Create exactly these output files:

1) `/root/reagent_policy_report.json`

Use this JSON schema:
```json
{
  "metadata": {
    "request_id": "string",
    "generated_for": "string"
  },
  "analysis": {
    "assumptions": {
      "runs_per_year_small_kit": 24,
      "runs_per_year_bulk_kit": 12,
      "switch_threshold_usd": 7000,
      "lab_override_rule": "highest approved revision per assay_id, else default_active_labs",
      "billing_rule": "latest active effective_month per assay"
    },
    "assays": [
      {
        "assay_id": "string",
        "assay_name": "string",
        "active_labs": 0,
        "reagent_price_per_1000_tests_usd": 0.0,
        "carrier_type": "string",
        "carrier_cost_usd": 0.0,
        "payment_per_run_per_lab_usd": 0.0,
        "tests_per_lab_per_run_small": 0,
        "tests_per_lab_per_run_bulk": 0,
        "annual_reagent_cost_small_kit_usd": 0.0,
        "annual_reagent_cost_bulk_kit_usd": 0.0,
        "annual_carrier_cost_small_kit_usd": 0.0,
        "annual_carrier_cost_bulk_kit_usd": 0.0,
        "annual_revenue_small_kit_usd": 0.0,
        "annual_revenue_bulk_kit_usd": 0.0,
        "annual_margin_small_kit_usd": 0.0,
        "annual_margin_bulk_kit_usd": 0.0,
        "annual_margin_difference_bulk_minus_small_usd": 0.0
      }
    ],
    "totals": {
      "total_annual_margin_small_kit_usd": 0.0,
      "total_annual_margin_bulk_kit_usd": 0.0,
      "total_annual_margin_difference_bulk_minus_small_usd": 0.0,
      "absolute_total_margin_difference_usd": 0.0
    },
    "recommendation": {
      "decision": "adopt_bulk_kit | keep_small_kit",
      "justification": "string"
    }
  }
}
```

2) `/root/reagent_policy_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total small-kit margin (USD),
  - total bulk-kit margin (USD),
  - absolute difference (USD),
  - final decision (`adopt_bulk_kit` or `keep_small_kit`). Use the exact slug in the summary.
