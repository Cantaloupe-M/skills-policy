You are a warehouse load planner for a regional snack distribution center.

Build a single Excel workbook at:

- `/root/snack_dc_august_load_plan.xlsx`

Use this source workbook:

- `/root/Snack_DC_August_Balancing.xlsx`

The source workbook has:

- `Stock Snapshot` sheet (AsOfDate, HorizonEnd, Item Code, On Floor, Daily Sales)
- `Scheduled Inbounds` sheet (Item, Arrival Date, Cases Due)
- `Load Config` sheet (Cases Per Pallet)

Create exactly two sheets in this order:

1. `Load_Detail`
2. `Load_Action_Summary`

## Sheet 1: `Load_Detail`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:L6):

1. `Item_Code`
2. `On_Floor_Cases`
3. `Daily_Sales_Cases_Per_Day`
4. `Current_Days_On_Hand`
5. `Projected_OOS_Date`
6. `Inbound_Cases_By_Horizon`
7. `Delivered_Days_On_Hand`
8. `Remaining_Demand_Cases`
9. `Additional_Cases_Needed`
10. `Pallets_Required`
11. `Required_Delivery_Date`
12. `Earlier_Delivery_Required`

One row per Item Code from `Stock Snapshot`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Stock Snapshot!B1`
- `HorizonEnd` = date in `Stock Snapshot!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `On_Floor_Cases / Daily_Sales_Cases_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Cases_By_Horizon` = sum of `Cases Due` for that Item where `Arrival Date <= HorizonEnd`
- `Delivered_Days_On_Hand` = `(On_Floor_Cases + Inbound_Cases_By_Horizon) / Daily_Sales_Cases_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Cases` = `Daily_Sales_Cases_Per_Day * PlanningDays`
- `Additional_Cases_Needed` = `max(0, Remaining_Demand_Cases - On_Floor_Cases - Inbound_Cases_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Cases_Needed / Cases_Per_Pallet)` when additional cases > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest scheduled inbound for that Item, or no inbound exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `E` and `K`.

## Sheet 2: `Load_Action_Summary`

Header row at row 1 (A1:E1):

1. `Item_Code`
2. `Required_Delivery_Date`
3. `Pallets_Required`
4. `Additional_Cases_Needed`
5. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each Item appearing once and in the same order as `Load_Detail`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
