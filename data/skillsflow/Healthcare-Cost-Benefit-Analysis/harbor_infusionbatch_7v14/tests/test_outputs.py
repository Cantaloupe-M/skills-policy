import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/infusion_batch_analysis.json')
OUTPUT_SUMMARY = Path('/root/infusion_batch_summary.md')
CATALOG_PATH = Path('/root/therapy_catalog.json')
BAG_PATH = Path('/root/bag_supply_cost.csv')
PAYMENT_PATH = Path('/root/delivery_payment.csv')
OVERRIDE_PATH = Path('/root/patient_overrides.csv')

DELIVERIES_7 = 52
DELIVERIES_14 = 26
DAYS_7 = 7
DAYS_14 = 14
THRESHOLD = 15000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
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
            key = alias_lookup.get(row['therapy_label'].lower())
            if key:
                payments[key] = float(row['payment_per_delivery_per_patient_usd'])
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
    total_7 = round2(sum(row['annual_margin_7_day_usd'] for row in rows))
    total_14 = round2(sum(row['annual_margin_14_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_14_minus_7_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'move_to_14_day' if abs_diff < THRESHOLD else 'keep_7_day'
    return rows, total_7, total_14, total_diff, abs_diff, decision


def load_output():
    assert OUTPUT_JSON.exists()
    return json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))


def test_required_output_files_exist():
    assert OUTPUT_JSON.exists()
    assert OUTPUT_SUMMARY.exists()


def test_schema_and_assumptions():
    data = load_output()
    assert set(data.keys()) == {'assumptions', 'therapies', 'totals', 'recommendation'}
    assert data['assumptions'] == {
        'deliveries_per_year_7_day': DELIVERIES_7,
        'deliveries_per_year_14_day': DELIVERIES_14,
        'days_per_delivery_7_day': DAYS_7,
        'days_per_delivery_14_day': DAYS_14,
        'switch_threshold_usd': THRESHOLD,
        'patient_override_rule': 'highest approved revision per therapy_code',
    }


def test_rows_and_order():
    data = load_output()
    expected_rows, _, _, _, _, _ = load_expected()
    assert [r['therapy_code'] for r in data['therapies']] == [r['therapy_code'] for r in expected_rows]
    for actual, expected in zip(data['therapies'], expected_rows):
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
    _, total_7, total_14, total_diff, abs_diff, decision = load_expected()
    totals = data['totals']
    assert close(totals['total_annual_margin_7_day_usd'], total_7)
    assert close(totals['total_annual_margin_14_day_usd'], total_14)
    assert close(totals['total_annual_margin_difference_14_minus_7_usd'], total_diff)
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
    for value in (data['totals']['total_annual_margin_7_day_usd'], data['totals']['total_annual_margin_14_day_usd'], data['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
