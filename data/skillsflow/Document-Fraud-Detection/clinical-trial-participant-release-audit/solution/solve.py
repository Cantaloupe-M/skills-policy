import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/participant_release_bundle.pdf')
PARTICIPANT_PATH = Path('/root/participant_registry.xlsx')
CATALOG_PATH = Path('/root/award_catalog.json')
VERSION_PATH = Path('/root/release_versions.csv')
OUTPUT_PATH = Path('/root/participant_release_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def first_nonempty_line(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ''


def flag(rows, page_number, participant_name, amount, payment_token, award_ref, reason):
    rows.append({
        'request_page_number': page_number,
        'participant_name': participant_name,
        'requested_amount': round(float(amount), 2),
        'payment_token': payment_token,
        'award_ref': award_ref,
        'reason': reason,
    })


participants = pd.read_excel(PARTICIPANT_PATH, sheet_name='participants').to_dict(orient='records')
aliases = pd.read_excel(PARTICIPANT_PATH, sheet_name='aliases').to_dict(orient='records')
catalog = json.loads(CATALOG_PATH.read_text(encoding='utf-8'))
versions = pd.read_csv(VERSION_PATH, keep_default_na=False).to_dict(orient='records')
participant_by_code = {row['participant_code']: row for row in participants}
alias_pairs = [(row['participant_name'], row['participant_code']) for row in participants]
alias_pairs.extend((row['alias_name'], row['participant_code']) for row in aliases)
alias_index = build_alias_index(alias_pairs)
awards = {}
for sponsor in catalog['sponsors']:
    for program in sponsor['programs']:
        for award in program['awards']:
            if award['status'] == 'active':
                awards[award['award_ref']] = {
                    'participant_code': award['participant_code'],
                    'expected_amount': float(award['approved_amount']),
                }
latest_version = {}
for row in versions:
    if row['approval_state'] != 'approved':
        continue
    if not row['version_amount'] or not row['participant_code']:
        continue
    current = latest_version.get(row['award_ref'])
    if current is None or int(row['version_no']) > current['version_no']:
        latest_version[row['award_ref']] = {
            'version_no': int(row['version_no']),
            'participant_code': row['participant_code'],
            'expected_amount': float(row['version_amount']),
        }
for award_ref, row in latest_version.items():
    if award_ref in awards:
        awards[award_ref]['participant_code'] = row['participant_code']
        awards[award_ref]['expected_amount'] = row['expected_amount']

retained_pages = {}
with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        if first_nonempty_line(text) != 'Participant Release Request':
            continue
        packet_ref = extract(r'Packet Ref:\s*(.+)', text)
        revision_text = extract(r'Revision No:\s*(\d+)', text) or '0'
        revision_no = int(revision_text)
        current = retained_pages.get(packet_ref)
        page_payload = {
            'page_number': page_number,
            'text': text,
            'revision_no': revision_no,
        }
        if current is None:
            retained_pages[packet_ref] = page_payload
        elif revision_no > current['revision_no']:
            retained_pages[packet_ref] = page_payload
        elif revision_no == current['revision_no'] and page_number > current['page_number']:
            retained_pages[packet_ref] = page_payload

results = []
for page_payload in sorted(retained_pages.values(), key=lambda item: item['page_number']):
    page_number = page_payload['page_number']
    text = page_payload['text']
    participant_name = extract(r'Participant:\s*(.+)', text)
    payment_token = extract(r'Payment Token:\s*(.+)', text)
    award_ref = extract(r'Award Ref:\s*(.+)', text)
    amount_text = extract(r'Requested Amount:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
    amount = float(amount_text.replace(',', ''))

    participant_code = match_key(participant_name, alias_index)
    if participant_code is None:
        flag(results, page_number, participant_name, amount, payment_token, award_ref, 'Unknown Participant')
        continue

    participant = participant_by_code[participant_code]
    if payment_token != participant['payment_token']:
        flag(results, page_number, participant_name, amount, payment_token, award_ref, 'Account Mismatch')
        continue

    award = awards.get(award_ref)
    if award is None:
        flag(results, page_number, participant_name, amount, payment_token, award_ref, 'Invalid Award Ref')
        continue

    if abs(amount - award['expected_amount']) > 0.01:
        flag(results, page_number, participant_name, amount, payment_token, award_ref, 'Amount Mismatch')
        continue

    if award['participant_code'] != participant_code:
        flag(results, page_number, participant_name, amount, payment_token, award_ref, 'Participant Mismatch')
        continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
