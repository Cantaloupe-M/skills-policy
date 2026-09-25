You are a supply planner for a pet food distribution center.

Build a single Excel workbook at:

- `/root/petcare_midmonth_pallet_gap.xlsx`

Use this source workbook:

- `/root/Petcare_Midmonth_Snapshot.xlsx`

The source workbook has:

- `Current Stock` sheet (AsOfDate, HorizonEnd, SKU, Units On Hand, Daily Rate)
- `Expected Arrivals` sheet (SKU, Arrival Date, Cases Expected, Dock Status)
- `Pallet Guide` sheet (Cases Per Pallet)

Important filter rule:

- Only include arrivals where `Dock Status` is either `Committed` or `Arranged`. Ignore rows with any other status (e.g., `Pending`, `Tentative`).

Create exactly two sheets in this order:

1. `SKU_Coverage`
2. `Pallet_Gap_List`

## Sheet 1: `SKU_Coverage`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:L6):

1. `SKU`
2. `Units_On_Hand`
3. `Daily_Rate_Units_Per_Day`
4. `Current_Days_On_Hand`
5. `Projected_OOS_Date`
6. `Inbound_Units_By_Horizon`
7. `Delivered_Days_On_Hand`
8. `Remaining_Demand_Units`
9. `Additional_Units_Needed`
10. `Pallets_Required`
11. `Required_Delivery_Date`
12. `Earlier_Delivery_Required`

One row per SKU from `Current Stock`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Current Stock!B1`
- `HorizonEnd` = date in `Current Stock!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Units_On_Hand / Daily_Rate_Units_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Units_By_Horizon` = sum of `Cases Expected` for that SKU where `Arrival Date <= HorizonEnd` AND `Dock Status` is `Committed` or `Arranged`
- `Delivered_Days_On_Hand` = `(Units_On_Hand + Inbound_Units_By_Horizon) / Daily_Rate_Units_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Units` = `Daily_Rate_Units_Per_Day * PlanningDays`
- `Additional_Units_Needed` = `max(0, Remaining_Demand_Units - Units_On_Hand - Inbound_Units_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Units_Needed / Cases_Per_Pallet)` when additional units > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest qualifying inbound for that SKU, or no qualifying inbound exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `E` and `K`.

## Sheet 2: `Pallet_Gap_List`

Header row at row 1 (A1:E1):

1. `SKU`
2. `Required_Delivery_Date`
3. `Pallets_Required`
4. `Additional_Units_Needed`
5. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each SKU appearing once and in the same order as `SKU_Coverage`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
