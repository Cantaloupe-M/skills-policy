You are finalizing the October 2025 commission asset rollforward for Solstice Energy Software. Build the workbook by aligning the nested activity payload with the metadata schedule and then reconciling the GL checkpoints.

Build the workbook at:

- `/root/Solstice_Commission_Assets_10-25.xlsx`

Use these source files:

- `/root/commission_activity.json`
- `/root/commission_metadata.csv`
- `/root/gl_balances.json`

Create exactly three sheets in this order:

1. `Commission Asset Summary`
2. `Field Comm Asset #1510`
3. `Partner Comm Asset #1515`

Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

- A: Payee
- B: Beginning Balance
- C: Jul Capitalized
- D: Jul Amortization
- E: Jul Ending Balance
- F: Aug Capitalized
- G: Aug Amortization
- H: Aug Ending Balance
- I: Sep Capitalized
- J: Sep Amortization
- K: Sep Ending Balance
- L: Oct Capitalized
- M: Oct Amortization
- N: Oct Ending Balance
- O: Useful Life Months
- P: Notes
- Q: Asset Account

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

- Include company name (`Solstice Energy Software`) and the period ending shown in the source package.
- Include sections for both accounts.
- Use formulas in these cells:
  - `B7` links to column `O` of `Field Comm Asset #1510` Period Totals row
  - `B8` links to column `O` of `Field Comm Asset #1510` Ending Balance row
  - `B9` links to column `O` of `Field Comm Asset #1510` GL Balance row
  - `B12` links to column `O` of `Partner Comm Asset #1515` Period Totals row
  - `B13` links to column `O` of `Partner Comm Asset #1515` Ending Balance row
  - `B14` links to column `O` of `Partner Comm Asset #1515` GL Balance row
  - `B16` formula: `B9 + B14`

Before populating the detailed sheets:

- Flatten `/root/commission_activity.json` by section.
- Keep only rows where `eligible` is true.
- Join each activity row to `/root/commission_metadata.csv` by `line_key`.
- Ignore metadata rows that do not match an eligible activity row.
- Sort each detailed sheet by payee name, then by `line_key`.
Important:

- Keep amount cells numeric, not text.
- Do not modify the source files.
- Final deliverable must be a single `.xlsx` workbook at the required path.
