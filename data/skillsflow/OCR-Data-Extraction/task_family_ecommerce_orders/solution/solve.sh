#!/bin/bash

set -e

cat > /app/workspace/extract_orders.py << 'PYTHON_SCRIPT'
import os
import re
import csv
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Set, Tuple
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from openpyxl import Workbook


def _parse_date_any_format(date_text: str) -> Optional[datetime]:
    """Parse date strings in multiple formats."""
    normalized = date_text.strip()
    normalized = normalized.replace("O", "0").replace("o", "0")
    normalized = normalized.replace("I", "1").replace("l", "1")
    normalized = normalized.replace(" ", "")
    
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
        "%Y/%m/%d", "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if 2000 <= dt.year <= 2030:
                return dt
        except ValueError:
            continue
    
    return None


def _as_two_decimal_string(value: Decimal) -> str:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:.2f}"


def _preprocess_image(img: Image.Image) -> List[Image.Image]:
    """Generate multiple preprocessed versions for OCR."""
    processed = []
    gray = ImageOps.grayscale(img)
    
    auto = ImageOps.autocontrast(gray, cutoff=2)
    processed.append(auto)
    
    inverted = ImageOps.invert(auto)
    processed.append(inverted)
    
    w, h = gray.size
    if w < 1000 or h < 1000:
        scale = max(1000 / w, 1000 / h, 2)
        scaled = gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        scaled = ImageOps.autocontrast(scaled, cutoff=2)
        processed.append(scaled)
    
    sharpened = auto.filter(ImageFilter.SHARPEN)
    processed.append(sharpened)
    
    threshold = auto.point(lambda p: 255 if p > 128 else 0)
    processed.append(threshold)
    
    threshold_low = auto.point(lambda p: 255 if p > 100 else 0)
    processed.append(threshold_low)
    
    return processed


def _ocr_extract_text(image_path: str) -> str:
    """OCR with multiple strategies."""
    img = Image.open(image_path)
    
    configs = [
        "--psm 6",
        "--psm 4",
        "--psm 3",
        "--psm 11",
    ]
    
    all_texts = []
    preprocessed_images = _preprocess_image(img)
    
    for proc_img in preprocessed_images:
        try:
            text = pytesseract.image_to_string(proc_img, config=configs[0])
            if text.strip():
                all_texts.append(text)
        except Exception:
            pass
    
    for config in configs[1:3]:
        for proc_img in preprocessed_images[:2]:
            try:
                text = pytesseract.image_to_string(proc_img, config=config)
                if text.strip():
                    all_texts.append(text)
            except Exception:
                pass
    
    return "\n".join(all_texts)


# Order ID patterns
_ORDER_ID_PATTERNS = [
    re.compile(r"ORDER\s*ID\s*:?\s*([A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{3,6})", re.IGNORECASE),
    re.compile(r"ORDER\s*NO\.?\s*:?\s*([A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{3,6})", re.IGNORECASE),
    re.compile(r"ORDER\s*#\s*:?\s*([A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{3,6})", re.IGNORECASE),
    re.compile(r"ORDER\s*NUMBER\s*:?\s*([A-Z]{2,4}[-\s]?\d{4}[-\s]?\d{3,6})", re.IGNORECASE),
    re.compile(r"SO[-\s]?\d{4}[-\s]?\d{3,6}", re.IGNORECASE),
    re.compile(r"INV[-\s]?\d{4,10}", re.IGNORECASE),
]


def _extract_order_id(text: str) -> Optional[str]:
    """Extract order ID from text."""
    for pat in _ORDER_ID_PATTERNS:
        match = pat.search(text)
        if match:
            order_id = match.group(1) if match.lastindex else match.group(0)
            return order_id.upper().replace(" ", "-")
    return None


