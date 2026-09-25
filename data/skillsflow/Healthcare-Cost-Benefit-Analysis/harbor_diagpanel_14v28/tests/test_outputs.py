import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/diagpanel_policy_report.json')
OUTPUT_SUMMARY = Path('/root/diagpanel_policy_summary.md')
MANIFEST_PATH = Path('/root/panel_manifest.json')
SHIPPER_PATH = Path('/root/shipper_cost.csv')
CONTRACT_PATH = Path('/root/contract_terms.csv')
ADJUSTMENT_PATH = Path('/root/network_adjustments.csv')
OVERRIDE_PATH = Path('/root/lab_capacity_overrides.csv')
HOLDOUT_PATH = Path('/root/holdouts.json')
TEMPLATE_PATH = Path('/root/report_template.json')

RUNS_14 = 26
RUNS_28 = 13
THRESHOLD = 6000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
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
    rows = []
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
    total_14 = round2(sum(row['annual_margin_14_day_usd'] for row in rows))
    total_28 = round2(sum(row['annual_margin_28_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_28_minus_14_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'adopt_28_day' if abs_diff < THRESHOLD else 'keep_14_day'
    template = json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))
    return template['metadata'], template['audit_notes'], rows, total_14, total_28, total_diff, abs_diff, decision


def load_output():
    assert OUTPUT_JSON.exists()
    return json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))


def test_required_output_files_exist():
    assert OUTPUT_JSON.exists()
    assert OUTPUT_SUMMARY.exists()


def test_template_preservation_and_schema():
    data = load_output()
    metadata, audit_notes, _, _, _, _, _, _ = load_expected()
    assert data['metadata'] == metadata
    assert data['audit_notes'] == audit_notes
    assert set(data['analysis'].keys()) == {'assumptions', 'panels', 'totals', 'recommendation'}
    assert data['analysis']['assumptions'] == {
        'runs_per_year_14_day': RUNS_14,
        'runs_per_year_28_day': RUNS_28,
        'switch_threshold_usd': THRESHOLD,
        'override_rule': 'highest numeric approved rev with non-empty active_labs, else default_active_labs',
        'holdout_rule': 'exclude holdout_state=exclude',
        'adjustment_rule': 'missing network_tier adjustment defaults to 0.0',
    }


def test_rows_and_order():
    data = load_output()
    _, _, expected_rows, _, _, _, _, _ = load_expected()
    assert [row['panel_code'] for row in data['analysis']['panels']] == [row['panel_code'] for row in expected_rows]
    for actual, expected in zip(data['analysis']['panels'], expected_rows):
        assert set(actual.keys()) == set(expected.keys())
        for key, expected_value in expected.items():
            if isinstance(expected_value, str):
                assert actual[key] == expected_value
            elif isinstance(expected_value, int):
                assert actual[key] == expected_value
            else:
                assert close(actual[key], expected_value)


def test_totals_and_decision():
    data = load_output()
    _, _, _, total_14, total_28, total_diff, abs_diff, decision = load_expected()
    totals = data['analysis']['totals']
    assert close(totals['total_annual_margin_14_day_usd'], total_14)
    assert close(totals['total_annual_margin_28_day_usd'], total_28)
    assert close(totals['total_annual_margin_difference_28_minus_14_usd'], total_diff)
    assert close(totals['absolute_total_margin_difference_usd'], abs_diff)
    assert data['analysis']['recommendation']['decision'] == decision
    assert data['analysis']['recommendation']['justification'].strip()


def test_summary_requirements():
    data = load_output()
    text = OUTPUT_SUMMARY.read_text(encoding='utf-8')
    lines = [line for line in text.splitlines() if line.strip()]
    assert 4 <= len(lines) <= 8
    decision = data['analysis']['recommendation']['decision']
    normalized = decision.replace('_', ' ').lower()
    assert (decision in text) or (normalized in text.lower()), f"Decision '{decision}' (or '{normalized}') not found in summary"
    for value in (data['analysis']['totals']['total_annual_margin_14_day_usd'], data['analysis']['totals']['total_annual_margin_28_day_usd'], data['analysis']['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
