You are finishing the September 2025 project accounting package for Orchid Health Systems. Build the capitalized project cost rollforward workbook from the nested source file, the override file, and the GL checkpoints.

    Build the workbook at:

    - `/root/Orchid_Project_Costs_9-25.xlsx`

    Use these source files:

    - `/root/project_cost_rollforward.json`
- `/root/schedule_overrides.csv`
- `/root/gl_balances.json`

    Create exactly three sheets in this order:

    1. `Project Cost Summary`
    2. `Cap Impl #1460`
    3. `Leasehold #1465`

    Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

    - A: Vendor
- B: Beginning Balance
- C: Jun Cap Adds
- D: Jun Amortization
- E: Jun Ending Balance
- F: Jul Cap Adds
- G: Jul Amortization
- H: Jul Ending Balance
- I: Aug Cap Adds
- J: Aug Amortization
- K: Aug Ending Balance
- L: Sep Cap Adds
- M: Sep Amortization
- N: Sep Ending Balance
- O: Useful Life Months
- P: Notes
- Q: Source Account

    For each detailed sheet, place these control rows immediately below the line items:

    - `Period Totals`
    - `Ending Balance`
    - `Variance`
    - `GL Balance`

    Required control-row formulas:

    - `Period Totals` row:
  - Columns `B:N` use `SUM(...)` over all line-item rows.
  - Column `O` formula: `C + F + I + L` (same row).
- `Ending Balance` row:
  - `E` = `B + C - D`
  - `H` = `E + F - G`
  - `K` = `H + I - J`
  - `N` = `K + L - M`
  - `O` = `D + G + J + M`
- `Variance` row:
  - Column `O` formula: `O(GL Balance row) - N(GL Balance row)`
- `GL Balance` row:
  - Columns `E/H/K/N` must match `/root/gl_balances.json` for the corresponding account.
  - Column `O` formula: `O(Period Totals row) - O(Ending Balance row)`

    Summary sheet requirements:

    - Include company name (`Orchid Health Systems`) and the period ending shown in the source package.
    - Include sections for both accounts.
    - Use formulas in these cells:
      - `B7` links to column `O` of `Cap Impl #1460` Period Totals row
- `B8` links to column `O` of `Cap Impl #1460` Ending Balance row
- `B9` links to column `O` of `Cap Impl #1460` GL Balance row
- `B12` links to column `O` of `Leasehold #1465` Period Totals row
- `B13` links to column `O` of `Leasehold #1465` Ending Balance row
- `B14` links to column `O` of `Leasehold #1465` GL Balance row
- `B16` formula: `B9 + B14`

    Before populating the detailed sheets:

- Flatten `/root/project_cost_rollforward.json` account-by-account.
- Ignore any item where `active` is false.
- If multiple active items share the same `row_id`, keep only the one with the highest `revision`.
- Apply `/root/schedule_overrides.csv` by `row_id`. Any nonblank override field replaces the value from the JSON source.
- After normalization, sort each detailed sheet by vendor name, then by `row_id`.

    Important:

    - Keep amount cells numeric, not text.
    - Do not modify the source files.
    - Final deliverable must be a single `.xlsx` workbook at the required path.
