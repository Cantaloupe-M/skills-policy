#!/bin/bash
set -euo pipefail

cat > /tmp/unpack.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Unpack and format XML contents of Office files (.docx, .pptx, .xlsx)"""

import random
import sys
import defusedxml.minidom
import zipfile
from pathlib import Path

assert len(sys.argv) == 3, "Usage: python unpack.py <office_file> <output_dir>"
input_file, output_dir = sys.argv[1], sys.argv[2]

output_path = Path(output_dir)
output_path.mkdir(parents=True, exist_ok=True)
zipfile.ZipFile(input_file).extractall(output_path)

xml_files = list(output_path.rglob("*.xml")) + list(output_path.rglob("*.rels"))
for xml_file in xml_files:
    content = xml_file.read_text(encoding="utf-8")
    dom = defusedxml.minidom.parseString(content)
    xml_file.write_bytes(dom.toprettyxml(indent="  ", encoding="ascii"))

if input_file.endswith(".docx"):
    suggested_rsid = "".join(random.choices("0123456789ABCDEF", k=8))
    print(f"Suggested RSID for edit session: {suggested_rsid}")
PYTHON_SCRIPT

cat > /tmp/pack.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Tool to pack a directory into a .docx, .pptx, or .xlsx file."""

import argparse
import shutil
import subprocess
import sys
import tempfile
import defusedxml.minidom
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Pack a directory into an Office file")
    parser.add_argument("input_directory", help="Unpacked Office document directory")
    parser.add_argument("output_file", help="Output Office file (.docx/.pptx/.xlsx)")
    parser.add_argument("--force", action="store_true", help="Skip validation")
    args = parser.parse_args()

    try:
        success = pack_document(
            args.input_directory, args.output_file, validate=not args.force
        )
        if args.force:
            print("Warning: Skipped validation, file may be corrupt", file=sys.stderr)
        elif not success:
            print("Contents would produce a corrupt file.", file=sys.stderr)
            print("Please validate XML before repacking.", file=sys.stderr)
            print("Use --force to skip validation and pack anyway.", file=sys.stderr)
            sys.exit(1)
    except ValueError as e:
        sys.exit(f"Error: {e}")


def pack_document(input_dir, output_file, validate=False):
    input_dir = Path(input_dir)
    output_file = Path(output_file)

    if not input_dir.is_dir():
        raise ValueError(f"{input_dir} is not a directory")
    if output_file.suffix.lower() not in {".docx", ".pptx", ".xlsx"}:
        raise ValueError(f"{output_file} must be a .docx, .pptx, or .xlsx file")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_content_dir = Path(temp_dir) / "content"
        shutil.copytree(input_dir, temp_content_dir)

        for pattern in ["*.xml", "*.rels"]:
            for xml_file in temp_content_dir.rglob(pattern):
                condense_xml(xml_file)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in temp_content_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(temp_content_dir))

        if validate:
            if not validate_document(output_file):
                output_file.unlink()
                return False

    return True


