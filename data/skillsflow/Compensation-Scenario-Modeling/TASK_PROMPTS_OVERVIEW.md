# Compensation Scenario Modeling: Task Prompt Overview

This document organizes the eight task prompts in the difficulty order declared by `ALL_TASK_DIFFICULTY_RANKING.json`. All tasks are **hard** spreadsheet-modeling tasks and require a formula-driven, three-year compensation workbook.

## Task Matrix

| # | Task | Domain | Inputs | Output workbook | Workbook sheets | EE totals row |
|---|---|---|---:|---|---:|---:|
| 01 | Orchestra Foundation Model | Union orchestra | 1 | `Orchestra_Compensation.xlsx` | 7 | 107 |
| 02 | Orchestra Archive Refresh Model | Festival orchestra | 1 | `Festival_Orchestra_Compensation.xlsx` | 7 | 107 |
| 03 | University Faculty Model | Full-time faculty | 1 | `University_Compensation.xlsx` | 7 | 79 |
| 04 | University Termload Refresh Model | Full-time faculty | 1 | `Faculty_Termload_Compensation.xlsx` | 7 | 79 |
| 05 | Property Management Model | Property-management staff | 2 | `Property_Management.xlsx` | 8 | 91 |
| 06 | Property Portfolio Refresh Model | Property-operations staff | 2 | `Portfolio_Services_Compensation.xlsx` | 8 | 91 |
| 07 | Airline Crew Model | Flight crew | 1 | `Airline_Crew_Compensation.xlsx` | 7 | 69 |
| 08 | Construction Union Model | Ironworkers Union Local 401 | 3 | `Construction_Union.xlsx` | 7 | 94 |

## Shared Requirements

- Build the final workbook at the exact `/root/...xlsx` path stated for the task.
- Use formula-driven quarterly and summary outputs; do not hardcode summary totals or year-over-year growth.
- Preserve all required source assumptions and roster records without loss or duplication.
- Maintain the requested worksheet names and order exactly.
- Use `Summary`, `Assumptions`, `Roster`, `Calculations --->`, and three `EE Calcs` worksheets unless the property tasks additionally require `Building Specs`.
- Define the specified assumption named ranges for every required year.
- Project years of service on future-year calculation sheets when stated by the task.

## 01. Orchestra Foundation Model

**Source prompt:** [instruction.md](01_orchestra_foundation_model/instruction.md)

- **Input:** `/root/orchestra_assumptions_and_roster.xlsx`
- **Output:** `/root/Orchestra_Compensation.xlsx`
- **Required sheets:** `Summary`, `Assumptions`, `Roster`, `Calculations --->`, `EE Calcs (Current)`, `EE Calcs (Yr+1)`, `EE Calcs (Yr+2)`.
- **Model:** Formula-driven three-year (Current, Year + 1, Year + 2) union-orchestra scenario model.
- **Summary drivers:** MWS, premiums, media fee, withholding/tax rates, and seniority tiers for all three years.
- **Summary components:** MWS, Overscale, Principal Pay, Media Exploitation, Seniority, Payroll Tax, Total Compensation Expense, and Y/Y Growth.
- **Calculation requirements:** Per-employee quarterly formulas; tiered payroll-tax treatment; quarterly aggregates in row 107; future sheets advance years of service by one year each.
- **Named ranges:** Key MWS, principal-tier, media, payroll-tax tier/limit, and seniority-tier assumptions for all years.

## 02. Orchestra Archive Refresh Model

**Source prompt:** [instruction.md](02_orchestra_archive_refresh_model/instruction.md)

- **Input:** `/root/festival_archive_packet.xlsx`
- **Output:** `/root/Festival_Orchestra_Compensation.xlsx`
- **Exclude:** The source `Archive Notes` worksheet is context only and must not appear in the deliverable.
- **Required sheets:** Same seven-sheet orchestra structure as task 01.
- **Model:** Formula-linked, three-year compensation model for a union-style festival orchestra roster.
- **Summary:** Three-year weekly-scale, principal-premium, media-fee, withholding-limit/rate, and seniority-tier drivers; quarterly rows for the eight orchestra metrics from task 01.
- **Calculation requirements:** Preserve the quarterly employee layout; aggregate quarterly totals in row 107; advance service years in Year + 1 and Year + 2; link all totals and Y/Y values by formula.
- **Named ranges:** Full orchestra assumption set across all three years.

