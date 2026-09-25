import re
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pytesseract
from PIL import Image, ImageFilter, ImageOps

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'}
MONEY_RE = re.compile(r"(?:[$€£]|RM|MYR)?\s*(\d{1,3}(?:[,\s]\d{3})*\.\d{2}|\d+\.\d{2})", re.IGNORECASE)


def as_two_decimal_string(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def preprocess_image(img: Image.Image) -> List[Image.Image]:
    gray = ImageOps.grayscale(img)
    variants: List[Image.Image] = []
    auto = ImageOps.autocontrast(gray, cutoff=1)
    variants.append(auto)
    variants.append(auto.filter(ImageFilter.SHARPEN))
    variants.append(auto.point(lambda p: 255 if p > 145 else 0))
    variants.append(auto.point(lambda p: 255 if p > 120 else 0))
    w, h = gray.size
    if w < 1600 or h < 1600:
        scale = max(1600 / max(w, 1), 1600 / max(h, 1), 2)
        scaled = gray.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        scaled = ImageOps.autocontrast(scaled, cutoff=1)
        variants.append(scaled)
    return variants


def ocr_extract_text(image_path: str) -> str:
    img = Image.open(image_path)
    variants = preprocess_image(img)
    configs = [
        '--psm 6',
        '--psm 4',
        '--psm 11',
        '--psm 6 -c tessedit_char_whitelist=0123456789/-.:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz# ',
    ]
    texts: List[str] = []
    for variant in variants:
        for config in configs:
            try:
                text = pytesseract.image_to_string(variant, config=config)
                if text.strip():
                    texts.append(text)
            except Exception:
                pass
    return '\n'.join(texts)


def parse_date_text(date_text: str, *, allow_month_year: bool = False, day_first_preferred: bool = True) -> Optional[datetime]:
    normalized = date_text.strip()
    normalized = normalized.replace('O', '0').replace('o', '0')
    normalized = normalized.replace('I', '1').replace('l', '1')
    normalized = normalized.replace(' ', '')
    day_first = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']
    month_first = ['%m/%d/%Y', '%m-%d-%Y', '%m/%d/%y', '%m-%d-%y']
    formats = (day_first + month_first) if day_first_preferred else (month_first + day_first)
    formats += ['%Y/%m/%d', '%Y-%m-%d']
    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if 2000 <= dt.year <= 2035:
                return dt
        except ValueError:
            continue
    if allow_month_year:
        for fmt in ['%m/%Y', '%m-%Y']:
            try:
                dt = datetime.strptime(normalized, fmt)
                if 2000 <= dt.year <= 2035:
                    return dt.replace(day=1)
            except ValueError:
                continue
    return None


def find_best_date(text: str, pattern_defs: Sequence[Tuple[str, int, bool]], *, allow_month_year: bool = False) -> Optional[datetime]:
    if not text:
        return None
    matches: List[Tuple[int, datetime]] = []
    for pattern, priority, day_first_preferred in pattern_defs:
        regex = re.compile(pattern, re.IGNORECASE)
        for match in regex.findall(text):
            candidate = match[0] if isinstance(match, tuple) else match
            dt = parse_date_text(candidate, allow_month_year=allow_month_year, day_first_preferred=day_first_preferred)
            if dt:
                matches.append((priority, dt))
    if not matches:
        generic_patterns = [r'(20\d{2}[-/]\d{2}[-/]\d{2})', r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})']
        for pattern in generic_patterns:
            for candidate in re.findall(pattern, text):
                dt = parse_date_text(candidate, allow_month_year=allow_month_year, day_first_preferred=True)
                if dt:
                    matches.append((1, dt))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def extract_amount_by_keywords(text: str, keyword_patterns: Sequence[str], exclude_patterns: Sequence[str] | None = None) -> Optional[Decimal]:
    if not text:
        return None
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    exclude_re = re.compile('|'.join(exclude_patterns), re.IGNORECASE) if exclude_patterns else None
    candidates: List[Tuple[int, Decimal]] = []
    for line_index, line in enumerate(lines):
        if exclude_re and exclude_re.search(line):
            continue
        for keyword_index, keyword in enumerate(keyword_patterns):
            if re.search(keyword, line, re.IGNORECASE):
                nums = MONEY_RE.findall(line)
                priority = len(keyword_patterns) - keyword_index
                if nums:
                    for num in nums[-2:]:
                        try:
                            candidates.append((priority, Decimal(num.replace(',', '').replace(' ', ''))))
                        except Exception:
                            pass
                elif line_index + 1 < len(lines):
                    next_nums = MONEY_RE.findall(lines[line_index + 1])
                    if next_nums:
                        try:
                            candidates.append((priority - 1, Decimal(next_nums[-1].replace(',', '').replace(' ', ''))))
                        except Exception:
                            pass
                break
    if not candidates:
        fallback: List[Decimal] = []
        for line in lines:
            if exclude_re and exclude_re.search(line):
                continue
            for num in MONEY_RE.findall(line):
                try:
                    fallback.append(Decimal(num.replace(',', '').replace(' ', '')))
                except Exception:
                    pass
        if fallback:
            return max(fallback)
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][1]


def list_images(root: Path, *, recursive: bool = False) -> List[Path]:
    if recursive:
        paths = [p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
        return sorted(paths, key=lambda p: p.relative_to(root).as_posix())
    paths = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    return sorted(paths, key=lambda p: p.name)
