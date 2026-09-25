You are supporting a retail pharmacy decision on auto-refill policy.

Analyze whether the pharmacy should keep 90-day fills or switch to 100-day fills for its top 10 maintenance medications.

Use these machine-readable input files:
- `/root/wholesale_price.csv`
- `/root/vial_price.csv`
- `/root/reimbursement.csv`

The PDFs below are the original source documents for those tables:
- `/root/Wholesale_Price.pdf`
- `/root/Reimbursement.pdf`

Assumptions and rules:
- Patients per medication: `300`
- Dosing: `1 tablet daily`
- 90-day model: `90 tablets/fill`, `4 fills/year`
- 100-day model: `100 tablets/fill`, `3 fills/year`
- Drug cost uses `price_per_1000_tablets_usd` from `wholesale_price.csv`.
- Supply cost uses `vial_price_usd` (from `vial_price.csv`) per patient per fill.
- Reimbursement per fill for 300 patients is in `reimbursement.csv`.
- Annual revenue formula: `annual_reimbursement - annual_drug_cost - annual_supply_cost`
- Per-medication difference: `annual_revenue_100_day - annual_revenue_90_day`
- Total difference: sum of all per-medication differences.
- Decision rule:
  - If `abs(total_difference) < 16000`, recommend switching to 100-day fills.
  - Otherwise, recommend keeping 90-day fills.
- Round all currency outputs to 2 decimals.

Create exactly these output files:

1) `/root/refill_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "patients_per_medication": 300,
    "fills_per_year_90_day": 4,
    "fills_per_year_100_day": 3,
    "tablets_per_fill_90_day": 90,
    "tablets_per_fill_100_day": 100,
    "switch_threshold_usd": 16000
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_tablets_usd": 0.0,
      "vial_size_drams": 0,
      "vial_price_usd": 0.0,
      "reimbursement_per_fill_300_patients_usd": 0.0,
      "annual_drug_cost_90_day_usd": 0.0,
      "annual_drug_cost_100_day_usd": 0.0,
      "annual_supply_cost_90_day_usd": 0.0,
      "annual_supply_cost_100_day_usd": 0.0,
      "annual_reimbursement_90_day_usd": 0.0,
      "annual_reimbursement_100_day_usd": 0.0,
      "annual_revenue_90_day_usd": 0.0,
      "annual_revenue_100_day_usd": 0.0,
      "annual_revenue_difference_100_minus_90_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_revenue_90_day_usd": 0.0,
    "total_annual_revenue_100_day_usd": 0.0,
    "total_annual_revenue_difference_100_minus_90_usd": 0.0,
    "absolute_total_revenue_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "switch_to_100_day | keep_90_day",
    "justification": "string"
  }
}
```

2) `/root/refill_summary.md`
- 4 to 8 lines.
- Must include:
  - total 90-day revenue (USD),
  - total 100-day revenue (USD),
  - absolute difference (USD),
  - final decision (`switch_to_100_day` or `keep_90_day`). Use the exact slug in the summary.

