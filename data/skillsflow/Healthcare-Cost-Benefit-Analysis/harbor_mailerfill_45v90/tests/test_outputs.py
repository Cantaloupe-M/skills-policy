import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/mailer_policy_analysis.json')
OUTPUT_SUMMARY = Path('/root/mailer_policy_summary.md')
COMPOUND_PATH = Path('/root/compound_cost.csv')
MAILER_PATH = Path('/root/mailer_cost.csv')
BASE_PAYMENT_PATH = Path('/root/base_payment.csv')
SERVICE_FEE_PATH = Path('/root/service_fee.csv')

PATIENTS = 150
FILLS_45 = 8
FILLS_90 = 4
DOSES_45 = 45
DOSES_90 = 90
THRESHOLD = 8500


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
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

    rows = []
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
        rows.append({
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
    total_45 = round2(sum(row['annual_margin_45_day_usd'] for row in rows))
    total_90 = round2(sum(row['annual_margin_90_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_90_minus_45_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'shift_to_90_day' if abs_diff < THRESHOLD else 'keep_45_day'
    return rows, total_45, total_90, total_diff, abs_diff, decision


def load_output():
    assert OUTPUT_JSON.exists()
    return json.loads(OUTPUT_JSON.read_text(encoding='utf-8'))


def test_required_output_files_exist():
    assert OUTPUT_JSON.exists()
    assert OUTPUT_SUMMARY.exists()


def test_schema_and_assumptions():
    data = load_output()
    assert set(data.keys()) == {'assumptions', 'medications', 'totals', 'recommendation'}
    assert data['assumptions'] == {
        'patients_per_medication': PATIENTS,
        'fills_per_year_45_day': FILLS_45,
        'fills_per_year_90_day': FILLS_90,
        'doses_per_fill_45_day': DOSES_45,
        'doses_per_fill_90_day': DOSES_90,
        'switch_threshold_usd': THRESHOLD,
    }


def test_rows_and_order():
    data = load_output()
    expected_rows, _, _, _, _, _ = load_expected()
    assert [row['medication'] for row in data['medications']] == [row['medication'] for row in expected_rows]
    for actual, expected in zip(data['medications'], expected_rows):
        assert set(actual.keys()) == set(expected.keys())
        for key, expected_value in expected.items():
            if isinstance(expected_value, str):
                assert actual[key] == expected_value
            else:
                assert close(actual[key], expected_value)


def test_totals_and_decision():
    data = load_output()
    _, total_45, total_90, total_diff, abs_diff, decision = load_expected()
    totals = data['totals']
    assert close(totals['total_annual_margin_45_day_usd'], total_45)
    assert close(totals['total_annual_margin_90_day_usd'], total_90)
    assert close(totals['total_annual_margin_difference_90_minus_45_usd'], total_diff)
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
    for value in (data['totals']['total_annual_margin_45_day_usd'], data['totals']['total_annual_margin_90_day_usd'], data['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
