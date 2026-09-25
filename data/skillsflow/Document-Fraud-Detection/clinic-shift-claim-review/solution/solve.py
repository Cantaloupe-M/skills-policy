import json
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from fuzzy_utils import build_alias_index, match_key

PDF_PATH = Path('/root/shift_claims.pdf')
CLINICIAN_PATH = Path('/root/clinician_directory.xlsx')
AUTH_PATH = Path('/root/shift_authorizations.csv')
CROSSWALK_PATH = Path('/root/shift_crosswalk.csv')
OUTPUT_PATH = Path('/root/shift_claim_flags.json')


def extract(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def flag(rows, page_number, clinician_name, amount, payout_account, shift_ref, reason):
    rows.append({
        'claim_page_number': page_number,
        'clinician_name': clinician_name,
        'requested_pay': round(float(amount), 2),
        'payout_account': payout_account,
        'shift_ref': shift_ref,
        'reason': reason,
    })


clinicians = pd.read_excel(CLINICIAN_PATH).to_dict(orient='records')
authorizations = pd.read_csv(AUTH_PATH).to_dict(orient='records')
crosswalk_rows = pd.read_csv(CROSSWALK_PATH).to_dict(orient='records')
clinician_by_id = {row['clinician_id']: row for row in clinicians}
alias_index = build_alias_index((row['clinician_name'], row['clinician_id']) for row in clinicians)
auth_by_code = {row['shift_code_internal']: row for row in authorizations}
crosswalk = {row['shift_ref']: row['shift_code_internal'] for row in crosswalk_rows}
results = []

with pdfplumber.open(PDF_PATH) as pdf:
    for page_number, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ''
        clinician_name = extract(r'Clinician:\s*(.+)', text)
        payout_account = extract(r'Payout Account:\s*(.+)', text)
        shift_ref = extract(r'Shift Ref:\s*(.+)', text)
        amount_text = extract(r'Requested Pay:\s*\$([0-9,]+\.\d{2})', text) or '0.00'
        amount = float(amount_text.replace(',', ''))

        clinician_id = match_key(clinician_name, alias_index)
        if clinician_id is None:
            flag(results, page_number, clinician_name, amount, payout_account, shift_ref, 'Unknown Clinician')
            continue

        clinician = clinician_by_id[clinician_id]
        if payout_account != clinician['payout_account']:
            flag(results, page_number, clinician_name, amount, payout_account, shift_ref, 'Account Mismatch')
            continue

        internal_code = crosswalk.get(shift_ref)
        authorization = auth_by_code.get(internal_code) if internal_code else None
        if authorization is None:
            flag(results, page_number, clinician_name, amount, payout_account, shift_ref, 'Invalid Shift Code')
            continue

        if abs(amount - float(authorization['approved_pay'])) > 0.01:
            flag(results, page_number, clinician_name, amount, payout_account, shift_ref, 'Amount Mismatch')
            continue

        if authorization['clinician_id'] != clinician_id:
            flag(results, page_number, clinician_name, amount, payout_account, shift_ref, 'Clinician Mismatch')
            continue

OUTPUT_PATH.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
