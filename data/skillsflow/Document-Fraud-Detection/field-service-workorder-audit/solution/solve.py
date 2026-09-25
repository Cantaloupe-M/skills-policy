import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/service_packets.pdf')
CONTRACTOR_PATH = Path('/root/contractor_directory.xlsx')
WORK_ORDER_PATH = Path('/root/work_orders.csv')
REVISION_PATH = Path('/root/work_order_revisions.csv')
OUTPUT_PATH = Path('/root/service_audit_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def flag(rows, page_number, contractor_name, amount, payment_account, work_order_id, reason):
    rows.append({
        'packet_page_number': page_number,
        'contractor_name': contractor_name,
        'billed_amount': round(float(amount), 2),
        'payment_account': payment_account,
        'work_order_id': work_order_id,
        'reason': reason,
    })


contractors = pd.read_excel(CONTRACTOR_PATH, sheet_name='contractors').to_dict(orient='records')
aliases = pd.read_excel(CONTRACTOR_PATH, sheet_name='aliases').to_dict(orient='records')
work_orders = pd.read_csv(WORK_ORDER_PATH).to_dict(orient='records')
revisions = pd.read_csv(REVISION_PATH).to_dict(orient='records')
contractor_by_id = {row['contractor_id']: row for row in contractors}
alias_pairs = [(row['legal_name'], row['contractor_id']) for row in contractors]
alias_pairs.extend((row['alias_name'], row['contractor_id']) for row in aliases)
alias_index = build_alias_index(alias_pairs)
valid_orders = {}
for row in work_orders:
    if row['status'] == 'active':
        valid_orders[row['work_order_id']] = {
            'contractor_id': row['contractor_id'],
            'expected_amount': float(row['approved_amount']),
        }
latest_revision = {}
for row in revisions:
    if row['approval_state'] != 'approved':
        continue
    current = latest_revision.get(row['work_order_id'])
    if current is None or int(row['revision']) > current['revision']:
        latest_revision[row['work_order_id']] = {
            'revision': int(row['revision']),
            'revised_amount': float(row['revised_amount']),
        }
for work_order_id, revision in latest_revision.items():
    if work_order_id in valid_orders:
        valid_orders[work_order_id]['expected_amount'] = revision['revised_amount']
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        contractor_name = extract(r'Contractor:\s*(.+)', text)
        payment_account = extract(r'Payment Account:\s*(.+)', text)
        work_order_id = extract(r'Work Order:\s*(.+)', text)
        amount_text = extract(r'Billed Total:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        contractor_id = match_key(contractor_name, alias_index)
        if contractor_id is None:
            flag(results, page_number, contractor_name, amount, payment_account, work_order_id, 'Unknown Contractor')
            continue

        contractor = contractor_by_id[contractor_id]
        if payment_account != contractor['payment_account']:
            flag(results, page_number, contractor_name, amount, payment_account, work_order_id, 'Account Mismatch')
            continue

        work_order = valid_orders.get(work_order_id)
        if work_order is None:
            flag(results, page_number, contractor_name, amount, payment_account, work_order_id, 'Invalid Work Order')
            continue

        if abs(amount - work_order['expected_amount']) > 0.01:
            flag(results, page_number, contractor_name, amount, payment_account, work_order_id, 'Amount Mismatch')
            continue

        if work_order['contractor_id'] != contractor_id:
            flag(results, page_number, contractor_name, amount, payment_account, work_order_id, 'Contractor Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
