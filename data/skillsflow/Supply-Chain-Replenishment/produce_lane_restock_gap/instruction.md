You are a produce operations planner balancing replenishment across cooler lanes.

Build a single Excel workbook at:

- `/root/produce_lane_restock_gap.xlsx`

Use these source workbooks:

- `/root/Produce_Lane_Inventory.xlsx`
- `/root/Produce_Arrivals.xlsx`

The inventory workbook has:

- `Lane Snapshot` sheet

Layout rules for `Lane Snapshot`:

- `B1` contains AsOfDate and `D1` contains HorizonEnd.
- Starting at row 3, each lane appears as a section.
- A section starts with a row whose column A value looks like `Lane: <lane name>`.
- The next row is that section's local header row: `SKU`, `Cases`, `Daily Pull`.
- The following rows until the next blank row or next `Lane:` row are data rows for that lane.

The arrivals workbook has:

- `Arrival Board` sheet (Lane, SKU, ETA, Cases, Load Status)

Important arrival rules:

- Only count rows where `Load Status` is `Ready` or `Docked`.
- Ignore rows with blank lane, blank SKU, blank ETA, invalid ETA text, or any other status.
- Use a fixed pallet size of `54` cases for all lane/SKU combinations.

Create exactly two sheets in this order:

1. `Lane_Coverage`
2. `Restock_Actions`

## Sheet 1: `Lane_Coverage`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:M6):

1. `Lane`
2. `SKU`
3. `Cases_On_Hand`
4. `Daily_Pull_Cases_Per_Day`
5. `Current_Days_On_Hand`
6. `Projected_OOS_Date`
7. `Inbound_Cases_By_Horizon`
8. `Delivered_Days_On_Hand`
9. `Remaining_Demand_Cases`
10. `Additional_Cases_Needed`
11. `Pallets_Required`
12. `Required_Delivery_Date`
13. `Earlier_Delivery_Required`

Create one row per lane/SKU pair from `Lane Snapshot`, preserving encounter order across sections.

Calculation rules:

- `AsOfDate` = date in `Lane Snapshot!B1`
- `HorizonEnd` = date in `Lane Snapshot!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Cases_On_Hand / Daily_Pull_Cases_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Cases_By_Horizon` = sum of qualifying `Cases` for the same Lane and SKU where `ETA <= HorizonEnd`
- `Delivered_Days_On_Hand` = `(Cases_On_Hand + Inbound_Cases_By_Horizon) / Daily_Pull_Cases_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Cases` = `Daily_Pull_Cases_Per_Day * PlanningDays`
- `Additional_Cases_Needed` = `max(0, Remaining_Demand_Cases - Cases_On_Hand - Inbound_Cases_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Cases_Needed / 54)` when additional cases > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest qualifying arrival for that Lane and SKU, or no qualifying arrival exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `F` and `L`.

## Sheet 2: `Restock_Actions`

Header row at row 1 (A1:F1):

1. `Lane`
2. `SKU`
3. `Required_Delivery_Date`
4. `Pallets_Required`
5. `Additional_Cases_Needed`
6. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each lane/SKU pair appearing once and in the same order as `Lane_Coverage`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
