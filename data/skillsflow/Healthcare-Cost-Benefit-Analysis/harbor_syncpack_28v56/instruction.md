You are supporting a medication synchronization program that is reconsidering how often it ships adherence card packs.

Compare keeping 28-day card cycles versus moving to 56-day card cycles for every medication in the provided inputs.

Use these machine-readable input files:
- `/root/ingredient_cost.csv`
- `/root/card_cost.csv`
- `/root/reimbursement.csv`

Assumptions and rules:
- Patients per medication: `180`
- Dosing: `2 capsules daily`
- 28-day model: `56 capsules/fill`, `12 fills/year`
- 56-day model: `112 capsules/fill`, `6 fills/year`
- Drug cost uses `price_per_1000_capsules_usd` from `ingredient_cost.csv`.
- Packaging cost uses `card_cost_usd` from `card_cost.csv` per patient per fill, matched by `blister_card_count`.
- Reimbursement per cycle for 180 patients is in `reimbursement.csv`.
- Annual margin formula: `annual_reimbursement - annual_drug_cost - annual_packaging_cost`
- Per-medication difference: `annual_margin_56_day_usd - annual_margin_28_day_usd`
- Total difference: the sum of all per-medication differences.
- Decision rule:
  - If `abs(total_difference) < 9000`, recommend `convert_to_56_day`.
  - Otherwise, recommend `keep_28_day`.
- Round all currency outputs to 2 decimals.
- Sort the `medications` array alphabetically by `medication`.

Create exactly these output files:

1) `/root/syncpack_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "patients_per_medication": 180,
    "fills_per_year_28_day": 12,
    "fills_per_year_56_day": 6,
    "capsules_per_fill_28_day": 56,
    "capsules_per_fill_56_day": 112,
    "switch_threshold_usd": 9000
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_capsules_usd": 0.0,
      "blister_card_count": 0,
      "card_cost_usd": 0.0,
      "reimbursement_per_cycle_180_patients_usd": 0.0,
      "annual_drug_cost_28_day_usd": 0.0,
      "annual_drug_cost_56_day_usd": 0.0,
      "annual_packaging_cost_28_day_usd": 0.0,
      "annual_packaging_cost_56_day_usd": 0.0,
      "annual_reimbursement_28_day_usd": 0.0,
      "annual_reimbursement_56_day_usd": 0.0,
      "annual_margin_28_day_usd": 0.0,
      "annual_margin_56_day_usd": 0.0,
      "annual_margin_difference_56_minus_28_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_28_day_usd": 0.0,
    "total_annual_margin_56_day_usd": 0.0,
    "total_annual_margin_difference_56_minus_28_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "convert_to_56_day | keep_28_day",
    "justification": "string"
  }
}
```

2) `/root/syncpack_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 28-day margin (USD),
  - total 56-day margin (USD),
  - absolute difference (USD),
  - final decision (`convert_to_56_day` or `keep_28_day`). Use the exact slug in the summary.
