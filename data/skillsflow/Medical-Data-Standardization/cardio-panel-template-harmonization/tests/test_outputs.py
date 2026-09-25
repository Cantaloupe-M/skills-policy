#!/usr/bin/env python3
import os
import re
import pandas as pd
import pytest

OUTPUT_FILE = '/root/cardiology_output_template.csv'
SOURCE_FILE = '/root/environment/data/cardiology_panel.csv'
TEMPLATE_FILE = '/root/environment/data/cardiology_output_template.csv'
EXPECTED_COLUMNS = ['BNP', 'NT_proBNP', 'Troponin_I', 'Troponin_T', 'Creatinine', 'Sodium', 'Potassium', 'Magnesium']
REFERENCE = {'BNP': {'min': 0, 'max': 5000}, 'NT_proBNP': {'min': 0, 'max': 35000}, 'Troponin_I': {'min': 0, 'max': 50}, 'Troponin_T': {'min': 0, 'max': 10}, 'Creatinine': {'min': 0.2, 'max': 20}, 'Sodium': {'min': 110, 'max': 170}, 'Potassium': {'min': 2.0, 'max': 8.5}, 'Magnesium': {'min': 0.5, 'max': 10}}
SPECS = {'BNP': ('single', 0.289, 0, 5000), 'NT_proBNP': ('single', 0.118, 0, 35000), 'Troponin_I': ('single', 1000, 0, 50), 'Troponin_T': ('single', 1000, 0, 10), 'Creatinine': ('single', 88.4, 0.2, 20), 'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Magnesium': ('single', 0.411, 0.5, 10)}
EXPECTED_SAMPLES = [
    {'row': 0, 'col': 'BNP', 'value': 124.00},
    {'row': 0, 'col': 'NT_proBNP', 'value': 450.00},
    {'row': 2, 'col': 'Troponin_I', 'value': 0.02},
    {'row': 4, 'col': 'Troponin_T', 'value': 0.01},
    {'row': 2, 'col': 'Creatinine', 'value': 1.08},
    {'row': 4, 'col': 'Magnesium', 'value': 1.95},
]


def ok(v, lo, hi):
    try:
        x = float(v)
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
    template_cols = list(pd.read_csv(TEMPLATE_FILE, nrows=0).columns)
    numeric_cols = [c for c in src.columns if c.lower() != 'encounter_id']
    missing_mask = src[numeric_cols].map(lambda x: pd.isna(x) or str(x).strip() == '' or str(x).strip().lower() == 'nan').any(axis=1)
    df = src.loc[~missing_mask].copy()
    for col in numeric_cols:
        if col not in SPECS:
            continue
        mode, factor, lo, hi = SPECS[col]
        df[col] = df[col].apply(parse_value)
        df[col] = df[col].apply(lambda v: convert_value(v, mode, factor, lo, hi))
        df[col] = df[col].apply(lambda x: f"{x:.2f}")
    return df[template_cols].reset_index(drop=True)


class TestOutput:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.df = pd.read_csv(OUTPUT_FILE, dtype=str) if os.path.exists(OUTPUT_FILE) else None
        self.expected = build_expected()

    def test_exists(self):
        assert os.path.exists(OUTPUT_FILE)

    def test_columns(self):
        assert list(self.df.columns) == EXPECTED_COLUMNS

    def test_no_placeholders(self):
        assert not self.df.map(lambda x: 'PLACEHOLDER' in str(x)).any().any()

    def test_format(self):
        pat = re.compile(r'^-?\d+\.\d{2}$')
        for c in EXPECTED_COLUMNS:
            for v in self.df[c]:
                assert pat.match(str(v)), (c, v)

    @pytest.mark.parametrize('c', EXPECTED_COLUMNS)
    def test_ranges(self, c):
        assert all(ok(v, REFERENCE[c]['min'], REFERENCE[c]['max']) for v in self.df[c]), c

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
