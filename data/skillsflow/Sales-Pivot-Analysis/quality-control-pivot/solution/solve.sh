#!/bin/bash
set -e

cat > /tmp/solve_quality.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Quality Control Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

def extract_parts_from_pdf(pdf_path):
    """Extract only row-level part data, skip summary/distractor tables."""
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 5:
                        # Only extract rows where first column is a numeric PART_ID
                        if row[0] and str(row[0]).strip().isdigit():
                            all_data.append({
                                'PART_ID': int(row[0]),
                                'PART_NAME': str(row[1]).strip(),
                                'LINE': str(row[2]).strip(),
                                'TOLERANCE_MM': float(str(row[3]).replace(',', '')),
                                'TARGET_WEIGHT': float(str(row[4]).replace(',', '')),
                            })
    return pd.DataFrame(all_data)

parts_df = extract_parts_from_pdf("/root/part_specifications.pdf")
insp_df = pd.read_excel("/root/inspection_records.xlsx")

df = insp_df.merge(parts_df, on='PART_ID', how='inner')

# Derived columns with missing data handling
import numpy as np

df['DEVIATION_MM'] = np.where(
    df['MEASUREMENT_MM'].isna(),
    np.nan,
    (df['MEASUREMENT_MM'] - df['TOLERANCE_MM']).abs()
)

df['WEIGHT_ERROR'] = np.where(
    df['ACTUAL_WEIGHT'].isna(),
    np.nan,
    ((df['ACTUAL_WEIGHT'] - df['TARGET_WEIGHT']).abs() / df['TARGET_WEIGHT'])
)

def get_quality_grade(dev):
    if pd.isna(dev):
        return "N/A"
    if dev <= 0.5:
        return "A"
    elif dev <= 1.0:
        return "B"
    else:
        return "C"

df['QUALITY_GRADE'] = df['DEVIATION_MM'].apply(get_quality_grade)

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["INSPECTION_ID", "PART_ID", "PART_NAME", "LINE", "MEASUREMENT_MM",
           "TOLERANCE_MM", "ACTUAL_WEIGHT", "TARGET_WEIGHT", "INSPECTOR", "SHIFT",
           "PASS_FAIL", "DEVIATION_MM", "WEIGHT_ERROR", "QUALITY_GRADE"]
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
            worksheetSource=WorksheetSource(ref=f"A1:N{num_rows}", sheet="SourceData")),
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

# HEADERS: LINE=3, SHIFT=9, DEVIATION_MM=11
add_pivot(wb, "Fail Rate by Line", "Inspection Count", row_idx=3, data_idx=0, subtotal="count")
add_pivot(wb, "Avg Deviation by Line", "Avg Deviation", row_idx=3, data_idx=11, subtotal="average")
add_pivot(wb, "Inspections by Shift", "Inspection Count", row_idx=9, data_idx=0, subtotal="count")
add_pivot(wb, "Line Shift Matrix", "Inspection Count", row_idx=3, data_idx=0, subtotal="count", col_idx=9)

wb.save("/root/quality_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_quality.py
