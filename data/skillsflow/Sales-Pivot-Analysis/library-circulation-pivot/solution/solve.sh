#!/bin/bash
set -e

cat > /tmp/solve_circulation.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Library Circulation Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from datetime import datetime
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

def extract_books_from_pdf(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 5:
                        if row[0] and str(row[0]).strip().isdigit():
                            all_data.append({
                                'BOOK_ID': int(row[0]),
                                'TITLE': str(row[1]).strip(),
                                'GENRE': str(row[2]).strip(),
                                'AUTHOR': str(row[3]).strip(),
                                'YEAR_PUBLISHED': int(row[4]),
                            })
    return pd.DataFrame(all_data)

books_df = extract_books_from_pdf("/root/book_catalog.pdf")
loans_df = pd.read_excel("/root/circulation_records.xlsx")

df = loans_df.merge(books_df, on='BOOK_ID', how='inner')

# Date arithmetic
df['LOAN_DATE'] = pd.to_datetime(df['LOAN_DATE'])
df['RETURN_DATE'] = pd.to_datetime(df['RETURN_DATE'])
df['LOAN_DURATION'] = (df['RETURN_DATE'] - df['LOAN_DATE']).dt.days

# Decade derivation
df['DECADE'] = df['YEAR_PUBLISHED'].apply(lambda y: f"{(y // 10) * 10}s")

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["LOAN_ID", "BOOK_ID", "TITLE", "GENRE", "AUTHOR", "YEAR_PUBLISHED",
           "BORROWER_TYPE", "LOAN_DATE", "RETURN_DATE", "LOAN_DURATION", "DECADE"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    ws.append(list(row))

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:K{num_rows}", sheet="SourceData")),
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

# HEADERS: GENRE=3, BORROWER_TYPE=6, LOAN_DURATION=9
add_pivot(wb, "Loans by Genre", "Loan Count", row_idx=3, data_idx=0, subtotal="count")
add_pivot(wb, "Avg Duration by Genre", "Avg Duration", row_idx=3, data_idx=9, subtotal="average")
add_pivot(wb, "Loans by Borrower Type", "Loan Count", row_idx=6, data_idx=0, subtotal="count")
add_pivot(wb, "Genre Borrower Matrix", "Loan Count", row_idx=3, data_idx=0, subtotal="count", col_idx=6)

wb.save("/root/circulation_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_circulation.py
