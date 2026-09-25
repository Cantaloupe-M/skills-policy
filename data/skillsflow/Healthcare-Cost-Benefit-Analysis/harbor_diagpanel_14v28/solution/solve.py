#!/usr/bin/env python3
import csv
import json
from pathlib import Path

MANIFEST_PATH = Path('/root/panel_manifest.json')
SHIPPER_PATH = Path('/root/shipper_cost.csv')
CONTRACT_PATH = Path('/root/contract_terms.csv')
ADJUSTMENT_PATH = Path('/root/network_adjustments.csv')
OVERRIDE_PATH = Path('/root/lab_capacity_overrides.csv')
HOLDOUT_PATH = Path('/root/holdouts.json')
TEMPLATE_PATH = Path('/root/report_template.json')
OUTPUT_JSON = Path('/root/diagpanel_policy_report.json')
OUTPUT_SUMMARY = Path('/root/diagpanel_policy_summary.md')

RUNS_14 = 26
RUNS_28 = 13
THRESHOLD = 6000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)

holdouts = json.loads(HOLDOUT_PATH.read_text(encoding='utf-8'))
excluded = {row['panel_code'] for row in holdouts['holdouts'] if row['holdout_state'] == 'exclude'}
manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
panels = {}
labels = {}
for cluster in manifest['service_clusters']:
    for panel in cluster['panels']:
        if panel['analysis_mode'] != 'review':
            continue
        if panel['panel_code'] in excluded:
            continue
        panels[panel['panel_code']] = panel
        labels[panel['panel_name'].lower()] = panel['panel_code']
        for alias in panel.get('alias_labels', []):
            labels[alias.lower()] = panel['panel_code']
shipper_costs = {}
with SHIPPER_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        shipper_costs[row['shipper_class']] = float(row['shipper_cost_usd'])
adjustments = {}
with ADJUSTMENT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        adjustments[row['network_tier']] = float(row['network_adjustment_per_run_per_lab_usd'])
contracts = {}
with CONTRACT_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['status_flag'] != 'current':
            continue
        code = labels.get(row['panel_ref'].lower())
        if code is None:
            continue
        current = contracts.get(code)
        if current is None or row['effective_week'] > current['effective_week']:
            contracts[code] = {'effective_week': row['effective_week'], 'base_payment': float(row['base_payment_per_run_per_lab_usd'])}
overrides = {}
with OVERRIDE_PATH.open(newline='', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['approval'] != 'approved':
            continue
        if not row['rev'] or not row['active_labs']:
            continue
        code = row['panel_code']
        if code not in panels:
            continue
        rev = int(row['rev'])
        current = overrides.get(code)
        if current is None or rev > current['rev']:
            overrides[code] = {'rev': rev, 'active_labs': int(row['active_labs'])}
template = json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))
rows = []
total_14 = 0.0
total_28 = 0.0
for code in sorted(panels):
    panel = panels[code]
    active_labs = overrides.get(code, {'active_labs': int(panel['default_active_labs'])})['active_labs']
    reagent = float(panel['reagent_cost_per_1000_tests_usd'])
    network_tier = panel['network_tier']
    adjustment = adjustments.get(network_tier, 0.0)
    shipper_class = panel['shipper_class']
    shipper_cost = shipper_costs[shipper_class]
    base_payment = contracts[code]['base_payment']
    total_payment = base_payment + adjustment
    tests_14 = int(panel['tests_per_lab_per_run_14_day'])
    tests_28 = int(panel['tests_per_lab_per_run_28_day'])
    annual_reagent_cost_14 = reagent * active_labs * tests_14 * RUNS_14 / 1000.0
    annual_reagent_cost_28 = reagent * active_labs * tests_28 * RUNS_28 / 1000.0
    annual_shipper_cost_14 = shipper_cost * active_labs * RUNS_14
    annual_shipper_cost_28 = shipper_cost * active_labs * RUNS_28
    annual_revenue_14 = total_payment * active_labs * RUNS_14
    annual_revenue_28 = total_payment * active_labs * RUNS_28
    annual_margin_14 = annual_revenue_14 - annual_reagent_cost_14 - annual_shipper_cost_14
    annual_margin_28 = annual_revenue_28 - annual_reagent_cost_28 - annual_shipper_cost_28
    diff = annual_margin_28 - annual_margin_14
    rows.append({
        'panel_code': code,
        'panel_name': panel['panel_name'],
        'active_labs': active_labs,
        'reagent_cost_per_1000_tests_usd': round2(reagent),
        'network_tier': network_tier,
        'network_adjustment_per_run_per_lab_usd': round2(adjustment),
        'shipper_class': shipper_class,
        'shipper_cost_usd': round2(shipper_cost),
        'base_payment_per_run_per_lab_usd': round2(base_payment),
        'total_payment_per_run_per_lab_usd': round2(total_payment),
        'tests_per_lab_per_run_14_day': tests_14,
        'tests_per_lab_per_run_28_day': tests_28,
        'annual_reagent_cost_14_day_usd': round2(annual_reagent_cost_14),
        'annual_reagent_cost_28_day_usd': round2(annual_reagent_cost_28),
        'annual_shipper_cost_14_day_usd': round2(annual_shipper_cost_14),
        'annual_shipper_cost_28_day_usd': round2(annual_shipper_cost_28),
        'annual_revenue_14_day_usd': round2(annual_revenue_14),
        'annual_revenue_28_day_usd': round2(annual_revenue_28),
        'annual_margin_14_day_usd': round2(annual_margin_14),
        'annual_margin_28_day_usd': round2(annual_margin_28),
        'annual_margin_difference_28_minus_14_usd': round2(diff),
    })
    total_14 += annual_margin_14
    total_28 += annual_margin_28

total_diff = total_28 - total_14
abs_diff = abs(total_diff)
decision = 'adopt_28_day' if abs_diff < THRESHOLD else 'keep_14_day'
justification = f"Absolute total margin difference (${round2(abs_diff):,.2f}) " + ("is below" if decision == 'adopt_28_day' else "meets or exceeds") + f" the ${THRESHOLD:,.0f} threshold."
template['analysis'] = {
    'assumptions': {
        'runs_per_year_14_day': RUNS_14,
        'runs_per_year_28_day': RUNS_28,
        'switch_threshold_usd': THRESHOLD,
        'override_rule': 'highest numeric approved rev with non-empty active_labs, else default_active_labs',
        'holdout_rule': 'exclude holdout_state=exclude',
        'adjustment_rule': 'missing network_tier adjustment defaults to 0.0',
    },
    'panels': rows,
    'totals': {
        'total_annual_margin_14_day_usd': round2(total_14),
        'total_annual_margin_28_day_usd': round2(total_28),
        'total_annual_margin_difference_28_minus_14_usd': round2(total_diff),
        'absolute_total_margin_difference_usd': round2(abs_diff),
    },
    'recommendation': {'decision': decision, 'justification': justification},
}
OUTPUT_JSON.write_text(json.dumps(template, indent=2, ensure_ascii=False) + "\n", encoding='utf-8')
OUTPUT_SUMMARY.write_text("\n".join([
    '# Diagnostic Panel Policy Review',
    f'- Total annual margin (14-day): ${round2(total_14):,.2f}',
    f'- Total annual margin (28-day): ${round2(total_28):,.2f}',
    f'- Absolute total margin difference: ${round2(abs_diff):,.2f}',
    f'- Decision: {decision}',
]) + "\n", encoding='utf-8')
