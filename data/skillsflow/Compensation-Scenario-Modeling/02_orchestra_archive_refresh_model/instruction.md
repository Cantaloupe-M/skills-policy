Build an Excel compensation model workbook at:

`/root/Festival_Orchestra_Compensation.xlsx`

Use the source file:

`/root/festival_archive_packet.xlsx`

The source packet includes an extra `Archive Notes` worksheet. It is context only and must not appear in the final workbook.

The model should remain a 3-year, formula-linked compensation workbook for a union-style orchestra roster.

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
   - `Assumptions` must preserve the source drivers.
   - `Roster` must include the full musician roster with no dropped or duplicated rows.

3. `Summary` sheet:
   - Keep the 3-year driver block for weekly scale, principal premiums, media fees, withholding limits/rates, and seniority tiers.
   - Keep quarterly summary rows for MWS, overscale, principal pay, media exploitation, seniority, payroll tax, total compensation expense, and Y/Y growth.
   - Quarterly summary rows must link to the EE Calcs sheets by formula.

4. Named ranges:
   - Define the full set of orchestra assumption named ranges across all 3 years.

5. Calculation sheets:
   - Preserve the quarter-by-quarter employee calculation layout.
   - Aggregate quarterly totals in row 107.
   - Year + 1 and Year + 2 must project service years forward.

6. Formula-linked outputs:
   - Summary totals, quarterly totals, and Y/Y rows must remain formula-linked rather than handwritten summaries.

Only the final workbook path above is graded.
