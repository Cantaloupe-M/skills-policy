#!/bin/bash

set -e

cat > /app/workspace/extract_construction.py << 'PYTHON_SCRIPT'
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
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
    gray = ImageOps.grayscale(img)
    auto = ImageOps.autocontrast(gray, cutoff=1)
    processed = [
        auto,
        auto.filter(ImageFilter.SHARPEN),
        auto.point(lambda p: 255 if p > 128 else 0),
        auto.point(lambda p: 255 if p > 100 else 0),
        auto.point(lambda p: 255 if p > 150 else 0),
    ]
    w, h = gray.size
    if w < 1600 or h < 1600:
        scale = max(1600 / max(w, 1), 1600 / max(h, 1), 2)
        scaled = auto.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        processed.extend([
            scaled,
            scaled.filter(ImageFilter.SHARPEN),
            scaled.point(lambda p: 255 if p > 130 else 0),
        ])
    return processed


def _ocr_extract_text(image_path: str) -> str:
    """OCR with multiple strategies and keep the best single read."""
    img = Image.open(image_path)
    configs = [
        "--psm 6",
        "--psm 4",
        "--psm 11",
        "--psm 6 -c tessedit_char_whitelist=0123456789.$/-:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
    ]
    texts = []
    for proc_img in _preprocess_image(img):
        for config in configs:
            try:
                text = pytesseract.image_to_string(proc_img, config=config)
                if text.strip():
                    texts.append(text)
            except Exception:
                pass
    if not texts:
        return ""
    def _score(text: str):
        upper = text.upper()
        line_item_count = 0
        for line in text.splitlines():
            compact = line.strip().upper()
            if '$' in compact and re.search(r'[A-Z]', compact) and re.search(r'\d', compact):
                line_item_count += 1
        return (
            line_item_count,
            1 if "PROJECT:" in upper else 0,
            1 if "MEAS" in upper else 0,
            len(re.findall(r"\$\s*\d+\.\d{2}", upper)),
            len(upper),
        )
    texts.sort(key=_score, reverse=True)
    return texts[0]


# Project code patterns
_PROJECT_CODE_RE = re.compile(r"PROJ[-\s]?\d{4}[-\s]?\d{3}", re.IGNORECASE)


def _extract_project_code(text: str) -> Optional[str]:
    """Extract project code from text."""
    match = _PROJECT_CODE_RE.search(text)
    if match:
        return match.group(0).upper().replace(" ", "-")
    return None


# Date patterns
_DATE_PATTERNS = [
    (re.compile(r"MEAS\.?\s*DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), True),
    (re.compile(r"MEASUREMENT\s*DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), True),
    (re.compile(r"DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), True),
    (re.compile(r"\b([0-3]?\d/[01]?\d/20\d{2})\b"), False),
    (re.compile(r"\b([0-3]?\d-[01]?\d-20\d{2})\b"), False),
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


# Money pattern
_MONEY_RE = re.compile(
    r"(\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2})",
)


def _extract_items_from_text(text: str) -> List[Dict[str, str]]:
    """Extract item details from text."""
    items = []
    seen = set()
    lines = text.splitlines()
    money_re = re.compile(r"\$?\s*(\d+(?:\.\d{2})?)")
    skip_re = re.compile(r"PROJECT\s*TOTAL|ITEM\s*DESCRIPTION|MEAS\.?\s*DATE|PROJECT:", re.IGNORECASE)
    
    for line in lines:
        line = line.strip()
        if not line or skip_re.search(line):
            continue
        if '$' not in line:
            continue
        money_matches = money_re.findall(line)
        if not money_matches:
            continue
        price_str = money_matches[-1]
        prefix = line[: line.rfind(price_str)].replace('$', ' ')
        qty_matches = list(re.finditer(r"\b\d+(?:\.\d+)?\b", prefix))
        if not qty_matches:
            continue
        qty_match = qty_matches[-1]
        qty_str = qty_match.group(0)
        desc = prefix[:qty_match.start()]
        desc = re.sub(r"[^A-Za-z0-9\s\-()]", " ", desc)
        desc = re.sub(r"\s+", " ", desc).strip(" -")
        if not desc:
            continue
        
        try:
            qty_formatted = str(Decimal(qty_str).normalize()) if '.' in qty_str else qty_str
            price_formatted = _as_two_decimal_string(Decimal(price_str))
            key = (desc.lower(), qty_formatted, price_formatted)
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "item_description": desc,
                "quantity": qty_formatted,
                "unit_price": price_formatted,
            })
        except Exception:
            pass
    
    return items


# Total keywords
_TOTAL_KEYWORDS = [
    r"PROJECT\s*TOTAL",
    r"GRAND\s*TOTAL",
    r"\bTOTAL\b",
]


def _extract_total_from_text(text: str) -> Optional[Decimal]:
    """Extract total amount from text."""
    if not text:
        return None
    
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    total_re = re.compile("|".join(_TOTAL_KEYWORDS), re.IGNORECASE)
    
    candidates: List[Tuple[Decimal, int]] = []
    
    for i, line in enumerate(lines):
        if total_re.search(line):
            nums = _MONEY_RE.findall(line)
            if nums:
                try:
                    val = Decimal(nums[-1].replace(",", "").replace(" ", ""))
                    priority = 50 if re.search(r"PROJECT\s*TOTAL", line, re.IGNORECASE) else 20
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


def extract_data_from_images(dataset_dir: str) -> Tuple[List[Dict], List[Dict]]:
    """Process all images and extract details and summary."""
    details: List[Dict] = []
    summary: Dict[str, Dict] = {}
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
            continue
        
        if not text:
            continue
        
        project_code = _extract_project_code(text)
        dt = _extract_date_from_text(text)
        amount = _extract_total_from_text(text)
        items = _extract_items_from_text(text)
        
        date_str = dt.strftime("%Y-%m-%d") if dt else None
        amount_str = _as_two_decimal_string(amount) if amount else None
        
        # Add details
        for item in items:
            details.append({
                "filename": entry,
                "project_code": project_code,
                "item_description": item.get("item_description"),
                "quantity": item.get("quantity"),
                "unit_price": item.get("unit_price"),
            })
        
        # Add summary (only first occurrence per project)
        if project_code and project_code not in summary:
            summary[project_code] = {
                "project_code": project_code,
                "date": date_str,
                "total_amount": amount_str,
            }
    
    summary_list = [summary[k] for k in sorted(summary.keys())]
    
    return details, summary_list


def main():
    dataset_dir = "/app/workspace/dataset/img"
    output_path = "/app/workspace/construction_summary.xlsx"
    
    details, summary = extract_data_from_images(dataset_dir)
    
    wb = Workbook()
    
    # Sheet 1: details
    ws_details = wb.active
    ws_details.title = "details"
    ws_details.append(["filename", "project_code", "item_description", "quantity", "unit_price"])
    for row in details:
        ws_details.append([
            row.get("filename"),
            row.get("project_code"),
            row.get("item_description"),
            row.get("quantity"),
            row.get("unit_price"),
        ])
    
    # Sheet 2: summary
    ws_summary = wb.create_sheet("summary")
    ws_summary.append(["project_code", "date", "total_amount"])
    for row in summary:
        ws_summary.append([
            row.get("project_code"),
            row.get("date"),
            row.get("total_amount"),
        ])
    
    wb.save(output_path)
    print(f"Extracted {len(details)} line items and {len(summary)} projects to {output_path}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /app/workspace/extract_construction.py
