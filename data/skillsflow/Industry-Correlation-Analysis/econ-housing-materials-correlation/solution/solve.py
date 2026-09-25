#!/usr/bin/env python3
"""
Oracle solution for Task 3 (dividend, structural): housing-materials correlation.
"""

from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "tools"))

from cycle_pipeline import (
    cycle_correlation_from_nominal,
    extract_long_panel,
    read_index_columns,
    write_answer,
)


def main():
    series_a = extract_long_panel(
        "housing_materials_panel.xlsx",
        annual_sheet="AnnualPanel",
        update_sheet="Update2025",
        series_label="Residential renovation spending",
        start_year=1995,
        current_year=2025,
        annual_status="final",
        update_status="final",
    )
    series_b = extract_long_panel(
        "housing_materials_panel.xlsx",
        annual_sheet="AnnualPanel",
        update_sheet="Update2025",
        series_label="Building materials dealer shipments",
        start_year=1995,
        current_year=2025,
        annual_status="final",
        update_status="final",
    )
    deflators = read_index_columns(
        "construction_price_reference.xlsx",
        sheet_name="AnnualIndices",
    )
    corr = cycle_correlation_from_nominal(
        series_a,
        series_b,
        deflators["Construction_Input_Price_2025_Base"],
    )
    write_answer(corr)


if __name__ == "__main__":
    main()
