# Service Demand Synchronization Analysis

In economic cycle analysis, understanding how different service sectors move together is essential. This task focuses on the co-movement of household hospitality consumption with travel-related spending.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **dining services receipts** and the detrended real **domestic travel outlays** for the years 1994 to 2025 (inclusive).

## Provided Data

The following datasets are placed in `/root/`:

- `service_table_07.xlsx` – Dining services receipts (nominal, annual with quarterly breakdown for 2025)
- `service_table_11.xlsx` – Domestic travel outlays (nominal, annual with quarterly breakdown for 2025)
- `service_price_index.xlsx` – Service price index (2025 = 1.0, for deflation)

Each data table contains a header row with the column label `National total` holding the aggregate value.

### Note on 2025

For the year 2025, only partial quarterly data is available. Use the average of available quarters as the annual value.

## Requirements

1. Extract the `National total` column from each service table.
2. Convert nominal values to real values by dividing by the service price index.
3. Apply the Hodrick-Prescott filter to extract the cyclical component:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100 (the standard smoothing parameter for annual data).
4. Compute the Pearson correlation between the two cyclical components.
5. Write the result to `/root/answer.txt`:
   - Output **only** the correlation coefficient as a single number.
   - Round to 5 decimal places.

## Example Output

If the correlation is 0.812345, your `answer.txt` should contain:

```
0.81235
```
