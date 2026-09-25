#!/usr/bin/env python3
import csv
import json
from pathlib import Path

CATALOG_PATH = Path('/root/therapy_catalog.json')
BAG_PATH = Path('/root/bag_supply_cost.csv')
PAYMENT_PATH = Path('/root/delivery_payment.csv')
OVERRIDE_PATH = Path('/root/patient_overrides.csv')
OUTPUT_JSON = Path('/root/infusion_batch_analysis.json')
OUTPUT_SUMMARY = Path('/root/infusion_batch_summary.md')
DELIVERIES_7 = 52
DELIVERIES_14 = 26
DAYS_7 = 7
DAYS_14 = 14
THRESHOLD = 15000

def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
therapies = {}
alias_lookup = {}
for group in catalog['service_lines']:
    for therapy in group['therapies']:
        if not therapy['include_in_review']:
            continue
        therapies[therapy['therapy_code']] = therapy
        alias_lookup[therapy['therapy_name'].lower()] = therapy['therapy_code']
        for alias in therapy.get('aliases', []):
            alias_lookup[alias.lower()] = therapy['therapy_code']
bag_costs = {}
with BAG_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        bag_costs[int(row['bag_size_ml'])] = float(row['bag_supply_cost_usd'])
payments = {}
with PAYMENT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        mapped = alias_lookup.get(row['therapy_label'].lower())
        if mapped:
            payments[mapped] = float(row['payment_per_delivery_per_patient_usd'])
approved = {}
with OVERRIDE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['status'] != 'approved':
            continue
        therapy_code = row['therapy_code']
        if therapy_code not in therapies:
            continue
        revision = int(row['revision'])
        current = approved.get(therapy_code)
        if current is None or revision > current['revision']:
            approved[therapy_code] = {'revision': revision, 'active_patients': int(row['active_patients'])}
rows = []
total_7 = 0.0
total_14 = 0.0
for therapy_code in sorted(therapies):
    therapy = therapies[therapy_code]
    active_patients = approved[therapy_code]['active_patients']
    bag_size = int(therapy['bag_size_ml'])
    bag_cost = bag_costs[bag_size]
    payment = payments[therapy_code]
    drug_cost = float(therapy['drug_cost_per_1000_mg_usd'])
    dose_per_day = float(therapy['dose_mg_per_day'])
    annual_drug_cost_7 = drug_cost * active_patients * dose_per_day * DAYS_7 * DELIVERIES_7 / 1000.0
    annual_drug_cost_14 = drug_cost * active_patients * dose_per_day * DAYS_14 * DELIVERIES_14 / 1000.0
    annual_supply_cost_7 = bag_cost * active_patients * DELIVERIES_7
    annual_supply_cost_14 = bag_cost * active_patients * DELIVERIES_14
    annual_revenue_7 = payment * active_patients * DELIVERIES_7
    annual_revenue_14 = payment * active_patients * DELIVERIES_14
    annual_margin_7 = annual_revenue_7 - annual_drug_cost_7 - annual_supply_cost_7
    annual_margin_14 = annual_revenue_14 - annual_drug_cost_14 - annual_supply_cost_14
    diff = annual_margin_14 - annual_margin_7
    rows.append({
        'therapy_code': therapy_code,
        'therapy_name': therapy['therapy_name'],
        'active_patients': active_patients,
        'drug_cost_per_1000_mg_usd': round2(drug_cost),
        'dose_mg_per_day': round2(dose_per_day),
        'bag_size_ml': bag_size,
        'bag_supply_cost_usd': round2(bag_cost),
        'payment_per_delivery_per_patient_usd': round2(payment),
        'annual_drug_cost_7_day_usd': round2(annual_drug_cost_7),
        'annual_drug_cost_14_day_usd': round2(annual_drug_cost_14),
        'annual_supply_cost_7_day_usd': round2(annual_supply_cost_7),
        'annual_supply_cost_14_day_usd': round2(annual_supply_cost_14),
        'annual_revenue_7_day_usd': round2(annual_revenue_7),
        'annual_revenue_14_day_usd': round2(annual_revenue_14),
        'annual_margin_7_day_usd': round2(annual_margin_7),
        'annual_margin_14_day_usd': round2(annual_margin_14),
        'annual_margin_difference_14_minus_7_usd': round2(diff),
    })
    total_7 += annual_margin_7
    total_14 += annual_margin_14

total_diff = total_14 - total_7
abs_diff = abs(total_diff)
decision = 'move_to_14_day' if abs_diff < THRESHOLD else 'keep_7_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'move_to_14_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'deliveries_per_year_7_day': DELIVERIES_7,
        'deliveries_per_year_14_day': DELIVERIES_14,
        'days_per_delivery_7_day': DAYS_7,
        'days_per_delivery_14_day': DAYS_14,
        'switch_threshold_usd': THRESHOLD,
        'patient_override_rule': 'highest approved revision per therapy_code',
    },
    'therapies': rows,
    'totals': {
        'total_annual_margin_7_day_usd': round2(total_7),
        'total_annual_margin_14_day_usd': round2(total_14),
        'total_annual_margin_difference_14_minus_7_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
OUTPUT_SUMMARY.write_text('\n'.join([
    '# Home Infusion Batching Review',
    f'- Total annual margin (7-day): ${round2(total_7):,.2f}',
    f'- Total annual margin (14-day): ${round2(total_14):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + '\n', encoding='utf-8')
