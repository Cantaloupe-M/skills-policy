#!/usr/bin/env python3
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))

from cycle_pipeline import cycle_correlation_from_nominal, extract_alias_priority_series, read_index_columns, write_answer


def main():
    series_a = extract_alias_priority_series('distribution_packaging_release.xlsx', 'AnnualRows', 'distribution_packaging_2025.xlsx', 'CurrentPartials', 'series_aliases.csv', 'Merchant wholesale turnover', 1990, 2025)
    series_b = extract_alias_priority_series('distribution_packaging_release.xlsx', 'AnnualRows', 'distribution_packaging_2025.xlsx', 'CurrentPartials', 'series_aliases.csv', 'Packaging converters shipments', 1990, 2025)
    deflators = read_index_columns('distribution_packaging_prices.xlsx', 'AnnualIndex')
    corr = cycle_correlation_from_nominal(series_a, series_b, deflators['Distribution_Packaging_Price_2025_Base'])
    write_answer(corr)


if __name__ == '__main__':
    main()