# Date patterns
_DATE_PATTERNS = [
    (re.compile(r"ORDER\s*DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), True),
    (re.compile(r"DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), True),
    (re.compile(r"\b([0-3]?\d/[01]?\d/20\d{2})\b"), False),
    (re.compile(r"\b([0-3]?\d-[01]?\d-20\d{2})\b"), False),
    (re.compile(r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"), False),
]


def _extract_date_from_text(text: str) -> Optional[datetime]:
    """Extract date from text."""
    if not text:
        return None
    
    found_dates: List[Tuple[datetime, bool]] = []
    
    for pat, has_context in _DATE_PATTERNS:
        for match in pat.findall(text):
            candidate = match if isinstance(match, str) else match
            dt = _parse_date_any_format(candidate)
            if dt:
                found_dates.append((dt, has_context))
    
    if not found_dates:
        return None
    
    context_dates = [d for d, has_ctx in found_dates if has_ctx]
    if context_dates:
        return context_dates[0]
    
    return found_dates[0][0]


# Money patterns
_MONEY_RE = re.compile(
    r"(?:[$€£RM\s]*)?(\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2})",
    re.IGNORECASE
)

_TOTAL_KEYWORDS = [
    r"GRAND\s*TOTAL",
    r"ORDER\s*TOTAL",
    r"TOTAL\s*DUE",
    r"AMOUNT\s*DUE",
    r"\bTOTAL\b",
]

_EXCLUDE_KEYWORDS = [
    r"SUB\s*TOTAL",
    r"SUBTOTAL",
    r"TAX",
    r"GST",
    r"SHIPPING",
    r"DELIVERY\s*FEE",
    r"DISCOUNT",
]


def _extract_total_from_text(text: str) -> Optional[Decimal]:
    """Extract total amount from text."""
    if not text:
        return None
    
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    total_re = re.compile("|".join(_TOTAL_KEYWORDS), re.IGNORECASE)
    exclude_re = re.compile("|".join(_EXCLUDE_KEYWORDS), re.IGNORECASE)
    
    candidates: List[Tuple[Decimal, int]] = []
    
    for i, line in enumerate(lines):
        if exclude_re.search(line):
            continue
        
        if total_re.search(line):
            nums = _MONEY_RE.findall(line)
            if nums:
                try:
                    val = Decimal(nums[-1].replace(",", "").replace(" ", ""))
                    priority = 50 if re.search(r"GRAND\s*TOTAL", line, re.IGNORECASE) else 20
                    candidates.append((val, priority))
                except Exception:
                    pass
            
            if not nums and i + 1 < len(lines):
                next_nums = _MONEY_RE.findall(lines[i + 1])
                if next_nums:
                    try:
                        val = Decimal(next_nums[-1].replace(",", "").replace(" ", ""))
                        candidates.append((val, 10))
                    except Exception:
                        pass
    
    if candidates:
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
    
    return None


def load_known_orders(csv_path: str) -> Set[str]:
    """Load known valid order IDs from CSV."""
    known = set()
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_id = row.get('order_id', '').strip().upper().replace(" ", "-")
                if order_id:
                    known.add(order_id)
    except Exception:
        pass
    return known


def extract_data_from_images(dataset_dir: str, known_orders: Set[str]) -> Dict[str, Dict[str, str]]:
    """Process all images and extract data."""
    results: Dict[str, Dict[str, str]] = {}
    seen_order_ids: Dict[str, str] = {}  # order_id -> first filename
    exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
    entries = sorted(os.listdir(dataset_dir))
    
    for entry in entries:
        _, ext = os.path.splitext(entry)
        if ext.lower() not in exts:
            continue
        file_path = os.path.join(dataset_dir, entry)
        
        try:
            text = _ocr_extract_text(file_path)
        except Exception:
            results[entry] = {"order_id": None, "date": None, "total_amount": None}
            continue
        
        if not text:
            results[entry] = {"order_id": None, "date": None, "total_amount": None}
            continue
        
        order_id = _extract_order_id(text)
        dt = _extract_date_from_text(text)
        amount = _extract_total_from_text(text)
        
        # Validate order_id against known orders
        if order_id and order_id not in known_orders:
            order_id = None
        
        # Check for duplicates
        if order_id:
            if order_id in seen_order_ids:
                # This is a duplicate
                results[entry] = {"order_id": None, "date": None, "total_amount": None}
                continue
            else:
                seen_order_ids[order_id] = entry
        
        date_str = dt.strftime("%Y-%m-%d") if dt else None
        amount_str = _as_two_decimal_string(amount) if amount else None
        
        results[entry] = {
            "order_id": order_id,
            "date": date_str,
            "total_amount": amount_str,
        }
    
    return results


def main():
    dataset_dir = "/app/workspace/dataset/img"
    known_orders_path = "/app/workspace/dataset/known_orders.csv"
    output_path = "/app/workspace/orders_summary.xlsx"
    
    known_orders = load_known_orders(known_orders_path)
    results = extract_data_from_images(dataset_dir, known_orders)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "orders"
    ws.append(["filename", "order_id", "date", "total_amount"])
    
    for filename in sorted(results.keys()):
        row = results[filename]
        ws.append([filename, row.get("order_id"), row.get("date"), row.get("total_amount")])
    
    wb.save(output_path)
    print(f"Extracted {len(results)} orders to {output_path}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /app/workspace/extract_orders.py
