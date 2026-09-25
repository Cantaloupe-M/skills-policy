"""Tests for 06-hospital-medication-reconciliation."""

import json
import re
from pathlib import Path

import pytest


def diff_close(actual, expected, tol=0.01):
    """Compare diff JSON with numeric tolerance for old_value/new_value."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False, f"Key mismatch"
        for k in expected:
            ok, msg = diff_close(actual[k], expected[k], tol)
            if not ok:
                return False, f"At '{k}': {msg}"
        return True, ""
    elif isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return False, f"Length mismatch: {len(actual)} vs {len(expected)}"
        for i in range(len(actual)):
            ok, msg = diff_close(actual[i], expected[i], tol)
            if not ok:
                return False, f"At index {i}: {msg}"
        return True, ""
    elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if abs(float(actual) - float(expected)) > tol:
            return False, f"Numeric: {actual} vs {expected}"
        return True, ""
    elif isinstance(actual, str) and isinstance(expected, str):
        if actual.strip() != expected.strip():
            return False, f"Text: '{actual}' vs '{expected}'"
        return True, ""
    else:
        if actual != expected:
            return False, f"Value: {actual} vs {expected}"
        return True, ""

OUTPUT_FILE = Path("/root/medication_diff_report.json")
DELETED_KEY = "deleted_medications"
MODIFIED_KEY = "modified_medications"
ID_PATTERN = re.compile(r"^MED\d{5}$")
EXPECTED = {
  "deleted_medications": [
    "MED00012",
    "MED00044",
    "MED00087",
    "MED00103"
  ],
  "modified_medications": [
    {
      "id": "MED00017",
      "field": "StockUnits",
      "old_value": 213,
      "new_value": 195
    },
    {
      "id": "MED00033",
      "field": "Form",
      "old_value": "Capsule",
      "new_value": "Liquid"
    },
    {
      "id": "MED00058",
      "field": "ReorderLevel",
      "old_value": 28,
      "new_value": 38
    },
    {
      "id": "MED00091",
      "field": "Medication",
      "old_value": "Lisinopril",
      "new_value": "Metformin XR"
    }
  ]
}

def load_output():
    assert OUTPUT_FILE.exists(), f"Output file not found at {OUTPUT_FILE}"
    try:
        return json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"Output is not valid JSON: {exc}")

def test_output_shape():
    data = load_output()
    assert set(data.keys()) == {DELETED_KEY, MODIFIED_KEY}
    assert isinstance(data[DELETED_KEY], list)
    assert isinstance(data[MODIFIED_KEY], list)

def test_deleted_ids_sorted_and_exact():
    data = load_output()
    assert data[DELETED_KEY] == sorted(data[DELETED_KEY])
    assert set(data[DELETED_KEY]) == set(EXPECTED[DELETED_KEY]), "Deleted IDs must match"
    for item_id in data[DELETED_KEY]:
        assert ID_PATTERN.fullmatch(item_id), f"Invalid ID format: {item_id}"

def test_modified_entries_schema_and_sort():
    data = load_output()
    expected_keys = {"id", "field", "old_value", "new_value"}
    assert data[MODIFIED_KEY] == sorted(data[MODIFIED_KEY], key=lambda item: (item["id"], item["field"]))
    for item in data[MODIFIED_KEY]:
        assert set(item.keys()) == expected_keys
        assert ID_PATTERN.fullmatch(item["id"]), "Invalid ID format: " + item["id"]

def test_modified_entries_exact_match():
    data = load_output()
    ok, msg = diff_close(data[MODIFIED_KEY], EXPECTED[MODIFIED_KEY])
    assert ok, msg
