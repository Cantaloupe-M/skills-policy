# Harbor Task: University Faculty Compensation Model

## Objective

Build a multi-year Excel compensation workbook for a university's full-time faculty.

## Output

`/root/University_Compensation.xlsx`

## Input

`/root/university_assumptions_and_roster.xlsx`

## Sheet Structure (exact 7 sheets, in this order)

1. `Summary` — Executive dashboard
2. `Assumptions` — All model parameters migrated from the input file
3. `Roster` — Full faculty roster migrated from the input file (75 faculty)
4. `Calculations --->` — Navigation helper with links to EE Calcs sheets
5. `EE Calcs (Current)` — Year 1 calculations, one row per faculty member + quarterly totals row
6. `EE Calcs (Yr+1)` — Year 2 calculations (same layout, 3% base wage growth, years-of-service +1)
7. `EE Calcs (Yr+2)` — Year 3 calculations (6% cumulative growth, years-of-service +2)

## Compensation Components (8 components, rows 26–32 in Summary)

| Row | Component | Description |
|-----|-----------|-------------|
| 26 | Base Pay (9-Month) | Annual salary ÷ 52 × 13, quarterly |
| 27 | Summer Session Pay | Credits × Summer rate per credit ÷ 4 |
| 28 | Sabbatical Bonus | 10% of base, if Sabbatical Eligible = TRUE |
| 29 | Department Stipend | Rank-based: Full Prof/Assoc/Asst/Instructor |
| 30 | Media Rights Allocation | Per faculty share of Media Pool ÷ 75 ÷ 4 |
| 31 | Health Insurance | Flat annual ÷ 4 |
| 32 | Retirement Match | Min(base_annual, prev_wage×0.06) × match rate ÷ 4 |

**Row 33:** `---TOTAL---` (bold, formula-driven — sum of rows 26–32 per quarter)  
**Row 34:** `Y/Y Growth` (formula-driven — G33/C33-1, K33/G33-1, O33/K33-1)

## Named Ranges (50 ranges)

Define ALL assumptions as named ranges in the workbook:

- `B9M_Yr1`, `B9M_Yr2`, `B9M_Yr3` — Base 9-month salary
- `SumRate_Yr1`, `SumRate_Yr2`, `SumRate_Yr3` — Summer session rate per credit
- `SabbPct_Yr1`, `SabbPct_Yr2`, `SabbPct_Yr3` — Sabbatical bonus rate
- `StipFP_Yr1-3`, `StipAP_Yr1-3`, `StipAsst_Yr1-3`, `StipInst_Yr1-3` — Department stipend by rank
- `MediaPool_Yr1-3` — Total media rights pool
- `HlthIns_Yr1-3` — Health insurance annual amount
- `RetRate_Yr1-3` — TIAA-C match rate
- `RetCap_Yr1-3` — Retirement match cap (% of salary)
- `WHLim_Yr1-3` — SS wage base limit
- `SSRate_Yr1-3`, `MedRate_Yr1-3` — Tax rates
- `Sr5to9_Yr1-3`, `Sr10to14_Yr1-3`, `Sr15to19_Yr1-3`, `Sr20to24_Yr1-3`, `Sr25up_Yr1-3` — Seniority adjustments

## EE Calcs Sheet Layout

Row 3: Headers (A..AI)  
Rows 4–78: One row per faculty member (75 faculty)  
Row 79: Quarterly totals (`=SUM(H4:H78)` pattern for each of H..AI)

### Column groups (H=column 8, etc.)

| Cols | Component |
|------|-----------|
| H–K (8–11) | Base Pay Q1–Q4 |
| L–O (12–15) | Summer Session Q1–Q4 |
| P–S (16–19) | Sabbatical Bonus Q1–Q4 |
| T–W (20–23) | Department Stipend Q1–Q4 |
| X–AA (24–27) | Media Rights Q1–Q4 |
| AB–AE (28–31) | Health Insurance Q1–Q4 |
| AF–AI (32–35) | Retirement Match Q1–Q4 |

## Formula Rules

- All Summary quarterly totals MUST link to EE Calcs via cross-sheet formulas: e.g., `='EE Calcs (Current)'!H79`
- Y/Y growth row MUST be formula-driven, not hardcoded
- Quarterly totals row MUST use SUM formulas over data rows
- EE Calcs Yr+1 and Yr+2 must use years-of-service +1/+2 from prior sheet

## Verification

The workbook will be verified for:
- Exact 7-sheet order and names
- 50 defined named ranges
- Summary B1 = organization name, C5 = starting base salary, D5 = formula =C5*1.03
- Rows 26–32 = component labels, row 33 = Total, row 34 = Y/Y Growth
- Quarterly totals in row 79 of each EE Calcs sheet
- Roster migrated: source rows mapped to output rows
