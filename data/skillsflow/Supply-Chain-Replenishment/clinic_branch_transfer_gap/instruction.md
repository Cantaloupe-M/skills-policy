You are a logistics coordinator for a medical supplies distributor serving a chain of clinics.

Build a single Excel workbook at:

- `/root/clinic_branch_transfer_gap.xlsx`

Use these source workbooks:

- `/root/Clinic_Branch_Inventory.xlsx`
- `/root/Clinic_Transfer_Schedule.xlsx`

The inventory workbook has:

- `Branch Stock` sheet (AsOfDate, HorizonEnd, Branch, Item, Units, Daily Use)

The transfer workbook has:

- `Planned Transfers` sheet (Transfer ID, Branch, Item, Transfer Date, Units Planned, Status)

Important deduplication and filtering rules:

- If a Transfer ID appears multiple times, keep only the row with the highest `Transfer Date` for that ID.
- After deduplication, only include transfers where `Status` is `Confirmed`. Ignore rows with `Tentative`, `Cancelled`, or any other status.

Create exactly two sheets in this order:

1. `Branch_Item_Coverage`
2. `Transfer_Gap_List`

## Sheet 1: `Branch_Item_Coverage`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:M6):

1. `Branch`
2. `Item`
3. `Units_On_Hand`
4. `Daily_Use_Units_Per_Day`
5. `Current_Days_On_Hand`
6. `Projected_OOS_Date`
7. `Inbound_Units_By_Horizon`
8. `Delivered_Days_On_Hand`
9. `Remaining_Demand_Units`
10. `Additional_Units_Needed`
11. `Pallets_Required`
12. `Required_Delivery_Date`
13. `Earlier_Delivery_Required`

One row per Branch-Item combination from `Branch Stock`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Branch Stock!B1`
- `HorizonEnd` = date in `Branch Stock!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Units_On_Hand / Daily_Use_Units_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Units_By_Horizon` = sum of `Units Planned` for that Branch+Item where `Transfer Date <= HorizonEnd` AND `Status` is `Confirmed` (after deduplication)
- `Delivered_Days_On_Hand` = `(Units_On_Hand + Inbound_Units_By_Horizon) / Daily_Use_Units_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Units` = `Daily_Use_Units_Per_Day * PlanningDays`
- `Additional_Units_Needed` = `max(0, Remaining_Demand_Units - Units_On_Hand - Inbound_Units_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Units_Needed / 48)` (standard pallet size is 48 units)
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest confirmed transfer for that Branch+Item, or no confirmed transfer exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `F` and `L`.

## Sheet 2: `Transfer_Gap_List`

Header row at row 1 (A1:F1):

1. `Branch`
2. `Item`
3. `Required_Delivery_Date`
4. `Pallets_Required`
5. `Additional_Units_Needed`
6. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each Branch-Item appearing once and in the same order as `Branch_Item_Coverage`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
