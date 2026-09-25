You need to update `/root/data/workbook.xlsx`. The workbook already contains the sheets `Task` and `Data`; work only inside these existing sheets.

Step 1: Populate the yellow cells in `H12:L17`, `H19:L24`, and `H26:L31` on sheet `Task` with spreadsheet formulas. Use two inputs for every lookup: the series code in column `D` of the current row and the year in row `10`. The source records are on sheet `Data` in rows `21:38`. Use one of these lookup patterns: `VLOOKUP` with `MATCH`, `HLOOKUP` with `MATCH`, `XLOOKUP` with `MATCH`, or `INDEX` with `MATCH`.

Step 2: In `H35:L40`, calculate `Net budget buffer` for the six departments with this formula:
`(Committed Funding - Operating Spend) / Approved Budget Base * 100`
Then calculate the column-wise minimum, maximum, median, simple mean, 25th percentile, and 75th percentile in `H42:L47`.

Step 3: In `H50:L50`, calculate the weighted mean for `Campus Budget Council` with `SUMPRODUCT`, using the Step 2 percentages as values and the `Approved Budget Base` block in `H26:L31` as weights.

Keep the existing workbook formatting unchanged. Do not add sheets, macros, VBA, external links, or helper tabs.
Save the finished workbook to `/root/output/result.xlsx`.
