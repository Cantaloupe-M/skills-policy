"""Tests for 07-shipping-container-manifest-diff."""

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

OUTPUT_FILE = Path("/root/container_diff_report.json")
DELETED_KEY = "missing_containers"
MODIFIED_KEY = "changed_containers"
ID_PATTERN = re.compile(r"^CNT\d{4}$")
EXPECTED = {
  "missing_containers": [
    "CNT0009",
    "CNT0063",
    "CNT0105",
    "CNT0136"
  ],
  "changed_containers": [
    {
      "id": "CNT0018",
      "field": "WeightTons",
      "old_value": 45.8,
      "new_value": 44.2
    },
    {
      "id": "CNT0040",
      "field": "Status",
      "old_value": "Loaded",
      "new_value": "InspectionHold"
    },
    {
      "id": "CNT0077",
      "field": "Route",
      "old_value": "PUS->SEA",
      "new_value": "DXB->MUM"
    },
    {
      "id": "CNT0110",
      "field": "CargoType",
      "old_value": "AutoParts",
      "new_value": "MedicalSupplies"
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
