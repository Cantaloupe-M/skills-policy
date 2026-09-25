#!/usr/bin/env python3
"""Tests for Employee Compensation Pivot Table Analysis task."""
import pytest
from openpyxl import load_workbook

OUTPUT_FILE = "/root/compensation_report.xlsx"

PIVOT_SHEETS = [
    ("Avg Salary by Department", "average", None),
    ("Headcount by Location", "count", None),
    ("Total Compensation by Title", "sum", None),
    ("Department Location Matrix", "average", "job_title"),
]

REQUIRED_COLUMNS = [
    ("emp_id", lambda h: "emp" in h and "id" in h),
    ("full_name", lambda h: "name" in h),
    ("DEPT_NAME", lambda h: "dept" in h and "name" in h),
    ("LOCATION", lambda h: "location" in h),
    ("job_title", lambda h: "title" in h or "job" in h),
    ("base_salary", lambda h: "salary" in h and "base" in h or h == "base_salary"),
    ("TOTAL_COMP", lambda h: "total" in h and "comp" in h),
    ("EXPERIENCE_BAND", lambda h: "experience" in h and "band" in h or h == "experience_band"),
    ("COMP_RATIO", lambda h: "comp" in h and "ratio" in h or h == "comp_ratio"),
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
        if "Department" in sheet_name:
            assert row_field and ("dept" in row_field.lower() or "department" in row_field.lower()), \
                f"Row field should be DEPT_NAME, got '{row_field}'"
        elif "Location" in sheet_name:
            assert row_field and "location" in row_field.lower(), f"Row field should be LOCATION, got '{row_field}'"
        elif "Title" in sheet_name:
            assert row_field and ("title" in row_field.lower() or "job" in row_field.lower()), \
                f"Row field should be job_title, got '{row_field}'"

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
        assert actual_col and ("title" in actual_col.lower() or "job" in actual_col.lower()), \
            f"Column field should be job_title, got '{actual_col}'"


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


VALID_LOCATIONS = {"San Francisco", "New York", "Chicago", "Dallas"}
VALID_EXPERIENCE_BANDS = {"Junior", "Mid", "Senior", "Veteran"}
VALID_TITLES = {"Junior", "Mid", "Senior", "Lead", "Principal", "Director"}


class TestSourceDataContent:
    def test_row_count(self, source_data):
        data, _ = source_data
        assert 300 <= len(data) <= 500, f"Expected ~400 rows, got {len(data)}"

    def test_location_values(self, source_data):
        data, headers = source_data
        loc_col = next((h for h in headers if "location" in h.lower()), None)
        locs = {row.get(loc_col) for row in data if row.get(loc_col)}
        invalid = locs - VALID_LOCATIONS
        assert not invalid, f"Invalid locations: {invalid}"

    def test_experience_band_values(self, source_data):
        data, headers = source_data
        band_col = next((h for h in headers if "experience" in h.lower() and "band" in h.lower()), None)
        if band_col:
            bands = {row.get(band_col) for row in data if row.get(band_col)}
            invalid = bands - VALID_EXPERIENCE_BANDS
            assert not invalid, f"Invalid experience bands: {invalid}"


class TestDataTransformations:
    def test_total_comp_calculation(self, source_data):
        data, headers = source_data
        salary_col = next((h for h in headers if "salary" in h.lower() and "base" in h.lower()), None)
        bonus_col = next((h for h in headers if "bonus" in h.lower()), None)
        comp_col = next((h for h in headers if "total" in h.lower() and "comp" in h.lower()), None)
        errors = []
        for i, row in enumerate(data[:50]):
            salary, bonus, comp = row.get(salary_col), row.get(bonus_col), row.get(comp_col)
            if all(v is not None for v in (salary, bonus, comp)):
                try:
                    if abs(float(salary) + float(bonus) - float(comp)) > 1:
                        errors.append(f"Row {i+2}")
                except (ValueError, TypeError):
                    pass
        assert not errors, f"Total comp errors: {errors[:5]}"

    def test_experience_band_correctness(self, source_data):
        data, headers = source_data
        yos_col = next((h for h in headers if "years" in h.lower() or "service" in h.lower()), None)
        band_col = next((h for h in headers if "experience" in h.lower() and "band" in h.lower()), None)
        if not all([yos_col, band_col]):
            pytest.skip("Missing columns")
        errors = []
        for i, row in enumerate(data[:100]):
            yos, band = row.get(yos_col), row.get(band_col)
            if yos is not None and band is not None:
                try:
                    y = float(yos)
                    if y < 3:
                        expected = "Junior"
                    elif y < 8:
                        expected = "Mid"
                    elif y < 15:
                        expected = "Senior"
                    else:
                        expected = "Veteran"
                    if band != expected:
                        errors.append(f"Row {i+2}: yos={y}, got '{band}', expected '{expected}'")
                except (ValueError, TypeError):
                    pass
        assert not errors, f"Experience band errors:\n" + "\n".join(errors[:5])

    def test_comp_ratio_range(self, source_data):
        data, headers = source_data
        ratio_col = next((h for h in headers if "comp" in h.lower() and "ratio" in h.lower()), None)
        if not ratio_col:
            pytest.skip("No comp_ratio column found")
        for i, row in enumerate(data[:50]):
            r = row.get(ratio_col)
            if r is not None:
                try:
                    val = float(r)
                    assert 0 < val < 1, f"Row {i+2}: comp_ratio {val} should be between 0 and 1"
                except (ValueError, TypeError):
                    pass

    def test_pivot_cache_has_fields(self, workbook):
        pivot = workbook["Avg Salary by Department"]._pivots[0]
        assert len(pivot.cache.cacheFields) > 0
