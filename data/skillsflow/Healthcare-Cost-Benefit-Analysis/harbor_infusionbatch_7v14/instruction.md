You are supporting a home infusion program that is deciding whether to keep weekly deliveries or move some therapies to 14-day delivery batching.

Evaluate the in-scope therapies and compare keeping 7-day deliveries versus moving to 14-day deliveries.

Use these machine-readable input files:
- `/root/therapy_catalog.json`
- `/root/bag_supply_cost.csv`
- `/root/delivery_payment.csv`
- `/root/patient_overrides.csv`

Assumptions and rules:
- Evaluate only therapies whose catalog entry has `include_in_review` set to `true`.
- Resolve `delivery_payment.csv` rows by matching `therapy_label` to either `therapy_name` or any alias listed for that therapy in `therapy_catalog.json`.
- Ignore payment rows that do not map to an in-scope therapy.
- Active patient count comes from `patient_overrides.csv`.
- In `patient_overrides.csv`, use only rows where `status` is `approved`.
- If multiple approved rows exist for the same `therapy_code`, keep the one with the highest `revision`.
- Ignore approved rows for therapies that are not in scope.
- 7-day model: `7 days/delivery`, `52 deliveries/year`
- 14-day model: `14 days/delivery`, `26 deliveries/year`
- Drug cost uses `drug_cost_per_1000_mg_usd` from `therapy_catalog.json` and `dose_mg_per_day` from the same therapy record.
- Bag supply cost uses `bag_supply_cost_usd` from `bag_supply_cost.csv`, matched by `bag_size_ml`.
- Revenue uses `payment_per_delivery_per_patient_usd` from `delivery_payment.csv`.
- Annual revenue formula: `payment_per_delivery_per_patient_usd * active_patients * deliveries_per_year`
- Annual drug cost formula: `drug_cost_per_1000_mg_usd * active_patients * dose_mg_per_day * days_per_delivery * deliveries_per_year / 1000`
- Annual margin formula: `annual_revenue - annual_drug_cost - annual_supply_cost`
- Per-therapy difference: `annual_margin_14_day_usd - annual_margin_7_day_usd`
- Total difference: the sum of all per-therapy differences.
- Decision rule:
  - If `abs(total_difference) < 15000`, recommend `move_to_14_day`.
  - Otherwise, recommend `keep_7_day`.
- Round all currency outputs to 2 decimals.
- Sort the `therapies` array by `therapy_code` ascending.

Create exactly these output files:

1) `/root/infusion_batch_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "deliveries_per_year_7_day": 52,
    "deliveries_per_year_14_day": 26,
    "days_per_delivery_7_day": 7,
    "days_per_delivery_14_day": 14,
    "switch_threshold_usd": 15000,
    "patient_override_rule": "highest approved revision per therapy_code"
  },
  "therapies": [
    {
      "therapy_code": "string",
      "therapy_name": "string",
      "active_patients": 0,
      "drug_cost_per_1000_mg_usd": 0.0,
      "dose_mg_per_day": 0.0,
      "bag_size_ml": 0,
      "bag_supply_cost_usd": 0.0,
      "payment_per_delivery_per_patient_usd": 0.0,
      "annual_drug_cost_7_day_usd": 0.0,
      "annual_drug_cost_14_day_usd": 0.0,
      "annual_supply_cost_7_day_usd": 0.0,
      "annual_supply_cost_14_day_usd": 0.0,
      "annual_revenue_7_day_usd": 0.0,
      "annual_revenue_14_day_usd": 0.0,
      "annual_margin_7_day_usd": 0.0,
      "annual_margin_14_day_usd": 0.0,
      "annual_margin_difference_14_minus_7_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_7_day_usd": 0.0,
    "total_annual_margin_14_day_usd": 0.0,
    "total_annual_margin_difference_14_minus_7_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "move_to_14_day | keep_7_day",
    "justification": "string"
  }
}
```

2) `/root/infusion_batch_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 7-day margin (USD),
  - total 14-day margin (USD),
  - absolute difference (USD),
  - final decision (`move_to_14_day` or `keep_7_day`). Use the exact slug in the summary.
