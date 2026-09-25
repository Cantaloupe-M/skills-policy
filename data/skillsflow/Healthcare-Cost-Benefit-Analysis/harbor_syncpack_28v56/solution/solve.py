#!/usr/bin/env python3
import csv
import json
from pathlib import Path

INGREDIENT_PATH = Path('/root/ingredient_cost.csv')
CARD_PATH = Path('/root/card_cost.csv')
REIMB_PATH = Path('/root/reimbursement.csv')
OUTPUT_JSON = Path('/root/syncpack_analysis.json')
OUTPUT_SUMMARY = Path('/root/syncpack_summary.md')
PATIENTS = 180
FILLS_28 = 12
FILLS_56 = 6
CAPS_28 = 56
CAPS_56 = 112
THRESHOLD = 9000

def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

ingredient_rows = []
with INGREDIENT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        ingredient_rows.append({'medication': row['medication'], 'price': float(row['price_per_1000_capsules_usd']), 'cards': int(row['blister_card_count'])})
card_costs = {}
with CARD_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        card_costs[int(row['blister_card_count'])] = float(row['card_cost_usd'])
reimbursements = {}
with REIMB_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        reimbursements[row['medication']] = float(row['reimbursement_per_cycle_180_patients_usd'])
medications = []
total_28 = 0.0
total_56 = 0.0
for row in sorted(ingredient_rows, key=lambda x: x['medication']):
    medication = row['medication']
    price = row['price']
    cards = row['cards']
    card_cost = card_costs[cards]
    reimbursement = reimbursements[medication]
    annual_drug_cost_28 = price * (PATIENTS * CAPS_28 * FILLS_28 / 1000.0)
    annual_drug_cost_56 = price * (PATIENTS * CAPS_56 * FILLS_56 / 1000.0)
    annual_packaging_cost_28 = card_cost * PATIENTS * FILLS_28
    annual_packaging_cost_56 = card_cost * PATIENTS * FILLS_56
    annual_reimbursement_28 = reimbursement * FILLS_28
    annual_reimbursement_56 = reimbursement * FILLS_56
    annual_margin_28 = annual_reimbursement_28 - annual_drug_cost_28 - annual_packaging_cost_28
    annual_margin_56 = annual_reimbursement_56 - annual_drug_cost_56 - annual_packaging_cost_56
    diff = annual_margin_56 - annual_margin_28
    medications.append({
        'medication': medication,
        'price_per_1000_capsules_usd': round2(price),
        'blister_card_count': cards,
        'card_cost_usd': round2(card_cost),
        'reimbursement_per_cycle_180_patients_usd': round2(reimbursement),
        'annual_drug_cost_28_day_usd': round2(annual_drug_cost_28),
        'annual_drug_cost_56_day_usd': round2(annual_drug_cost_56),
        'annual_packaging_cost_28_day_usd': round2(annual_packaging_cost_28),
        'annual_packaging_cost_56_day_usd': round2(annual_packaging_cost_56),
        'annual_reimbursement_28_day_usd': round2(annual_reimbursement_28),
        'annual_reimbursement_56_day_usd': round2(annual_reimbursement_56),
        'annual_margin_28_day_usd': round2(annual_margin_28),
        'annual_margin_56_day_usd': round2(annual_margin_56),
        'annual_margin_difference_56_minus_28_usd': round2(diff),
    })
    total_28 += annual_margin_28
    total_56 += annual_margin_56

total_diff = total_56 - total_28
abs_diff = abs(total_diff)
decision = 'convert_to_56_day' if abs_diff < THRESHOLD else 'keep_28_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'convert_to_56_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'patients_per_medication': PATIENTS,
        'fills_per_year_28_day': FILLS_28,
        'fills_per_year_56_day': FILLS_56,
        'capsules_per_fill_28_day': CAPS_28,
        'capsules_per_fill_56_day': CAPS_56,
        'switch_threshold_usd': THRESHOLD,
    },
    'medications': medications,
    'totals': {
        'total_annual_margin_28_day_usd': round2(total_28),
        'total_annual_margin_56_day_usd': round2(total_56),
        'total_annual_margin_difference_56_minus_28_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
OUTPUT_SUMMARY.write_text('\n'.join([
    '# Sync-Pack Cycle Review',
    f'- Total annual margin (28-day): ${round2(total_28):,.2f}',
    f'- Total annual margin (56-day): ${round2(total_56):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + '\n', encoding='utf-8')
