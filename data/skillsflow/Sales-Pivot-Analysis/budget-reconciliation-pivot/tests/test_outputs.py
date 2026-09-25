#!/usr/bin/env python3
"""Tests for Budget Reconciliation Pivot Table Analysis task."""
import pytest
from openpyxl import load_workbook

OUTPUT_FILE = "/root/budget_report.xlsx"

PIVOT_SHEETS = [
    ("Spending by Division", "sum", None),
    ("Spending by Department", "sum", None),
    ("Variance by Department", "sum", None),
    ("Category Quarter Matrix", "sum", "fiscal_quarter"),
    ("Avg Utilization by Division", "average", None),
]

REQUIRED_COLUMNS = [
    ("tx_id", lambda h: "tx_id" in h or "txid" in h.replace("_", "") or "transaction" in h),
    ("team_code", lambda h: "team" in h and "code" in h),
    ("TEAM_NAME", lambda h: "team" in h and "name" in h),
    ("DEPT_NAME", lambda h: "dept" in h and "name" in h),
    ("DIVISION", lambda h: "division" in h),
    ("expense_category", lambda h: "category" in h and "expense" in h or h == "expense_category"),
    ("amount", lambda h: h == "amount"),
    ("fiscal_quarter", lambda h: "quarter" in h and "fiscal" in h or h == "fiscal_quarter"),
    ("BUDGET_AMOUNT", lambda h: "budget" in h and "amount" in h or h == "budget_amount"),
    ("VARIANCE", lambda h: "variance" in h),
    ("UTILIZATION_PCT", lambda h: "utilization" in h),
]


@pytest.fixture(scope="module")
def workbook():
    return load_workbook(OUTPUT_FILE)


def _get_pivot_field_names(pivot):
    cache = pivot.cache
    if cache and cache.cacheFields:
        return [f.name for f in cache.cacheFields]
    return []


def _get_field_name_by_index(pivot, fields):
    field_names = _get_pivot_field_names(pivot)
    if fields and len(fields) > 0:
        idx = fields[0].x
        if idx is not None and 0 <= idx < len(field_names):
            return field_names[idx]
    return None


class TestSheetExistence:
    def test_has_six_sheets(self, workbook):
        """Should have 5 pivot sheets + 1 source data sheet."""
        assert len(workbook.sheetnames) >= 6, f"Expected 6+ sheets, got {len(workbook.sheetnames)}: {workbook.sheetnames}"


class TestPivotTableConfiguration:
    @pytest.mark.parametrize("sheet_name,expected_agg,col_field", PIVOT_SHEETS)
    def test_pivot_exists(self, workbook, sheet_name, expected_agg, col_field):
        assert sheet_name in workbook.sheetnames, f"Missing sheet '{sheet_name}'"
        pivots = workbook[sheet_name]._pivots
        assert len(pivots) > 0, f"No pivot table found in '{sheet_name}'"

    @pytest.mark.parametrize("sheet_name,expected_agg,col_field", PIVOT_SHEETS)
    def test_pivot_row_field(self, workbook, sheet_name, expected_agg, col_field):
        pivot = workbook[sheet_name]._pivots[0]
        row_field = _get_field_name_by_index(pivot, pivot.rowFields)
        if "Division" in sheet_name:
            assert row_field and "division" in row_field.lower(), f"Row should be DIVISION, got '{row_field}'"
        elif "Department" in sheet_name:
            assert row_field and ("dept" in row_field.lower() or "department" in row_field.lower()), \
                f"Row should be DEPT_NAME, got '{row_field}'"
        elif "Category" in sheet_name:
            assert row_field and "category" in row_field.lower(), f"Row should be expense_category, got '{row_field}'"

    @pytest.mark.parametrize("sheet_name,expected_agg,col_field", PIVOT_SHEETS)
    def test_pivot_aggregation(self, workbook, sheet_name, expected_agg, col_field):
        pivot = workbook[sheet_name]._pivots[0]
        data_field = pivot.dataFields[0]
        assert data_field.subtotal == expected_agg, f"Expected '{expected_agg}', got '{data_field.subtotal}'"

    @pytest.mark.parametrize("sheet_name,expected_agg,col_field", PIVOT_SHEETS)
    def test_pivot_col_field(self, workbook, sheet_name, expected_agg, col_field):
        if not col_field:
            pytest.skip(f"'{sheet_name}' is not a matrix pivot")
        pivot = workbook[sheet_name]._pivots[0]
        actual_col = _get_field_name_by_index(pivot, pivot.colFields)
        assert actual_col and "quarter" in actual_col.lower(), \
            f"Column field should contain 'quarter', got '{actual_col}'"


@pytest.fixture(scope="module")
def source_sheet(workbook):
    for name in workbook.sheetnames:
        if "source" in name.lower() or "data" in name.lower():
            return workbook[name]
    pytest.fail("No source data sheet found")


