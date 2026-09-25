You are a planner coordinating zone-level replenishment for a beauty distribution floor.

Build a single Excel workbook at:

- `/root/beauty_zone_alias_gap.xlsx`

Use these source workbooks:

- `/root/Beauty_Zone_Stock.xlsx`
- `/root/Beauty_Mixed_Feed.xlsx`
- `/root/Beauty_Zone_Alias_Key.xlsx`

The stock workbook has:

- `Zone Snapshot` sheet (AsOfDate, HorizonEnd, Zone, SKU, On Hand, Daily Demand)

The mixed feed workbook has:

- `Zone Feed` sheet (Record Type, Dispatch Ref, Revision, Zone Alias, SKU Code, ETA, Units, Release State)

The alias workbook has:

- `Alias Map` sheet (Alias, Canonical Zone)

Important feed rules:

- Only rows where `Record Type` is `DELIVERY` are candidate inbound rows.
- If a `Dispatch Ref` appears multiple times, keep only the row with the highest `Revision` for that Dispatch Ref.
- After deduplication, only count rows where `Release State` is `Released` or `Staged`.
- Convert `Zone Alias` to the canonical zone using `Alias Map` before matching against stock rows.
- Ignore rows with unknown alias, blank SKU Code, blank ETA, invalid ETA text, or any other release state.
- Use a fixed pallet size of `36` units for all zone/SKU combinations.

Create exactly two sheets in this order:

1. `Zone_Coverage`
2. `Dispatch_Gap_List`

## Sheet 1: `Zone_Coverage`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:M6):

1. `Zone`
2. `SKU`
3. `Units_On_Hand`
4. `Daily_Demand_Units_Per_Day`
5. `Current_Days_On_Hand`
6. `Projected_OOS_Date`
7. `Inbound_Units_By_Horizon`
8. `Delivered_Days_On_Hand`
9. `Remaining_Demand_Units`
10. `Additional_Units_Needed`
11. `Pallets_Required`
12. `Required_Delivery_Date`
13. `Earlier_Delivery_Required`

Create one row per zone/SKU pair from `Zone Snapshot`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Zone Snapshot!B1`
- `HorizonEnd` = date in `Zone Snapshot!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `Units_On_Hand / Daily_Demand_Units_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Units_By_Horizon` = sum of qualifying `Units` for the same canonical Zone and SKU where `ETA <= HorizonEnd`
- `Delivered_Days_On_Hand` = `(Units_On_Hand + Inbound_Units_By_Horizon) / Daily_Demand_Units_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Units` = `Daily_Demand_Units_Per_Day * PlanningDays`
- `Additional_Units_Needed` = `max(0, Remaining_Demand_Units - Units_On_Hand - Inbound_Units_By_Horizon)`
- `Pallets_Required` = `ceil(Additional_Units_Needed / 36)` when additional units > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Pallets_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Required_Delivery_Date` is before the earliest qualifying inbound for that zone/SKU pair, or no qualifying inbound exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `F` and `L`.

## Sheet 2: `Dispatch_Gap_List`

Header row at row 1 (A1:F1):

1. `Zone`
2. `SKU`
3. `Required_Delivery_Date`
4. `Pallets_Required`
5. `Additional_Units_Needed`
6. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required > 0`, with each zone/SKU pair appearing once and in the same order as `Zone_Coverage`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
