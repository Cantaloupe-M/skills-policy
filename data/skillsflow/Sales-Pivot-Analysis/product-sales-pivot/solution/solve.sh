#!/bin/bash
set -e

cat > /tmp/solve_product_sales.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Product Sales Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

# Extract product catalog from PDF
def extract_products_from_pdf(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 5:
                        if row[0] and str(row[0]).strip().isdigit():
                            all_data.append({
                                'PRODUCT_ID': int(row[0]),
                                'PRODUCT_NAME': str(row[1]).strip(),
                                'CATEGORY': str(row[2]).strip(),
                                'UNIT_COST': float(str(row[3]).replace(',', '')),
                                'UNIT_PRICE_CATALOG': float(str(row[4]).replace(',', '')),
                            })
    return pd.DataFrame(all_data)

products_df = extract_products_from_pdf("/root/product_catalog.pdf")
sales_df = pd.read_excel("/root/sales_transactions.xlsx")

# Join
df = sales_df.merge(products_df, on='PRODUCT_ID', how='inner')

# Compute derived columns
df['REVENUE'] = df['QUANTITY'] * df['UNIT_PRICE']
df['PROFIT'] = df['REVENUE'] - (df['QUANTITY'] * df['UNIT_COST'])
df['MARGIN_PCT'] = df['PROFIT'] / df['REVENUE']

# Create workbook
wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["TRANSACTION_ID", "PRODUCT_ID", "PRODUCT_NAME", "CATEGORY", "REGION",
           "MONTH", "QUARTER", "QUANTITY", "UNIT_PRICE", "UNIT_COST",
           "REVENUE", "PROFIT", "MARGIN_PCT"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    ws.append(list(row))

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:{chr(64+len(HEADERS))}{num_rows}", sheet="SourceData")),
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

# HEADERS indices: CATEGORY=3, REGION=4, QUANTITY=7, REVENUE=10
add_pivot(wb, "Revenue by Category", "Total Revenue", row_idx=3, data_idx=10, subtotal="sum")
add_pivot(wb, "Units by Region", "Total Units", row_idx=4, data_idx=7, subtotal="sum")
add_pivot(wb, "Products by Category", "Transaction Count", row_idx=3, data_idx=0, subtotal="count")
add_pivot(wb, "Category Region Matrix", "Revenue", row_idx=3, data_idx=10, subtotal="sum", col_idx=4)

wb.save("/root/product_sales_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_product_sales.py
