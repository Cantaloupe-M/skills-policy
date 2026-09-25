#!/bin/bash
set -e

cat > /tmp/solve_budget.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Budget Reconciliation Pivot Table Analysis."""
import pandas as pd
import numpy as np
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems
import re


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def extract_hierarchy_from_pdf(pdf_path):
    """Extract team hierarchy, skipping text paragraphs and notes."""
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    team_code = clean_text(row[0])
                    if not re.fullmatch(r'T\d+', team_code):
                        continue

                    all_data.append({
                        'TEAM_CODE': team_code,
                        'TEAM_NAME': clean_text(row[1]),
                        'DEPT_NAME': clean_text(row[2]),
                        'DIVISION': clean_text(row[3]),
                    })
    return pd.DataFrame(all_data, columns=['TEAM_CODE', 'TEAM_NAME', 'DEPT_NAME', 'DIVISION']).drop_duplicates(subset=['TEAM_CODE'])

hierarchy_df = extract_hierarchy_from_pdf("/root/org_hierarchy.pdf").rename(columns={"TEAM_CODE": "team_code"})
expenses_df = pd.read_csv("/root/expense_transactions.csv")
budget_wide = pd.read_excel("/root/budget_allocations.xlsx")

# Normalize headers and key values before joining data from different sources.
expenses_df.columns = expenses_df.columns.str.strip()
hierarchy_df.columns = hierarchy_df.columns.str.strip()
budget_wide.columns = budget_wide.columns.str.strip()
expenses_df['team_code'] = expenses_df['team_code'].astype(str).str.strip()
expenses_df['expense_category'] = expenses_df['expense_category'].astype(str).str.strip()
expenses_df['fiscal_quarter'] = expenses_df['fiscal_quarter'].astype(str).str.strip()
hierarchy_df['team_code'] = hierarchy_df['team_code'].astype(str).str.strip()
hierarchy_df['TEAM_NAME'] = hierarchy_df['TEAM_NAME'].astype(str).str.strip()
hierarchy_df['DEPT_NAME'] = hierarchy_df['DEPT_NAME'].astype(str).str.strip()
hierarchy_df['DIVISION'] = hierarchy_df['DIVISION'].astype(str).str.strip()
budget_wide['DEPT_NAME'] = budget_wide['DEPT_NAME'].astype(str).str.strip()
budget_wide['CATEGORY'] = budget_wide['CATEGORY'].astype(str).str.strip()

# Step 1: Join expenses with hierarchy to get TEAM_NAME, DEPT_NAME, and DIVISION
df = expenses_df.merge(hierarchy_df, on='team_code', how='inner')

# Step 2: Transform budget from wide to long format
budget_long = pd.melt(
    budget_wide,
    id_vars=['DEPT_NAME', 'CATEGORY'],
    value_vars=['Q1_BUDGET', 'Q2_BUDGET', 'Q3_BUDGET', 'Q4_BUDGET'],
    var_name='FISCAL_QUARTER',
    value_name='BUDGET_AMOUNT'
)
# Map Q1_BUDGET -> Q1, Q2_BUDGET -> Q2, etc.
budget_long['FISCAL_QUARTER'] = budget_long['FISCAL_QUARTER'].str.replace('_BUDGET', '')

# Step 3: Join expenses with budget on DEPT_NAME + category + quarter
df = df.merge(
    budget_long,
    left_on=['DEPT_NAME', 'expense_category', 'fiscal_quarter'],
    right_on=['DEPT_NAME', 'CATEGORY', 'FISCAL_QUARTER'],
    how='left'
)

# Derived columns
df['VARIANCE'] = np.where(
    df['BUDGET_AMOUNT'].isna(),
    np.nan,
    df['amount'] - df['BUDGET_AMOUNT']
)

df['UTILIZATION_PCT'] = np.where(
    (df['BUDGET_AMOUNT'].isna()) | (df['BUDGET_AMOUNT'] == 0),
    np.nan,
    df['amount'] / df['BUDGET_AMOUNT']
)

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["tx_id", "team_code", "TEAM_NAME", "DEPT_NAME", "DIVISION",
           "expense_category", "amount", "fiscal_quarter",
           "BUDGET_AMOUNT", "VARIANCE", "UTILIZATION_PCT"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    vals = []
    for v in row:
        if pd.isna(v):
            vals.append(None)
        else:
            vals.append(v)
    ws.append(vals)

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:K{num_rows}", sheet="SourceData")),
        cacheFields=[CacheField(name=h, sharedItems=SharedItems()) for h in HEADERS],
    )

def add_pivot(wb, sheet_name, name, row_idx, data_idx, subtotal, col_idx=None):
    pivot_ws = wb.create_sheet(sheet_name)
    loc_ref = "A3:H15" if col_idx else "A3:B20"
    pivot = TableDefinition(name=name, cacheId=0, dataCaption=subtotal.title(),
                            location=Location(ref=loc_ref, firstHeaderRow=1,
                                            firstDataRow=1 if not col_idx else 2, firstDataCol=1))
    for i in range(len(HEADERS)):
        axis = "axisRow" if i == row_idx else ("axisCol" if i == col_idx else None)
        pivot.pivotFields.append(PivotField(axis=axis, dataField=(i == data_idx), showAll=False))
    pivot.rowFields.append(RowColField(x=row_idx))
    if col_idx:
        pivot.colFields.append(RowColField(x=col_idx))
    pivot.dataFields.append(DataField(name=name, fld=data_idx, subtotal=subtotal))
    pivot.cache = make_cache(len(df) + 1)
    pivot_ws._pivots.append(pivot)

# HEADERS: DIVISION=4, DEPT_NAME=3, expense_category=5, amount=6, fiscal_quarter=7, VARIANCE=9, UTILIZATION_PCT=10
add_pivot(wb, "Spending by Division", "Total Spending", row_idx=4, data_idx=6, subtotal="sum")
add_pivot(wb, "Spending by Department", "Total Spending", row_idx=3, data_idx=6, subtotal="sum")
add_pivot(wb, "Variance by Department", "Total Variance", row_idx=3, data_idx=9, subtotal="sum")
add_pivot(wb, "Category Quarter Matrix", "Spending", row_idx=5, data_idx=6, subtotal="sum", col_idx=7)
add_pivot(wb, "Avg Utilization by Division", "Avg Utilization", row_idx=4, data_idx=10, subtotal="average")

wb.save("/root/budget_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_budget.py
