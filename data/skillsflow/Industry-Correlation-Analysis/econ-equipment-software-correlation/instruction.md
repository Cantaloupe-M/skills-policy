# Capital Spending Co-Movement Analysis

Understanding how different categories of business investment move together over the business cycle is central to macroeconomic analysis. This task examines the synchronization between physical equipment spending and software investment.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **industrial equipment orders** and the detrended real **enterprise software investment** for the years 1992 to 2025 (inclusive).

## Provided Data

The following datasets are placed in `/root/`:

- `capital_table_03.xlsx` – Industrial equipment orders (nominal, annual with quarterly breakdown for 2025)
- `capital_table_09.xlsx` – Enterprise software investment (nominal, annual with quarterly breakdown for 2025)
- `capital_goods_deflator.xlsx` – Capital goods price index (2025 = 1.0, for deflation)

Each data table contains a header row with the column label `Private total` holding the aggregate value.

### Note on 2025

For the year 2025, only partial quarterly data is available. Use the average of available quarters as the annual value.

## Requirements

1. Extract the `Private total` column from each capital table.
2. Convert nominal values to real values by dividing by the capital goods price index.
3. Apply the Hodrick-Prescott filter to extract the cyclical component:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100 (the standard smoothing parameter for annual data).
4. Compute the Pearson correlation between the two cyclical components.
5. Write the result to `/root/answer.txt`:
   - Output **only** the correlation coefficient as a single number.
   - Round to 5 decimal places.

## Example Output

If the correlation is -0.45678, your `answer.txt` should contain:

```
-0.45678
```
