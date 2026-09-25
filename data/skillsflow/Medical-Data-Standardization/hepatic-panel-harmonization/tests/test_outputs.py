#!/usr/bin/env python3
import os
import re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/hepatic_lab_panel_harmonized.csv'
SOURCE_FILE = '/root/environment/data/hepatic_lab_panel.csv'
EXPECTED_COLUMNS = ['AST', 'ALT', 'ALP', 'GGT', 'Total_Bilirubin', 'Direct_Bilirubin', 'Albumin', 'Total_Protein', 'INR', 'Ammonia', 'Platelets', 'AFP', 'Bile_Acids', 'Creatinine', 'Sodium', 'Hemoglobin', 'Ferritin', 'Glucose']
REFERENCE = {'AST': {'min': 5, 'max': 2000}, 'ALT': {'min': 5, 'max': 2000}, 'ALP': {'min': 20, 'max': 2000}, 'GGT': {'min': 5, 'max': 2500}, 'Total_Bilirubin': {'min': 0.1, 'max': 30}, 'Direct_Bilirubin': {'min': 0.0, 'max': 15}, 'Albumin': {'min': 1.0, 'max': 6.5}, 'Total_Protein': {'min': 3.0, 'max': 12.0}, 'INR': {'min': 0.8, 'max': 12.0}, 'Ammonia': {'min': 10, 'max': 400}, 'Platelets': {'min': 10, 'max': 1500}, 'AFP': {'min': 0.5, 'max': 200000}, 'Bile_Acids': {'min': 0.5, 'max': 400}, 'Creatinine': {'min': 0.2, 'max': 20}, 'Sodium': {'min': 110, 'max': 170}, 'Hemoglobin': {'min': 3, 'max': 20}, 'Ferritin': {'min': 5, 'max': 5000}, 'Glucose': {'min': 20, 'max': 800}}
SPECS = {'AST': ('same', 1.0, 5, 2000), 'ALT': ('same', 1.0, 5, 2000), 'ALP': ('same', 1.0, 20, 2000), 'GGT': ('same', 1.0, 5, 2500), 'Total_Bilirubin': ('single', 17.1, 0.1, 30), 'Direct_Bilirubin': ('single', 17.1, 0.0, 15), 'Albumin': ('single', 10.0, 1.0, 6.5), 'Total_Protein': {'single': 10.0}, 'INR': ('same', 1.0, 0.8, 12.0), 'Ammonia': ('single', 0.587, 10, 400), 'Platelets': ('same', 1.0, 10, 1500), 'AFP': ('same', 1.0, 0.5, 200000), 'Bile_Acids': ('same', 1.0, 0.5, 400), 'Creatinine': ('single', 88.4, 0.2, 20), 'Sodium': ('same', 1.0, 110, 170), 'Hemoglobin': ('single', 10.0, 3, 20), 'Ferritin': ('single', 2.247, 5, 5000), 'Glucose': ('single', 0.0555, 20, 800)}
EXPECTED_SAMPLES = [
    {'row': 0, 'col': 'Total_Bilirubin', 'value': 0.76},
    {'row': 0, 'col': 'Albumin', 'value': 3.90},
    {'row': 2, 'col': 'Ammonia', 'value': 28.00},
    {'row': 5, 'col': 'Creatinine', 'value': 1.10},
    {'row': 5, 'col': 'Hemoglobin', 'value': 13.50},
    {'row': 2, 'col': 'Glucose', 'value': 92.00},
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
    numeric_cols = [c for c in src.columns if c.lower() != 'patient_id']
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
