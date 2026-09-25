import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/chargeback_packets.pdf')
PROVIDER_PATH = Path('/root/provider_directory.xlsx')
ORDER_PATH = Path('/root/maintenance_orders.json')
ADJUSTMENT_PATH = Path('/root/maintenance_adjustments.csv')
OUTPUT_PATH = Path('/root/fleet_chargeback_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def flag(rows, page_number, provider_name, amount, payment_account, order_id, reason):
    rows.append({
        'packet_page_number': page_number,
        'provider_name': provider_name,
        'chargeback_total': round(float(amount), 2),
        'payment_account': payment_account,
        'order_id': order_id,
        'reason': reason,
    })


providers = pd.read_excel(PROVIDER_PATH, sheet_name='providers').to_dict(orient='records')
aliases = pd.read_excel(PROVIDER_PATH, sheet_name='aliases').to_dict(orient='records')
order_catalog = json.loads(ORDER_PATH.read_text(encoding='utf-8'))
adjustments = pd.read_csv(ADJUSTMENT_PATH).to_dict(orient='records')
provider_by_id = {row['provider_id']: row for row in providers}
alias_pairs = [(row['provider_name'], row['provider_id']) for row in providers]
alias_pairs.extend((row['alias_name'], row['provider_id']) for row in aliases)
alias_index = build_alias_index(alias_pairs)
orders = {}
for depot in order_catalog['depots']:
    for order in depot['orders']:
        if order['lifecycle'] == 'approved':
            orders[order['order_id']] = {
                'provider_id': order['provider_id'],
                'expected_amount': float(order['approved_charge']),
            }
latest_adjustment = {}
for row in adjustments:
    if row['decision'] != 'approved':
        continue
    current = latest_adjustment.get(row['order_id'])
    if current is None or int(row['amendment_no']) > current['amendment_no']:
        latest_adjustment[row['order_id']] = {
            'amendment_no': int(row['amendment_no']),
            'amended_charge': float(row['amended_charge']),
        }
for order_id, row in latest_adjustment.items():
    if order_id in orders:
        orders[order_id]['expected_amount'] = row['amended_charge']
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        provider_name = extract(r'Provider:\s*(.+)', text)
        payment_account = extract(r'Payment Account:\s*(.+)', text)
        order_id = extract(r'Order ID:\s*(.+)', text)
        amount_text = extract(r'Chargeback Total:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        provider_id = match_key(provider_name, alias_index)
        if provider_id is None:
            flag(results, page_number, provider_name, amount, payment_account, order_id, 'Unknown Provider')
            continue

        provider = provider_by_id[provider_id]
        if payment_account != provider['payment_account']:
            flag(results, page_number, provider_name, amount, payment_account, order_id, 'Account Mismatch')
            continue

        order = orders.get(order_id)
        if order is None:
            flag(results, page_number, provider_name, amount, payment_account, order_id, 'Invalid Order ID')
            continue

        if abs(amount - order['expected_amount']) > 0.01:
            flag(results, page_number, provider_name, amount, payment_account, order_id, 'Amount Mismatch')
            continue

        if order['provider_id'] != provider_id:
            flag(results, page_number, provider_name, amount, payment_account, order_id, 'Provider Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
