import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/syncpack_analysis.json')
OUTPUT_SUMMARY = Path('/root/syncpack_summary.md')
INGREDIENT_PATH = Path('/root/ingredient_cost.csv')
CARD_PATH = Path('/root/card_cost.csv')
REIMB_PATH = Path('/root/reimbursement.csv')

PATIENTS = 180
FILLS_28 = 12
FILLS_56 = 6
CAPS_28 = 56
CAPS_56 = 112
THRESHOLD = 9000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
    ingredient_rows = []
    with INGREDIENT_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            ingredient_rows.append({'medication': row['medication'], 'price': float(row['price_per_1000_capsules_usd']), 'cards': int(row['blister_card_count'])})
    card_costs = {}
    with CARD_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            card_costs[int(row['blister_card_count'])] = float(row['card_cost_usd'])
    reimbursements = {}
    with REIMB_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            reimbursements[row['medication']] = float(row['reimbursement_per_cycle_180_patients_usd'])
    rows = []
    for row in sorted(ingredient_rows, key=lambda x: x['medication']):
        medication = row['medication']
        price = row['price']
        cards = row['cards']
        card_cost = card_costs[cards]
        reimbursement = reimbursements[medication]
        annual_drug_cost_28 = price * (PATIENTS * CAPS_28 * FILLS_28 / 1000.0)
        annual_drug_cost_56 = price * (PATIENTS * CAPS_56 * FILLS_56 / 1000.0)
        annual_packaging_cost_28 = card_cost * PATIENTS * FILLS_28
        annual_packaging_cost_56 = card_cost * PATIENTS * FILLS_56
        annual_reimbursement_28 = reimbursement * FILLS_28
        annual_reimbursement_56 = reimbursement * FILLS_56
        annual_margin_28 = annual_reimbursement_28 - annual_drug_cost_28 - annual_packaging_cost_28
        annual_margin_56 = annual_reimbursement_56 - annual_drug_cost_56 - annual_packaging_cost_56
        diff = annual_margin_56 - annual_margin_28
        rows.append({
            'medication': medication,
            'price_per_1000_capsules_usd': round2(price),
            'blister_card_count': cards,
            'card_cost_usd': round2(card_cost),
            'reimbursement_per_cycle_180_patients_usd': round2(reimbursement),
            'annual_drug_cost_28_day_usd': round2(annual_drug_cost_28),
            'annual_drug_cost_56_day_usd': round2(annual_drug_cost_56),
            'annual_packaging_cost_28_day_usd': round2(annual_packaging_cost_28),
            'annual_packaging_cost_56_day_usd': round2(annual_packaging_cost_56),
            'annual_reimbursement_28_day_usd': round2(annual_reimbursement_28),
            'annual_reimbursement_56_day_usd': round2(annual_reimbursement_56),
            'annual_margin_28_day_usd': round2(annual_margin_28),
            'annual_margin_56_day_usd': round2(annual_margin_56),
            'annual_margin_difference_56_minus_28_usd': round2(diff),
        })
    total_28 = round2(sum(row['annual_margin_28_day_usd'] for row in rows))
    total_56 = round2(sum(row['annual_margin_56_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_56_minus_28_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'convert_to_56_day' if abs_diff < THRESHOLD else 'keep_28_day'
    return rows, total_28, total_56, total_diff, abs_diff, decision


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
        'fills_per_year_28_day': FILLS_28,
        'fills_per_year_56_day': FILLS_56,
        'capsules_per_fill_28_day': CAPS_28,
        'capsules_per_fill_56_day': CAPS_56,
        'switch_threshold_usd': THRESHOLD,
    }


def test_rows_and_order():
    data = load_output()
    expected_rows, _, _, _, _, _ = load_expected()
    assert [r['medication'] for r in data['medications']] == [r['medication'] for r in expected_rows]
    for actual, expected in zip(data['medications'], expected_rows):
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
    _, total_28, total_56, total_diff, abs_diff, decision = load_expected()
    totals = data['totals']
    assert close(totals['total_annual_margin_28_day_usd'], total_28)
    assert close(totals['total_annual_margin_56_day_usd'], total_56)
    assert close(totals['total_annual_margin_difference_56_minus_28_usd'], total_diff)
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
    for value in (data['totals']['total_annual_margin_28_day_usd'], data['totals']['total_annual_margin_56_day_usd'], data['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
