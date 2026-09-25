#!/usr/bin/env python3
import csv
import json
from pathlib import Path

CATALOG_PATH = Path('/root/program_catalog.json')
COOLER_PATH = Path('/root/cooler_cost.csv')
PAYMENT_PATH = Path('/root/contract_payment.csv')
OVERRIDE_PATH = Path('/root/site_overrides.csv')
OUTPUT_JSON = Path('/root/oncocooler_analysis.json')
OUTPUT_SUMMARY = Path('/root/oncocooler_summary.md')

DISPATCHES_10 = 36
DISPATCHES_20 = 18
DAYS_10 = 10
DAYS_20 = 20
THRESHOLD = 10000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
programs = {}
labels = {}
for group in catalog['service_groups']:
    for program in group['programs']:
        if program['review_flag'] != 'review':
            continue
        programs[program['program_code']] = program
        labels[program['program_name'].lower()] = program['program_code']
        for alias in program.get('known_labels', []):
            labels[alias.lower()] = program['program_code']
cooler_costs = {}
with COOLER_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        cooler_costs[row['cooler_type']] = float(row['cooler_cost_usd'])
payments = {}
with PAYMENT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        key = labels.get(row['program_label'].lower())
        if key:
            payments[key] = float(row['payment_per_dispatch_per_site_usd'])
overrides = {}
with OVERRIDE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['approval_state'] != 'approved':
            continue
        code = row['program_code']
        if code not in programs:
            continue
        version = int(row['version_no'])
        current = overrides.get(code)
        if current is None or version > current['version_no']:
            overrides[code] = {'version_no': version, 'active_sites': int(row['active_sites'])}
rows = []
total_10 = 0.0
total_20 = 0.0
for code in sorted(programs):
    program = programs[code]
    active_sites = overrides.get(code, {'active_sites': int(program['default_active_sites'])})['active_sites']
    payment = payments[code]
    acquisition = float(program['acquisition_cost_per_1000_units_usd'])
    units_per_day = float(program['units_per_day'])
    cooler_type = program['cooler_type']
    cooler_cost = cooler_costs[cooler_type]
    annual_drug_cost_10 = acquisition * active_sites * units_per_day * DAYS_10 * DISPATCHES_10 / 1000.0
    annual_drug_cost_20 = acquisition * active_sites * units_per_day * DAYS_20 * DISPATCHES_20 / 1000.0
    annual_cooler_cost_10 = cooler_cost * active_sites * DISPATCHES_10
    annual_cooler_cost_20 = cooler_cost * active_sites * DISPATCHES_20
    annual_revenue_10 = payment * active_sites * DISPATCHES_10
    annual_revenue_20 = payment * active_sites * DISPATCHES_20
    annual_margin_10 = annual_revenue_10 - annual_drug_cost_10 - annual_cooler_cost_10
    annual_margin_20 = annual_revenue_20 - annual_drug_cost_20 - annual_cooler_cost_20
    diff = annual_margin_20 - annual_margin_10
    rows.append({
        'program_code': code,
        'program_name': program['program_name'],
        'active_sites': active_sites,
        'acquisition_cost_per_1000_units_usd': round2(acquisition),
        'units_per_day': round2(units_per_day),
        'cooler_type': cooler_type,
        'cooler_cost_usd': round2(cooler_cost),
        'payment_per_dispatch_per_site_usd': round2(payment),
        'annual_drug_cost_10_day_usd': round2(annual_drug_cost_10),
        'annual_drug_cost_20_day_usd': round2(annual_drug_cost_20),
        'annual_cooler_cost_10_day_usd': round2(annual_cooler_cost_10),
        'annual_cooler_cost_20_day_usd': round2(annual_cooler_cost_20),
        'annual_revenue_10_day_usd': round2(annual_revenue_10),
        'annual_revenue_20_day_usd': round2(annual_revenue_20),
        'annual_margin_10_day_usd': round2(annual_margin_10),
        'annual_margin_20_day_usd': round2(annual_margin_20),
        'annual_margin_difference_20_minus_10_usd': round2(diff),
    })
    total_10 += annual_margin_10
    total_20 += annual_margin_20

total_diff = total_20 - total_10
abs_diff = abs(total_diff)
decision = 'move_to_20_day' if abs_diff < THRESHOLD else 'keep_10_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'move_to_20_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'dispatches_per_year_10_day': DISPATCHES_10,
        'dispatches_per_year_20_day': DISPATCHES_20,
        'days_per_dispatch_10_day': DAYS_10,
        'days_per_dispatch_20_day': DAYS_20,
        'switch_threshold_usd': THRESHOLD,
        'site_override_rule': 'highest approved version_no per program_code, else default_active_sites',
    },
    'programs': rows,
    'totals': {
        'total_annual_margin_10_day_usd': round2(total_10),
        'total_annual_margin_20_day_usd': round2(total_20),
        'total_annual_margin_difference_20_minus_10_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
OUTPUT_SUMMARY.write_text("\n".join([
    '# Oncology Cooler Dispatch Review',
    f'- Total annual margin (10-day): ${round2(total_10):,.2f}',
    f'- Total annual margin (20-day): ${round2(total_20):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + "\n", encoding='utf-8')
