#!/usr/bin/env python3
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))

from cycle_pipeline import cycle_correlation_from_nominal, extract_register_selected_series, read_index_columns, write_answer


def main():
    update_files = {'A': 'coldchain_updates_a.csv', 'B': 'coldchain_updates_b.csv'}
    series_a, deflator_col_a = extract_register_selected_series('coldchain_series_register.csv', 'Temperature-controlled storage fees', 'coldchain_archive.xlsx', 'HistoryMatrix', 'coldchain_update_selector.xlsx', 'UseThese', update_files, 2025)
    series_b, deflator_col_b = extract_register_selected_series('coldchain_series_register.csv', 'Urban last-mile parcel charges', 'coldchain_archive.xlsx', 'HistoryMatrix', 'coldchain_update_selector.xlsx', 'UseThese', update_files, 2025)
    deflators = read_index_columns('coldchain_price_book.xlsx', 'Indices')
    corr = cycle_correlation_from_nominal(series_a, series_b, deflators[deflator_col_a], deflators[deflator_col_b])
    write_answer(corr)


if __name__ == '__main__':
    main()
