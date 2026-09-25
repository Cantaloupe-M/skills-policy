#!/usr/bin/env python3
import os
import re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/electrolyte_rounding_panel_harmonized.csv'
SOURCE_FILE = '/root/environment/data/electrolyte_rounding_panel.csv'
EXPECTED_COLUMNS = ['Sodium', 'Potassium', 'Chloride', 'Bicarbonate', 'Magnesium', 'Calcium', 'Glucose', 'Creatinine']
REFERENCE = {'Sodium': {'min': 110, 'max': 170}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'Chloride': {'min': 70, 'max': 140}, 'Bicarbonate': {'min': 5, 'max': 40}, 'Magnesium': {'min': 0.5, 'max': 10}, 'Calcium': {'min': 5.0, 'max': 15.0}, 'Glucose': {'min': 20, 'max': 800}, 'Creatinine': {'min': 0.2, 'max': 20}}
SPECS = {'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Chloride': ('same', 1.0, 70, 140), 'Bicarbonate': ('same', 1.0, 5, 40), 'Magnesium': ('single', 0.411, 0.5, 10), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Glucose': ('single', 0.0555, 20, 800), 'Creatinine': ('single', 88.4, 0.2, 20)}
EXPECTED_SAMPLES = [
    {'row': 0, 'col': 'Magnesium', 'value': 1.32},
    {'row': 0, 'col': 'Calcium', 'value': 8.80},
    {'row': 2, 'col': 'Glucose', 'value': 95.00},
    {'row': 5, 'col': 'Creatinine', 'value': 1.14},
]


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
    if 'e' in s.lower():
        return float(s)
    return float(s)


def convert_value(v, mode, factor, lo, hi):
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


def build_expected():
    src = pd.read_csv(SOURCE_FILE, dtype=str)
    numeric_cols = [c for c in src.columns if c.lower() != 'encounter_id']
    missing_mask = src[numeric_cols].map(lambda x: pd.isna(x) or str(x).strip() == '' or str(x).strip().lower() == 'nan').any(axis=1)
    df = src.loc[~missing_mask].copy()
    for col in numeric_cols:
        mode, factor, lo, hi = SPECS[col]
        df[col] = df[col].apply(parse_value)
        df[col] = df[col].apply(lambda v: convert_value(v, mode, factor, lo, hi))
        df[col] = df[col].apply(lambda x: f"{x:.2f}")
    return df[EXPECTED_COLUMNS].reset_index(drop=True)


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

    def test_row_count(self):
        assert len(self.df) == len(self.expected)

    def test_full_row_by_row_match(self):
        for i in range(len(self.df)):
            for col in EXPECTED_COLUMNS:
                actual = float(self.df.iloc[i][col])
                expected = float(self.expected.iloc[i][col])
                assert abs(actual - expected) <= max(0.01, abs(expected) * 0.001), (i, col, actual, expected)

    @pytest.mark.parametrize('sample', EXPECTED_SAMPLES)
    def test_anchor_samples(self, sample):
        actual = float(self.df.iloc[sample['row']][sample['col']])
        assert abs(actual - sample['value']) <= 0.01, (sample, actual)
