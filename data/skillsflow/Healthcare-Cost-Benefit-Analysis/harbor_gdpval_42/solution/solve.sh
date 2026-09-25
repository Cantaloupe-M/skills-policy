#!/bin/bash
set -euo pipefail

cat > /tmp/solve_refill_analysis.py << 'PYTHON'
#!/usr/bin/env python3

import csv
import json

WHOLESALE_PATH = "/root/wholesale_price.csv"
VIAL_PATH = "/root/vial_price.csv"
REIMBURSEMENT_PATH = "/root/reimbursement.csv"
OUTPUT_JSON = "/root/refill_analysis.json"
OUTPUT_SUMMARY = "/root/refill_summary.md"

PATIENTS = 300
FILLS_90 = 4
FILLS_100 = 3
TABLETS_90 = 90
TABLETS_100 = 100
SWITCH_THRESHOLD = 16000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def read_wholesale() -> list:
    rows = []
    with open(WHOLESALE_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "medication": row["medication"],
                    "price_per_1000_tablets_usd": float(row["price_per_1000_tablets_usd"]),
                    "vial_size_drams": int(row["vial_size_drams"]),
                }
            )
    return rows


def read_vial_prices() -> dict:
    prices = {}
    with open(VIAL_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            prices[int(row["vial_size_drams"])] = float(row["vial_price_usd"])
    return prices


def read_reimbursements() -> dict:
    values = {}
    with open(REIMBURSEMENT_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            values[row["medication"]] = float(row["reimbursement_per_fill_300_patients_usd"])
    return values


def main() -> None:
    wholesale_rows = read_wholesale()
    vial_prices = read_vial_prices()
    reimbursements = read_reimbursements()

    medications = []
    total_revenue_90 = 0.0
    total_revenue_100 = 0.0

    for row in wholesale_rows:
        medication = row["medication"]
        price_per_1000 = row["price_per_1000_tablets_usd"]
        vial_size = row["vial_size_drams"]
        vial_price = vial_prices[vial_size]
        reimbursement_per_fill = reimbursements[medication]

        annual_drug_cost_90 = price_per_1000 * (PATIENTS * TABLETS_90 * FILLS_90 / 1000.0)
        annual_drug_cost_100 = price_per_1000 * (PATIENTS * TABLETS_100 * FILLS_100 / 1000.0)

        annual_supply_cost_90 = vial_price * PATIENTS * FILLS_90
        annual_supply_cost_100 = vial_price * PATIENTS * FILLS_100

        annual_reimbursement_90 = reimbursement_per_fill * FILLS_90
        annual_reimbursement_100 = reimbursement_per_fill * FILLS_100

        annual_revenue_90 = annual_reimbursement_90 - annual_drug_cost_90 - annual_supply_cost_90
        annual_revenue_100 = annual_reimbursement_100 - annual_drug_cost_100 - annual_supply_cost_100
        annual_difference = annual_revenue_100 - annual_revenue_90

        med_record = {
            "medication": medication,
            "price_per_1000_tablets_usd": round2(price_per_1000),
            "vial_size_drams": vial_size,
            "vial_price_usd": round2(vial_price),
            "reimbursement_per_fill_300_patients_usd": round2(reimbursement_per_fill),
            "annual_drug_cost_90_day_usd": round2(annual_drug_cost_90),
            "annual_drug_cost_100_day_usd": round2(annual_drug_cost_100),
            "annual_supply_cost_90_day_usd": round2(annual_supply_cost_90),
            "annual_supply_cost_100_day_usd": round2(annual_supply_cost_100),
            "annual_reimbursement_90_day_usd": round2(annual_reimbursement_90),
            "annual_reimbursement_100_day_usd": round2(annual_reimbursement_100),
            "annual_revenue_90_day_usd": round2(annual_revenue_90),
            "annual_revenue_100_day_usd": round2(annual_revenue_100),
            "annual_revenue_difference_100_minus_90_usd": round2(annual_difference),
        }
        medications.append(med_record)

        total_revenue_90 += annual_revenue_90
        total_revenue_100 += annual_revenue_100

    total_difference = total_revenue_100 - total_revenue_90
    absolute_difference = abs(total_difference)

    if absolute_difference < SWITCH_THRESHOLD:
        decision = "switch_to_100_day"
        justification = (
            f"Absolute revenue difference (${round2(absolute_difference)}) "
            f"is below the ${SWITCH_THRESHOLD} threshold."
        )
    else:
        decision = "keep_90_day"
        justification = (
            f"Absolute revenue difference (${round2(absolute_difference)}) "
            f"meets or exceeds the ${SWITCH_THRESHOLD} threshold."
        )

    payload = {
        "assumptions": {
            "patients_per_medication": PATIENTS,
            "fills_per_year_90_day": FILLS_90,
            "fills_per_year_100_day": FILLS_100,
            "tablets_per_fill_90_day": TABLETS_90,
            "tablets_per_fill_100_day": TABLETS_100,
            "switch_threshold_usd": SWITCH_THRESHOLD,
        },
        "medications": medications,
        "totals": {
            "total_annual_revenue_90_day_usd": round2(total_revenue_90),
            "total_annual_revenue_100_day_usd": round2(total_revenue_100),
            "total_annual_revenue_difference_100_minus_90_usd": round2(total_difference),
            "absolute_total_revenue_difference_usd": round2(absolute_difference),
        },
        "recommendation": {
            "decision": decision,
            "justification": justification,
        },
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    summary_lines = [
        "# Auto-Refill Policy Analysis",
        f"- Total annual revenue (90-day): ${round2(total_revenue_90):,.2f}",
        f"- Total annual revenue (100-day): ${round2(total_revenue_100):,.2f}",
        f"- Total difference (100 minus 90): ${round2(total_difference):,.2f}",
        f"- Absolute difference: ${round2(absolute_difference):,.2f}",
        f"- Decision: {decision}",
    ]
    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    print(f"Wrote {OUTPUT_JSON} and {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
PYTHON

python3 /tmp/solve_refill_analysis.py
