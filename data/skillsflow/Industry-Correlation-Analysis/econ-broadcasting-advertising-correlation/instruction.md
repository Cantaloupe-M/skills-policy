# Media Revenue Co-Movement Analysis

Broadcasting and advertising markets often expand and contract together over the business cycle. This task measures how closely those two media revenue streams move together after removing long-run trend growth.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **broadcasting carriage receipts** and the detrended real **advertising placement revenue** for the years 1993 to 2025 (inclusive).

## Provided Data

The following files are placed in `/root/`:

- `media_release_table_05.xlsx` – Broadcasting carriage receipts (nominal, sheet `Broadcasting`)
- `media_release_table_12.xlsx` – Advertising placement revenue (nominal, sheet `Advertising`)
- `media_service_prices.xlsx` – Media service price indices (sheet `Media Prices`)

Each release table contains a metadata row before the actual header row. In both release tables, the aggregate series is stored in the column labeled `Domestic total`.

### Note on 2025

Only partial quarterly data is available for 2025. The quarter labels use `Q1`, `Q2`, and `Q3`. Use the average of the available quarters as the annual 2025 value.

### Deflator Rule

In `media_service_prices.xlsx`, use the column `Media_Services_Price_2025_Base` for deflation. Ignore the other index columns.

## Requirements

1. Extract the `Domestic total` column from each release table.
2. Convert nominal values to real values by dividing by `Media_Services_Price_2025_Base`.
3. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
4. Compute the Pearson correlation between the two cyclical components.
5. Write the result to `/root/answer.txt`:
   - Output only the correlation coefficient as a single number.
   - Round to 5 decimal places.
