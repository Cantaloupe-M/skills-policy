You are a household goods planner refreshing a route dispatch tracker.

Update an existing Excel workbook at:

- `/root/Household_Route_Template.xlsx`

Save the updated workbook to:

- `/root/household_route_tracker_refresh.xlsx`

The template workbook already contains these sheets in this order:

1. `Overview`
2. `Coverage_Detail`
3. `Dispatch_Plan`
4. `Pack Matrix`
5. `Route Alias Map`

Additional source data:

- `/root/Household_Current_Stock.xlsx` with sheet `Route Snapshot`
- `/root/Household_Dispatch_Queue.xlsx` with sheet `Queue Export`

Rules for `Route Snapshot`:

- `B1` contains AsOfDate and `D1` contains HorizonEnd.
- Starting at row 3, each route appears as a section.
- A section starts with a row whose column A value looks like `Route <route code>`.
- The next row is that section's local header row: `SKU`, `On Hand Cases`, `Daily Demand`.
- The following rows until the next blank row or next `Route ` row are data rows for that route.

Rules for `Queue Export`:

- Only rows where `Row Type` is `DISPATCH` are candidate inbound rows.
- If a `Queue ID` appears multiple times, keep only the row with the highest `Revision No` for that Queue ID.
- After deduplication, only count rows where `Queue State` is `Approved` or `Released`.
- Convert `Route Alias` to the canonical route using the template sheet `Route Alias Map` before matching against stock rows.
- Use the route/SKU-specific `Cases Per Load` from the template sheet `Pack Matrix` when computing `Loads_Required`.
- Ignore rows with unknown alias, blank SKU, blank Ship Date, invalid Ship Date text, or any other queue state.

Preserve the sheet order exactly: `Overview`, `Coverage_Detail`, `Dispatch_Plan`, `Pack Matrix`, `Route Alias Map`.
Do not modify `Overview`, `Pack Matrix`, or `Route Alias Map`.
Clear and repopulate only `Coverage_Detail` and `Dispatch_Plan`.

## Sheet: `Coverage_Detail`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=HorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=PlanningDays`, `B4=<integer>`

Place this header row at row 6 (A6:M6):

1. `Route`
2. `SKU`
3. `On_Hand_Cases`
4. `Daily_Demand_Cases_Per_Day`
5. `Current_Days_On_Hand`
6. `Projected_OOS_Date`
7. `Inbound_Cases_By_Horizon`
8. `Delivered_Days_On_Hand`
9. `Remaining_Demand_Cases`
10. `Additional_Cases_Needed`
11. `Loads_Required`
12. `Required_Delivery_Date`
13. `Earlier_Delivery_Required`

Create one row per route/SKU pair from `Route Snapshot`, preserving encounter order across sections.

Calculation rules:

- `AsOfDate` = date in `Route Snapshot!B1`
- `HorizonEnd` = date in `Route Snapshot!D1`
- `PlanningDays` = calendar day difference `(HorizonEnd - AsOfDate)`
- `Current_Days_On_Hand` = `On_Hand_Cases / Daily_Demand_Cases_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_Days_On_Hand)` when rate > 0, else blank
- `Inbound_Cases_By_Horizon` = sum of qualifying `Cases` for the same canonical Route and SKU where `Ship Date <= HorizonEnd`
- `Delivered_Days_On_Hand` = `(On_Hand_Cases + Inbound_Cases_By_Horizon) / Daily_Demand_Cases_Per_Day` when rate > 0, else blank
- `Remaining_Demand_Cases` = `Daily_Demand_Cases_Per_Day * PlanningDays`
- `Additional_Cases_Needed` = `max(0, Remaining_Demand_Cases - On_Hand_Cases - Inbound_Cases_By_Horizon)`
- `Loads_Required` = `ceil(Additional_Cases_Needed / Cases_Per_Load)` when additional cases > 0, else `0`
- `Required_Delivery_Date`:
  - blank when `Loads_Required = 0`
  - else use `Projected_OOS_Date`
- `Earlier_Delivery_Required` = `TRUE` when loads required > 0 and (`Required_Delivery_Date` is before the earliest qualifying dispatch for that route/SKU pair, or no qualifying dispatch exists); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `F` and `L`.

## Sheet: `Dispatch_Plan`

Header row at row 1 (A1:F1):

1. `Route`
2. `SKU`
3. `Required_Delivery_Date`
4. `Loads_Required`
5. `Additional_Cases_Needed`
6. `Earlier_Delivery_Required`

Include only rows where `Loads_Required > 0`, with each route/SKU pair appearing once and in the same order as `Coverage_Detail`.

Constraints:

- Keep numeric fields numeric.
- Do not modify the `Overview`, `Pack Matrix`, or `Route Alias Map` sheets.
- Preserve the existing sheet order.
- Final answer must be the updated `.xlsx` file at the required output path.
