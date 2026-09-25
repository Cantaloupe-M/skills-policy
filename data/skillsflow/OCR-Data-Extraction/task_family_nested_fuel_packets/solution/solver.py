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


DATA_DIR = Path('/app/workspace/dataset')
OUTPUT_PATH = Path('/app/workspace/fuel_packets.xlsx')

DATE_PATTERNS = [
    (r'SALE\s*DATE[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})', 50, True),
    (r'DATE[:\s]*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4}|\d{4}-\d{2}-\d{2})', 20, True),
    (r'\b(20\d{2}-\d{2}-\d{2})\b', 5, True),
    (r'\b([0-3]?\d-[01]?\d-20\d{2})\b', 5, True),
    (r'\b([01]?\d/[0-3]?\d/20\d{2})\b', 4, False),
]
AMOUNT_KEYWORDS = [r'GRAND\s+TOTAL', r'TOTAL\s+AMOUNT', r'AMOUNT\s+PAID', r'\bTOTAL\b']
EXCLUDE_KEYWORDS = [r'DISCOUNT', r'CASHBACK', r'SAVINGS', r'LOYALTY', r'TAX']
TARGET_KEYWORDS = [r'FUEL\s+RECEIPT', r'PUMP\s+SALE', r'TAX\s+INVOICE']
TXN_PATTERNS = [
    r'TXN\s*REF(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
    r'TRANSACTION\s*NO(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
    r'REF\s*NO(?:\s*:\s*|\s+)([A-Z0-9\-]+)',
]


def normalize_ref(value: str | None) -> str | None:
    if not value:
        return value
    value = re.sub(r'[^A-Z0-9\-]', '', value.upper())
    parts = value.split('-')
    normalized = []
    for idx, part in enumerate(parts):
        if idx >= 2 or (idx == 1 and any(ch.isdigit() for ch in part)):
            part = part.replace('O', '0').replace('I', '1').replace('L', '1')
        normalized.append(part)
    if len(normalized) >= 3:
        suffix = re.sub(r'\D', '', normalized[-1].replace('O', '0').replace('I', '1').replace('L', '1'))
        if suffix:
            normalized[-1] = suffix[-3:].zfill(3)
    return '-'.join(normalized)


def extract_txn_ref(text: str):
    for pattern in TXN_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_ref(match.group(1))
    return None


def is_target(text: str):
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in TARGET_KEYWORDS)


def main() -> None:
    seen_refs = set()
    rows = []
    for image_path in list_images(DATA_DIR, recursive=True):
        rel_path = image_path.relative_to(DATA_DIR).as_posix()
        text = ocr_extract_text(str(image_path))
        txn_ref = extract_txn_ref(text)
        if not is_target(text) or not txn_ref:
            continue
        if txn_ref in seen_refs:
            continue
        seen_refs.add(txn_ref)
        dt = find_best_date(text, DATE_PATTERNS)
        amount = extract_amount_by_keywords(text, AMOUNT_KEYWORDS, EXCLUDE_KEYWORDS)
        batch_name = rel_path.split('/')[0]
        rows.append([
            batch_name,
            rel_path,
            txn_ref,
            dt.strftime('%Y-%m-%d') if dt else None,
            as_two_decimal_string(amount) if amount is not None else None,
        ])
    wb = Workbook()
    ws = wb.active
    ws.title = 'transactions'
    ws.append(['batch_name', 'relative_path', 'txn_ref', 'date', 'total_amount'])
    for row in rows:
        ws.append(row)
    wb.save(OUTPUT_PATH)


if __name__ == '__main__':
    main()