## 03. University Faculty Model

**Source prompt:** [instruction.md](03_university_faculty_model/instruction.md)

- **Input:** `/root/university_assumptions_and_roster.xlsx`
- **Output:** `/root/University_Compensation.xlsx`
- **Population:** 75 full-time faculty.
- **Required sheets:** Standard seven-sheet structure; each EE Calcs sheet contains faculty rows 4-78 and quarterly totals in row 79.
- **Summary rows 26-34:** Base Pay (9-Month), Summer Session Pay, Sabbatical Bonus, Department Stipend, Media Rights Allocation, Health Insurance, Retirement Match, Total, and Y/Y Growth.
- **Core formulas:** Base salary is annual salary / 52 x 13; summer pay is credits x rate / 4; sabbatical is 10% of base when eligible; department stipend is rank-based; media pool is allocated per faculty member; retirement uses the stated cap and match-rate logic.
- **Projection rules:** Year 2 uses 3% base-wage growth and +1 service year; Year 3 uses 6% cumulative growth and +2 service years.
- **Named ranges:** All 50 specified faculty ranges, covering salary, summer, sabbatical, rank stipends, media, health, retirement, tax, and seniority drivers across Years 1-3.
- **Additional checks:** `Summary!B1` organization name; `C5` starting base salary; `D5` formula `=C5*1.03`; all summary quarterly values link to EE Calcs totals.

## 04. University Termload Refresh Model

**Source prompt:** [instruction.md](04_university_termload_refresh_model/instruction.md)

- **Input:** `/root/faculty_termload_packet.xlsx`
- **Output:** `/root/Faculty_Termload_Compensation.xlsx`
- **Exclude:** The source `Packet Notes` sheet must not appear in the final workbook.
- **Required sheets:** Standard seven-sheet faculty structure.
- **Model:** Preserve faculty assumptions and roster, with EE Calcs quarterly totals in row 79.
- **Summary components:** The same seven faculty compensation components as task 03, followed by Total and Y/Y Growth.
- **Formula rules:** Define faculty named ranges for three years, advance service years on projected sheets, cross-link Summary totals to EE Calcs, and calculate Total/Y/Y rows by formula.

## 05. Property Management Model

**Source prompt:** [instruction.md](05_property_management_model/instruction.md)

- **Inputs:** `/root/building_specs.xlsx` (10 buildings) and `/root/staff_roster.xlsx` (87 staff).
- **Output:** `/root/Property_Management.xlsx`
- **Required sheets:** `Summary`, `Assumptions`, `Building Specs`, `Roster`, `Calculations --->`, and three EE Calcs sheets.
- **Merge requirement:** Join staff `Assigned Building` to building specifications by Building ID to calculate each employee's Occupancy Incentive.
- **Calculation layout:** 87 employees in rows 4-90; quarterly totals in row 91.
- **Summary rows 26-34:** Base Pay, Property Mgmt Bonus, Occupancy Incentive, Portfolio Fee, Vehicle Allowance, Health Insurance, Retirement Match, Total, and Y/Y Growth.
- **Core rules:** Base pay is annual salary / 4; property bonus is 4% of base annual; portfolio fee is 1.5%; vehicle allowance is $4,800 annually; health and retirement are quarterly allocations.
- **Named ranges:** All listed three-year property assumptions; verifier requires at least 46 named ranges.
- **Summary linkage:** Total row 33 references the EE Calcs quarterly total row by cross-sheet formulas.

## 06. Property Portfolio Refresh Model

**Source prompt:** [instruction.md](06_property_portfolio_refresh_model/instruction.md)