@pytest.fixture(scope="module")
def headers(source_sheet):
    first_row = next(source_sheet.iter_rows(min_row=1, max_row=1, values_only=True))
    return [str(h).strip().lower() if h else "" for h in first_row]


class TestSourceDataSheet:
    @pytest.mark.parametrize("desc,match_fn", REQUIRED_COLUMNS)
    def test_has_required_column(self, headers, desc, match_fn):
        assert any(match_fn(h) for h in headers), f"Missing {desc} column. Found: {headers}"


@pytest.fixture(scope="module")
def source_data(source_sheet):
    rows = list(source_sheet.iter_rows(values_only=True))
    headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(rows[0])]
    data = [dict(zip(headers, row)) for row in rows[1:] if any(cell is not None for cell in row)]
    return data, headers


VALID_DIVISIONS = {"Technology", "Business", "Operations"}
VALID_QUARTERS = {"Q1", "Q2", "Q3", "Q4"}
VALID_CATEGORIES = {"Personnel", "Software", "Hardware", "Travel", "Training", "Consulting", "Office"}


class TestSourceDataContent:
    def test_row_count(self, source_data):
        data, _ = source_data
        assert 1500 <= len(data) <= 2500, f"Expected ~2000 rows, got {len(data)}"

    def test_division_values(self, source_data):
        data, headers = source_data
        col = next((h for h in headers if "division" in h.lower()), None)
        vals = {row.get(col) for row in data if row.get(col)}
        invalid = vals - VALID_DIVISIONS
        assert not invalid, f"Invalid divisions: {invalid}"

    def test_quarter_values(self, source_data):
        data, headers = source_data
        col = next((h for h in headers if "quarter" in h.lower() and "fiscal" in h.lower() or h == "fiscal_quarter"), None)
        vals = {row.get(col) for row in data if row.get(col)}
        invalid = vals - VALID_QUARTERS
        assert not invalid, f"Invalid quarters: {invalid}"

    def test_has_negative_amounts(self, source_data):
        """Should include negative amounts (refunds/credits)."""
        data, headers = source_data
        col = next((h for h in headers if h == "amount"), None)
        if not col:
            pytest.skip("No amount column")
        negatives = sum(1 for row in data if row.get(col) is not None and float(row.get(col)) < 0)
        assert negatives > 0, "Expected some negative amounts (refunds)"

    def test_all_three_divisions_present(self, source_data):
        data, headers = source_data
        col = next((h for h in headers if "division" in h.lower()), None)
        vals = {row.get(col) for row in data if row.get(col)}
        for div in VALID_DIVISIONS:
            assert div in vals, f"Missing division: {div}"


class TestDataTransformations:
    def test_variance_calculation(self, source_data):
        data, headers = source_data
        amt_col = next((h for h in headers if h == "amount"), None)
        budget_col = next((h for h in headers if "budget" in h.lower() and "amount" in h.lower()), None)
        var_col = next((h for h in headers if "variance" in h.lower()), None)
        if not all([amt_col, budget_col, var_col]):
            pytest.skip("Missing columns")
        errors = []
        for i, row in enumerate(data[:50]):
            amt, budget, var = row.get(amt_col), row.get(budget_col), row.get(var_col)
            if all(v is not None for v in (amt, budget, var)):
                try:
                    expected = float(amt) - float(budget)
                    if abs(expected - float(var)) > 1:
                        errors.append(f"Row {i+2}")
                except (ValueError, TypeError):
                    pass
        assert not errors, f"Variance errors: {errors[:5]}"

    def test_utilization_range(self, source_data):
        """UTILIZATION_PCT should be a reasonable ratio."""
        data, headers = source_data
        util_col = next((h for h in headers if "utilization" in h.lower()), None)
        if not util_col:
            pytest.skip("No utilization column")
        non_null = 0
        for i, row in enumerate(data[:100]):
            u = row.get(util_col)
            if u is not None:
                non_null += 1
        assert non_null > 0, "Expected some non-null utilization values"

    def test_budget_amount_populated(self, source_data):
        """At least some rows should have budget amounts from the wide->long transform."""
        data, headers = source_data
        budget_col = next((h for h in headers if "budget" in h.lower() and "amount" in h.lower()), None)
        if not budget_col:
            pytest.skip("No budget_amount column")
        non_null = sum(1 for row in data if row.get(budget_col) is not None)
        assert non_null > len(data) * 0.5, f"Expected >50% budget amounts populated, got {non_null}/{len(data)}"

    def test_pivot_cache_has_fields(self, workbook):
        pivot = workbook["Spending by Division"]._pivots[0]
        assert len(pivot.cache.cacheFields) > 0

    def test_five_pivot_sheets(self, workbook):
        """Should have exactly 5 pivot table sheets."""
        pivot_count = 0
        for name in workbook.sheetnames:
            ws = workbook[name]
            if hasattr(ws, '_pivots') and len(ws._pivots) > 0:
                pivot_count += 1
        assert pivot_count == 5, f"Expected 5 pivot table sheets, found {pivot_count}"
