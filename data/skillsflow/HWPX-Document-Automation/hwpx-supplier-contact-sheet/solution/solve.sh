#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TASK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_ROOT="${HWPX_RUNTIME_ROOT:-/root}"

mkdir -p "$RUNTIME_ROOT"
for name in supplier_contact_template.hwpx supplier_contact.json; do
  if [ ! -f "$RUNTIME_ROOT/$name" ]; then
    cp "$TASK_DIR/environment/$name" "$RUNTIME_ROOT/$name"
  fi
done

python3 - <<'PY'
import json
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.hancom.co.kr/hwpml/2010/HWPML"
NSMAP = {"hp": NS}
ET.register_namespace("hp", NS)

root_dir = Path(os.environ.get("HWPX_RUNTIME_ROOT", "/root"))
input_path = root_dir / "supplier_contact_template.hwpx"
data_path = root_dir / "supplier_contact.json"
output_path = root_dir / "supplier_contact_ready.hwpx"
mapping = json.loads(data_path.read_text(encoding="utf-8"))

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

with zipfile.ZipFile(input_path) as src, zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as dst:
    for info in src.infolist():
        data = src.read(info.filename)
        if info.filename == "Contents/section0.xml":
            root = ET.fromstring(data)
            for paragraph in root.findall(".//hp:p", NSMAP):
                original = paragraph_text(paragraph)
                updated = original
                for key, value in mapping.items():
                    updated = updated.replace(f"{{{{{key}}}}}", value)
                if updated != original:
                    rewrite_paragraph(paragraph, updated)
            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        dst.writestr(info, data)
PY
