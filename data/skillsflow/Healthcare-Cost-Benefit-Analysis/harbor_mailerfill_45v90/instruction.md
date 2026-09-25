You are supporting a specialty pharmacy mailer program that is reconsidering how often it ships adherence refill packs.

Compare keeping 45-day fills versus moving to 90-day fills for every medication in the provided inputs.

Use these machine-readable input files:
- `/root/compound_cost.csv`
- `/root/mailer_cost.csv`
- `/root/base_payment.csv`
- `/root/service_fee.csv`

Assumptions and rules:
- Patients per medication: `150`
- Dosing: `1 dose daily`
- 45-day model: `45 doses/fill`, `8 fills/year`
- 90-day model: `90 doses/fill`, `4 fills/year`
- Drug cost uses `price_per_1000_doses_usd` from `compound_cost.csv`.
- Mailing cost uses `mailer_cost_usd` from `mailer_cost.csv` per patient per fill, matched by `mailer_format`.
- Payment per fill is the sum of:
  - `base_payment_per_fill_150_patients_usd` from `base_payment.csv`
  - `service_fee_per_fill_150_patients_usd` from `service_fee.csv`
- Annual margin formula: `annual_payment - annual_drug_cost - annual_mailer_cost`
- Per-medication difference: `annual_margin_90_day_usd - annual_margin_45_day_usd`
- Total difference: the sum of all per-medication differences.
- Decision rule:
  - If `abs(total_difference) < 8500`, recommend `shift_to_90_day`.
  - Otherwise, recommend `keep_45_day`.
- Round all currency outputs to 2 decimals.
- Sort the `medications` array alphabetically by `medication`.

Create exactly these output files:

1) `/root/mailer_policy_analysis.json`

Use this JSON schema:
```json
{
  "assumptions": {
    "patients_per_medication": 150,
    "fills_per_year_45_day": 8,
    "fills_per_year_90_day": 4,
    "doses_per_fill_45_day": 45,
    "doses_per_fill_90_day": 90,
    "switch_threshold_usd": 8500
  },
  "medications": [
    {
      "medication": "string",
      "price_per_1000_doses_usd": 0.0,
      "mailer_format": "string",
      "mailer_cost_usd": 0.0,
      "base_payment_per_fill_150_patients_usd": 0.0,
      "service_fee_per_fill_150_patients_usd": 0.0,
      "total_payment_per_fill_150_patients_usd": 0.0,
      "annual_drug_cost_45_day_usd": 0.0,
      "annual_drug_cost_90_day_usd": 0.0,
      "annual_mailer_cost_45_day_usd": 0.0,
      "annual_mailer_cost_90_day_usd": 0.0,
      "annual_payment_45_day_usd": 0.0,
      "annual_payment_90_day_usd": 0.0,
      "annual_margin_45_day_usd": 0.0,
      "annual_margin_90_day_usd": 0.0,
      "annual_margin_difference_90_minus_45_usd": 0.0
    }
  ],
  "totals": {
    "total_annual_margin_45_day_usd": 0.0,
    "total_annual_margin_90_day_usd": 0.0,
    "total_annual_margin_difference_90_minus_45_usd": 0.0,
    "absolute_total_margin_difference_usd": 0.0
  },
  "recommendation": {
    "decision": "shift_to_90_day | keep_45_day",
    "justification": "string"
  }
}
```

2) `/root/mailer_policy_summary.md`
- 4 to 8 non-empty lines.
- Must include:
  - total 45-day margin (USD),
  - total 90-day margin (USD),
  - absolute difference (USD),
  - final decision (`shift_to_90_day` or `keep_45_day`). Use the exact slug in the summary.
