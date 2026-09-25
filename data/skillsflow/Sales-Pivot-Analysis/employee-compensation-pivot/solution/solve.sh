#!/bin/bash
set -e

cat > /tmp/solve_compensation.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Employee Compensation Pivot Table Analysis."""
import pandas as pd
import pdfplumber
import re
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_departments_from_pdf(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or len(row) < 4:
                        continue

                    dept_code = clean_text(row[0])
                    if not re.fullmatch(r"D\d+", dept_code):
                        continue

                    budget_text = re.sub(r"[^\d]", "", str(row[3]))
                    if not budget_text:
                        continue

                    all_data.append({
                        'DEPT_CODE': dept_code,
                        'DEPT_NAME': clean_text(row[1]),
                        'LOCATION': clean_text(row[2]),
                        'ANNUAL_BUDGET': int(budget_text),
                    })
    return pd.DataFrame(all_data, columns=['DEPT_CODE', 'DEPT_NAME', 'LOCATION', 'ANNUAL_BUDGET']).drop_duplicates(subset=['DEPT_CODE'])

depts_df = extract_departments_from_pdf("/root/departments.pdf")
emp_df = pd.read_csv("/root/employee_compensation.csv")

# Join: CSV department_code -> PDF DEPT_CODE
df = emp_df.merge(depts_df, left_on='department_code', right_on='DEPT_CODE', how='inner')

# Derived columns
df['TOTAL_COMP'] = df['base_salary'] + df['annual_bonus']

def get_experience_band(yos):
    if yos < 3: return "Junior"
    elif yos < 8: return "Mid"
    elif yos < 15: return "Senior"
    else: return "Veteran"

df['EXPERIENCE_BAND'] = df['years_of_service'].apply(get_experience_band)
df['COMP_RATIO'] = df['TOTAL_COMP'] / df['ANNUAL_BUDGET']

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["emp_id", "full_name", "department_code", "DEPT_NAME", "LOCATION",
           "job_title", "base_salary", "annual_bonus", "years_of_service", "hire_year",
           "ANNUAL_BUDGET", "TOTAL_COMP", "EXPERIENCE_BAND", "COMP_RATIO"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    ws.append(list(row))

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:N{num_rows}", sheet="SourceData")),
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

# HEADERS: DEPT_NAME=3, LOCATION=4, job_title=5, base_salary=6, TOTAL_COMP=11
add_pivot(wb, "Avg Salary by Department", "Avg Salary", row_idx=3, data_idx=6, subtotal="average")
add_pivot(wb, "Headcount by Location", "Headcount", row_idx=4, data_idx=0, subtotal="count")
add_pivot(wb, "Total Compensation by Title", "Total Comp", row_idx=5, data_idx=11, subtotal="sum")
add_pivot(wb, "Department Location Matrix", "Avg Salary", row_idx=3, data_idx=6, subtotal="average", col_idx=5)

wb.save("/root/compensation_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_compensation.py
