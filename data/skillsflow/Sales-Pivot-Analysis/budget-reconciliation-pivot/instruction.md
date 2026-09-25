Read the organizational hierarchy from `/root/org_hierarchy.pdf`, expense transactions from `/root/expense_transactions.csv`, and budget allocations from `/root/budget_allocations.xlsx`. Then create a budget reconciliation report at `/root/budget_report.xlsx`.

The org hierarchy PDF contains a table with columns: TEAM_CODE, TEAM_NAME, DEPT_NAME, DIVISION. Note: the PDF may contain introductory text paragraphs and notes sections mixed around the table — only extract the row-level team data where TEAM_CODE starts with "T" followed by digits.

The expense transactions CSV contains columns: tx_id, team_code, expense_category, amount, fiscal_quarter. Note: some expense amounts are negative (representing refunds or credits) — these are valid records and must be included.

The budget allocations XLSX is in **wide format** with columns: DEPT_NAME, CATEGORY, Q1_BUDGET, Q2_BUDGET, Q3_BUDGET, Q4_BUDGET. Each row represents a department-category combination with separate budget columns for each quarter. You must transform this to long format with columns DEPT_NAME, CATEGORY, FISCAL_QUARTER, BUDGET_AMOUNT — where FISCAL_QUARTER values are "Q1", "Q2", "Q3", "Q4" and BUDGET_AMOUNT is the corresponding quarterly value.

The data flow is:
1. Extract the team hierarchy from the PDF
2. Join expenses with the hierarchy on team_code/TEAM_CODE to get DEPT_NAME and DIVISION for each expense
3. Transform the budget XLSX from wide to long format
4. Join the enriched expenses with the long-format budget on DEPT_NAME + expense_category/CATEGORY + fiscal_quarter/FISCAL_QUARTER

Create a new Excel file with **five** pivot table sheets and one source data sheet (six sheets total):

1. "Spending by Division"
This sheet contains a pivot table with:
Rows: DIVISION
Values: Sum of amount

2. "Spending by Department"
This sheet contains a pivot table with:
Rows: DEPT_NAME
Values: Sum of amount

3. "Variance by Department"
This sheet contains a pivot table with:
Rows: DEPT_NAME
Values: Sum of VARIANCE (see SourceData enrichment below)

4. "Category Quarter Matrix"
This sheet contains a pivot table with:
Rows: expense_category
Columns: fiscal_quarter
Values: Sum of amount

5. "Avg Utilization by Division"
This sheet contains a pivot table with:
Rows: DIVISION
Values: Average of UTILIZATION_PCT (see SourceData enrichment below)

6. "SourceData"
This sheet contains the fully joined data enriched with:
- BUDGET_AMOUNT: The matching quarterly budget from the transformed budget table
- VARIANCE: amount - BUDGET_AMOUNT (negative means under budget, positive means over budget). If no matching budget row exists, set to empty/null.
- UTILIZATION_PCT: amount / BUDGET_AMOUNT (as a decimal). If BUDGET_AMOUNT is zero or missing, set to empty/null.

Save the final results in `/root/budget_report.xlsx`
