# Harbor Task: Property Management Compensation Model

## Objective

Build a multi-year Excel compensation workbook for a property management company's staff.

## Output

`/root/Property_Management.xlsx`

## Inputs (TWO source files)

1. `/root/building_specs.xlsx` — Building Specifications sheet with 10 buildings
   - Columns: Building ID, Building Name, Address, Property Type, Unit Count, Avg Unit Size, Management Fee Rate, Maintenance Reserve, Occupancy Rate

2. `/root/staff_roster.xlsx` — Staff Roster sheet with 87 staff members
   - Columns: Staff ID, Last Name, First Name, Title, Assigned Building, Yrs of Service, License Type, Units Managed

## Sheet Structure (exact 8 sheets, in this order)

1. `Summary` — Executive dashboard
2. `Assumptions` — All model parameters migrated from the input file
3. `Building Specs` — Building data migrated from building_specs.xlsx (10 buildings)
4. `Roster` — Full staff roster migrated from staff_roster.xlsx (87 staff)
5. `Calculations --->` — Navigation helper
6. `EE Calcs (Current)` — Year 1 calculations (rows 4–90, quarterly totals row 91)
7. `EE Calcs (Yr+1)` — Year 2 calculations
8. `EE Calcs (Yr+2)` — Year 3 calculations

## Compensation Components (8 components, rows 26–33 in Summary)

| Row | Component | Description |
|-----|-----------|-------------|
| 26 | Base Pay | Annual salary ÷ 4 |
| 27 | Property Mgmt Bonus | 4% of base annual (PropBns rate) |
| 28 | Occupancy Incentive | Building-level occupancy bonus (OccCap per year) |
| 29 | Portfolio Fee | 1.5% of base annual |
| 30 | Vehicle Allowance | $4800/yr flat |
| 31 | Health Insurance | Annual ÷ 4 |
| 32 | Retirement Match | 6% of base annual ÷ 4 |
| 33 | TOTAL | Formula-driven |
| 34 | Y/Y Growth | Formula-driven |

## Named Ranges

Define ALL assumptions as named ranges: BaseSal_Yr1, BaseSal_Yr2, BaseSal_Yr3, PropBns_Yr1, PropBns_Yr2, PropBns_Yr3, OccCap_Yr1, OccCap_Yr2, OccCap_Yr3, PortRate_Yr1, PortRate_Yr2, PortRate_Yr3, VehAllow_Yr1, VehAllow_Yr2, VehAllow_Yr3, HlthIns_Yr1, HlthIns_Yr2, HlthIns_Yr3, RetRate_Yr1, RetRate_Yr2, RetRate_Yr3, WHLim_Yr1, WHLim_Yr2, WHLim_Yr3, SSRate_Yr1, SSRate_Yr2, SSRate_Yr3, MedRate_Yr1, MedRate_Yr2, MedRate_Yr3, Sr5to9_Yr1, Sr5to9_Yr2, Sr5to9_Yr3, Sr10to14_Yr1, Sr10to14_Yr2, Sr10to14_Yr3, Sr15to19_Yr1, Sr15to19_Yr2, Sr15to19_Yr3, Sr20to24_Yr1, Sr20to24_Yr2, Sr20to24_Yr3, Sr25up_Yr1, Sr25up_Yr2, Sr25up_Yr3

## Two-File Merge Requirement

The model MUST read BOTH input files and merge them:
- staff_roster contains the Assigned Building field
- building_specs contains occupancy rates per building
- Merge on Building ID to compute Occupancy Incentive per employee

## Summary Sheet Formulas

The Summary sheet's TOTAL row (row 33) must reference the quarterly totals row from `EE Calcs (Current)` at row 91. Each cell should use cross-sheet reference like: `='EE Calcs (Current)'!C91`

## Verification

- 8-sheet structure
- 87 staff rows in EE Calcs
- Quarterly totals row 91 of each EE Calcs sheet
- Named ranges defined (at least 46)
