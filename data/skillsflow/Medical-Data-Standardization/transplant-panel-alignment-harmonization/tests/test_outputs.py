#!/usr/bin/env python3
import os, re
import pandas as pd
import pytest
OUTPUT_FILE = '/root/transplant_panel_harmonized.csv'
EXPECTED_COLUMNS = ['Tacrolimus', 'Creatinine', 'Magnesium', 'Potassium', 'Glucose', 'Bilirubin_Total', 'Albumin', 'AST', 'ALT', 'Phosphorus']
REFERENCE = {'Tacrolimus': {'min': 1, 'max': 40}, 'Creatinine': {'min': 0.2, 'max': 20}, 'Magnesium': {'min': 0.5, 'max': 10}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'Glucose': {'min': 20, 'max': 800}, 'Bilirubin_Total': {'min': 0.1, 'max': 30}, 'Albumin': {'min': 1.0, 'max': 6.5}, 'AST': {'min': 5, 'max': 2000}, 'ALT': {'min': 5, 'max': 2000}, 'Phosphorus': {'min': 1.0, 'max': 15}}
def ok(v, lo, hi):
    try:
        x = float(v)
        return lo <= x <= hi
    except Exception:
        return False
class TestOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(OUTPUT_FILE, dtype=str) if os.path.exists(OUTPUT_FILE) else None
    def test_file_exists(self):
        assert os.path.exists(OUTPUT_FILE)
    def test_columns(self):
        assert list(self.df.columns) == EXPECTED_COLUMNS
    def test_count(self):
        assert len(self.df) == 8
    def test_format(self):
        pat = re.compile(r'^-?\d+\.\d{2}$')
        for c in EXPECTED_COLUMNS:
            for v in self.df[c]:
                assert pat.match(str(v))
    @pytest.mark.parametrize('c', EXPECTED_COLUMNS)
    def test_ranges(self, c):
        assert all(ok(v, REFERENCE[c]['min'], REFERENCE[c]['max']) for v in self.df[c])
