import json
from pathlib import Path

OUTPUT_PATH = Path('/root/participant_release_flags.json')
GROUND_TRUTH_PATH = Path(__file__).with_name('ground_truth.json')
PAGE_KEY = 'request_page_number'
REQUIRED_KEYS = ['request_page_number', 'participant_name', 'requested_amount', 'payment_token', 'award_ref', 'reason']


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def json_close(actual, expected, tol=0.01):
    """Compare two JSON structures with numeric tolerance."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False, f"Key mismatch: {set(actual.keys())} vs {set(expected.keys())}"
        for k in expected:
            ok, msg = json_close(actual[k], expected[k], tol)
            if not ok:
                return False, f"At key '{k}': {msg}"
        return True, ""
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False, f"Length mismatch: {len(actual)} vs {len(expected)}"
        for i in range(len(actual)):
            ok, msg = json_close(actual[i], expected[i], tol)
            if not ok:
                return False, f"At index {i}: {msg}"
        return True, ""
    elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if abs(float(actual) - float(expected)) > tol:
            return False, f"Numeric mismatch: {actual} vs {expected} (tol={tol})"
        return True, ""
    elif isinstance(actual, str) and isinstance(expected, str):
        if actual.strip() != expected.strip():
            return False, f"String mismatch: '{actual}' vs '{expected}'"
        return True, ""
    else:
        if actual != expected:
            return False, f"Value mismatch: {actual} vs {expected}"
        return True, ""


def test_output_exists():
    assert OUTPUT_PATH.exists(), f'Missing required output: {OUTPUT_PATH}'


def test_output_matches_ground_truth():
    actual = load_json(OUTPUT_PATH)
    expected = load_json(GROUND_TRUTH_PATH)

    assert isinstance(actual, list), 'Output must be a JSON array.'
    assert [row[PAGE_KEY] for row in actual] == sorted(row[PAGE_KEY] for row in actual), 'Rows must be sorted by page number ascending.'
    for row in actual:
        assert set(row.keys()) == set(REQUIRED_KEYS), f'Unexpected keys in row: {row}'
    ok, msg = json_close(actual, expected)
    assert ok, msg
