Build a multi-year Excel compensation workbook for a property operations team.

Output:

`/root/Portfolio_Services_Compensation.xlsx`

Inputs:

1. `/root/asset_register_packet.xlsx`
2. `/root/operations_roster_packet.xlsx`

Both source packets include a `Packet Notes` worksheet. Those note tabs are context only and must not appear in the final workbook.

Required workbook contract:

1. The workbook must contain exactly these worksheets (in this order):
   - `Summary`
   - `Assumptions`
   - `Building Specs`
   - `Roster`
   - `Calculations --->`
   - `EE Calcs (Current)`
   - `EE Calcs (Yr+1)`
   - `EE Calcs (Yr+2)`

2. Read both source files and preserve their working data in the final workbook:
   - asset / building data in `Building Specs`
   - staff data in `Roster`

3. Keep the standard 3-year property compensation structure:
   - quarterly totals row 91 in each EE Calcs sheet
   - summary rows for base pay, property bonus, occupancy incentive, portfolio fee, vehicle allowance, health insurance, retirement match, total, and Y/Y growth
   - formula-linked summary references to EE Calcs totals

4. Define the property assumption named ranges across all 3 years.

Only the final workbook path above is graded.
