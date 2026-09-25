# Harbor Task: Construction Union Compensation Model

## Objective

Build a multi-year Excel compensation workbook for Ironworkers Union Local 401 members.

## Output

`/root/Construction_Union.xlsx`

## Inputs (THREE source files)

1. `/root/union_assumptions_and_roster.xlsx` — Assumptions + Member Roster (90 members)
2. `/root/project_codes.xlsx` — Active project codes (10 projects)
3. `/root/member_projects.xlsx` — Member-to-project assignments

## Sheet Structure (exact 7 sheets, in this order)

1. `Summary` — Executive dashboard
2. `Assumptions` — All model parameters
3. `Roster` — Full union member roster (90 members)
4. `Calculations --->` — Navigation helper
5. `EE Calcs (Current)` — Year 1 calculations (rows 4–93, quarterly totals row 94)
6. `EE Calcs (Yr+1)` — Year 2 calculations
7. `EE Calcs (Yr+2)` — Year 3 calculations

## Compensation Components (10 components, rows 26–34 in Summary)

| Row | Component | Description |
|-----|-----------|-------------|
| 26 | Hourly Wages | Hourly rate × 2080 hrs + shift differential |
| 27 | Fringe Benefits | Fringe rate × 2080 hrs |
| 28 | Health Insurance | HlthRate × 2080 hrs |
| 29 | Pension Contribution | PensRate × 2080 hrs |
| 30 | NEBF Contribution | 3% of gross wages |
| 31 | Training Fund | TrainRate × 2080 hrs |
| 32 | Annuity Fund | AnnuityRate × 2080 hrs |
| 33 | Union Dues | 2.5% of gross wages (deducted) |
| 34 | TOTAL | Formula-driven |
| 35 | Y/Y Growth | Formula-driven |

## Apprenticeship Tier System

| Tier | Hourly Rate |
|------|------------|
| Apprentice Yr1 | ApprenticeRate1 |
| Apprentice Yr2 | ApprenticeRate2 |
| Apprentice Yr3 | ApprenticeRate3 |
| Journeyman | JourneyRate |
| Foreman | ForemanRate |
| General Foreman | GenForemanRate |

## Shift Differentials

| Shift | Differential |
|-------|-------------|
| Day | $0 |
| Afternoon | $3.00/hr |
| Night | $5.00/hr |

## Multi-File Merge

The model must:
1. Read union_assumptions_and_roster.xlsx for member data and assumptions
2. Read project_codes.xlsx for project information
3. Read member_projects.xlsx for member-project assignments
4. Optionally use project data for assignment tracking

## Named Ranges

Define ALL assumptions as named ranges: ApprenticeRate1_Yr1, ApprenticeRate1_Yr2, ApprenticeRate1_Yr3, ApprenticeRate2_Yr1, ApprenticeRate2_Yr2, ApprenticeRate2_Yr3, ApprenticeRate3_Yr1, ApprenticeRate3_Yr2, ApprenticeRate3_Yr3, JourneyRate_Yr1, JourneyRate_Yr2, JourneyRate_Yr3, ForemanRate_Yr1, ForemanRate_Yr2, ForemanRate_Yr3, GenForemanRate_Yr1, GenForemanRate_Yr2, GenForemanRate_Yr3, FringeRate_Yr1, FringeRate_Yr2, FringeRate_Yr3, HlthRate_Yr1, HlthRate_Yr2, HlthRate_Yr3, PensRate_Yr1, PensRate_Yr2, PensRate_Yr3, NEBFRate_Yr1, NEBFRate_Yr2, NEBFRate_Yr3, UnionDuesRate_Yr1, UnionDuesRate_Yr2, UnionDuesRate_Yr3, TrainRate_Yr1, TrainRate_Yr2, TrainRate_Yr3, AnnuityRate_Yr1, AnnuityRate_Yr2, AnnuityRate_Yr3, Shift2_Yr1, Shift2_Yr2, Shift2_Yr3, Shift3_Yr1, Shift3_Yr2, Shift3_Yr3, OTMult_Yr1, OTMult_Yr2, OTMult_Yr3, StdHours_Yr1, StdHours_Yr2, StdHours_Yr3, ToolAll_Yr1, ToolAll_Yr2, ToolAll_Yr3, WHLim_Yr1, WHLim_Yr2, WHLim_Yr3, SSRate_Yr1, SSRate_Yr2, SSRate_Yr3, MedRate_Yr1, MedRate_Yr2, MedRate_Yr3, Sr5to9_Yr1, Sr5to9_Yr2, Sr5to9_Yr3, Sr10to14_Yr1, Sr10to14_Yr2, Sr10to14_Yr3, Sr15to19_Yr1, Sr15to19_Yr2, Sr15to19_Yr3, Sr20to24_Yr1, Sr20to24_Yr2, Sr20to24_Yr3, Sr25up_Yr1, Sr25up_Yr2, Sr25up_Yr3

## Summary Sheet Formulas

The Summary sheet's TOTAL row (row 34) must reference the quarterly totals row from `EE Calcs (Current)` at row 94. Each cell should use cross-sheet reference like: `='EE Calcs (Current)'!C94`

## Verification

- 7-sheet structure
- 90 member rows in EE Calcs
- Quarterly totals row 94 of each EE Calcs sheet
- Named ranges defined (at least 85)
