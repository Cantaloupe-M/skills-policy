import json
import os
from pathlib import Path

GROUND_TRUTH = Path('/tests/expected_output.json')
OUTPUT_FILE = Path('/root/answers.json')

def load_json(path):
    with open(path) as f:
        return json.load(f)


def test_file_exists():
    assert OUTPUT_FILE.is_file()


def test_json_schema():
    """Verify the output JSON has all required keys with correct types."""
    answers = load_json(OUTPUT_FILE)
    
    required_keys = {
        'fund_query': str,
        'quarter': str,
        'matched_manager': str,
        'accession_number': str,
        'aum': (int, float),
        'stock_holdings': (int, float),
        'stock_aum': (int, float),
        'top3_cusips_by_value': list
    }
    
    for key, expected_type in required_keys.items():
        assert key in answers, f"Missing required key: {key}"
        assert isinstance(answers[key], expected_type), \
            f"Key '{key}' has wrong type: expected {expected_type}, got {type(answers[key])}"
    
    # Check top3_cusips is a list of 3 strings
    assert len(answers['top3_cusips_by_value']) == 3, \
        f"top3_cusips_by_value should have 3 items, got {len(answers['top3_cusips_by_value'])}"
    for i, cusip in enumerate(answers['top3_cusips_by_value']):
        assert isinstance(cusip, str), \
            f"top3_cusips_by_value[{i}] should be string, got {type(cusip)}"


def test_manager_matching():
    """Verify the manager matching logic produced a valid result."""
    answers = load_json(OUTPUT_FILE)
    gt = load_json(GROUND_TRUTH)
    
    # Check that matched_manager is not empty
    assert answers['matched_manager'], "matched_manager should not be empty"
    assert answers['accession_number'], "accession_number should not be empty"
    
    # Check against ground truth
    assert answers['matched_manager'] == gt['matched_manager'], \
        f"Manager mismatch: got '{answers['matched_manager']}', expected '{gt['matched_manager']}'"
    assert answers['accession_number'] == gt['accession_number'], \
        f"Accession number mismatch: got '{answers['accession_number']}', expected '{gt['accession_number']}'"


def test_stock_holdings_count():
    """Verify stock holdings count is reasonable."""
    answers = load_json(OUTPUT_FILE)
    gt = load_json(GROUND_TRUTH)
    
    # Allow some tolerance for counting
    count_diff = abs(answers['stock_holdings'] - gt['stock_holdings'])
    assert count_diff <= 5, \
        f"Stock holdings count too different: got {answers['stock_holdings']}, expected {gt['stock_holdings']} (diff={count_diff})"


def test_aum_values():
    """Verify AUM calculations."""
    answers = load_json(OUTPUT_FILE)
    gt = load_json(GROUND_TRUTH)
    
    # Check total AUM
    aum_diff = abs(answers['aum'] - gt['aum'])
    assert aum_diff < 1e-3, \
        f"AUM mismatch: got {answers['aum']}, expected {gt['aum']} (diff={aum_diff})"
    
    # Check stock AUM
    stock_aum_diff = abs(answers['stock_aum'] - gt['stock_aum'])
    assert stock_aum_diff < 1e-3, \
        f"Stock AUM mismatch: got {answers['stock_aum']}, expected {gt['stock_aum']} (diff={stock_aum_diff})"


def test_top3_cusips():
    """Verify top 3 CUSIPs by value."""
    answers = load_json(OUTPUT_FILE)
    gt = load_json(GROUND_TRUTH)
    
    # Check if top CUSIPs match (allowing some tolerance for ties)
    assert answers['top3_cusips_by_value'][0] == gt['top3_cusips_by_value'][0], \
        f"Top CUSIP mismatch: got {answers['top3_cusips_by_value'][0]}, expected {gt['top3_cusips_by_value'][0]}"
    
    # For positions 2 and 3, allow swapping if values are very close
    # (This handles cases where CUSIPs have very similar values)
    assert set(answers['top3_cusips_by_value']) == set(gt['top3_cusips_by_value']), \
        f"Top 3 CUSIPs set mismatch: got {answers['top3_cusips_by_value']}, expected {gt['top3_cusips_by_value']}"


def test_full_output():
    """Final comprehensive check against ground truth."""
    answers = load_json(OUTPUT_FILE)
    gt = load_json(GROUND_TRUTH)
    
    assert answers['fund_query'] == gt['fund_query']
    assert answers['quarter'] == gt['quarter']
    assert answers['matched_manager'] == gt['matched_manager']
    assert answers['accession_number'] == gt['accession_number']
    assert abs(answers['aum'] - gt['aum']) < 1e-3
    assert abs(answers['stock_holdings'] - gt['stock_holdings']) <= 5
    assert abs(answers['stock_aum'] - gt['stock_aum']) < 1e-3
    assert set(answers['top3_cusips_by_value']) == set(gt['top3_cusips_by_value'])