- **Inputs:** `/root/asset_register_packet.xlsx` and `/root/operations_roster_packet.xlsx`.
- **Output:** `/root/Portfolio_Services_Compensation.xlsx`
- **Exclude:** `Packet Notes` tabs in both sources are context-only and must be omitted from the deliverable.
- **Required sheets:** Standard eight-sheet property structure, including `Building Specs` and `Roster`.
- **Data migration:** Asset/building data goes to `Building Specs`; staff data goes to `Roster`.
- **Model:** Standard three-year property compensation model; EE Calcs quarterly totals are in row 91.
- **Summary components:** Base Pay, Property Bonus, Occupancy Incentive, Portfolio Fee, Vehicle Allowance, Health Insurance, Retirement Match, Total, and Y/Y Growth.
- **Formula rules:** Define three-year property named ranges and link Summary values to EE Calcs totals by formula.

## 07. Airline Crew Model

**Source prompt:** [instruction.md](07_airline_crew_model/instruction.md)

- **Input:** `/root/airline_assumptions_and_roster.xlsx`
- **Output:** `/root/Airline_Crew_Compensation.xlsx`
- **Population:** 65 flight crew; EE Calcs data rows 4-68, quarterly totals row 69.
- **Required sheets:** Standard seven-sheet structure.
- **Summary rows 26-33:** Base Salary, Flight Pay Premium, Per Diem, Hotel Stipend, Uniform Allowance, Loyalty Bonus, Total, and Y/Y Growth.
- **Conditional logic:** Per diem is paid only when attendance is at least 85%; formula is `IF(attendance_rate >= 0.85, per_diem_amount, 0)`.
- **Loyalty logic:** Five service tiers: Bronze (3-5 years), Silver (6-10), Gold (11-15), Platinum (16-20), Diamond (20+), with their specified annual bonuses.
- **Named ranges:** All listed salary, flight-pay, per-diem, hotel, uniform, loyalty, health, retirement, tax, and seniority assumptions for three years; verifier requires at least 65 ranges.
- **Summary linkage:** Total row 32 cross-references the quarterly total row in `EE Calcs (Current)`.

## 08. Construction Union Model

**Source prompt:** [instruction.md](08_construction_union_model/instruction.md)

- **Inputs:** `/root/union_assumptions_and_roster.xlsx` (90 members), `/root/project_codes.xlsx` (10 projects), and `/root/member_projects.xlsx` (assignments).
- **Output:** `/root/Construction_Union.xlsx`
- **Required sheets:** Standard seven-sheet structure.
- **Calculation layout:** Member rows 4-93; quarterly totals in row 94.
- **Summary rows 26-35:** Hourly Wages, Fringe Benefits, Health Insurance, Pension Contribution, NEBF Contribution, Training Fund, Annuity Fund, Union Dues, Total, and Y/Y Growth.
- **Compensation rules:** Use hourly rates and 2,080 hours; account for shift differential; calculate the stated fringe, health, pension, NEBF, training, annuity, and dues formulas.
- **Tier logic:** Apprenticeship Years 1-3, Journeyman, Foreman, and General Foreman use their corresponding named rates. Shift differentials are $0 day, $3 afternoon, and $5 night per hour.
- **Data integration:** Read all three files; project data may be used for assignment tracking.
- **Named ranges:** All listed three-year wage, benefit, shift, overtime, hours, allowance, tax, and seniority assumptions; verifier requires at least 85 ranges.
- **Summary linkage:** Total row 34 cross-references the `EE Calcs (Current)` row 94 quarterly totals.

## Source Files

| # | Original prompt |
|---|---|
| 01 | [01_orchestra_foundation_model/instruction.md](01_orchestra_foundation_model/instruction.md) |
| 02 | [02_orchestra_archive_refresh_model/instruction.md](02_orchestra_archive_refresh_model/instruction.md) |
| 03 | [03_university_faculty_model/instruction.md](03_university_faculty_model/instruction.md) |
| 04 | [04_university_termload_refresh_model/instruction.md](04_university_termload_refresh_model/instruction.md) |
| 05 | [05_property_management_model/instruction.md](05_property_management_model/instruction.md) |
| 06 | [06_property_portfolio_refresh_model/instruction.md](06_property_portfolio_refresh_model/instruction.md) |
| 07 | [07_airline_crew_model/instruction.md](07_airline_crew_model/instruction.md) |
| 08 | [08_construction_union_model/instruction.md](08_construction_union_model/instruction.md) |
