import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/stipend_packets.pdf')
RECIPIENT_PATH = Path('/root/recipient_roster.xlsx')
AUTH_PATH = Path('/root/award_authorizations.csv')
ADJUSTMENT_PATH = Path('/root/award_adjustments.csv')
OUTPUT_PATH = Path('/root/stipend_review.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def first_nonempty_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def flag(rows, page_number, recipient_name, amount, bank_token, award_ref, reason):
    rows.append({
        'request_page_number': page_number,
        'recipient_name': recipient_name,
        'requested_amount': round(float(amount), 2),
        'bank_token': bank_token,
        'award_ref': award_ref,
        'reason': reason,
    })


recipients = pd.read_excel(RECIPIENT_PATH, sheet_name='recipients').to_dict(orient='records')
aliases = pd.read_excel(RECIPIENT_PATH, sheet_name='aliases').to_dict(orient='records')
authorizations = pd.read_csv(AUTH_PATH).to_dict(orient='records')
adjustments = pd.read_csv(ADJUSTMENT_PATH).to_dict(orient='records')
recipient_by_code = {row['recipient_code']: row for row in recipients}
alias_pairs = [(row['registered_name'], row['recipient_code']) for row in recipients]
alias_pairs.extend((row['name_variant'], row['recipient_code']) for row in aliases)
alias_index = build_alias_index(alias_pairs)
valid_awards = {}
for row in authorizations:
    if row['state'] == 'active':
        valid_awards[row['award_ref']] = {
            'expected_amount': float(row['approved_value']),
            'campus_code': row['campus_code'],
        }
latest_adjustment = {}
for row in adjustments:
    if row['state'] != 'approved':
        continue
    current = latest_adjustment.get(row['award_ref'])
    if current is None or int(row['revision_no']) > current['revision_no']:
        latest_adjustment[row['award_ref']] = {
            'revision_no': int(row['revision_no']),
            'adjusted_value': float(row['adjusted_value']),
            'campus_code': row['campus_code'],
        }
for award_ref, row in latest_adjustment.items():
    if award_ref in valid_awards:
        valid_awards[award_ref]['expected_amount'] = row['adjusted_value']
        valid_awards[award_ref]['campus_code'] = row['campus_code']
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        if first_nonempty_line(text) != 'Stipend Disbursement Request':
            continue
        recipient_name = extract(r'Recipient:\s*(.+)', text)
        campus_code = extract(r'Campus:\s*(.+)', text)
        bank_token = extract(r'Bank Token:\s*(.+)', text)
        award_ref = extract(r'Award Ref:\s*(.+)', text)
        amount_text = extract(r'Requested Amount:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        recipient_code = match_key(recipient_name, alias_index)
        if recipient_code is None:
            flag(results, page_number, recipient_name, amount, bank_token, award_ref, 'Unknown Recipient')
            continue

        recipient = recipient_by_code[recipient_code]
        if bank_token != recipient['bank_token']:
            flag(results, page_number, recipient_name, amount, bank_token, award_ref, 'Account Mismatch')
            continue

        award = valid_awards.get(award_ref)
        if award is None:
            flag(results, page_number, recipient_name, amount, bank_token, award_ref, 'Invalid Award Ref')
            continue

        if abs(amount - award['expected_amount']) > 0.01:
            flag(results, page_number, recipient_name, amount, bank_token, award_ref, 'Amount Mismatch')
            continue

        if campus_code != award['campus_code']:
            flag(results, page_number, recipient_name, amount, bank_token, award_ref, 'Campus Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
