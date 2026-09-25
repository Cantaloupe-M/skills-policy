You are preparing the September 2025 warranty reserve package for Northstar Appliances. Build the warranty reserve workbook from a consolidated schedule, an account-routing file, and the GL checkpoints.

Build the workbook at:

- `/root/Northstar_Warranty_Reserve_9-25.xlsx`

Use these source files:

- `/root/warranty_reserve_combined.csv`
- `/root/reserve_account_map.json`
- `/root/gl_balances.json`

Create exactly three sheets in this order:

1. `Warranty Summary`
2. `Consumer Warranty #2440`
3. `Commercial Warranty #2445`

Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

- A: Claim Group
- B: Beginning Balance
- C: Jun Accruals
- D: Jun Claims Paid
- E: Jun Ending Balance
- F: Jul Accruals
- G: Jul Claims Paid
- H: Jul Ending Balance
- I: Aug Accruals
- J: Aug Claims Paid
- K: Aug Ending Balance
- L: Sep Accruals
- M: Sep Claims Paid
- N: Sep Ending Balance
- O: Coverage Months
- P: Notes
- Q: Reserve Account

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

- Include company name (`Northstar Appliances`) and the period ending shown in the source package.
- Include sections for both accounts.
- Use formulas in these cells:
  - `B7` links to column `O` of `Consumer Warranty #2440` Period Totals row
  - `B8` links to column `O` of `Consumer Warranty #2440` Ending Balance row
  - `B9` links to column `O` of `Consumer Warranty #2440` GL Balance row
  - `B12` links to column `O` of `Commercial Warranty #2445` Period Totals row
  - `B13` links to column `O` of `Commercial Warranty #2445` Ending Balance row
  - `B14` links to column `O` of `Commercial Warranty #2445` GL Balance row
  - `B16` formula: `B9 + B14`

Before populating the detailed sheets:

- Read `/root/reserve_account_map.json` to route each active row in `/root/warranty_reserve_combined.csv` to the correct detail sheet.
- Keep only rows where `record_status` is `active`.
- Split the consolidated schedule by `bucket_code` so each detail sheet contains only its matching reserve bucket.
- Sort each detailed sheet by claim group name.
Important:

- Keep amount cells numeric, not text.
- Do not modify the source files.
- Final deliverable must be a single `.xlsx` workbook at the required path.
