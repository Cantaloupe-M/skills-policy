# Harbor Task: Airline Crew Compensation Model

## Objective

Build a multi-year Excel compensation workbook for an airline's flight crew.

## Output

`/root/Airline_Crew_Compensation.xlsx`

## Input

`/root/airline_assumptions_and_roster.xlsx`

## Sheet Structure (exact 7 sheets, in this order)

1. `Summary` — Executive dashboard
2. `Assumptions` — All model parameters
3. `Roster` — Full flight crew roster (65 crew members)
4. `Calculations --->` — Navigation helper
5. `EE Calcs (Current)` — Year 1 calculations (rows 4–68, quarterly totals row 69)
6. `EE Calcs (Yr+1)` — Year 2 calculations
7. `EE Calcs (Yr+2)` — Year 3 calculations

## Compensation Components (7 components, rows 26–32 in Summary)

| Row | Component | Description |
|-----|-----------|-------------|
| 26 | Base Salary | Annual salary ÷ 4 |
| 27 | Flight Pay Premium | Annual block hours × FPP rate ÷ 4 |
| 28 | Per Diem | $75/day × 200 cap days ÷ 4, IF attendance >= 85% |
| 29 | Hotel Stipend | Annual ÷ 4 |
| 30 | Uniform Allowance | Annual ÷ 4 |
| 31 | Loyalty Bonus | 5-tier based on years of service |
| 32 | TOTAL | Formula-driven |
| 33 | Y/Y Growth | Formula-driven |

## Key Conditional Logic

### Conditional Per-Diem
Formula: `IF(attendance_rate >= 0.85, per_diem_amount, 0)`

### 5-Tier Loyalty Bonus
| Years of Service | Tier | Annual Bonus |
|-----------------|------|-------------|
| 3-5 | Bronze | $2500 |
| 6-10 | Silver | $6000 |
| 11-15 | Gold | $10000 |
| 16-20 | Platinum | $16000 |
| 20+ | Diamond | $25000 |

## Named Ranges

Define: BaseSal_Yr1, BaseSal_Yr2, BaseSal_Yr3, FPP_Yr1, FPP_Yr2, FPP_Yr3, PerDiem_Yr1, PerDiem_Yr2, PerDiem_Yr3, PDCap_Yr1, PDCap_Yr2, PDCap_Yr3, PDThresh_Yr1, PDThresh_Yr2, PDThresh_Yr3, HotelStip_Yr1, HotelStip_Yr2, HotelStip_Yr3, UnifAll_Yr1, UnifAll_Yr2, UnifAll_Yr3, Loy1Rate_Yr1, Loy1Rate_Yr2, Loy1Rate_Yr3, Loy2Rate_Yr1, Loy2Rate_Yr2, Loy2Rate_Yr3, Loy3Rate_Yr1, Loy3Rate_Yr2, Loy3Rate_Yr3, Loy4Rate_Yr1, Loy4Rate_Yr2, Loy4Rate_Yr3, Loy5Rate_Yr1, Loy5Rate_Yr2, Loy5Rate_Yr3, HlthIns_Yr1, HlthIns_Yr2, HlthIns_Yr3, RetRate_Yr1, RetRate_Yr2, RetRate_Yr3, WHLim_Yr1, WHLim_Yr2, WHLim_Yr3, SSRate_Yr1, SSRate_Yr2, SSRate_Yr3, MedRate_Yr1, MedRate_Yr2, MedRate_Yr3, Sr5to9_Yr1, Sr5to9_Yr2, Sr5to9_Yr3, Sr10to14_Yr1, Sr10to14_Yr2, Sr10to14_Yr3, Sr15to19_Yr1, Sr15to19_Yr2, Sr15to19_Yr3, Sr20to24_Yr1, Sr20to24_Yr2, Sr20to24_Yr3, Sr25up_Yr1, Sr25up_Yr2, Sr25up_Yr3

## Summary Sheet Formulas

The Summary sheet's TOTAL row (row 32) must reference the quarterly totals row from `EE Calcs (Current)` at row 69. Each cell should use cross-sheet reference like: `='EE Calcs (Current)'!C69`

## Verification

- 7-sheet structure
- 65 crew rows in EE Calcs
- Quarterly totals row 69 of each EE Calcs sheet
- Named ranges defined (at least 65)