def validate_document(doc_path):
    match doc_path.suffix.lower():
        case ".docx":
            filter_name = "html:HTML"
        case ".pptx":
            filter_name = "html:impress_html_Export"
        case ".xlsx":
            filter_name = "html:HTML (StarCalc)"

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    filter_name,
                    "--outdir",
                    temp_dir,
                    str(doc_path),
                ],
                capture_output=True,
                timeout=10,
                text=True,
            )
            if not (Path(temp_dir) / f"{doc_path.stem}.html").exists():
                error_msg = result.stderr.strip() or "Document validation failed"
                print(f"Validation error: {error_msg}", file=sys.stderr)
                return False
            return True
        except FileNotFoundError:
            print("Warning: soffice not found. Skipping validation.", file=sys.stderr)
            return True
        except subprocess.TimeoutExpired:
            print("Validation error: Timeout during conversion", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return False


def condense_xml(xml_file):
    with open(xml_file, "r", encoding="utf-8") as f:
        dom = defusedxml.minidom.parse(f)

    for element in dom.getElementsByTagName("*"):
        if element.tagName.endswith(":t"):
            continue
        for child in list(element.childNodes):
            if (
                child.nodeType == child.TEXT_NODE
                and child.nodeValue
                and child.nodeValue.strip() == ""
            ) or child.nodeType == child.COMMENT_NODE:
                element.removeChild(child)

    with open(xml_file, "wb") as f:
        f.write(dom.toxml(encoding="UTF-8"))


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

cat > /tmp/recalc.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
"""Recalculate all formulas in an Excel file using LibreOffice."""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from openpyxl import load_workbook


def setup_libreoffice_macro():
    if platform.system() == "Darwin":
        macro_dir = os.path.expanduser("~/Library/Application Support/LibreOffice/4/user/basic/Standard")
    else:
        macro_dir = os.path.expanduser("~/.config/libreoffice/4/user/basic/Standard")

    macro_file = os.path.join(macro_dir, "Module1.xba")

    if os.path.exists(macro_file):
        with open(macro_file, "r") as f:
            if "RecalculateAndSave" in f.read():
                return True

    if not os.path.exists(macro_dir):
        subprocess.run(["soffice", "--headless", "--terminate_after_init"], capture_output=True, timeout=10)
        os.makedirs(macro_dir, exist_ok=True)

    macro_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">
    Sub RecalculateAndSave()
      ThisComponent.calculateAll()
      ThisComponent.store()
      ThisComponent.close(True)
    End Sub
</script:module>'''

    try:
        with open(macro_file, "w") as f:
            f.write(macro_content)
        return True
    except Exception:
        return False


def recalc(filename, timeout=30):
    if not Path(filename).exists():
        return {"error": f"File {filename} does not exist"}

    abs_path = str(Path(filename).absolute())

    if not setup_libreoffice_macro():
        return {"error": "Failed to setup LibreOffice macro"}

    cmd = [
        "soffice", "--headless", "--norestore",
        "vnd.sun.star.script:Standard.Module1.RecalculateAndSave?language=Basic&location=application",
        abs_path,
    ]

    if platform.system() != "Windows":
        timeout_cmd = "timeout" if platform.system() == "Linux" else None
        if platform.system() == "Darwin":
            try:
                subprocess.run(["gtimeout", "--version"], capture_output=True, timeout=1, check=False)
                timeout_cmd = "gtimeout"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        if timeout_cmd:
            cmd = [timeout_cmd, str(timeout)] + cmd

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 and result.returncode != 124:
        error_msg = result.stderr or "Unknown error during recalculation"
        if "Module1" in error_msg or "RecalculateAndSave" not in error_msg:
            return {"error": "LibreOffice macro not configured properly"}
        return {"error": error_msg}

    try:
        wb = load_workbook(filename, data_only=True)
        excel_errors = ["#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "#N/A"]
        error_details = {err: [] for err in excel_errors}
        total_errors = 0

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None and isinstance(cell.value, str):
                        for err in excel_errors:
                            if err in cell.value:
                                location = f"{sheet_name}!{cell.coordinate}"
                                error_details[err].append(location)
                                total_errors += 1
                                break
        wb.close()

        result_data = {
            "status": "success" if total_errors == 0 else "errors_found",
            "total_errors": total_errors,
            "error_summary": {},
        }
        for err_type, locations in error_details.items():
            if locations:
                result_data["error_summary"][err_type] = {
                    "count": len(locations),
                    "locations": locations[:20],
                }

        wb_formulas = load_workbook(filename, data_only=False)
        formula_count = 0
        for sheet_name in wb_formulas.sheetnames:
            ws = wb_formulas[sheet_name]
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value and isinstance(cell.value, str) and cell.value.startswith("="):
                        formula_count += 1
        wb_formulas.close()

        result_data["total_formulas"] = formula_count
        return result_data
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    filename = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    print(json.dumps(recalc(filename, timeout), indent=2))


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

cat > /tmp/update_embedded_matrix.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from openpyxl import load_workbook

A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
IGNORE_MARKERS = ('archive', 'archived', 'superseded', 'draft', 'obsolete')
PREFER_MARKERS = ('final', 'approved', 'live', 'current')
UPDATE_PATTERN = re.compile(
    r'([A-Za-z0-9]+)\s+to\s+([A-Za-z0-9]+)\s*=\s*([0-9]+(?:\.[0-9]+)?)',
    re.IGNORECASE,
)


def normalize(text: object) -> str:
    return ''.join(ch.lower() for ch in str(text) if ch.isalnum())


def is_formula(value: object) -> bool:
    return isinstance(value, str) and value.startswith('=')


def extract_text_chunks(work_dir: Path) -> list[str]:
    chunks: list[str] = []
    slide_dir = work_dir / 'ppt' / 'slides'
    for slide_xml in sorted(slide_dir.glob('slide*.xml')):
        tree = ET.parse(slide_xml)
        for node in tree.iterfind(f'.//{A_NS}t'):
            text = (node.text or '').strip()
            if not text:
                continue
            parts = [part.strip() for part in re.split(r'\|\||\n', text) if part.strip()]
            chunks.extend(parts)
    return chunks


def choose_update(chunks: list[str]) -> tuple[str, str, float]:
    candidates: list[tuple[int, int, str, str, float]] = []
    for index, chunk in enumerate(chunks):
        match = UPDATE_PATTERN.search(chunk)
        if not match:
            continue
        lower = chunk.lower()
        score = 0
        if any(marker in lower for marker in PREFER_MARKERS):
            score += 5
        if any(marker in lower for marker in IGNORE_MARKERS):
            score -= 5
        candidates.append((score, index, match.group(1), match.group(2), float(match.group(3))))
    if not candidates:
        raise ValueError('No usable update instruction found in slide text')
    candidates.sort(key=lambda item: (item[0], item[1]))
    _, _, from_token, to_token, rate = candidates[-1]
    return from_token, to_token, rate


def token_matches(value: object, token: str) -> bool:
    if value is None:
        return False
    return normalize(token) in normalize(value)


def locate_matrix(ws, from_token: str, to_token: str):
    for anchor_row in range(1, ws.max_row + 1):
        for anchor_col in range(1, ws.max_column + 1):
            row_labels = {
                row: ws.cell(row=row, column=anchor_col).value
                for row in range(anchor_row + 1, ws.max_row + 1)
                if ws.cell(row=row, column=anchor_col).value not in (None, '')
            }
            col_labels = {
                col: ws.cell(row=anchor_row, column=col).value
                for col in range(anchor_col + 1, ws.max_column + 1)
                if ws.cell(row=anchor_row, column=col).value not in (None, '')
            }
            if len(row_labels) < 2 or len(col_labels) < 2:
                continue

            from_rows = [row for row, value in row_labels.items() if token_matches(value, from_token)]
            to_rows = [row for row, value in row_labels.items() if token_matches(value, to_token)]
            from_cols = [col for col, value in col_labels.items() if token_matches(value, from_token)]
            to_cols = [col for col, value in col_labels.items() if token_matches(value, to_token)]
            if not from_rows or not to_rows or not from_cols or not to_cols:
                continue

            for from_row in from_rows:
                for to_row in to_rows:
                    for from_col in from_cols:
                        for to_col in to_cols:
                            direct = ws.cell(row=from_row, column=to_col).value
                            inverse = ws.cell(row=to_row, column=from_col).value
                            if direct is None or inverse is None:
                                continue
                            return {
                                'from_row': from_row,
                                'to_row': to_row,
                                'from_col': from_col,
                                'to_col': to_col,
                            }
    return None


def locate_workbook_target(workbook_path: Path, from_token: str, to_token: str):
    wb = load_workbook(workbook_path)
    try:
        for ws in wb.worksheets:
            matrix = locate_matrix(ws, from_token, to_token)
            if matrix:
                return wb, ws, matrix
    except Exception:
        wb.close()
        raise
    wb.close()
    raise ValueError(f'Could not find a reciprocal matrix for {from_token} and {to_token}')


def recalc_excel(workbook_path: Path) -> None:
    result = subprocess.run(
        ['python3', '/tmp/recalc.py', str(workbook_path), '90'],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f'Recalculation failed: {result.stderr or result.stdout}')
    payload = result.stdout.strip()
    if payload:
        data = json.loads(payload)
        if 'error' in data:
            raise RuntimeError(data['error'])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    work_dir = Path(tempfile.mkdtemp(prefix='embedded-matrix-'))
    try:
        subprocess.run(['python3', '/tmp/unpack.py', args.input, str(work_dir)], check=True)
        text_chunks = extract_text_chunks(work_dir)
        from_token, to_token, new_rate = choose_update(text_chunks)

        embeddings = sorted((work_dir / 'ppt' / 'embeddings').glob('*.xlsx'))
        if not embeddings:
            raise ValueError('No embedded workbook found inside the PPTX')
        workbook_path = embeddings[0]

        wb, ws, matrix = locate_workbook_target(workbook_path, from_token, to_token)
        try:
            direct_cell = ws.cell(row=matrix['from_row'], column=matrix['to_col'])
            inverse_cell = ws.cell(row=matrix['to_row'], column=matrix['from_col'])
            if not is_formula(direct_cell.value):
                direct_cell.value = new_rate
            elif not is_formula(inverse_cell.value):
                inverse_cell.value = 1.0 / new_rate
            else:
                raise ValueError('Both candidate cells are formulas; no writable input cell found')
            wb.save(workbook_path)
        finally:
            wb.close()

        recalc_excel(workbook_path)
        subprocess.run(['python3', '/tmp/pack.py', str(work_dir), args.output, '--force'], check=True)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
PYTHON_SCRIPT

python3 /tmp/update_embedded_matrix.py --input /root/input.pptx --output /root/results.pptx
echo "Solution complete."
