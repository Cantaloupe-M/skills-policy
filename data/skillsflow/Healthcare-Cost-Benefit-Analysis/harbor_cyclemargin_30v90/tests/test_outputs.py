import csv
import json
from pathlib import Path

OUTPUT_JSON = Path('/root/cycle_margin_analysis.json')
OUTPUT_SUMMARY = Path('/root/cycle_margin_summary.md')
ACQ_PATH = Path('/root/acquisition_cost.csv')
PACK_PATH = Path('/root/packaging_cost.csv')
REIMB_PATH = Path('/root/reimbursement.csv')

PATIENTS = 240
FILLS_30 = 12
FILLS_90 = 4
DOSES_30 = 60
DOSES_90 = 180
THRESHOLD = 12000


def round2(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def load_expected():
    acq = []
    with ACQ_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            acq.append({'therapy': row['therapy'], 'price': float(row['price_per_1000_doses_usd']), 'canister': int(row['canister_size_units'])})
    pack = {}
    with PACK_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            pack[int(row['canister_size_units'])] = float(row['packaging_cost_usd'])
    reimb = {}
    with REIMB_PATH.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            reimb[row['therapy']] = float(row['reimbursement_per_fill_240_patients_usd'])
    rows = []
    for row in sorted(acq, key=lambda x: x['therapy']):
        therapy = row['therapy']
        price = row['price']
        canister = row['canister']
        packaging = pack[canister]
        reimbursement = reimb[therapy]
        annual_drug_cost_30 = price * (PATIENTS * DOSES_30 * FILLS_30 / 1000.0)
        annual_drug_cost_90 = price * (PATIENTS * DOSES_90 * FILLS_90 / 1000.0)
        annual_packaging_cost_30 = packaging * PATIENTS * FILLS_30
        annual_packaging_cost_90 = packaging * PATIENTS * FILLS_90
        annual_reimbursement_30 = reimbursement * FILLS_30
        annual_reimbursement_90 = reimbursement * FILLS_90
        annual_margin_30 = annual_reimbursement_30 - annual_drug_cost_30 - annual_packaging_cost_30
        annual_margin_90 = annual_reimbursement_90 - annual_drug_cost_90 - annual_packaging_cost_90
        diff = annual_margin_90 - annual_margin_30
        rows.append({
            'therapy': therapy,
            'price_per_1000_doses_usd': round2(price),
            'canister_size_units': canister,
            'packaging_cost_usd': round2(packaging),
            'reimbursement_per_fill_240_patients_usd': round2(reimbursement),
            'annual_drug_cost_30_day_usd': round2(annual_drug_cost_30),
            'annual_drug_cost_90_day_usd': round2(annual_drug_cost_90),
            'annual_packaging_cost_30_day_usd': round2(annual_packaging_cost_30),
            'annual_packaging_cost_90_day_usd': round2(annual_packaging_cost_90),
            'annual_reimbursement_30_day_usd': round2(annual_reimbursement_30),
            'annual_reimbursement_90_day_usd': round2(annual_reimbursement_90),
            'annual_margin_30_day_usd': round2(annual_margin_30),
            'annual_margin_90_day_usd': round2(annual_margin_90),
            'annual_margin_difference_90_minus_30_usd': round2(diff),
        })
    total_30 = round2(sum(row['annual_margin_30_day_usd'] for row in rows))
    total_90 = round2(sum(row['annual_margin_90_day_usd'] for row in rows))
    total_diff = round2(sum(row['annual_margin_difference_90_minus_30_usd'] for row in rows))
    abs_diff = round2(abs(total_diff))
    decision = 'adopt_90_day' if abs_diff < THRESHOLD else 'keep_30_day'
    return rows, total_30, total_90, total_diff, abs_diff, decision


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
        'patients_per_therapy': PATIENTS,
        'fills_per_year_30_day': FILLS_30,
        'fills_per_year_90_day': FILLS_90,
        'doses_per_fill_30_day': DOSES_30,
        'doses_per_fill_90_day': DOSES_90,
        'switch_threshold_usd': THRESHOLD,
    }


def test_rows_and_order():
    data = load_output()
    expected_rows, _, _, _, _, _ = load_expected()
    assert [r['therapy'] for r in data['therapies']] == [r['therapy'] for r in expected_rows]
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
    _, total_30, total_90, total_diff, abs_diff, decision = load_expected()
    totals = data['totals']
    assert close(totals['total_annual_margin_30_day_usd'], total_30)
    assert close(totals['total_annual_margin_90_day_usd'], total_90)
    assert close(totals['total_annual_margin_difference_90_minus_30_usd'], total_diff)
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
    for value in (data['totals']['total_annual_margin_30_day_usd'], data['totals']['total_annual_margin_90_day_usd'], data['totals']['absolute_total_margin_difference_usd']):
        assert f'{value:,.2f}' in text
