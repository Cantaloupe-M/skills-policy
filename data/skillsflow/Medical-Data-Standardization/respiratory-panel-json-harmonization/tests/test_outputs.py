#!/usr/bin/env python3
import os, re
import pandas as pd
import pytest
OUTPUT_FILE = '/root/respiratory_panel_harmonized.csv'
EXPECTED_COLUMNS = ['pH_Arterial', 'pCO2_Arterial', 'pO2_Arterial', 'Bicarbonate', 'Lactate', 'Glucose', 'Magnesium']
REFERENCE = {'pH_Arterial': {'min': 6.8, 'max': 7.8}, 'pCO2_Arterial': {'min': 15, 'max': 100}, 'pO2_Arterial': {'min': 30, 'max': 500}, 'Bicarbonate': {'min': 5, 'max': 40}, 'Lactate': {'min': 0.3, 'max': 20}, 'Glucose': {'min': 20, 'max': 800}, 'Magnesium': {'min': 0.5, 'max': 10}}
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
    def test_exists(self):
        assert os.path.exists(OUTPUT_FILE)
    def test_columns(self):
        assert list(self.df.columns) == EXPECTED_COLUMNS
    def test_count(self):
        assert len(self.df) == 7
    def test_format(self):
        pat = re.compile(r'^-?\d+\.\d{2}$')
        for c in EXPECTED_COLUMNS:
            for v in self.df[c]:
                assert pat.match(str(v))
    @pytest.mark.parametrize('c', EXPECTED_COLUMNS)
    def test_ranges(self, c):
        assert all(ok(v, REFERENCE[c]['min'], REFERENCE[c]['max']) for v in self.df[c])
