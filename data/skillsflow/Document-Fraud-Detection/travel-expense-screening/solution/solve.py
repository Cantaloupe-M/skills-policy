import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/expense_claims.pdf')
EMPLOYEE_PATH = Path('/root/employee_directory.xlsx')
TRIP_PATH = Path('/root/trip_approvals.csv')
OUTPUT_PATH = Path('/root/expense_alerts.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def flag(rows, page_number, employee_name, amount, bank_account, trip_id, reason):
    rows.append({
        'claim_page_number': page_number,
        'employee_name': employee_name,
        'claimed_amount': round(float(amount), 2),
        'bank_account': bank_account,
        'trip_id': trip_id,
        'reason': reason,
    })


employees = pd.read_excel(EMPLOYEE_PATH, sheet_name='employees').to_dict(orient='records')
trips = pd.read_csv(TRIP_PATH).to_dict(orient='records')
employee_by_id = {row['employee_id']: row for row in employees}
alias_index = build_alias_index((row['employee_name'], row['employee_id']) for row in employees)
trip_by_id = {row['trip_id']: row for row in trips}
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        employee_name = extract(r'Employee:\s*(.+)', text)
        bank_account = extract(r'Bank Account:\s*(.+)', text)
        trip_id = extract(r'Trip ID:\s*(.+)', text)
        amount_text = extract(r'Claim Total:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        employee_id = match_key(employee_name, alias_index)
        if employee_id is None:
            flag(results, page_number, employee_name, amount, bank_account, trip_id, 'Unknown Employee')
            continue

        employee = employee_by_id[employee_id]
        if bank_account != employee['bank_account']:
            flag(results, page_number, employee_name, amount, bank_account, trip_id, 'Account Mismatch')
            continue

        trip = trip_by_id.get(trip_id)
        if trip is None:
            flag(results, page_number, employee_name, amount, bank_account, trip_id, 'Invalid Trip ID')
            continue

        if abs(amount - float(trip['approved_amount'])) > 0.01:
            flag(results, page_number, employee_name, amount, bank_account, trip_id, 'Amount Mismatch')
            continue

        if trip['employee_id'] != employee_id:
            flag(results, page_number, employee_name, amount, bank_account, trip_id, 'Traveler Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
