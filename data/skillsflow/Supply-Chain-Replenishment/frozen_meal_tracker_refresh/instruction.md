You are a demand planner for a frozen meal distribution network.

Update an existing Excel workbook at:

- `/root/Frozen_Meal_Template.xlsx`

Save the updated workbook to:

- `/root/frozen_meal_recovery_tracker.xlsx`

The template workbook already contains:

- `Instructions` sheet (do not modify)
- `Coverage_Detail` sheet (clear and repopulate)
- `Recovery_Loads` sheet (clear and repopulate)
- `Pallet Guide` sheet (read-only, contains per-SKU Cases Per Pallet)

Additional source data:

- `/root/Frozen_Meal_Current_Stock.xlsx` with sheet `Stock` (AsOfDate, HorizonEnd, SKU, Units, Daily Rate)
- `/root/Frozen_Meal_Recovery_Log.xlsx` with sheet `Recovery Log` (Load ID, Revision, SKU, Load Date, Units, Stage)

Important deduplication and filtering rules for Recovery Log:

- If a Load ID appears multiple times with different Revisions, keep only the row with the highest Revision for that Load ID.
- After deduplication, only include loads where `Stage` is either `Booked` or `Loaded`. Ignore rows with `Tentative`, `Cancelled`, or any other stage.

Preserve the sheet order: `Instructions`, `Coverage_Detail`, `Recovery_Loads`, `Pallet Guide`.

## Sheet: `Coverage_Detail`

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
10. `Loads_Required`
11. `Required_Delivery_Date`
12. `Earlier_Delivery_Required`

One row per SKU from `Stock`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Stock!B1`
- `HorizonEnd` = date in `Stock!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Units_On_Hand / Daily_Rate_Units_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Units_By_Horizon` = sum of `Units` for that SKU where `Load Date <= HorizonEnd` AND `Stage` is `Booked` or `Loaded` (after deduplication)
- `Delivered_Days_On_Hand` = `(Units_On_Hand + Inbound_Units_By_Horizon) / Daily_Rate_Units_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Units` = `Daily_Rate_Units_Per_Day * PlanningDays`
- `Additional_Units_Needed` = `max(0, Remaining_Demand_Units - Units_On_Hand - Inbound_Units_By_Horizon)`
- `Loads_Required` = `ceil(Additional_Units_Needed / Cases_Per_Pallet)` using per-SKU Cases Per Pallet from `Pallet Guide` sheet
- `Required_Delivery_Date`:
  - blank when `Loads_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when loads required > 0 and (`Required_Delivery_Date` is before the earliest qualifying load for that SKU, or no qualifying load exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `E` and `K`.

## Sheet: `Recovery_Loads`

Header row at row 1 (A1:E1):

1. `SKU`
2. `Required_Delivery_Date`
3. `Loads_Required`
4. `Additional_Units_Needed`
5. `Earlier_Delivery_Required`

Include only rows where `Loads_Required > 0`, with each SKU appearing once and in the same order as `Coverage_Detail`.

Constraints:

- Keep numeric fields numeric.
- Do not modify the `Instructions` or `Pallet Guide` sheets.
- Preserve the existing sheet order.
- Final answer must be the updated `.xlsx` file at the required output path.
