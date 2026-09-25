import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/coldchain_charge_packets.pdf')
CARRIER_PATH = Path('/root/carrier_registry.xlsx')
AUTH_PATH = Path('/root/shipment_authorizations.csv')
SNAPSHOT_PATH = Path('/root/shipment_snapshots.csv')
OUTPUT_PATH = Path('/root/coldchain_charge_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def first_nonempty_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def flag(rows, page_number, carrier_name, amount, remit_account, shipment_ref, reason):
    rows.append({
        'request_page_number': page_number,
        'carrier_name': carrier_name,
        'requested_charge': round(float(amount), 2),
        'remit_account': remit_account,
        'shipment_ref': shipment_ref,
        'reason': reason,
    })


carriers = pd.read_excel(CARRIER_PATH, sheet_name='carriers').to_dict(orient='records')
aliases = pd.read_excel(CARRIER_PATH, sheet_name='aliases').to_dict(orient='records')
authorizations = pd.read_csv(AUTH_PATH).to_dict(orient='records')
snapshots = pd.read_csv(SNAPSHOT_PATH, keep_default_na=False).to_dict(orient='records')
carrier_by_id = {row['carrier_id']: row for row in carriers}
alias_pairs = [(row['carrier_name'], row['carrier_id']) for row in carriers]
alias_pairs.extend((row['alias_name'], row['carrier_id']) for row in aliases)
alias_index = build_alias_index(alias_pairs)
shipments = {}
for row in authorizations:
    if row['record_state'] == 'approved':
        shipments[row['shipment_ref']] = {
            'carrier_id': row['carrier_id'],
            'expected_amount': float(row['expected_charge']),
        }
latest_snapshot = {}
for row in snapshots:
    if row['snapshot_state'] != 'approved':
        continue
    if not row['expected_charge'] or not row['carrier_id']:
        continue
    current = latest_snapshot.get(row['shipment_ref'])
    if current is None or int(row['snapshot_seq']) > current['snapshot_seq']:
        latest_snapshot[row['shipment_ref']] = {
            'snapshot_seq': int(row['snapshot_seq']),
            'carrier_id': row['carrier_id'],
            'expected_amount': float(row['expected_charge']),
        }
for shipment_ref, row in latest_snapshot.items():
    if shipment_ref in shipments:
        shipments[shipment_ref]['carrier_id'] = row['carrier_id']
        shipments[shipment_ref]['expected_amount'] = row['expected_amount']
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        if first_nonempty_line(text) != 'Cold Chain Charge Request':
            continue
        carrier_name = extract(r'Carrier:\s*(.+)', text)
        remit_account = extract(r'Remit Account:\s*(.+)', text)
        shipment_ref = extract(r'Shipment Ref:\s*(.+)', text)
        amount_text = extract(r'Requested Charge:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        carrier_id = match_key(carrier_name, alias_index)
        if carrier_id is None:
            flag(results, page_number, carrier_name, amount, remit_account, shipment_ref, 'Unknown Carrier')
            continue

        carrier = carrier_by_id[carrier_id]
        if remit_account != carrier['remit_account']:
            flag(results, page_number, carrier_name, amount, remit_account, shipment_ref, 'Account Mismatch')
            continue

        shipment = shipments.get(shipment_ref)
        if shipment is None:
            flag(results, page_number, carrier_name, amount, remit_account, shipment_ref, 'Invalid Shipment Ref')
            continue

        if abs(amount - shipment['expected_amount']) > 0.01:
            flag(results, page_number, carrier_name, amount, remit_account, shipment_ref, 'Amount Mismatch')
            continue

        if shipment['carrier_id'] != carrier_id:
            flag(results, page_number, carrier_name, amount, remit_account, shipment_ref, 'Carrier Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
