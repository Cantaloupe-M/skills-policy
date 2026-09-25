"""Tests for 05-datacenter-hardware-registry-diff."""

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

OUTPUT_FILE = Path("/root/hardware_diff_report.json")
DELETED_KEY = "decommissioned_servers"
MODIFIED_KEY = "updated_servers"
ID_PATTERN = re.compile(r"^SVR\d{4}$")
EXPECTED = {
  "decommissioned_servers": [
    "SVR0007",
    "SVR0055",
    "SVR0088",
    "SVR0111"
  ],
  "updated_servers": [
    {
      "id": "SVR0014",
      "field": "CPUCores",
      "old_value": 16,
      "new_value": 32
    },
    {
      "id": "SVR0042",
      "field": "Firmware",
      "old_value": "v3.9.0",
      "new_value": "v4.0.1"
    },
    {
      "id": "SVR0070",
      "field": "Rack",
      "old_value": "R11-U01",
      "new_value": "R21-U18"
    },
    {
      "id": "SVR0099",
      "field": "Role",
      "old_value": "queue",
      "new_value": "analytics"
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
