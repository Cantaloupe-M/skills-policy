You are closing November 2025 for Cedar Ridge Manufacturing. Build the accrual rollforward workbook from the prepared schedules and GL checkpoints.

    Build the workbook at:

    - `/root/CedarRidge_Accrual_Rollforward_11-25.xlsx`

    Use these source files:

    - `/root/payroll_accrual_schedule.csv`
- `/root/bonus_accrual_schedule.csv`
- `/root/gl_balances.json`

    Create exactly three sheets in this order:

    1. `Accrual Summary`
    2. `Payroll Accrual #2105`
    3. `Bonus Accrual #2110`

    Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

    - A: Accrual Bucket
- B: Beginning Balance
- C: Sep Accruals
- D: Sep Releases
- E: Sep Ending Balance
- F: Oct Accruals
- G: Oct Releases
- H: Oct Ending Balance
- I: Nov Accruals
- J: Nov Releases
- K: Nov Ending Balance
- L: Reserve Months
- M: Notes
- N: Department Code

    For each detailed sheet, place these control rows immediately below the line items:

    - `Period Totals`
    - `Ending Balance`
    - `Variance`
    - `GL Balance`

    Required control-row formulas:

    - `Period Totals` row:
  - Columns `B:K` use `SUM(...)` over all line-item rows.
  - Column `L` formula: `C + F + I` (same row).
- `Ending Balance` row:
  - `E` = `B + C - D`
  - `H` = `E + F - G`
  - `K` = `H + I - J`
  - `L` = `D + G + J`
- `Variance` row:
  - Column `L` formula: `L(GL Balance row) - K(GL Balance row)`
- `GL Balance` row:
  - Columns `E/H/K` must match `/root/gl_balances.json` for the corresponding account.
  - Column `L` formula: `L(Period Totals row) - L(Ending Balance row)`

    Summary sheet requirements:

    - Include company name (`Cedar Ridge Manufacturing`) and the period ending shown in the source package.
    - Include sections for both accounts.
    - Use formulas in these cells:
      - `B7` links to column `L` of `Payroll Accrual #2105` Period Totals row
- `B8` links to column `L` of `Payroll Accrual #2105` Ending Balance row
- `B9` links to column `L` of `Payroll Accrual #2105` GL Balance row
- `B12` links to column `L` of `Bonus Accrual #2110` Period Totals row
- `B13` links to column `L` of `Bonus Accrual #2110` Ending Balance row
- `B14` links to column `L` of `Bonus Accrual #2110` GL Balance row
- `B16` formula: `B9 + B14`



    Important:

    - Keep amount cells numeric, not text.
    - Do not modify the source files.
    - Final deliverable must be a single `.xlsx` workbook at the required path.
