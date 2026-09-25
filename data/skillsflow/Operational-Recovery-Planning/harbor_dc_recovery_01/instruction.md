You are the Data Center Operations Director for a Manitoba IT data center operations facility.

Use the reference file `/root/Open_Server_Requests_Listing.xlsx` to build a **Server Provisioning Recovery Plan** covering January 22, 2018 through May 1, 2018.

Create exactly these two deliverables:

1. `/root/server_provisioning_recovery_plan_analysis.xlsx`
2. `/root/server_provisioning_recovery_summary.md`

## Workbook Requirements

The workbook must contain exactly 3 sheets with these names:

1. `Current Capacity and Racks`
2. `Relocated Network Equipment`
3. `10 hr Shift Relocate Network Eq`

All three sheets must use the same structure and column layout:

- `C2`: `Rack-Mount Web Servers`
- `F2`: `Blade Database Servers`
- `I2`: `Network Appliances`
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

- `2018-01-22`: Web `1065`, Database `855`
- `2018-02-01`: Web `855`, Database `555`
- `2018-02-15`: Web `900`, Database `900`
- `2018-03-01`: Web `900`, Database `575`
- `2018-04-02`: Web `900`, Database `575`
- `2018-05-01`: Web `900`, Database `575`
- All other dates: Web due `0`, Database due `0`

Operational constraints:

- Weekend days: Web/Database/Network Appliance planned production must all be `0`.
- Manitoba holidays: `2018-02-19` and `2018-03-30` must be `0` for Web/Database/Network Appliance.
- All planned quantities must be whole numbers `>= 0`.
- Blade Database Servers production start cannot be:
  - before `2018-03-01` in `Current Capacity and Racks`
  - before `2018-02-20` in `Relocated Network Equipment`
  - before `2018-02-20` in `10 hr Shift Relocate Network Eq`

Scenario constraints:

1. **Current Capacity and Racks**
   - Web planned production and Database planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Network Appliances total production (sum of column `I` from rows `4..103`) must be at least `1200`.

2. **Relocated Network Equipment**
   - Web planned production and Database planned production must each be:
     - `<= 120` before `2018-02-05`
     - `<= 135` on/after `2018-02-05`
   - Network Appliances output must be at least `100` total before `2018-02-01`.
   - Network Appliances output must be `0` on/after `2018-02-01`.

3. **10 hr Shift Relocate Network Eq**
   - Network Appliances output must be `0` for the entire horizon.
   - Dates where `Web > 135` or `Database > 135` represent the temporary 10-hour shift window:
     - each such day must be a working day on/after `2018-02-01`
     - any individual planned value (Web or Database) must be `<= 170`
     - the count of such days must be between `20` and `24` inclusive
   - Outside the temporary window:
     - each individual planned value (Web and Database) must be `<= 120` before `2018-02-05`
     - each individual planned value (Web and Database) must be `<= 135` on/after `2018-02-05`

## Summary Requirements

`/root/server_provisioning_recovery_summary.md` must include these sections and fields:

- `## Scenario 1`
- `## Scenario 2`
- `## Scenario 3`

Each section must include:

- `Actions:`
- `Rack-Mount Web Servers Impact:`
- `Blade Database Servers Impact:`
- `Network Appliances Impact:`
- `May PO On-Time:`

Required on-time statements:

- Scenario 1: `May PO On-Time: No`
- Scenario 2: `May PO On-Time: Web Yes, Database No`
- Scenario 3: `May PO On-Time: Yes`

Scenario 3 must explicitly mention the phrase `30-day notification`.
