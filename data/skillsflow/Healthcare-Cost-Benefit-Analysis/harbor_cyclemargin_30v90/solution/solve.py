#!/usr/bin/env python3
import csv
import json
from pathlib import Path

ACQ_PATH = Path('/root/acquisition_cost.csv')
PACK_PATH = Path('/root/packaging_cost.csv')
REIMB_PATH = Path('/root/reimbursement.csv')
OUTPUT_JSON = Path('/root/cycle_margin_analysis.json')
OUTPUT_SUMMARY = Path('/root/cycle_margin_summary.md')
PATIENTS = 240
FILLS_30 = 12
FILLS_90 = 4
DOSES_30 = 60
DOSES_90 = 180
THRESHOLD = 12000

def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

acq = []
with ACQ_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        acq.append({'therapy': row['therapy'], 'price': float(row['price_per_1000_doses_usd']), 'canister': int(row['canister_size_units'])})
pack = {}
with PACK_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        pack[int(row['canister_size_units'])] = float(row['packaging_cost_usd'])
reimb = {}
with REIMB_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        reimb[row['therapy']] = float(row['reimbursement_per_fill_240_patients_usd'])
therapies = []
total_30 = 0.0
total_90 = 0.0
for row in sorted(acq, key=lambda x: x['therapy']):
    therapy = row['therapy']
    price = row['price']
    canister = row['canister']
    packaging = pack[canister]
    reimbursement = reimb[therapy]
    annual_drug_cost_30 = price * (PATIENTS * DOSES_30 * FILLS_30 / 1000.0)
    annual_drug_cost_90 = price * (PATIENTS * DOSES_90 * FILLS_90 / 1000.0)
    annual_packaging_cost_30 = packaging * PATIENTS * FILLS_30
    annual_packaging_cost_90 = packaging * PATIENTS * FILLS_90
    annual_reimbursement_30 = reimbursement * FILLS_30
    annual_reimbursement_90 = reimbursement * FILLS_90
    annual_margin_30 = annual_reimbursement_30 - annual_drug_cost_30 - annual_packaging_cost_30
    annual_margin_90 = annual_reimbursement_90 - annual_drug_cost_90 - annual_packaging_cost_90
    diff = annual_margin_90 - annual_margin_30
    therapies.append({
        'therapy': therapy,
        'price_per_1000_doses_usd': round2(price),
        'canister_size_units': canister,
        'packaging_cost_usd': round2(packaging),
        'reimbursement_per_fill_240_patients_usd': round2(reimbursement),
        'annual_drug_cost_30_day_usd': round2(annual_drug_cost_30),
        'annual_drug_cost_90_day_usd': round2(annual_drug_cost_90),
        'annual_packaging_cost_30_day_usd': round2(annual_packaging_cost_30),
        'annual_packaging_cost_90_day_usd': round2(annual_packaging_cost_90),
        'annual_reimbursement_30_day_usd': round2(annual_reimbursement_30),
        'annual_reimbursement_90_day_usd': round2(annual_reimbursement_90),
        'annual_margin_30_day_usd': round2(annual_margin_30),
        'annual_margin_90_day_usd': round2(annual_margin_90),
        'annual_margin_difference_90_minus_30_usd': round2(diff),
    })
    total_30 += annual_margin_30
    total_90 += annual_margin_90

total_diff = total_90 - total_30
abs_diff = abs(total_diff)
decision = 'adopt_90_day' if abs_diff < THRESHOLD else 'keep_30_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'adopt_90_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'patients_per_therapy': PATIENTS,
        'fills_per_year_30_day': FILLS_30,
        'fills_per_year_90_day': FILLS_90,
        'doses_per_fill_30_day': DOSES_30,
        'doses_per_fill_90_day': DOSES_90,
        'switch_threshold_usd': THRESHOLD,
    },
    'therapies': therapies,
    'totals': {
        'total_annual_margin_30_day_usd': round2(total_30),
        'total_annual_margin_90_day_usd': round2(total_90),
        'total_annual_margin_difference_90_minus_30_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
OUTPUT_SUMMARY.write_text('\n'.join([
    '# Pulmonology Refill Cycle Review',
    f'- Total annual margin (30-day): ${round2(total_30):,.2f}',
    f'- Total annual margin (90-day): ${round2(total_90):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + '\n', encoding='utf-8')
