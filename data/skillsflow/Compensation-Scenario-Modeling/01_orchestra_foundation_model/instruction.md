Build an Excel compensation model workbook at:

`/root/Orchestra_Compensation.xlsx`

Use the source file:

`/root/orchestra_assumptions_and_roster.xlsx`

The model should be designed for ad hoc scenario analysis over 3 years (Current, Year + 1, Year + 2), and it must be formula-driven.

Required output requirements:

1. The workbook must contain exactly these worksheets (in this order):
   - `Summary`
   - `Assumptions`
   - `Roster`
   - `Calculations --->`
   - `EE Calcs (Current)`
   - `EE Calcs (Yr+1)`
   - `EE Calcs (Yr+2)`

2. Migrate the source assumptions and roster into the model:
   - `Assumptions` sheet must preserve assumption text and numeric drivers from the source workbook.
   - `Roster` sheet must include all musicians with no dropped/duplicated rows.

3. `Summary` sheet:
   - Include input drivers for MWS, premiums, media fee, withholding/tax rates, and seniority tiers for all 3 years.
   - Include quarterly compensation summary rows for:
     - MWS
     - Overscale
     - Principal Pay
     - Media Exploitation
     - Seniority
     - Payroll Tax
     - Total Compensation Expense
     - Y/Y growth rate
   - The quarterly rows must be formula-linked to the calculation sheets (`EE Calcs (Current)`, `EE Calcs (Yr+1)`, `EE Calcs (Yr+2)`), not hardcoded.

4. Named ranges:
   - Define named ranges for the key assumptions (MWS, principal tiers, media, payroll tax tiers/limits, and seniority tiers) across all 3 years.

5. Calculation sheets:
   - Must include per-employee formulas for each compensation component by quarter.
   - Must include payroll tax formulas with tiered tax treatment.
   - Must aggregate quarterly totals in row 107.
   - Year + 1 and Year + 2 sheets must project years-of-service forward (+1 each year).

6. Formula-first constraint:
   - Summary totals, quarterly totals, and YoY growth rows must be formula-driven.
   - Do not hardcode summary outputs.

Only the final workbook path above is graded.
