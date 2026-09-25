#!/usr/bin/env python3
import os, re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/neonatal_sepsis_panel_harmonized.csv'
EXPECTED_COLUMNS = ['CRP_mg_L_or_mg_dL', 'Serum_Creat_umol_or_mgdl', 'BUN_mmol_or_mgdl', 'Glucose_mmol_or_mgdl', 'Total_Bili_umol_or_mgdl', 'Direct_Bili_umol_or_mgdl', 'Lactate_mgdl_or_mmol', 'Platelet_Count', 'WBC_Count', 'Hemoglobin_gL_or_gdL', 'Sodium', 'Potassium', 'pCO2_kPa_or_mmHg']
REFERENCE = {'CRP_mg_L_or_mg_dL': {'min': 0, 'max': 50}, 'Serum_Creat_umol_or_mgdl': {'min': 0.2, 'max': 20}, 'BUN_mmol_or_mgdl': {'min': 5, 'max': 200}, 'Glucose_mmol_or_mgdl': {'min': 20, 'max': 800}, 'Total_Bili_umol_or_mgdl': {'min': 0.1, 'max': 30}, 'Direct_Bili_umol_or_mgdl': {'min': 0.0, 'max': 15}, 'Lactate_mgdl_or_mmol': {'min': 0.3, 'max': 20}, 'Platelet_Count': {'min': 10, 'max': 1500}, 'WBC_Count': {'min': 0.5, 'max': 50}, 'Hemoglobin_gL_or_gdL': {'min': 3, 'max': 20}, 'Sodium': {'min': 110, 'max': 170}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'pCO2_kPa_or_mmHg': {'min': 15, 'max': 100}}

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

    def test_columns_exact(self):
        assert self.df is not None
        assert list(self.df.columns) == EXPECTED_COLUMNS

    def test_no_missing(self):
        assert self.df is not None
        assert not self.df.isna().any().any()
        assert not (self.df.applymap(lambda x: str(x).strip() == '')).any().any()

    def test_no_scientific_or_commas(self):
        for col in EXPECTED_COLUMNS:
            for v in self.df[col]:
                s = str(v)
                assert ',' not in s
                assert 'e' not in s.lower()

    def test_two_decimals(self):
        pat = re.compile(r'^-?\d+\.\d{2}$')
        for col in EXPECTED_COLUMNS:
            for v in self.df[col]:
                assert pat.match(str(v)), (col, v)

    @pytest.mark.parametrize('col', EXPECTED_COLUMNS)
    def test_ranges(self, col):
        lo = REFERENCE[col]['min']
        hi = REFERENCE[col]['max']
        bad = [v for v in self.df[col] if not in_range(v, lo, hi)]
        assert not bad, (col, bad[:5])
