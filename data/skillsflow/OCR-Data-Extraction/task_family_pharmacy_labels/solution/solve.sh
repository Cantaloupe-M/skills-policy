#!/bin/bash

set -e

cat > /app/workspace/extract_pharmacy.py << 'PYTHON_SCRIPT'
import os
import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageOps, ImageFilter
import pytesseract
from openpyxl import Workbook


def _parse_date_any_format(date_text: str) -> Optional[datetime]:
    """Parse date strings in multiple formats, including month/year only."""
    normalized = date_text.strip()
    normalized = normalized.replace("O", "0").replace("o", "0")
    normalized = normalized.replace("I", "1").replace("l", "1")
    normalized = normalized.replace(" ", "")
    
    # Full date formats
    full_formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
        "%Y/%m/%d", "%Y-%m-%d",
    ]
    
    for fmt in full_formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if 2000 <= dt.year <= 2030:
                return dt
        except ValueError:
            continue
    
    # Month/year only formats
    month_year_formats = ["%m/%Y", "%m-%Y"]
    for fmt in month_year_formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            # Use first day of month
            if 2000 <= dt.year <= 2030:
                return dt.replace(day=1)
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
        ImageOps.invert(auto),
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
        "--psm 7",
        "--psm 6 -c tessedit_char_whitelist=0123456789.$RMYrm/-:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
        "--psm 11 -c tessedit_char_whitelist=0123456789.$RMYrm/-:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
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
        return (
            1 if re.search(r"(?:MYR|RM|\$)\s*\d", upper) else 0,
            1 if "EXP" in upper else 0,
            len(re.findall(r"\d+\.\d{2}", upper)),
            len(upper),
        )
    texts.sort(key=_score, reverse=True)
    return texts[0]


# Date patterns with priority (higher number = higher priority)
_DATE_PATTERNS = [
    (re.compile(r"EXPIR[Y]?\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 50),
    (re.compile(r"EXP\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 50),
    (re.compile(r"EXPIR[Y]?\s*:?\s*([01]?\d[/\-]\d{2,4})", re.IGNORECASE), 50),
    (re.compile(r"EXP\s*:?\s*([01]?\d[/\-]\d{2,4})", re.IGNORECASE), 50),
    (re.compile(r"EXPIRES?\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 40),
    (re.compile(r"MFG\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 10),
    (re.compile(r"MANUFACTURED?\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 10),
    (re.compile(r"DATE\s*:?\s*([0-3]?\d[/\-][01]?\d[/\-]\d{2,4})", re.IGNORECASE), 5),
    # Generic date patterns
    (re.compile(r"\b([0-3]?\d/[01]?\d/20\d{2})\b"), 1),
    (re.compile(r"\b([0-3]?\d-[01]?\d-20\d{2})\b"), 1),
    (re.compile(r"\b([01]?\d/20\d{2})\b"), 1),
]


def _extract_date_from_text(text: str) -> Optional[datetime]:
    """Extract date with priority to expiry dates."""
    if not text:
        return None
    
    found_dates: List[Tuple[datetime, int]] = []
    
    for pat, priority in _DATE_PATTERNS:
        for match in pat.findall(text):
            candidate = match if isinstance(match, str) else match
            dt = _parse_date_any_format(candidate)
            if dt:
                found_dates.append((dt, priority))
    
    if not found_dates:
        return None
    
    # Return highest priority date
    found_dates.sort(key=lambda x: x[1], reverse=True)
    return found_dates[0][0]


# Price patterns
_PRICE_RE = re.compile(
    r"(?:[$€£]|RM|MYR)?\s*(\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2})",
    re.IGNORECASE
)

_PRICE_KEYWORDS = [
    r"PRICE\s*:?",
    r"\$",
    r"\bRM\b",
    r"\bMYR\b",
    r"TOTAL\s*PRICE",
]


def _extract_price_from_text(text: str) -> Optional[Decimal]:
    """Extract price with keyword context."""
    if not text:
        return None
    
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    
    price_kw_re = re.compile("|".join(_PRICE_KEYWORDS), re.IGNORECASE)
    
    candidates: List[Decimal] = []
    
    for line in lines:
        # Check for price keywords
        if price_kw_re.search(line):
            nums = _PRICE_RE.findall(line)
            if nums:
                try:
                    val = Decimal(nums[-1].replace(",", "").replace(" ", ""))
                    candidates.append(val)
                except Exception:
                    pass
    
    # Also look for "EACH" which often indicates unit price
    for line in lines:
        if "EACH" in line.upper():
            nums = _PRICE_RE.findall(line)
            if nums:
                try:
                    val = Decimal(nums[-1].replace(",", "").replace(" ", ""))
                    if val not in candidates:
                        candidates.append(val)
                except Exception:
                    pass
    
    # Fallback: look for any price-like number
    if not candidates:
        all_nums = _PRICE_RE.findall(text)
        for num in all_nums:
            try:
                val = Decimal(num.replace(",", "").replace(" ", ""))
                # Reasonable price range for pharmacy items
                if Decimal("0.01") <= val <= Decimal("9999.99"):
                    candidates.append(val)
            except Exception:
                pass
    
    # Return first candidate (most likely to be correct)
    if candidates:
        return candidates[0]
    
    return None


def extract_data_from_images(dataset_dir: str) -> Dict[str, Dict[str, str]]:
    """Process all images and extract date/price for each."""
    results: Dict[str, Dict[str, str]] = {}
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
            results[entry] = {"date": None, "price": None}
            continue
        
        if not text:
            results[entry] = {"date": None, "price": None}
            continue
        
        dt = _extract_date_from_text(text)
        price = _extract_price_from_text(text)
        
        date_str = dt.strftime("%Y-%m-%d") if dt else None
        price_str = _as_two_decimal_string(price) if price else None
        
        results[entry] = {
            "date": date_str,
            "price": price_str,
        }
    
    return results


def main():
    dataset_dir = "/app/workspace/dataset/img"
    output_path = "/app/workspace/pharmacy_prices.xlsx"
    
    results = extract_data_from_images(dataset_dir)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "products"
    ws.append(["filename", "date", "price"])
    
    for filename in sorted(results.keys()):
        row = results[filename]
        ws.append([filename, row.get("date"), row.get("price")])
    
    wb.save(output_path)
    print(f"Extracted {len(results)} pharmacy labels to {output_path}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /app/workspace/extract_pharmacy.py
