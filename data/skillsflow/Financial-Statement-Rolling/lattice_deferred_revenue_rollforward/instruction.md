You are covering the August 2025 close for LatticeWare. Build the deferred revenue workbook from the prepared schedules and GL checkpoints.

    Build the workbook at:

    - `/root/LatticeWare_Deferred_Revenue_8-25.xlsx`

    Use these source files:

    - `/root/saas_deferred_revenue_schedule.csv`
- `/root/services_deferred_revenue_schedule.csv`
- `/root/gl_balances.json`

    Create exactly three sheets in this order:

    1. `Deferred Summary`
    2. `SaaS Rev #2300`
    3. `Services Rev #2310`

    Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

    - A: Customer
- B: Beginning Balance
- C: May Billings
- D: May Recognition
- E: May Ending Balance
- F: Jun Billings
- G: Jun Recognition
- H: Jun Ending Balance
- I: Jul Billings
- J: Jul Recognition
- K: Jul Ending Balance
- L: Aug Billings
- M: Aug Recognition
- N: Aug Ending Balance
- O: Contract Months
- P: Notes
- Q: Revenue Code

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

    - Include company name (`LatticeWare`) and the period ending shown in the source package.
    - Include sections for both accounts.
    - Use formulas in these cells:
      - `B7` links to column `O` of `SaaS Rev #2300` Period Totals row
- `B8` links to column `O` of `SaaS Rev #2300` Ending Balance row
- `B9` links to column `O` of `SaaS Rev #2300` GL Balance row
- `B12` links to column `O` of `Services Rev #2310` Period Totals row
- `B13` links to column `O` of `Services Rev #2310` Ending Balance row
- `B14` links to column `O` of `Services Rev #2310` GL Balance row
- `B16` formula: `B9 + B14`



    Important:

    - Keep amount cells numeric, not text.
    - Do not modify the source files.
    - Final deliverable must be a single `.xlsx` workbook at the required path.
