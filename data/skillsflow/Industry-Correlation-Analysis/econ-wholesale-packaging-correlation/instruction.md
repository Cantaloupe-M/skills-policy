# Distribution and Packaging Cycle Comparison

Wholesale distribution and packaging output often move together, but the source release for this task includes aliases and duplicate official rows. Your job is to reconstruct the correct annual series before computing the cyclical correlation.

## Goal

Calculate the Pearson correlation coefficient between the detrended real **merchant wholesale turnover** and the detrended real **packaging converters shipments** for the years 1990 to 2025 (inclusive).

## Provided Data

The following files are placed in `/root/`:

- `distribution_packaging_release.xlsx` – Annual observations (sheet `AnnualRows`)
- `distribution_packaging_2025.xlsx` – Partial 2025 quarterly updates (sheet `CurrentPartials`)
- `series_aliases.csv` – Alias mapping for the requested series
- `distribution_packaging_prices.xlsx` – Shared price index (sheet `AnnualIndex`)

## Alias Rule

The annual and current-period files may refer to the requested series using alternate aliases. Use `series_aliases.csv` to determine which aliases should be treated as valid matches for each requested series.

## Deduplication Rule

In both release files:

1. Keep only rows where `record_type` equals `official`.
2. If multiple official rows remain for the same year or subperiod, keep the row with the smallest numeric value in `priority`.

## Annualization Rule

In `distribution_packaging_2025.xlsx`, the `subperiod` column contains partial 2025 quarters. After alias matching and deduplication, average the available quarter values to form the annual 2025 observation.

## Deflator Rule

Use `Distribution_Packaging_Price_2025_Base` to deflate both nominal series.

## Requirements

1. Use the alias file to match the correct rows for each requested series.
2. Build the annual 1990-2024 history from the annual release file using the deduplication rule.
3. Build the 2025 value from the quarterly update file using the same deduplication rule.
4. Deflate both nominal series.
5. Apply the Hodrick-Prescott filter:
   - Take the natural logarithm of the real series before filtering.
   - Use λ = 100.
6. Compute the Pearson correlation between the two cyclical components.
7. Write the result to `/root/answer.txt`:
   - Output only the correlation coefficient as a single number.
   - Round to 5 decimal places.
