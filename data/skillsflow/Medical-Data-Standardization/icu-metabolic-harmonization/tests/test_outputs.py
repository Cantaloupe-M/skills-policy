#!/usr/bin/env python3
import os
import re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/icu_metabolic_panel_harmonized.csv'
MAIN_FILE = '/root/environment/data/metabolic_main.csv'
EXTRA_FILE = '/root/environment/data/metabolic_additional.csv'
EXPECTED_COLUMNS = ['Sodium', 'Potassium', 'Chloride', 'Bicarbonate', 'Glucose', 'Lactate', 'Calcium', 'Magnesium', 'Phosphorus', 'Creatinine', 'BUN', 'Anion_Gap', 'Osmolality', 'Beta_Hydroxybutyrate', 'pH_Arterial', 'pCO2_Arterial']
REFERENCE = {'Sodium': {'min': 110, 'max': 170}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'Chloride': {'min': 70, 'max': 140}, 'Bicarbonate': {'min': 5, 'max': 40}, 'Glucose': {'min': 20, 'max': 800}, 'Lactate': {'min': 0.3, 'max': 20}, 'Calcium': {'min': 5.0, 'max': 15.0}, 'Magnesium': {'min': 0.5, 'max': 10.0}, 'Phosphorus': {'min': 1.0, 'max': 15.0}, 'Creatinine': {'min': 0.2, 'max': 20}, 'BUN': {'min': 5, 'max': 200}, 'Anion_Gap': {'min': 0, 'max': 40}, 'Osmolality': {'min': 200, 'max': 450}, 'Beta_Hydroxybutyrate': {'min': 0, 'max': 15}, 'pH_Arterial': {'min': 6.8, 'max': 7.8}, 'pCO2_Arterial': {'min': 15, 'max': 100}}
SPECS = {'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Chloride': ('same', 1.0, 70, 140), 'Bicarbonate': ('same', 1.0, 5, 40), 'Glucose': ('single', 0.0555, 20, 800), 'Lactate': ('single-reverse', 9.01, 0.3, 20), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Magnesium': ('single', 0.411, 0.5, 10.0), 'Phosphorus': ('single', 0.323, 1.0, 15.0), 'Creatinine': ('single', 88.4, 0.2, 20), 'BUN': ('single', 0.357, 5, 200), 'Anion_Gap': ('same', 1.0, 0, 40), 'Osmolality': ('same', 1.0, 200, 450), 'Beta_Hydroxybutyrate': ('single', 10.4, 0, 15), 'pH_Arterial': ('same', 1.0, 6.8, 7.8), 'pCO2_Arterial': ('single', 0.133, 15, 100)}
ANCHOR_ROW_INDEXES = [0, 1, 3]
ANCHOR_COLUMNS = ['Glucose', 'Lactate', 'Calcium', 'Creatinine', 'BUN', 'pCO2_Arterial']


def in_range(value, lo, hi):
    try:
        x = float(value)
        return lo <= x <= hi
    except Exception:
        return False


def parse_value(value):
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s == '' or s.lower() == 'nan':
        return None
    if ',' in s:
        s = s.replace(',', '.')
    return float(s)


def normalize_frame(df, specs, id_column=None):
    numeric_cols = [c for c in df.columns if c != id_column]
    missing_mask = df[numeric_cols].map(lambda x: pd.isna(x) or str(x).strip() == '' or str(x).strip().lower() == 'nan').any(axis=1)
    df = df.loc[~missing_mask].copy()
    for col in numeric_cols:
        mode, factor, lo, hi = specs[col]
        df[col] = df[col].apply(parse_value)

        def convert(v):
            if v is None:
                return None
            if lo <= v <= hi:
                return v
            if mode == 'single':
                c = v / factor
                return c if lo <= c <= hi else v
            if mode == 'single-reverse':
                c = v * factor
                return c if lo <= c <= hi else v
            return v

        df[col] = df[col].apply(convert)
        df[col] = df[col].apply(lambda x: f"{x:.2f}")
    return df


def build_expected():
    main = pd.read_csv(MAIN_FILE, dtype=str)
    extra = pd.read_csv(EXTRA_FILE, dtype=str)
    main_clean = normalize_frame(main, {k: SPECS[k] for k in main.columns if k != 'record_id'}, id_column='record_id')
    extra_clean = normalize_frame(extra, {k: SPECS[k] for k in extra.columns if k != 'record_id'}, id_column='record_id')
    merged = main_clean.merge(extra_clean, on='record_id', how='inner')
    return merged[EXPECTED_COLUMNS].reset_index(drop=True)


class TestOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(OUTPUT_FILE, dtype=str) if os.path.exists(OUTPUT_FILE) else None
        self.expected = build_expected()

    def test_file_exists(self):
        assert os.path.exists(OUTPUT_FILE)

    def test_columns_exact(self):
        assert self.df is not None
        assert list(self.df.columns) == EXPECTED_COLUMNS

    def test_no_missing(self):
        assert self.df is not None
        assert not self.df.isna().any().any()
        assert not (self.df.map(lambda x: str(x).strip() == '')).any().any()

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

    def test_row_count(self):
        assert len(self.df) == len(self.expected)

    @pytest.mark.parametrize('row_idx', ANCHOR_ROW_INDEXES)
    @pytest.mark.parametrize('col', ANCHOR_COLUMNS)
    def test_anchor_values(self, row_idx, col):
        actual = float(self.df.iloc[row_idx][col])
        expected = float(self.expected.iloc[row_idx][col])
        assert abs(actual - expected) <= max(0.01, abs(expected) * 0.001), (row_idx, col, actual, expected)
