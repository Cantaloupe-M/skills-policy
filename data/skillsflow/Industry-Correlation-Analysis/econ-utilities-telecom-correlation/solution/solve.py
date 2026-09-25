#!/usr/bin/env python3
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))

from cycle_pipeline import (
    cycle_correlation_from_nominal,
    extract_update_average,
    extract_wide_matrix,
    read_index_columns,
    write_answer,
)


def main():
    series_a = extract_wide_matrix('network_matrix_release.xlsx', 'OfficialAnnuals', 'Regulated electric utility revenue', 'series_name', 'status_flag', 'official', 1991, 2025)
    series_b = extract_wide_matrix('network_matrix_release.xlsx', 'OfficialAnnuals', 'Wireline telecom services revenue', 'series_name', 'status_flag', 'official', 1991, 2025)
    series_a[2025] = extract_update_average('network_update_2025.csv', 'Regulated electric utility revenue', 'series_name', 'period', 'amount', 2025, 'status_flag', 'official')
    series_b[2025] = extract_update_average('network_update_2025.csv', 'Wireline telecom services revenue', 'series_name', 'period', 'amount', 2025, 'status_flag', 'official')
    deflators = read_index_columns('network_service_prices.xlsx', 'Indices')
    corr = cycle_correlation_from_nominal(series_a, series_b, deflators['Utilities_Telecom_Price_2025_Base'])
    write_answer(corr)


if __name__ == '__main__':
    main()
