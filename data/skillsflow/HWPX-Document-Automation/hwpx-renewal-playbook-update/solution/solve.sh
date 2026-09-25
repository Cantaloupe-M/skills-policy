#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_ROOT="${HWPX_RUNTIME_ROOT:-/root}"

mkdir -p "$RUNTIME_ROOT"
for name in renewal_playbook.hwpx renewal_update.json followups.csv; do
  if [ ! -f "$RUNTIME_ROOT/$name" ]; then
    cp "$TASK_DIR/environment/$name" "$RUNTIME_ROOT/$name"
  fi
done

python3 - <<'PY'
import csv
import json
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.hancom.co.kr/hwpml/2010/HWPML"
NSMAP = {"hp": NS}
ET.register_namespace("hp", NS)

root_dir = Path(os.environ.get("HWPX_RUNTIME_ROOT", "/root"))
input_path = root_dir / "renewal_playbook.hwpx"
update = json.loads((root_dir / "renewal_update.json").read_text(encoding="utf-8"))
with (root_dir / "followups.csv").open(encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    followups = [row["item"] for row in sorted(reader, key=lambda row: int(row["sequence"]))]
output_path = root_dir / "renewal_playbook_updated.hwpx"
new_window = f'{update["window_start"]} ~ {update["window_end"]}'

def paragraph_text(paragraph):
    return "".join((node.text or "") for node in paragraph.findall(".//hp:t", NSMAP))

def rewrite_paragraph(paragraph, new_text):
    runs = paragraph.findall("hp:run", NSMAP)
    if not runs:
        runs = [ET.SubElement(paragraph, f"{{{NS}}}run", {"charPrIDRef": "0"})]
    first_run = runs[0]
    text_node = first_run.find("hp:t", NSMAP)
    if text_node is None:
        text_node = ET.SubElement(first_run, f"{{{NS}}}t")
    text_node.text = new_text
    for extra_text in list(first_run):
        if extra_text.tag == f"{{{NS}}}t" and extra_text is not text_node:
            first_run.remove(extra_text)
    for extra_run in runs[1:]:
        paragraph.remove(extra_run)
    for lineseg in paragraph.findall("hp:linesegarray", NSMAP):
        paragraph.remove(lineseg)

def update_paragraphs(root):
    followup_index = 0
    for paragraph in root.findall(".//hp:p", NSMAP):
        text = paragraph_text(paragraph)
        new_text = text
        if text.startswith("고객사: "):
            new_text = f'고객사: {update["customer"]}'
        elif text.startswith("현 담당자: "):
            new_text = f'현 담당자: {update["owner_name"]}'
        elif text.startswith("갱신 윈도우: "):
            new_text = f'갱신 윈도우: {new_window}'
        elif text.startswith("갱신 윈도우 확인: "):
            new_text = f'갱신 윈도우 확인: {new_window}'
        elif text.startswith("가격 메모: "):
            new_text = f'가격 메모: {update["note"]}'
        elif re.match(r"^[123]\. ", text):
            new_text = f'{followup_index + 1}. {followups[followup_index]}'
            followup_index += 1
        if new_text != text:
            rewrite_paragraph(paragraph, new_text)

with zipfile.ZipFile(input_path) as src, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as dst:
    for info in src.infolist():
        data = src.read(info.filename)
        if info.filename.startswith("Contents/section") and info.filename.endswith(".xml"):
            root = ET.fromstring(data)
            update_paragraphs(root)
            for row in root.findall(".//hp:tr", NSMAP):
                cells = row.findall("hp:tc", NSMAP)
                if len(cells) != 2:
                    continue
                label_paragraph = cells[0].find(".//hp:p", NSMAP)
                value_paragraph = cells[1].find(".//hp:p", NSMAP)
                if label_paragraph is None or value_paragraph is None:
                    continue
                label = paragraph_text(label_paragraph)
                if label == "가격 밴드":
                    rewrite_paragraph(value_paragraph, update["band"])
                elif label == "에스컬레이션 연락처":
                    rewrite_paragraph(value_paragraph, update["escalation_email"])
            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        dst.writestr(info, data)
PY
