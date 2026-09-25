from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / 'tools'))
from ocr_utils import as_two_decimal_string, extract_amount_by_keywords, find_best_date, list_images, ocr_extract_text


DATA_DIR = Path('/app/workspace/dataset/img')
ROSTER_PATH = Path('/app/workspace/dataset/claim_roster.csv')
OUTPUT_PATH = Path('/app/workspace/travel_claims.xlsx')

DATE_PATTERNS = [
    (r'TRANSACTION\s*DATE[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})', 50, True),
    (r'PURCHASE\s*DATE[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})', 40, True),
    (r'DATE[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})', 10, True),
    (r'\b(20\d{2}-\d{2}-\d{2})\b', 5, True),
    (r'\b([0-3]?\d-[01]?\d-20\d{2})\b', 5, True),
    (r'\b([01]?\d/[0-3]?\d/20\d{2})\b', 4, False),
]
AMOUNT_KEYWORDS = [r'REIMBURSABLE\s+TOTAL', r'TOTAL\s+CLAIM', r'AMOUNT\s+CLAIMED', r'TOTAL\s+DUE']
EXCLUDE_KEYWORDS = [r'ADVANCE', r'CASH\s+PAID', r'TIP', r'TAX']
CLAIM_PATTERNS = [
    r'CLAIM\s*CODE(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
    r'CLAIM\s*REF(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
    r'EXPENSE\s*CODE(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
]


def normalize_claim_code(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r'[^A-Z0-9\-]', '', value.upper())
    parts = value.split('-')
    normalized = []
    for idx, part in enumerate(parts):
        if idx >= 1:
            part = part.replace('O', '0').replace('I', '1').replace('L', '1')
        normalized.append(part)
    if len(normalized) >= 3:
        year = re.sub(r'\D', '', normalized[1])
        suffix = re.sub(r'\D', '', normalized[2])
        if len(year) >= 4:
            normalized[1] = year[:4]
        if suffix:
            normalized[2] = suffix[-3:].zfill(3)
    return '-'.join(normalized)


def load_roster():
    mapping = {}
    with ROSTER_PATH.open('r', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            mapping[row['claim_code'].strip().upper()] = (row['employee_id'].strip(), row['trip_id'].strip())
    return mapping


def extract_claim_code(text: str):
    for pattern in CLAIM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_claim_code(match.group(1))
    return None


def extract_row(image_path: Path, roster):
    text = ocr_extract_text(str(image_path))
    claim_code = extract_claim_code(text)
    dt = find_best_date(text, DATE_PATTERNS)
    amount = extract_amount_by_keywords(text, AMOUNT_KEYWORDS, EXCLUDE_KEYWORDS)
    employee_id = None
    trip_id = None
    if claim_code and claim_code in roster:
        employee_id, trip_id = roster[claim_code]
    return [
        image_path.name,
        claim_code,
        employee_id,
        trip_id,
        dt.strftime('%Y-%m-%d') if dt else None,
        as_two_decimal_string(amount) if amount is not None else None,
    ]


def main() -> None:
    roster = load_roster()
    wb = Workbook()
    ws = wb.active
    ws.title = 'claims'
    ws.append(['filename', 'claim_code', 'employee_id', 'trip_id', 'date', 'total_amount'])
    for image_path in list_images(DATA_DIR, recursive=False):
        ws.append(extract_row(image_path, roster))
    wb.save(OUTPUT_PATH)


if __name__ == '__main__':
    main()
