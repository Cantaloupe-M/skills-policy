import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/oncocooler_analysis.json')
OUTPUT_SUMMARY = Path('/root/oncocooler_summary.md')
CATALOG_PATH = Path('/root/program_catalog.json')
COOLER_PATH = Path('/root/cooler_cost.csv')
PAYMENT_PATH = Path('/root/contract_payment.csv')
OVERRIDE_PATH = Path('/root/site_overrides.csv')

DISPATCHES_10 = 36
DISPATCHES_20 = 18
DAYS_10 = 10
DAYS_20 = 20
THRESHOLD = 10000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
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
    total_10 = round2(sum(row['annual_margin_10_day_usd'] for row in rows))
    total_20 = round2(sum(row['annual_margin_20_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_20_minus_10_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'move_to_20_day' if abs_diff < THRESHOLD else 'keep_10_day'
    return rows, total_10, total_20, total_diff, abs_diff, decision


def load_output():
    assert OUTPUT_JSON.exists()
    return json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))


def test_required_output_files_exist():
    assert OUTPUT_JSON.exists()
    assert OUTPUT_SUMMARY.exists()


def test_schema_and_assumptions():
    data = load_output()
    assert set(data.keys()) == {'assumptions', 'programs', 'totals', 'recommendation'}
    assert data['assumptions'] == {
        'dispatches_per_year_10_day': DISPATCHES_10,
        'dispatches_per_year_20_day': DISPATCHES_20,
        'days_per_dispatch_10_day': DAYS_10,
        'days_per_dispatch_20_day': DAYS_20,
        'switch_threshold_usd': THRESHOLD,
        'site_override_rule': 'highest approved version_no per program_code, else default_active_sites',
    }


def test_rows_and_order():
    data = load_output()
    expected_rows, _, _, _, _, _ = load_expected()
    assert [row['program_code'] for row in data['programs']] == [row['program_code'] for row in expected_rows]
    for actual, expected in zip(data['programs'], expected_rows):
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
    _, total_10, total_20, total_diff, abs_diff, decision = load_expected()
    totals = data['totals']
    assert close(totals['total_annual_margin_10_day_usd'], total_10)
    assert close(totals['total_annual_margin_20_day_usd'], total_20)
    assert close(totals['total_annual_margin_difference_20_minus_10_usd'], total_diff)
    assert close(totals['absolute_total_margin_difference_usd'], abs_diff)
    assert data['recommendation']['decision'] == decision
    assert data['recommendation']['justification'].strip()


def test_summary_requirements():
    data = load_output()
    text = OUTPUT_SUMMARY.read_text(encoding='utf-8')
    lines = [line for line in text.splitlines() if line.strip()]
    assert 4 <= len(lines) <= 8
    decision = data['recommendation']['decision']
    normalized = decision.replace('_', ' ').lower()
    assert (decision in text) or (normalized in text.lower()), f"Decision '{decision}' (or '{normalized}') not found in summary"
    for value in (data['totals']['total_annual_margin_10_day_usd'], data['totals']['total_annual_margin_20_day_usd'], data['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
