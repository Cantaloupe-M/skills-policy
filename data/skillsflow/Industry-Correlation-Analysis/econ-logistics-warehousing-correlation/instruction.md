# Logistics and Warehousing Cycle Alignment

Freight intermediation and warehousing investment often move together over the business cycle. This task examines their co-movement using a more realistic data release structure.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **freight brokerage revenue** and the detrended real **warehouse equipment outlays** for the years 1993 to 2025 (inclusive).

## Provided Data

The following datasets are placed in `/root/`:

1. `logistics_history.xlsx` (sheet `AnnualSeries`):
   - Long-format historical annual observations.
   - Columns: `calendar_year`, `BROKER_REV`, `WHSE_EQUIP`, and additional distractor series.

2. `logistics_current_release.xlsx` (sheet `QuarterlyUpdate`):
   - Quarterly updates for 2025.
   - Columns: `series_code`, `subperiod`, `version`, `value`.
   - Use only rows where `version` equals `"revised"` (ignore `"prelim"`).

3. `series_catalog.csv`:
   - Mapping file that links requested series names to codes.
   - Columns: `requested_series`, `history_sheet`, `history_code`, `current_sheet`, `current_code`, `deflator_column`.

4. `logistics_price_book.xlsx` (sheet `Indices`):
   - Price indices for deflation.
   - Columns: `Year`, `Transport_Services_Price_2025_Base`, `Warehouse_Equipment_Price_2025_Base`.

### Important Notes

1. Use `series_catalog.csv` to determine which columns and codes correspond to each requested series.
2. For historical data (years before 2025), extract values from `logistics_history.xlsx` using the appropriate `history_code` column.
3. For 2025, extract values from `logistics_current_release.xlsx` using the appropriate `current_code` and filtering for `version == "revised"`. Annualize by averaging the available quarterly values.
4. Each series has its own price index column for deflation (specified in `deflator_column`).

## Requirements

1. Use the catalog to locate the correct codes and deflator columns for each series.
2. Extract historical annual values (1993–2024) from the history workbook.
3. Extract and annualize 2025 values from the current release workbook (revised only).
4. Deflate each nominal series using its corresponding price index.
5. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
6. Compute the Pearson correlation between the two cyclical components.
7. Write the result to `/root/answer.txt`:
   - Output **only** the correlation coefficient as a single number.
   - Round to 5 decimal places.

## Example Output

If the correlation is -0.31245, your `answer.txt` should contain:

```
-0.31245
```
