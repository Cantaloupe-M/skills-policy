Build a multi-year Excel compensation workbook for a university's full-time faculty.

Output:

`/root/Faculty_Termload_Compensation.xlsx`

Input:

`/root/faculty_termload_packet.xlsx`

The source packet includes an extra `Packet Notes` sheet. Ignore it in the final output.

Workbook contract:

1. Keep exactly these 7 worksheets in order:
   - `Summary`
   - `Assumptions`
   - `Roster`
   - `Calculations --->`
   - `EE Calcs (Current)`
   - `EE Calcs (Yr+1)`
   - `EE Calcs (Yr+2)`

2. Preserve the standard faculty modeling structure:
   - assumptions migrated into `Assumptions`
   - faculty roster migrated into `Roster`
   - quarterly totals on row 79 of each EE Calcs sheet

3. `Summary` must still include these 8 compensation components:
   - Base Pay (9-Month)
   - Summer Session Pay
   - Sabbatical Bonus
   - Department Stipend
   - Media Rights Allocation
   - Health Insurance
   - Retirement Match
   - TOTAL and Y/Y Growth rows

4. Define the faculty assumption named ranges across all 3 years.

5. Keep the year-projection behavior:
   - projected sheets advance service years
   - summary totals remain cross-sheet linked
   - total and Y/Y rows remain formula-based

Only the final workbook path above is graded.
