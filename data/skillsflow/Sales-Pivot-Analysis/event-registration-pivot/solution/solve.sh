#!/bin/bash
set -e

cat > /tmp/solve_registration.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Oracle solution for Event Registration Pivot Table Analysis."""
import pandas as pd
import pdfplumber
from openpyxl import Workbook
from openpyxl.pivot.table import TableDefinition, Location, PivotField, DataField, RowColField
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource, SharedItems

def extract_events_from_pdf(pdf_path):
    all_data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if row and len(row) >= 5:
                        if row[0] and str(row[0]).strip().isdigit():
                            all_data.append({
                                'EVENT_ID': int(row[0]),
                                'EVENT_NAME': str(row[1]).strip(),
                                'TRACK': str(row[2]).strip(),
                                'VENUE': str(row[3]).strip(),
                                'MAX_CAPACITY': int(row[4]),
                            })
    return pd.DataFrame(all_data)

events_df = extract_events_from_pdf("/root/event_catalog.pdf")
online_df = pd.read_excel("/root/online_registrations.xlsx")
walkin_df = pd.read_csv("/root/walkin_registrations.csv")

# Schema alignment: rename walk-in columns to match online
walkin_df = walkin_df.rename(columns={
    'walk_in_id': 'REG_ID',
    'event_code': 'EVENT_ID',
    'guest_name': 'ATTENDEE_NAME',
    'registration_type': 'REG_TYPE',
    'fee_paid': 'AMOUNT_PAID',
})

# Add source tracking
online_df['SOURCE'] = 'Online'
walkin_df['SOURCE'] = 'Walk-in'

# Combine
combined = pd.concat([online_df, walkin_df], ignore_index=True)

# Join with event catalog (inner join drops orphans)
df = combined.merge(events_df, on='EVENT_ID', how='inner')

# Derived columns
df['IS_VIP'] = df['REG_TYPE'].apply(lambda x: "Yes" if x == "VIP" else "No")

def get_price_tier(amt):
    if amt <= 0: return "Free"
    elif amt <= 100: return "Budget"
    elif amt <= 200: return "Standard"
    else: return "Premium"

df['PRICE_TIER'] = df['AMOUNT_PAID'].apply(get_price_tier)

wb = Workbook()
ws = wb.active
ws.title = "SourceData"

HEADERS = ["REG_ID", "EVENT_ID", "EVENT_NAME", "TRACK", "VENUE", "MAX_CAPACITY",
           "ATTENDEE_NAME", "REG_TYPE", "AMOUNT_PAID", "SOURCE", "IS_VIP", "PRICE_TIER"]
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

# HEADERS: TRACK=3, VENUE=4, REG_TYPE=7, AMOUNT_PAID=8
add_pivot(wb, "Revenue by Track", "Total Revenue", row_idx=3, data_idx=8, subtotal="sum")
add_pivot(wb, "Attendance by Venue", "Attendance", row_idx=4, data_idx=0, subtotal="count")
add_pivot(wb, "Track RegType Matrix", "Revenue", row_idx=3, data_idx=8, subtotal="sum", col_idx=7)
add_pivot(wb, "Events by Track", "Registration Count", row_idx=3, data_idx=0, subtotal="count")

wb.save("/root/registration_report.xlsx")
print("Done!")
PYTHON_SCRIPT

python3 /tmp/solve_registration.py
