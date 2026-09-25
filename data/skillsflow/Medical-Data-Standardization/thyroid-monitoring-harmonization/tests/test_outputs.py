#!/usr/bin/env python3
import os
import re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/thyroid_monitoring_panel_harmonized.csv'
SOURCE_FILE = '/root/environment/data/thyroid_monitoring_panel.csv'
EXPECTED_COLUMNS = ['TSH', 'Free_T4', 'Free_T3', 'Total_T4', 'Total_T3', 'Anti_TPO', 'Thyroglobulin', 'Thyroglobulin_Antibody', 'Calcium', 'Ionized_Calcium', 'Phosphorus', 'Magnesium', 'PTH', 'Vitamin_D_25OH', 'Calcitonin', 'Creatinine']
REFERENCE = {'TSH': {'min': 0.01, 'max': 150}, 'Free_T4': {'min': 0.2, 'max': 6.0}, 'Free_T3': {'min': 1.0, 'max': 10.0}, 'Total_T4': {'min': 1.0, 'max': 24.0}, 'Total_T3': {'min': 20, 'max': 600}, 'Anti_TPO': {'min': 0, 'max': 5000}, 'Thyroglobulin': {'min': 0.1, 'max': 5000}, 'Thyroglobulin_Antibody': {'min': 0, 'max': 4000}, 'Calcium': {'min': 5.0, 'max': 15.0}, 'Ionized_Calcium': {'min': 0.8, 'max': 2.0}, 'Phosphorus': {'min': 1.0, 'max': 15.0}, 'Magnesium': {'min': 0.5, 'max': 10.0}, 'PTH': {'min': 5, 'max': 2500}, 'Vitamin_D_25OH': {'min': 4, 'max': 200}, 'Calcitonin': {'min': 0, 'max': 500}, 'Creatinine': {'min': 0.2, 'max': 20}}
SPECS = {'TSH': ('same', 1.0, 0.01, 150), 'Free_T4': ('single', 12.87, 0.2, 6.0), 'Free_T3': ('single', 15.38, 1.0, 10.0), 'Total_T4': ('single', 12.87, 1.0, 24.0), 'Total_T3': ('single', 0.0154, 20, 600), 'Anti_TPO': ('same', 1.0, 0, 5000), 'Thyroglobulin': ('same', 1.0, 0.1, 5000), 'Thyroglobulin_Antibody': ('same', 1.0, 0, 4000), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Ionized_Calcium': ('same', 1.0, 0.8, 2.0), 'Phosphorus': ('single', 0.323, 1.0, 15.0), 'Magnesium': ('single', 0.411, 0.5, 10.0), 'PTH': ('single', 0.106, 5, 2500), 'Vitamin_D_25OH': ('single', 2.5, 4, 200), 'Calcitonin': ('same', 1.0, 0, 500), 'Creatinine': ('single', 88.4, 0.2, 20)}
EXPECTED_SAMPLES = [
    {'row': 0, 'col': 'Free_T4', 'value': 1.25},
    {'row': 2, 'col': 'PTH', 'value': 45.0},
    {'row': 5, 'col': 'Vitamin_D_25OH', 'value': 32.0},
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
