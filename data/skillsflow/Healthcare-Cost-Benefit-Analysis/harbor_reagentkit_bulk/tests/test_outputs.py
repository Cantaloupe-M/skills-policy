import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/reagent_policy_report.json')
OUTPUT_SUMMARY = Path('/root/reagent_policy_summary.md')
MANIFEST_PATH = Path('/root/assay_manifest.json')
CARRIER_PATH = Path('/root/carrier_cost.csv')
BILLING_PATH = Path('/root/billing.csv')
OVERRIDE_PATH = Path('/root/lab_overrides.csv')
TEMPLATE_PATH = Path('/root/report_template.json')

RUNS_SMALL = 24
RUNS_BULK = 12
THRESHOLD = 7000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    assays = {}
    alias_lookup = {}
    for region in manifest['regions']:
        for assay in region['assays']:
            if not assay['in_scope']:
                continue
            assays[assay['assay_id']] = assay
            alias_lookup[assay['assay_name'].lower()] = assay['assay_id']
            for alias in assay.get('aliases', []):
                alias_lookup[alias.lower()] = assay['assay_id']
    carrier_costs = {}
    with CARRIER_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            carrier_costs[row['carrier_type']] = float(row['carrier_cost_usd'])
    payments = {}
    with BILLING_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['is_active'] != 'true':
                continue
            assay_id = alias_lookup.get(row['assay_label'].lower())
            if assay_id is None:
                continue
            current = payments.get(assay_id)
            if current is None or row['effective_month'] > current['effective_month']:
                payments[assay_id] = {'effective_month': row['effective_month'], 'payment': float(row['payment_per_run_per_lab_usd'])}
    approved = {}
    with OVERRIDE_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['status'] != 'approved':
                continue
            assay_id = row['assay_id']
            if assay_id not in assays:
                continue
            revision = int(row['revision'])
            current = approved.get(assay_id)
            if current is None or revision > current['revision']:
                approved[assay_id] = {'revision': revision, 'active_labs': int(row['active_labs'])}
    rows = []
    for assay_id in sorted(assays):
        assay = assays[assay_id]
        active_labs = approved.get(assay_id, {'active_labs': int(assay['default_active_labs'])})['active_labs']
        carrier_type = assay['carrier_type']
        carrier_cost = carrier_costs[carrier_type]
        payment = payments[assay_id]['payment']
        reagent = float(assay['reagent_price_per_1000_tests_usd'])
        tests_small = int(assay['tests_per_lab_per_run_small'])
        tests_bulk = int(assay['tests_per_lab_per_run_bulk'])
        annual_reagent_cost_small = reagent * active_labs * tests_small * RUNS_SMALL / 1000.0
        annual_reagent_cost_bulk = reagent * active_labs * tests_bulk * RUNS_BULK / 1000.0
        annual_carrier_cost_small = carrier_cost * active_labs * RUNS_SMALL
        annual_carrier_cost_bulk = carrier_cost * active_labs * RUNS_BULK
        annual_revenue_small = payment * active_labs * RUNS_SMALL
        annual_revenue_bulk = payment * active_labs * RUNS_BULK
        annual_margin_small = annual_revenue_small - annual_reagent_cost_small - annual_carrier_cost_small
        annual_margin_bulk = annual_revenue_bulk - annual_reagent_cost_bulk - annual_carrier_cost_bulk
        diff = annual_margin_bulk - annual_margin_small
        rows.append({
            'assay_id': assay_id,
            'assay_name': assay['assay_name'],
            'active_labs': active_labs,
            'reagent_price_per_1000_tests_usd': round2(reagent),
            'carrier_type': carrier_type,
            'carrier_cost_usd': round2(carrier_cost),
            'payment_per_run_per_lab_usd': round2(payment),
            'tests_per_lab_per_run_small': tests_small,
            'tests_per_lab_per_run_bulk': tests_bulk,
            'annual_reagent_cost_small_kit_usd': round2(annual_reagent_cost_small),
            'annual_reagent_cost_bulk_kit_usd': round2(annual_reagent_cost_bulk),
            'annual_carrier_cost_small_kit_usd': round2(annual_carrier_cost_small),
            'annual_carrier_cost_bulk_kit_usd': round2(annual_carrier_cost_bulk),
            'annual_revenue_small_kit_usd': round2(annual_revenue_small),
            'annual_revenue_bulk_kit_usd': round2(annual_revenue_bulk),
            'annual_margin_small_kit_usd': round2(annual_margin_small),
            'annual_margin_bulk_kit_usd': round2(annual_margin_bulk),
            'annual_margin_difference_bulk_minus_small_usd': round2(diff),
        })
    total_small = round2(sum(row['annual_margin_small_kit_usd'] for row in rows))
    total_bulk = round2(sum(row['annual_margin_bulk_kit_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_bulk_minus_small_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'adopt_bulk_kit' if abs_diff < THRESHOLD else 'keep_small_kit'
    template = json.loads(TEMPLATE_PATH.read_text(encoding='utf-8'))
    return template['metadata'], rows, total_small, total_bulk, total_diff, abs_diff, decision


def load_output():
    assert OUTPUT_JSON.exists()
    return json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))


def test_required_output_files_exist():
    assert OUTPUT_JSON.exists()
    assert OUTPUT_SUMMARY.exists()


def test_metadata_and_schema():
    data = load_output()
    metadata, _, _, _, _, _, _ = load_expected()
    assert data['metadata'] == metadata
    assert set(data['analysis'].keys()) == {'assumptions', 'assays', 'totals', 'recommendation'}
    assert data['analysis']['assumptions'] == {
        'runs_per_year_small_kit': RUNS_SMALL,
        'runs_per_year_bulk_kit': RUNS_BULK,
        'switch_threshold_usd': THRESHOLD,
        'lab_override_rule': 'highest approved revision per assay_id, else default_active_labs',
        'billing_rule': 'latest active effective_month per assay',
    }


def test_rows_and_order():
    data = load_output()
    _, expected_rows, _, _, _, _, _ = load_expected()
    assert [r['assay_id'] for r in data['analysis']['assays']] == [r['assay_id'] for r in expected_rows]
    for actual, expected in zip(data['analysis']['assays'], expected_rows):
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
    _, _, total_small, total_bulk, total_diff, abs_diff, decision = load_expected()
    totals = data['analysis']['totals']
    assert close(totals['total_annual_margin_small_kit_usd'], total_small)
    assert close(totals['total_annual_margin_bulk_kit_usd'], total_bulk)
    assert close(totals['total_annual_margin_difference_bulk_minus_small_usd'], total_diff)
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
    for value in (data['analysis']['totals']['total_annual_margin_small_kit_usd'], data['analysis']['totals']['total_annual_margin_bulk_kit_usd'], data['analysis']['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
