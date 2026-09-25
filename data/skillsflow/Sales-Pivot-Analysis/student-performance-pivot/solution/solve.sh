#!/bin/bash
set -e

cat > /tmp/solve_student_performance.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Student Performance Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

def extract_students_from_pdf(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 4:
                        if row[0] and str(row[0]).strip().isdigit():
                            all_data.append({
                                'STUDENT_ID': int(row[0]),
                                'STUDENT_NAME': str(row[1]).strip(),
                                'DEPARTMENT': str(row[2]).strip(),
                                'ENROLLMENT_YEAR': int(row[3]),
                            })
    return pd.DataFrame(all_data)

students_df = extract_students_from_pdf("/root/student_roster.pdf")
grades_df = pd.read_excel("/root/course_grades.xlsx")

df = grades_df.merge(students_df, on='STUDENT_ID', how='inner')

# Grade band
def get_grade_band(score):
    if score >= 90: return "A"
    elif score >= 80: return "B"
    elif score >= 70: return "C"
    elif score >= 60: return "D"
    else: return "F"

df['GRADE_BAND'] = df['SCORE'].apply(get_grade_band)
df['WEIGHTED_SCORE'] = df['SCORE'] * df['CREDITS']

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["STUDENT_ID", "STUDENT_NAME", "DEPARTMENT", "ENROLLMENT_YEAR",
           "COURSE_NAME", "SEMESTER", "SCORE", "CREDITS", "GRADE_BAND", "WEIGHTED_SCORE"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    ws.append(list(row))

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:J{num_rows}", sheet="SourceData")),
        cacheFields=[CacheField(name=h, sharedItems=SharedItems()) for h in HEADERS],
    )

def add_pivot(wb, sheet_name, name, row_idx, data_idx, subtotal, col_idx=None):
    pivot_ws = wb.create_sheet(sheet_name)
    loc_ref = "A3:F15" if col_idx else "A3:B20"
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

# HEADERS: DEPARTMENT=2, SEMESTER=5, SCORE=6, CREDITS=7
add_pivot(wb, "Avg Score by Department", "Avg Score", row_idx=2, data_idx=6, subtotal="average")
add_pivot(wb, "Students by Department", "Record Count", row_idx=2, data_idx=0, subtotal="count")
add_pivot(wb, "Credits by Semester", "Total Credits", row_idx=5, data_idx=7, subtotal="sum")
add_pivot(wb, "Department Semester Matrix", "Avg Score", row_idx=2, data_idx=6, subtotal="average", col_idx=5)

wb.save("/root/student_performance_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_student_performance.py
