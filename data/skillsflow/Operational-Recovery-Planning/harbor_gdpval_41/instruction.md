You are the Production Manager for a Manitoba automotive accessory plant.

Use the reference file `/root/Open_Purchase_Orders_Listing.xlsx` to build a **Running Board Recovery Plan** covering January 22, 2018 through May 1, 2018.

Create exactly these two deliverables:

1. `/root/running_board_recovery_plan_analysis.xlsx`
2. `/root/running_board_recovery_summary.md`

## Workbook Requirements

The workbook must contain exactly 3 sheets with these names:

1. `Current Capacity and Cells`
2. `Relocated Grill Guard`
3. `10 hr Shift Relocate Grill Guar`

All three sheets must use the same structure and column layout:

- `C2`: `Crew Cab Running Boards`
- `F2`: `Extended Cab Running Boards`
- `I2`: `Grill Guard`
- `C3:K3` headers:
  - `Planned Production`
  - `Purchase Orders Due`
  - `Cumulative Open Purchase Orders (EOD)`
  - `Planned Production`
  - `Purchase Orders Due`
  - `Cumulative Open Purchase Orders (EOD)`
  - `Actual Var to PO`
  - `Total Prod`
  - `Notes`

Use rows `4..103` for the date horizon (100 calendar days, inclusive):

- Row 4 date = `2018-01-22`
- Row 103 date = `2018-05-01`
- Dates must increment by exactly 1 day per row.

Column rules:

- `B`: Date values (literal dates or `=B(previous)+1` formulas)
- `C,D,F,G,I`: numeric constants only (no formulas)
- `E,H,J`: formulas (not hard-coded numbers)

PO due quantities (same on all 3 sheets):

- `2018-01-22`: Crew `1065`, Extended `855`
- `2018-02-01`: Crew `855`, Extended `555`
- `2018-02-15`: Crew `900`, Extended `900`
- `2018-03-01`: Crew `900`, Extended `575`
- `2018-04-02`: Crew `900`, Extended `575`
- `2018-05-01`: Crew `900`, Extended `575`
- All other dates: Crew due `0`, Extended due `0`

Operational constraints:

- Weekend days: Crew/Extended/Grill Guard planned production must all be `0`.
- Manitoba holidays: `2018-02-19` and `2018-03-30` must be `0` for Crew/Extended/Grill Guard.
- All planned quantities must be whole numbers `>= 0`.
- Extended Cab production start cannot be:
  - before `2018-03-01` in `Current Capacity and Cells`
  - before `2018-02-20` in `Relocated Grill Guard`
  - before `2018-02-20` in `10 hr Shift Relocate Grill Guar`

Scenario constraints:

1. **Current Capacity and Cells**
   - Crew planned production and Extended planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Grill Guard total production (sum of column `I` from rows `4..103`) must be at least `1200`.

2. **Relocated Grill Guard**
   - Crew planned production and Extended planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Grill Guard output must be at least `100` total before `2018-02-01`.
   - Grill Guard output must be `0` on/after `2018-02-01`.

3. **10 hr Shift Relocate Grill Guar**
   - Grill Guard output must be `0` for the entire horizon.
   - Dates where `Crew > 135` or `Extended > 135` represent the temporary 10-hour shift window:
     - each such day must be a working day on/after `2018-02-01`
     - any individual planned value (Crew or Extended) must be `<= 170`
     - the count of such days must be between `20` and `24` inclusive
   - Outside the temporary window:
     - each individual planned value (Crew and Extended) must be `<= 120` before `2018-02-05`
     - each individual planned value (Crew and Extended) must be `<= 135` on/after `2018-02-05`

## Summary Requirements

`/root/running_board_recovery_summary.md` must include these sections and fields:

- `## Scenario 1`
- `## Scenario 2`
- `## Scenario 3`

Each section must include:

- `Actions:`
- `Crew Cab Impact:`
- `Extended Cab Impact:`
- `Grill Guard Impact:`
- `May PO On-Time:`

Required on-time statements:

- Scenario 1: `May PO On-Time: No`
- Scenario 2: `May PO On-Time: Crew Yes, Extended No`
- Scenario 3: `May PO On-Time: Yes`

Scenario 3 must explicitly mention the phrase `30-day notification`.
