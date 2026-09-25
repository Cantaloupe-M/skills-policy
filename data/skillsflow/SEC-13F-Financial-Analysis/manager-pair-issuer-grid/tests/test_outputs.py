import json
from pathlib import Path
GROUND_TRUTH = Path('/tests/expected_output.json')
OUTPUT_FILE = Path('/root/answers.json')

def load_json(path):
    with open(path) as f:
        return json.load(f)

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

def test_file_exists():
    assert OUTPUT_FILE.is_file()


def test_answers():
    actual = load_json(OUTPUT_FILE)
    expected = load_json(GROUND_TRUTH)
    ok, msg = json_close(actual, expected)
    assert ok, msg
