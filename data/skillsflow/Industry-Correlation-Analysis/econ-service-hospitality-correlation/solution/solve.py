#!/usr/bin/env python3
"""
Oracle solution for Task 1 (canonical): service-hospitality correlation.
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
        "service_table_07.xlsx",
        "Table 7",
        "National total",
        start_year=1994,
        current_year=2025,
    )
    series_b = extract_canonical_table(
        "service_table_11.xlsx",
        "Table 11",
        "National total",
        start_year=1994,
        current_year=2025,
    )
    deflators = read_index_columns(
        "service_price_index.xlsx",
        "Annual Index",
    )
    corr = cycle_correlation_from_nominal(
        series_a,
        series_b,
        deflators["Service_Price_2025_Base"],
    )
    write_answer(corr)


if __name__ == "__main__":
    main()
