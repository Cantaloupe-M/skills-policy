import json
import os
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "inventory_report_ready.hwpx"
DATA_FILE = TASK_ROOT / "inventory_data.json"
NS = {"hp": "http://www.hancom.co.kr/hwpml/2010/HWPML"}

def load_section(hwpx_path: Path, section_name: str) -> str:
    with zipfile.ZipFile(hwpx_path) as zf:
        return zf.read(f"Contents/{section_name}").decode("utf-8")

def paragraph_texts(section_xml: str):
    root = ET.fromstring(section_xml)
    for paragraph in root.findall(".//hp:p", NS):
        yield paragraph, "".join((node.text or "") for node in paragraph.findall(".//hp:t", NS))

def test_output_exists_and_is_zip():
    assert OUTPUT_FILE.exists()
    assert zipfile.is_zipfile(OUTPUT_FILE)

def test_required_values_present_and_placeholders_removed():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    section_xml = load_section(OUTPUT_FILE, "section0.xml")
    for value in data.values():
        assert value in section_xml
    assert "비고: 월간 정기 보고" in section_xml
    assert not re.search(r"\{\{[^}]+\}\}", section_xml)

def test_modified_paragraphs_do_not_keep_layout_cache():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    fragments = list(data.values())
    section_xml = load_section(OUTPUT_FILE, "section0.xml")
    for paragraph, text in paragraph_texts(section_xml):
        if any(fragment in text for fragment in fragments):
            assert paragraph.find("hp:linesegarray", NS) is None
