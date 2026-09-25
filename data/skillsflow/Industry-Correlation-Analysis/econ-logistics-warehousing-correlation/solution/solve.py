#!/usr/bin/env python3
"""
Oracle solution for Task 4 (dividend, adversarial-but-derivable): logistics-warehousing correlation.
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "tools"))

from cycle_pipeline import (
    cycle_correlation_from_nominal,
    extract_catalog_series,
    read_index_columns,
    write_answer,
)


def main():
    series_a, deflator_col_a = extract_catalog_series(
        history_workbook="logistics_history.xlsx",
        current_workbook="logistics_current_release.xlsx",
        catalog_csv="series_catalog.csv",
        requested_series="Freight brokerage revenue",
        current_year=2025,
    )
    series_b, deflator_col_b = extract_catalog_series(
        history_workbook="logistics_history.xlsx",
        current_workbook="logistics_current_release.xlsx",
        catalog_csv="series_catalog.csv",
        requested_series="Warehouse equipment outlays",
        current_year=2025,
    )
    deflators = read_index_columns(
        "logistics_price_book.xlsx",
        sheet_name="Indices",
    )
    corr = cycle_correlation_from_nominal(
        series_a,
        series_b,
        deflators[deflator_col_a],
        deflators[deflator_col_b],
    )
    write_answer(corr)


if __name__ == "__main__":
    main()
