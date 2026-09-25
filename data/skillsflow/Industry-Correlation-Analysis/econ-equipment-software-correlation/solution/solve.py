#!/usr/bin/env python3
"""
Oracle solution for Task 2 (dividend, parameter-only): equipment-software correlation.
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "tools"))

from cycle_pipeline import (
    cycle_correlation_from_nominal,
    extract_canonical_table,
    read_index_columns,
    write_answer,
)


def main():
    series_a = extract_canonical_table(
        "capital_table_03.xlsx",
        "Table 3",
        "Private total",
        start_year=1992,
        current_year=2025,
    )
    series_b = extract_canonical_table(
        "capital_table_09.xlsx",
        "Table 9",
        "Private total",
        start_year=1992,
        current_year=2025,
    )
    deflators = read_index_columns(
        "capital_goods_deflator.xlsx",
        "Annual Index",
    )
    corr = cycle_correlation_from_nominal(
        series_a,
        series_b,
        deflators["Capital_Goods_Price_2025_Base"],
    )
    write_answer(corr)


if __name__ == "__main__":
    main()
