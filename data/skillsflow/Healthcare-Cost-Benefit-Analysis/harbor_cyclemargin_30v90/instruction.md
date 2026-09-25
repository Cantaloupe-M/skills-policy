You are supporting a community pulmonology clinic that is reviewing its refill-cycle policy for inhaled maintenance therapies.

Compare keeping 30-day fills versus moving to 90-day fills for every therapy in the provided inputs.

Use these machine-readable input files:
- `/root/acquisition_cost.csv`
- `/root/packaging_cost.csv`
- `/root/reimbursement.csv`

Assumptions and rules:
- Patients per therapy: `240`
- Dosing: `2 inhalations daily`
- 30-day model: `60 doses/fill`, `12 fills/year`
- 90-day model: `180 doses/fill`, `4 fills/year`
- Drug cost uses `price_per_1000_doses_usd` from `acquisition_cost.csv`.
- Packaging cost uses `packaging_cost_usd` from `packaging_cost.csv` per patient per fill, matched by `canister_size_units`.
- Reimbursement per fill for 240 patients is in `reimbursement.csv`.
- Annual margin formula: `annual_reimbursement - annual_drug_cost - annual_packaging_cost`
- Per-therapy difference: `annual_margin_90_day_usd - annual_margin_30_day_usd`
- Total difference: the sum of all per-therapy differences.
- Decision rule:
  - If `abs(total_difference) < 12000`, recommend `adopt_90_day`.
  - Otherwise, recommend `keep_30_day`.
- Round all currency outputs to 2 decimals.
- Sort the `therapies` array alphabetically by `therapy`.

Create exactly these output files:

1) `/root/cycle_margin_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "patients_per_therapy": 240,
    "fills_per_year_30_day": 12,
    "fills_per_year_90_day": 4,
    "doses_per_fill_30_day": 60,
    "doses_per_fill_90_day": 180,
    "switch_threshold_usd": 12000
  },
  "therapies": [
    {
      "therapy": "string",
      "price_per_1000_doses_usd": 0.0,
      "canister_size_units": 0,
      "packaging_cost_usd": 0.0,
      "reimbursement_per_fill_240_patients_usd": 0.0,
      "annual_drug_cost_30_day_usd": 0.0,
      "annual_drug_cost_90_day_usd": 0.0,
      "annual_packaging_cost_30_day_usd": 0.0,
      "annual_packaging_cost_90_day_usd": 0.0,
      "annual_reimbursement_30_day_usd": 0.0,
      "annual_reimbursement_90_day_usd": 0.0,
      "annual_margin_30_day_usd": 0.0,
      "annual_margin_90_day_usd": 0.0,
      "annual_margin_difference_90_minus_30_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_30_day_usd": 0.0,
    "total_annual_margin_90_day_usd": 0.0,
    "total_annual_margin_difference_90_minus_30_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "adopt_90_day | keep_30_day",
    "justification": "string"
  }
}
```

2) `/root/cycle_margin_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 30-day margin (USD),
  - total 90-day margin (USD),
  - absolute difference (USD),
  - final decision (`adopt_90_day` or `keep_30_day`). Use the exact slug in the summary.
