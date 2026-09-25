#!/usr/bin/env python3
import csv
import json
from pathlib import Path

MANIFEST_PATH = Path('/root/campaign_manifest.json')
CRATE_PATH = Path('/root/crate_cost.csv')
BILLING_PATH = Path('/root/billing.csv')
OVERRIDE_PATH = Path('/root/location_overrides.csv')
SUSPENSION_PATH = Path('/root/suspensions.csv')
OUTPUT_JSON = Path('/root/vaxcrate_analysis.json')
OUTPUT_SUMMARY = Path('/root/vaxcrate_summary.md')

DISPATCHES_6 = 60
DISPATCHES_12 = 30
DAYS_6 = 6
DAYS_12 = 12
THRESHOLD = 11000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

held = set()
with SUSPENSION_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['suspension_status'] == 'hold':
            held.add(row['campaign_id'])
manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
campaigns = {}
labels = {}
for region in manifest['regions']:
    for campaign in region['campaigns']:
        if campaign['analysis_flag'] != 'review':
            continue
        if campaign['campaign_id'] in held:
            continue
        campaigns[campaign['campaign_id']] = campaign
        labels[campaign['campaign_name'].lower()] = campaign['campaign_id']
        for alias in campaign.get('alias_labels', []):
            labels[alias.lower()] = campaign['campaign_id']
crate_costs = {}
with CRATE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        crate_costs[row['crate_tier']] = float(row['crate_cost_usd'])
payments = {}
with BILLING_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['status'] != 'active':
            continue
        code = labels.get(row['campaign_label'].lower())
        if code is None:
            continue
        current = payments.get(code)
        if current is None or row['cycle_tag'] > current['cycle_tag']:
            payments[code] = {'cycle_tag': row['cycle_tag'], 'payment': float(row['payment_per_dispatch_per_clinic_usd'])}
overrides = {}
with OVERRIDE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['state'] != 'approved':
            continue
        if not row['revision'] or not row['active_clinics']:
            continue
        code = row['campaign_id']
        if code not in campaigns:
            continue
        revision = int(row['revision'])
        current = overrides.get(code)
        if current is None or revision > current['revision']:
            overrides[code] = {'revision': revision, 'active_clinics': int(row['active_clinics'])}
rows = []
total_6 = 0.0
total_12 = 0.0
for code in sorted(campaigns):
    campaign = campaigns[code]
    active_clinics = overrides.get(code, {'active_clinics': int(campaign['default_active_clinics'])})['active_clinics']
    payment = payments[code]['payment']
    drug_cost = float(campaign['drug_cost_per_1000_doses_usd'])
    doses_per_day = float(campaign['doses_per_day'])
    crate_tier = campaign['crate_tier']
    crate_cost = crate_costs[crate_tier]
    annual_drug_cost_6 = drug_cost * active_clinics * doses_per_day * DAYS_6 * DISPATCHES_6 / 1000.0
    annual_drug_cost_12 = drug_cost * active_clinics * doses_per_day * DAYS_12 * DISPATCHES_12 / 1000.0
    annual_crate_cost_6 = crate_cost * active_clinics * DISPATCHES_6
    annual_crate_cost_12 = crate_cost * active_clinics * DISPATCHES_12
    annual_revenue_6 = payment * active_clinics * DISPATCHES_6
    annual_revenue_12 = payment * active_clinics * DISPATCHES_12
    annual_margin_6 = annual_revenue_6 - annual_drug_cost_6 - annual_crate_cost_6
    annual_margin_12 = annual_revenue_12 - annual_drug_cost_12 - annual_crate_cost_12
    diff = annual_margin_12 - annual_margin_6
    rows.append({
        'campaign_id': code,
        'campaign_name': campaign['campaign_name'],
        'active_clinics': active_clinics,
        'drug_cost_per_1000_doses_usd': round2(drug_cost),
        'doses_per_day': round2(doses_per_day),
        'crate_tier': crate_tier,
        'crate_cost_usd': round2(crate_cost),
        'payment_per_dispatch_per_clinic_usd': round2(payment),
        'annual_drug_cost_6_day_usd': round2(annual_drug_cost_6),
        'annual_drug_cost_12_day_usd': round2(annual_drug_cost_12),
        'annual_crate_cost_6_day_usd': round2(annual_crate_cost_6),
        'annual_crate_cost_12_day_usd': round2(annual_crate_cost_12),
        'annual_revenue_6_day_usd': round2(annual_revenue_6),
        'annual_revenue_12_day_usd': round2(annual_revenue_12),
        'annual_margin_6_day_usd': round2(annual_margin_6),
        'annual_margin_12_day_usd': round2(annual_margin_12),
        'annual_margin_difference_12_minus_6_usd': round2(diff),
    })
    total_6 += annual_margin_6
    total_12 += annual_margin_12

total_diff = total_12 - total_6
abs_diff = abs(total_diff)
decision = 'move_to_12_day' if abs_diff < THRESHOLD else 'keep_6_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'move_to_12_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
payload = {
    'assumptions': {
        'dispatches_per_year_6_day': DISPATCHES_6,
        'dispatches_per_year_12_day': DISPATCHES_12,
        'days_per_dispatch_6_day': DAYS_6,
        'days_per_dispatch_12_day': DAYS_12,
        'switch_threshold_usd': THRESHOLD,
        'override_rule': 'highest numeric approved revision with non-empty active_clinics, else default_active_clinics',
        'suspension_rule': 'exclude hold campaigns',
    },
    'campaigns': rows,
    'totals': {
        'total_annual_margin_6_day_usd': round2(total_6),
        'total_annual_margin_12_day_usd': round2(total_12),
        'total_annual_margin_difference_12_minus_6_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
OUTPUT_SUMMARY.write_text("\n".join([
    '# Vaccine Crate Dispatch Review',
    f'- Total annual margin (6-day): ${round2(total_6):,.2f}',
    f'- Total annual margin (12-day): ${round2(total_12):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + "\n", encoding='utf-8')
