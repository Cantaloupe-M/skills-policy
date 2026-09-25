You are supporting a regional vaccination outreach team that is reviewing whether to keep smaller crate dispatches or move to larger consolidated crate dispatches.

Evaluate the in-scope campaigns and compare the 6-day dispatch policy versus the 12-day dispatch policy.

Use these machine-readable input files:
- `/root/campaign_manifest.json`
- `/root/crate_cost.csv`
- `/root/billing.csv`
- `/root/location_overrides.csv`
- `/root/suspensions.csv`

Assumptions and rules:
- Evaluate only campaigns whose manifest field `analysis_flag` equals `review`.
- Exclude any campaign whose `campaign_id` appears in `suspensions.csv` with `suspension_status` equal to `hold`.
- Resolve `billing.csv` rows by matching `campaign_label` to either `campaign_name` or any entry in `alias_labels` from `campaign_manifest.json`.
- Use only billing rows where `status` is `active`.
- If multiple active billing rows map to the same retained campaign, keep the one with the latest `cycle_tag`.
- Active clinic count comes from `location_overrides.csv`.
- In `location_overrides.csv`, use only rows where `state` is `approved`.
- Ignore approved rows whose `revision` is blank or whose `active_clinics` is blank.
- If multiple approved valid rows exist for the same `campaign_id`, keep the one with the highest numeric `revision`.
- If a retained campaign has no approved valid override row, use `default_active_clinics` from `campaign_manifest.json`.
- 6-day model: `6 days/dispatch`, `60 dispatches/year`
- 12-day model: `12 days/dispatch`, `30 dispatches/year`
- Drug cost uses `drug_cost_per_1000_doses_usd` and `doses_per_day` from `campaign_manifest.json`.
- Crate cost uses `crate_cost_usd` from `crate_cost.csv`, matched by `crate_tier`.
- Revenue uses `payment_per_dispatch_per_clinic_usd` from the retained billing row.
- Annual revenue formula: `payment_per_dispatch_per_clinic_usd * active_clinics * dispatches_per_year`
- Annual drug cost formula: `drug_cost_per_1000_doses_usd * active_clinics * doses_per_day * days_per_dispatch * dispatches_per_year / 1000`
- Annual margin formula: `annual_revenue - annual_drug_cost - annual_crate_cost`
- Per-campaign difference: `annual_margin_12_day_usd - annual_margin_6_day_usd`
- Total difference: the sum of all per-campaign differences.
- Decision rule:
  - If `abs(total_difference) < 11000`, recommend `move_to_12_day`.
  - Otherwise, recommend `keep_6_day`.
- Round all currency outputs to 2 decimals.
- Sort the `campaigns` array by `campaign_id` ascending.

Create exactly these output files:

1) `/root/vaxcrate_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "dispatches_per_year_6_day": 60,
    "dispatches_per_year_12_day": 30,
    "days_per_dispatch_6_day": 6,
    "days_per_dispatch_12_day": 12,
    "switch_threshold_usd": 11000,
    "override_rule": "highest numeric approved revision with non-empty active_clinics, else default_active_clinics",
    "suspension_rule": "exclude hold campaigns"
  },
  "campaigns": [
    {
      "campaign_id": "string",
      "campaign_name": "string",
      "active_clinics": 0,
      "drug_cost_per_1000_doses_usd": 0.0,
      "doses_per_day": 0.0,
      "crate_tier": "string",
      "crate_cost_usd": 0.0,
      "payment_per_dispatch_per_clinic_usd": 0.0,
      "annual_drug_cost_6_day_usd": 0.0,
      "annual_drug_cost_12_day_usd": 0.0,
      "annual_crate_cost_6_day_usd": 0.0,
      "annual_crate_cost_12_day_usd": 0.0,
      "annual_revenue_6_day_usd": 0.0,
      "annual_revenue_12_day_usd": 0.0,
      "annual_margin_6_day_usd": 0.0,
      "annual_margin_12_day_usd": 0.0,
      "annual_margin_difference_12_minus_6_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_6_day_usd": 0.0,
    "total_annual_margin_12_day_usd": 0.0,
    "total_annual_margin_difference_12_minus_6_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "move_to_12_day | keep_6_day",
    "justification": "string"
  }
}
```

2) `/root/vaxcrate_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 6-day margin (USD),
  - total 12-day margin (USD),
  - absolute difference (USD),
  - final decision (`move_to_12_day` or `keep_6_day`). Use the exact slug in the summary.
