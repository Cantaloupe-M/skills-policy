You are the Farm Operations Manager for a Manitoba agricultural harvest operations facility.

Use the reference file `/root/Open_Harvest_Orders_Listing.xlsx` to build a **Harvest Recovery Plan** covering January 22, 2018 through May 1, 2018.

Create exactly these two deliverables:

1. `/root/harvest_recovery_plan_analysis.xlsx`
2. `/root/harvest_recovery_summary.md`

## Workbook Requirements

The workbook must contain exactly 3 sheets with these names:

1. `Current Equipment and Bins`
2. `Relocated Flax Processing`
3. `10 hr Shift Relocate Flax Proc`

All three sheets must use the same structure and column layout:

- `C2`: `Wheat Bin Loads`
- `F2`: `Canola Bin Loads`
- `I2`: `Flax Processing`
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

- `2018-01-22`: Wheat `1065`, Canola `855`
- `2018-02-01`: Wheat `855`, Canola `555`
- `2018-02-15`: Wheat `900`, Canola `900`
- `2018-03-01`: Wheat `900`, Canola `575`
- `2018-04-02`: Wheat `900`, Canola `575`
- `2018-05-01`: Wheat `900`, Canola `575`
- All other dates: Wheat due `0`, Canola due `0`

Operational constraints:

- Weekend days: Wheat/Canola/Flax planned production must all be `0`.
- Manitoba holidays: `2018-02-19` and `2018-03-30` must be `0` for Wheat/Canola/Flax.
- All planned quantities must be whole numbers `>= 0`.
- Canola Bin Loads production start cannot be:
  - before `2018-03-01` in `Current Equipment and Bins`
  - before `2018-02-20` in `Relocated Flax Processing`
  - before `2018-02-20` in `10 hr Shift Relocate Flax Proc`

Scenario constraints:

1. **Current Equipment and Bins**
   - Wheat planned production and Canola planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Flax Processing total production (sum of column `I` from rows `4..103`) must be at least `1200`.

2. **Relocated Flax Processing**
   - Wheat planned production and Canola planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Flax Processing output must be at least `100` total before `2018-02-01`.
   - Flax Processing output must be `0` on/after `2018-02-01`.

3. **10 hr Shift Relocate Flax Proc**
   - Flax Processing output must be `0` for the entire horizon.
   - Dates where `Wheat > 135` or `Canola > 135` represent the temporary 10-hour shift window:
     - each such day must be a working day on/after `2018-02-01`
     - any individual planned value (Wheat or Canola) must be `<= 170`
     - the count of such days must be between `20` and `24` inclusive
   - Outside the temporary window:
     - each individual planned value (Wheat and Canola) must be `<= 120` before `2018-02-05`
     - each individual planned value (Wheat and Canola) must be `<= 135` on/after `2018-02-05`

## Summary Requirements

`/root/harvest_recovery_summary.md` must include these sections and fields:

- `## Scenario 1`
- `## Scenario 2`
- `## Scenario 3`

Each section must include:

- `Actions:`
- `Wheat Bin Loads Impact:`
- `Canola Bin Loads Impact:`
- `Flax Processing Impact:`
- `May PO On-Time:`

Required on-time statements:

- Scenario 1: `May PO On-Time: No`
- Scenario 2: `May PO On-Time: Wheat Yes, Canola No`
- Scenario 3: `May PO On-Time: Yes`

Scenario 3 must explicitly mention the phrase `30-day notification`.
