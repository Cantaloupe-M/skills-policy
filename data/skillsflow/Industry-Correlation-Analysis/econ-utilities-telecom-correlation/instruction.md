# Network Services Cycle Alignment

Utility and telecom service revenues are both sensitive to business-cycle conditions, but they are often published in different tabular layouts. This task asks you to compute how closely those two sectors move together after detrending.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **regulated electric utility revenue** and the detrended real **wireline telecom services revenue** for the years 1991 to 2025 (inclusive).

## Provided Data

The following files are placed in `/root/`:

- `network_matrix_release.xlsx` – Annual wide-format matrix (sheet `OfficialAnnuals`)
- `network_update_2025.csv` – Monthly 2025 updates
- `network_service_prices.xlsx` – Shared sector price index (sheet `Indices`)

### Annual Matrix Rule

In `network_matrix_release.xlsx`, each row is a series and each year from 1991 to 2024 appears as its own column. Use only the row where:

- `series_name` matches the requested series, and
- `status_flag` equals `official`

Ignore rows where `status_flag` is `memo`.

### Current-Year Rule

In `network_update_2025.csv`, use only rows where `status_flag` equals `official`. The `period` column contains values like `2025-01`, `2025-02`, and so on. Average the available 2025 monthly amounts to form the annual 2025 value.

### Deflator Rule

Use `Utilities_Telecom_Price_2025_Base` from `network_service_prices.xlsx` to deflate both nominal series.

## Requirements

1. Extract the annual 1991-2024 values from the wide matrix.
2. Extract and average the available 2025 official monthly values from the CSV file.
3. Deflate both nominal series using `Utilities_Telecom_Price_2025_Base`.
4. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
5. Compute the Pearson correlation between the two cyclical components.
6. Write the result to `/root/answer.txt`:
   - Output only the correlation coefficient as a single number.
   - Round to 5 decimal places.
