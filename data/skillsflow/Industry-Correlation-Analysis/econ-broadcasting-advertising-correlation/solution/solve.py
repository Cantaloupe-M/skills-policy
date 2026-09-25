#!/usr/bin/env python3
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))

from cycle_pipeline import cycle_correlation_from_nominal, extract_canonical_table, read_index_columns, write_answer


def main():
    series_a = extract_canonical_table('media_release_table_05.xlsx', 'Broadcasting', 'Domestic total', 1993, 2025)
    series_b = extract_canonical_table('media_release_table_12.xlsx', 'Advertising', 'Domestic total', 1993, 2025)
    deflators = read_index_columns('media_service_prices.xlsx', 'Media Prices')
    corr = cycle_correlation_from_nominal(series_a, series_b, deflators['Media_Services_Price_2025_Base'])
    write_answer(corr)


if __name__ == '__main__':
    main()
