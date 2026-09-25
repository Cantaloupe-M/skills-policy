#!/bin/bash
set -euo pipefail

cat > /tmp/oracle_config.json <<'JSON_CONFIG'
{
  "target_embedding": "Microsoft_Excel_Worksheet.xlsx",
  "target_sheet": "Live Catalyst Matrix",
  "anchor_row": 4,
  "anchor_col": 2,
  "alias_map": "/root/label_aliases.csv"
}
JSON_CONFIG

cat > /tmp/update_embedded_matrix.py <<'PYTHON_SCRIPT'
#!/usr/bin/env python3
import argparse
import csv
import json
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import defusedxml.minidom
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
IGNORE_MARKERS = ('archive', 'archived', 'superseded', 'draft', 'obsolete')
PREFER_MARKERS = ('final', 'approved', 'live', 'current')
UPDATE_PATTERN = re.compile(
    r'([A-Za-z0-9]+)\s+to\s+([A-Za-z0-9]+)\s*=\s*([0-9]+(?:\.[0-9]+)?)',
    re.IGNORECASE,
)
X_NS = {'': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def normalize(text: object) -> str:
    return ''.join(ch.lower() for ch in str(text) if ch.isalnum())


def is_formula(value: object) -> bool:
    return isinstance(value, str) and value.startswith('=')


def load_config(config_path: Path) -> dict:
    with open(config_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def unpack_office(input_file: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(input_file, 'r') as zf:
        zf.extractall(output_dir)
    xml_files = list(output_dir.rglob('*.xml')) + list(output_dir.rglob('*.rels'))
    for xml_file in xml_files:
        content = xml_file.read_text(encoding='utf-8')
        dom = defusedxml.minidom.parseString(content)
        xml_file.write_bytes(dom.toprettyxml(indent='  ', encoding='ascii'))


def condense_xml(xml_file: Path) -> None:
    with open(xml_file, 'r', encoding='utf-8') as handle:
        dom = defusedxml.minidom.parse(handle)
    for element in dom.getElementsByTagName('*'):
        if element.tagName.endswith(':t'):
            continue
        for child in list(element.childNodes):
            if (
                child.nodeType == child.TEXT_NODE
                and child.nodeValue
                and child.nodeValue.strip() == ''
            ) or child.nodeType == child.COMMENT_NODE:
                element.removeChild(child)
    with open(xml_file, 'wb') as handle:
        handle.write(dom.toxml(encoding='UTF-8'))


def pack_office(input_dir: Path, output_file: Path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_content_dir = Path(temp_dir) / 'content'
        shutil.copytree(input_dir, temp_content_dir)
        for pattern in ('*.xml', '*.rels'):
            for xml_file in temp_content_dir.rglob(pattern):
                condense_xml(xml_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in temp_content_dir.rglob('*'):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(temp_content_dir))


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


def resolve_aliases(config: dict, from_token: str, to_token: str) -> tuple[str, str]:
    alias_path = config.get('alias_map')
    if not alias_path:
        return from_token, to_token
    alias_map = {}
    with open(alias_path, 'r', encoding='utf-8', newline='') as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            alias_map[normalize(row['note_token'])] = row['workbook_label']
    return alias_map.get(normalize(from_token), from_token), alias_map.get(normalize(to_token), to_token)


def select_embedding(work_dir: Path, config: dict) -> Path:
    embeddings_dir = work_dir / 'ppt' / 'embeddings'
    embeddings = sorted(embeddings_dir.glob('*.xlsx'))
    if not embeddings:
        raise ValueError('No embedded workbook found inside the PPTX')
    target_name = config.get('target_embedding')
    if target_name:
        target_path = embeddings_dir / target_name
        if not target_path.exists():
            raise ValueError(f'Target embedding {target_name} not found')
        return target_path
    if len(embeddings) != 1:
        raise ValueError('Multiple embedded workbooks found but no target embedding was configured')
    return embeddings[0]


def token_matches(value: object, token: str) -> bool:
    return value is not None and normalize(token) in normalize(value)


def matrix_labels_at_anchor(ws, anchor_row: int, anchor_col: int):
    row_labels = {}
    row = anchor_row + 1
    while row <= ws.max_row and ws.cell(row=row, column=anchor_col).value not in (None, ''):
        row_labels[row] = ws.cell(row=row, column=anchor_col).value
        row += 1
    col_labels = {}
    col = anchor_col + 1
    while col <= ws.max_column and ws.cell(row=anchor_row, column=col).value not in (None, ''):
        col_labels[col] = ws.cell(row=anchor_row, column=col).value
        col += 1
    return row_labels, col_labels


def locate_matrix_at_anchor(ws, anchor_row: int, anchor_col: int, from_token: str, to_token: str):
    row_labels, col_labels = matrix_labels_at_anchor(ws, anchor_row, anchor_col)
    from_rows = [row for row, value in row_labels.items() if token_matches(value, from_token)]
    to_rows = [row for row, value in row_labels.items() if token_matches(value, to_token)]
    from_cols = [col for col, value in col_labels.items() if token_matches(value, from_token)]
    to_cols = [col for col, value in col_labels.items() if token_matches(value, to_token)]
    if not from_rows or not to_rows or not from_cols or not to_cols:
        raise ValueError(f'Could not find tokens {from_token} / {to_token} at anchor {anchor_row},{anchor_col}')
    return {
        'from_row': from_rows[0],
        'to_row': to_rows[0],
        'from_col': from_cols[0],
        'to_col': to_cols[0],
    }


def find_title_cell(ws, title: str):
    for row in ws.iter_rows():
        for cell in row:
            if cell.value == title:
                return cell.row, cell.column
    raise ValueError(f'Could not find matrix title {title!r}')


def locate_matrix(ws, from_token: str, to_token: str):
    for anchor_row in range(1, ws.max_row + 1):
        for anchor_col in range(1, ws.max_column + 1):
            if ws.cell(row=anchor_row, column=anchor_col).value in (None, ''):
                continue
            try:
                matrix = locate_matrix_at_anchor(ws, anchor_row, anchor_col, from_token, to_token)
                direct = ws.cell(row=matrix['from_row'], column=matrix['to_col']).value
                inverse = ws.cell(row=matrix['to_row'], column=matrix['from_col']).value
                if direct is not None and inverse is not None:
                    return matrix
            except Exception:
                continue
    raise ValueError(f'Could not find a reciprocal matrix for {from_token} and {to_token}')


def locate_target(ws, config: dict, from_token: str, to_token: str):
    if config.get('matrix_title'):
        title_row, title_col = find_title_cell(ws, config['matrix_title'])
        return locate_matrix_at_anchor(ws, title_row + 1, title_col, from_token, to_token)
    if config.get('anchor_row') and config.get('anchor_col'):
        return locate_matrix_at_anchor(ws, int(config['anchor_row']), int(config['anchor_col']), from_token, to_token)
    return locate_matrix(ws, from_token, to_token)


def unpack_embedded_workbook(workbook_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(workbook_path, 'r') as zf:
        zf.extractall(output_dir)


def pack_embedded_workbook(input_dir: Path, workbook_path: Path) -> None:
    with zipfile.ZipFile(workbook_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(input_dir.rglob('*')):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(input_dir))


def resolve_sheet_xml(xlsx_dir: Path, sheet_name: str) -> Path:
    workbook_tree = ET.parse(xlsx_dir / 'xl' / 'workbook.xml')
    rels_tree = ET.parse(xlsx_dir / 'xl' / '_rels' / 'workbook.xml.rels')

    rel_targets = {}
    for rel in rels_tree.getroot().findall('{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
        rel_targets[rel.get('Id')] = rel.get('Target')

    sheets = workbook_tree.getroot().find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheets')
    if sheets is None:
        raise ValueError('Workbook sheets metadata is missing')

    rel_attr = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    for sheet in sheets.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet'):
        if sheet.get('name') != sheet_name:
            continue
        rel_id = sheet.get(rel_attr)
        target = rel_targets.get(rel_id)
        if not target:
            raise ValueError(f'Could not resolve XML target for sheet {sheet_name!r}')
        target_path = Path(target.lstrip('/'))
        if target.startswith('/'):
            return xlsx_dir / target_path
        return xlsx_dir / 'xl' / target_path

    raise ValueError(f'Could not find sheet {sheet_name!r} inside workbook metadata')


def patch_cell_cache(sheet_xml: Path, row: int, col: int, new_value: float) -> None:
    tree = ET.parse(sheet_xml)
    root = tree.getroot()
    target_ref = f'{get_column_letter(col)}{row}'
    for c in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
        if c.get('r') == target_ref:
            v_elem = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            if v_elem is None:
                v_elem = ET.SubElement(c, '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            v_elem.text = str(new_value)
            tree.write(sheet_xml, encoding='UTF-8', xml_declaration=True)
            return
    raise ValueError(f'Could not find cell {target_ref} in {sheet_xml.name}')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()

    config = load_config(Path(args.config))
    work_dir = Path(tempfile.mkdtemp(prefix='embedded-matrix-'))
    try:
        unpack_office(Path(args.input), work_dir)
        text_chunks = extract_text_chunks(work_dir)
        from_token, to_token, new_rate = choose_update(text_chunks)
        from_token, to_token = resolve_aliases(config, from_token, to_token)
        workbook_path = select_embedding(work_dir, config)

        wb = load_workbook(workbook_path, data_only=False)
        try:
            ws = wb[config['target_sheet']] if config.get('target_sheet') else wb.active
            target_sheet_name = ws.title
            matrix = locate_target(ws, config, from_token, to_token)
            direct_cell = ws.cell(row=matrix['from_row'], column=matrix['to_col'])
            inverse_cell = ws.cell(row=matrix['to_row'], column=matrix['from_col'])
            if not is_formula(direct_cell.value):
                direct_cell.value = new_rate
                direct_is_formula = False
                inverse_is_formula = is_formula(inverse_cell.value)
            elif not is_formula(inverse_cell.value):
                inverse_cell.value = 1.0 / new_rate
                direct_is_formula = True
                inverse_is_formula = False
            else:
                raise ValueError('Both candidate cells are formulas; no writable input cell found')
            wb.save(workbook_path)
        finally:
            wb.close()

        if direct_is_formula or inverse_is_formula:
            xlsx_dir = Path(tempfile.mkdtemp(prefix='embedded-xlsx-'))
            try:
                unpack_embedded_workbook(workbook_path, xlsx_dir)
                sheet_xml = resolve_sheet_xml(xlsx_dir, target_sheet_name)
                if direct_is_formula:
                    patch_cell_cache(sheet_xml, matrix['from_row'], matrix['to_col'], new_rate)
                if inverse_is_formula:
                    patch_cell_cache(sheet_xml, matrix['to_row'], matrix['from_col'], 1.0 / new_rate)
                pack_embedded_workbook(xlsx_dir, workbook_path)
            finally:
                shutil.rmtree(xlsx_dir, ignore_errors=True)

        pack_office(work_dir, Path(args.output))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
PYTHON_SCRIPT

python3 /tmp/update_embedded_matrix.py --input /root/input.pptx --output /root/results.pptx --config /tmp/oracle_config.json
