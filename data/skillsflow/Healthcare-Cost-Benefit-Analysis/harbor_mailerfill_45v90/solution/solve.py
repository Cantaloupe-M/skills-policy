#!/usr/bin/env python3
import csv
import json
from pathlib import Path

COMPOUND_PATH = Path('/root/compound_cost.csv')
MAILER_PATH = Path('/root/mailer_cost.csv')
BASE_PAYMENT_PATH = Path('/root/base_payment.csv')
SERVICE_FEE_PATH = Path('/root/service_fee.csv')
OUTPUT_JSON = Path('/root/mailer_policy_analysis.json')
OUTPUT_SUMMARY = Path('/root/mailer_policy_summary.md')

PATIENTS = 150
FILLS_45 = 8
FILLS_90 = 4
DOSES_45 = 45
DOSES_90 = 90
THRESHOLD = 8500


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

compounds = []
with COMPOUND_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        compounds.append({'medication': row['medication'], 'price': float(row['price_per_1000_doses_usd']), 'mailer_format': row['mailer_format']})
mailer_costs = {}
with MAILER_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        mailer_costs[row['mailer_format']] = float(row['mailer_cost_usd'])
base_payments = {}
with BASE_PAYMENT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        base_payments[row['medication']] = float(row['base_payment_per_fill_150_patients_usd'])
service_fees = {}
with SERVICE_FEE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        service_fees[row['medication']] = float(row['service_fee_per_fill_150_patients_usd'])
medications = []
total_45 = 0.0
total_90 = 0.0
for row in sorted(compounds, key=lambda x: x['medication']):
    medication = row['medication']
    price = row['price']
    mailer_format = row['mailer_format']
    mailer_cost = mailer_costs[mailer_format]
    base_payment = base_payments[medication]
    service_fee = service_fees[medication]
    total_payment = base_payment + service_fee
    annual_drug_cost_45 = price * (PATIENTS * DOSES_45 * FILLS_45 / 1000.0)
    annual_drug_cost_90 = price * (PATIENTS * DOSES_90 * FILLS_90 / 1000.0)
    annual_mailer_cost_45 = mailer_cost * PATIENTS * FILLS_45
    annual_mailer_cost_90 = mailer_cost * PATIENTS * FILLS_90
    annual_payment_45 = total_payment * FILLS_45
    annual_payment_90 = total_payment * FILLS_90
    annual_margin_45 = annual_payment_45 - annual_drug_cost_45 - annual_mailer_cost_45
    annual_margin_90 = annual_payment_90 - annual_drug_cost_90 - annual_mailer_cost_90
    diff = annual_margin_90 - annual_margin_45
    medications.append({
        'medication': medication,
        'price_per_1000_doses_usd': round2(price),
        'mailer_format': mailer_format,
        'mailer_cost_usd': round2(mailer_cost),
        'base_payment_per_fill_150_patients_usd': round2(base_payment),
        'service_fee_per_fill_150_patients_usd': round2(service_fee),
        'total_payment_per_fill_150_patients_usd': round2(total_payment),
        'annual_drug_cost_45_day_usd': round2(annual_drug_cost_45),
        'annual_drug_cost_90_day_usd': round2(annual_drug_cost_90),
        'annual_mailer_cost_45_day_usd': round2(annual_mailer_cost_45),
        'annual_mailer_cost_90_day_usd': round2(annual_mailer_cost_90),
        'annual_payment_45_day_usd': round2(annual_payment_45),
        'annual_payment_90_day_usd': round2(annual_payment_90),
        'annual_margin_45_day_usd': round2(annual_margin_45),
        'annual_margin_90_day_usd': round2(annual_margin_90),
        'annual_margin_difference_90_minus_45_usd': round2(diff),
    })
    total_45 += annual_margin_45
    total_90 += annual_margin_90

total_diff = total_90 - total_45
abs_diff = abs(total_diff)
decision = 'shift_to_90_day' if abs_diff < THRESHOLD else 'keep_45_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'shift_to_90_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'patients_per_medication': PATIENTS,
        'fills_per_year_45_day': FILLS_45,
        'fills_per_year_90_day': FILLS_90,
        'doses_per_fill_45_day': DOSES_45,
        'doses_per_fill_90_day': DOSES_90,
        'switch_threshold_usd': THRESHOLD,
    },
    'medications': medications,
    'totals': {
        'total_annual_margin_45_day_usd': round2(total_45),
        'total_annual_margin_90_day_usd': round2(total_90),
        'total_annual_margin_difference_90_minus_45_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
OUTPUT_SUMMARY.write_text("\n".join([
    '# Mailer Refill Policy Review',
    f'- Total annual margin (45-day): ${round2(total_45):,.2f}',
    f'- Total annual margin (90-day): ${round2(total_90):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + "\n", encoding='utf-8')
