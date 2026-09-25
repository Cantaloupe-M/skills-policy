#!/usr/bin/env python3
import os, re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/oncology_followup_panel_harmonized.csv'
EXPECTED_COLUMNS = ['LDH', 'Uric_Acid', 'Creatinine', 'Phosphorus', 'Calcium', 'Albumin', 'Glucose', 'Magnesium', 'Potassium', 'WBC_Count']
REFERENCE = {'LDH': {'min': 80, 'max': 2500}, 'Uric_Acid': {'min': 1.0, 'max': 20.0}, 'Creatinine': {'min': 0.2, 'max': 20.0}, 'Phosphorus': {'min': 1.0, 'max': 15.0}, 'Calcium': {'min': 5.0, 'max': 15.0}, 'Albumin': {'min': 1.0, 'max': 6.5}, 'Glucose': {'min': 20, 'max': 800}, 'Magnesium': {'min': 0.5, 'max': 10.0}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'WBC_Count': {'min': 0.5, 'max': 50}}

def in_range(value, lo, hi):
    try:
        x = float(value)
        return lo <= x <= hi
    except Exception:
        return False

class TestOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(OUTPUT_FILE, dtype=str) if os.path.exists(OUTPUT_FILE) else None

    def test_file_exists(self):
        assert os.path.exists(OUTPUT_FILE)

    def test_row_count(self):
        assert self.df is not None
        assert len(self.df) == 6

    def test_columns_exact(self):
        assert list(self.df.columns) == EXPECTED_COLUMNS

    def test_two_decimals(self):
        pat = re.compile(r'^-?\d+\.\d{2}$')
        for col in EXPECTED_COLUMNS:
            for v in self.df[col]:
                assert pat.match(str(v))

    @pytest.mark.parametrize('col', EXPECTED_COLUMNS)
    def test_ranges(self, col):
        lo = REFERENCE[col]['min']
        hi = REFERENCE[col]['max']
        assert all(in_range(v, lo, hi) for v in self.df[col])
