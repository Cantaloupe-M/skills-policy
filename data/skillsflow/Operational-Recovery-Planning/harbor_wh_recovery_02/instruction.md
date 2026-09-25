You are the Warehouse Operations Manager for a Manitoba warehouse fulfillment operations facility.

Use the reference file `/root/Open_Fulfillment_Orders_Listing.xlsx` to build a **Fulfillment Recovery Plan** covering January 22, 2018 through May 1, 2018.

Create exactly these two deliverables:

1. `/root/fulfillment_recovery_plan_analysis.xlsx`
2. `/root/fulfillment_recovery_summary.md`

## Workbook Requirements

The workbook must contain exactly 3 sheets with these names:

1. `Current Capacity and Zones`
2. `Relocated Bulk Storage`
3. `10 hr Shift Relocate Bulk Stor`

All three sheets must use the same structure and column layout:

- `C2`: `Priority Express Orders`
- `F2`: `Standard Freight Orders`
- `I2`: `Bulk Pallet Loads`
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

- `2018-01-22`: Express `1065`, Standard `855`
- `2018-02-01`: Express `855`, Standard `555`
- `2018-02-15`: Express `900`, Standard `900`
- `2018-03-01`: Express `900`, Standard `575`
- `2018-04-02`: Express `900`, Standard `575`
- `2018-05-01`: Express `900`, Standard `575`
- All other dates: Express due `0`, Standard due `0`

Operational constraints:

- Weekend days: Express/Standard/Bulk Pallet planned production must all be `0`.
- Manitoba holidays: `2018-02-19` and `2018-03-30` must be `0` for Express/Standard/Bulk Pallet.
- All planned quantities must be whole numbers `>= 0`.
- Standard Freight Orders production start cannot be:
  - before `2018-03-01` in `Current Capacity and Zones`
  - before `2018-02-20` in `Relocated Bulk Storage`
  - before `2018-02-20` in `10 hr Shift Relocate Bulk Stor`

Scenario constraints:

1. **Current Capacity and Zones**
   - Express planned production and Standard planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Bulk Pallet Loads total production (sum of column `I` from rows `4..103`) must be at least `1200`.

2. **Relocated Bulk Storage**
   - Express planned production and Standard planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Bulk Pallet Loads output must be at least `100` total before `2018-02-01`.
   - Bulk Pallet Loads output must be `0` on/after `2018-02-01`.

3. **10 hr Shift Relocate Bulk Stor**
   - Bulk Pallet Loads output must be `0` for the entire horizon.
   - Dates where `Express > 135` or `Standard > 135` represent the temporary 10-hour shift window:
     - each such day must be a working day on/after `2018-02-01`
     - any individual planned value (Express or Standard) must be `<= 170`
     - the count of such days must be between `20` and `24` inclusive
   - Outside the temporary window:
     - each individual planned value (Express and Standard) must be `<= 120` before `2018-02-05`
     - each individual planned value (Express and Standard) must be `<= 135` on/after `2018-02-05`

## Summary Requirements

`/root/fulfillment_recovery_summary.md` must include these sections and fields:

- `## Scenario 1`
- `## Scenario 2`
- `## Scenario 3`

Each section must include:

- `Actions:`
- `Priority Express Orders Impact:`
- `Standard Freight Orders Impact:`
- `Bulk Pallet Loads Impact:`
- `May PO On-Time:`

Required on-time statements:

- Scenario 1: `May PO On-Time: No`
- Scenario 2: `May PO On-Time: Express Yes, Standard No`
- Scenario 3: `May PO On-Time: Yes`

Scenario 3 must explicitly mention the phrase `30-day notification`.
