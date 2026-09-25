import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/honorarium_requests.pdf')
SPEAKER_PATH = Path('/root/speaker_registry.xlsx')
APPROVAL_PATH = Path('/root/session_approvals.csv')
OUTPUT_PATH = Path('/root/honorarium_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def flag(rows, page_number, speaker_name, amount, payment_account, approval_code, reason):
    rows.append({
        'request_page_number': page_number,
        'speaker_name': speaker_name,
        'requested_fee': round(float(amount), 2),
        'payment_account': payment_account,
        'approval_code': approval_code,
        'reason': reason,
    })


speakers = pd.read_excel(SPEAKER_PATH, sheet_name='speakers').to_dict(orient='records')
approvals = pd.read_csv(APPROVAL_PATH).to_dict(orient='records')
speaker_by_id = {row['speaker_id']: row for row in speakers}
alias_index = build_alias_index((row['speaker_name'], row['speaker_id']) for row in speakers)
approval_by_code = {row['approval_code']: row for row in approvals}
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        speaker_name = extract(r'Speaker:\s*(.+)', text)
        payment_account = extract(r'Payment Account:\s*(.+)', text)
        approval_code = extract(r'Approval Code:\s*(.+)', text)
        amount_text = extract(r'Requested Fee:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        speaker_id = match_key(speaker_name, alias_index)
        if speaker_id is None:
            flag(results, page_number, speaker_name, amount, payment_account, approval_code, 'Unknown Speaker')
            continue

        speaker = speaker_by_id[speaker_id]
        if payment_account != speaker['payment_account']:
            flag(results, page_number, speaker_name, amount, payment_account, approval_code, 'Account Mismatch')
            continue

        approval = approval_by_code.get(approval_code)
        if approval is None:
            flag(results, page_number, speaker_name, amount, payment_account, approval_code, 'Invalid Approval Code')
            continue

        if abs(amount - float(approval['approved_fee'])) > 0.01:
            flag(results, page_number, speaker_name, amount, payment_account, approval_code, 'Fee Mismatch')
            continue

        if approval['speaker_id'] != speaker_id:
            flag(results, page_number, speaker_name, amount, payment_account, approval_code, 'Speaker Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
