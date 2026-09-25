# Housing Cycle Alignment Analysis

Housing markets and construction supply chains often exhibit synchronized cyclical behavior. This task examines the relationship between residential renovation activity and building materials distribution.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **residential renovation spending** and the detrended real **building materials dealer shipments** for the years 1995 to 2025 (inclusive).

## Provided Data

The following datasets are placed in `/root/`:

- `housing_materials_panel.xlsx` – Combined panel dataset:
  - Sheet `AnnualPanel`: long-format records for both series (annual, with columns `series_label`, `period_label`, `period_kind`, `release_status`, `amount`).
  - Sheet `Update2025`: monthly updates for 2025 (columns `series_label`, `month`, `release_status`, `amount`).
- `construction_price_reference.xlsx` – Construction input price index (2025 = 1.0, sheet `AnnualIndices`, column `Construction_Input_Price_2025_Base`).

### Important Notes

1. In `AnnualPanel`, each row corresponds to a single observation. Use only rows where:
   - `period_kind` equals `"annual"`.
   - `release_status` equals `"final"` (ignore `"prelim"` or other statuses).

2. In `Update2025`, use only rows where `release_status` equals `"final"`. The `month` column contains values like `"2025-01"`, `"2025-02"`, etc. Annualize the 2025 value by averaging the available monthly amounts.

3. Both series share the same price index for deflation.

## Requirements

1. Extract the two series from `AnnualPanel` and `Update2025` according to the filtering rules above.
2. Deflate nominal values using the construction input price index.
3. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
4. Compute the Pearson correlation between the two cyclical components.
5. Write the result to `/root/answer.txt`:
   - Output **only** the correlation coefficient as a single number.
   - Round to 5 decimal places.

## Example Output

If the correlation is 0.62345, your `answer.txt` should contain:

```
0.62345
```
