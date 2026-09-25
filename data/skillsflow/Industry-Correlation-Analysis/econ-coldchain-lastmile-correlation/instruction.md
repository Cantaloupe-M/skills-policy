# Cold-Chain and Last-Mile Cycle Correlation

This task combines a historical matrix, two overlapping current-period update files, a selector workbook, and two different deflators. Your goal is to reconstruct two macro-sensitive logistics series and measure their cyclical co-movement.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **temperature-controlled storage fees** and the detrended real **urban last-mile parcel charges** for the years 1994 to 2025 (inclusive).

## Provided Data

The following files are placed in `/root/`:

- `coldchain_archive.xlsx` – Historical annual matrix (sheet `HistoryMatrix`)
- `coldchain_updates_a.csv` – Current 2025 monthly updates from source A
- `coldchain_updates_b.csv` – Current 2025 monthly updates from source B
- `coldchain_update_selector.xlsx` – Month-level selection rules (sheet `UseThese`)
- `coldchain_series_register.csv` – Series register containing codes, historical status, and deflator columns
- `coldchain_price_book.xlsx` – Price indices (sheet `Indices`)

## Register Rule

Use `coldchain_series_register.csv` to determine, for each requested series:

- which historical code to read from `coldchain_archive.xlsx`
- which `status_bucket` is valid in the historical matrix
- which current-period code to use in the update files
- which deflator column to use in `coldchain_price_book.xlsx`

## Historical Rule

In `coldchain_archive.xlsx`, use only the row where both of the following match the register entry:

- `series_code`
- `status_bucket`

The annual year columns in the matrix cover 1994 through 2024.

## Current-Year Rule

The 2025 monthly values are split across `coldchain_updates_a.csv` and `coldchain_updates_b.csv`. Use `coldchain_update_selector.xlsx` to choose the correct source file and `version` for each month and each series.

For each selected row:

- if the selected record exists and has a numeric `amount`, keep it
- if the selected record is blank or missing, ignore that month

Average the remaining selected monthly amounts to form the annual 2025 value.

## Deflator Rule

Use the deflator column specified in the register for each series. The two requested series do not share the same deflator.

## Requirements

1. Use the register to identify the correct historical code, historical status, current code, and deflator column for each series.
2. Extract the annual 1994-2024 history from the matrix.
3. Use the selector workbook to pick the correct monthly 2025 observations from the two update files.
4. Average the valid selected monthly observations to form the 2025 value for each series.
5. Deflate each nominal series using its own deflator column.
6. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
7. Compute the Pearson correlation between the two cyclical components.
8. Write the result to `/root/answer.txt`:
   - Output only the correlation coefficient as a single number.
   - Round to 5 decimal places.
