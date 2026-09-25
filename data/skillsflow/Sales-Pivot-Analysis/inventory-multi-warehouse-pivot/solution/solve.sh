#!/bin/bash
set -e

cat > /tmp/solve_inventory.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Inventory Multi-Warehouse Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

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
                                'SKU': int(row[0]),
                                'ITEM_NAME': str(row[1]).strip(),
                                'CATEGORY': str(row[2]).strip(),
                                'WEIGHT_KG': float(str(row[3]).replace(',', '')),
                                'REORDER_LEVEL': int(str(row[4]).replace(',', '')),
                            })
    return pd.DataFrame(all_data)

products_df = extract_products_from_pdf("/root/product_info.pdf")
wh_a = pd.read_excel("/root/warehouse_a_inventory.xlsx")
wh_b = pd.read_excel("/root/warehouse_b_inventory.xlsx")

# Combine warehouses
inventory_df = pd.concat([wh_a, wh_b], ignore_index=True)

# Join with product info
df = inventory_df.merge(products_df, on='SKU', how='inner')

# Derived columns
df['TOTAL_VALUE'] = df['QUANTITY_ON_HAND'] * df['UNIT_VALUE']
df['TOTAL_WEIGHT'] = df['QUANTITY_ON_HAND'] * df['WEIGHT_KG']
df['REORDER_FLAG'] = df.apply(lambda r: "Yes" if r['QUANTITY_ON_HAND'] < r['REORDER_LEVEL'] else "No", axis=1)

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["SKU", "ITEM_NAME", "CATEGORY", "WAREHOUSE", "QUANTITY_ON_HAND",
           "UNIT_VALUE", "WEIGHT_KG", "REORDER_LEVEL", "LAST_RECEIVED",
           "TOTAL_VALUE", "TOTAL_WEIGHT", "REORDER_FLAG"]
ws.append(HEADERS)
for row in df[HEADERS].itertuples(index=False):
    ws.append(list(row))

def make_cache(num_rows):
    return CacheDefinition(
        cacheSource=CacheSource(type="worksheet",
            worksheetSource=WorksheetSource(ref=f"A1:L{num_rows}", sheet="SourceData")),
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

# HEADERS: CATEGORY=2, WAREHOUSE=3, QUANTITY_ON_HAND=4, TOTAL_VALUE=9
add_pivot(wb, "Stock by Category", "Total Stock", row_idx=2, data_idx=4, subtotal="sum")
add_pivot(wb, "Value by Warehouse", "Total Value", row_idx=3, data_idx=9, subtotal="sum")
add_pivot(wb, "Items by Category", "Item Count", row_idx=2, data_idx=0, subtotal="count")
add_pivot(wb, "Category Warehouse Matrix", "Value", row_idx=2, data_idx=9, subtotal="sum", col_idx=3)

wb.save("/root/inventory_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_inventory.py
