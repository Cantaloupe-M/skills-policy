You are a bakery replenishment planner reviewing weekly rack coverage.

Build a single Excel workbook at:

- `/root/bakery_weekly_commit_gap.xlsx`

Use this source workbook:

- `/root/Bakery_Rack_Weekly_Plan.xlsx`

The source workbook has:

- `Rack Snapshot` sheet (AsOfDate, HorizonEnd, SKU Ref, Cases on Rack, Avg Daily Pull)
- `Booking Feed` sheet (SKU Ref, ETA, Booked Cases, Booking State, Comment)
- `Pallet Defaults` sheet (Cases Per Pallet)

Important booking rules:

- Only count booking rows where `Booking State` is `Firm` or `Locked`.
- Ignore booking rows with blank SKU, blank ETA, invalid ETA text, or any other booking state.

Create exactly two sheets in this order:

1. `Rack_Coverage`
2. `Commit_Gap_Actions`

## Sheet 1: `Rack_Coverage`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:L6):

1. `SKU_Ref`
2. `Cases_On_Rack`
3. `Avg_Daily_Pull_Cases`
4. `Current_Days_On_Hand`
5. `Projected_OOS_Date`
6. `Booked_Cases_By_Horizon`
7. `Delivered_Days_On_Hand`
8. `Remaining_Demand_Cases`
9. `Additional_Cases_Needed`
10. `Pallets_Required`
11. `Required_Delivery_Date`
12. `Earlier_Delivery_Required`

One row per SKU Ref from `Rack Snapshot`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Rack Snapshot!B1`
- `HorizonEnd` = date in `Rack Snapshot!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Cases_On_Rack / Avg_Daily_Pull_Cases` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Booked_Cases_By_Horizon` = sum of qualifying `Booked Cases` for that SKU where `ETA <= HorizonEnd`
- `Delivered_Days_On_Hand` = `(Cases_On_Rack + Booked_Cases_By_Horizon) / Avg_Daily_Pull_Cases` when rate > 0, else blank
- `Remaining_Demand_Cases` = `Avg_Daily_Pull_Cases * PlanningDays`
- `Additional_Cases_Needed` = `max(0, Remaining_Demand_Cases - Cases_On_Rack - Booked_Cases_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Cases_Needed / Cases_Per_Pallet)` when additional cases > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest qualifying booking for that SKU, or no qualifying booking exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `E` and `K`.

## Sheet 2: `Commit_Gap_Actions`

Header row at row 1 (A1:E1):

1. `SKU_Ref`
2. `Required_Delivery_Date`
3. `Pallets_Required`
4. `Additional_Cases_Needed`
5. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each SKU appearing once and in the same order as `Rack_Coverage`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
