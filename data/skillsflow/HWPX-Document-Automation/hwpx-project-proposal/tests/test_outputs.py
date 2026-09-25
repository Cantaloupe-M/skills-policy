import json
import os
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "project_proposal_ready.hwpx"
DATA_FILE = TASK_ROOT / "project_proposal.json"
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
    section0_xml = load_section(OUTPUT_FILE, "section0.xml")
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    combined = section0_xml + section1_xml
    for key, value in data.items():
        if key == "예산":
            normalized = value.replace(",", "")
            assert normalized in combined
            assert value not in combined
        elif key == "단계1":
            assert f"{value} (3개월)" in combined
        elif key == "단계2":
            assert f"{value} (3개월)" in combined
        elif key == "단계3":
            assert f"{value} (1개월)" in combined
        else:
            assert value in combined
    assert "비고: 내부 검토용" in section0_xml
    assert not re.search(r"\{\{[^}]+\}\}", combined)

def test_modified_paragraphs_do_not_keep_layout_cache():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    fragments = []
    for key, value in data.items():
        if key == "예산":
            fragments.append(value.replace(",", ""))
        elif key == "단계1":
            fragments.append(f"{value} (3개월)")
        elif key == "단계2":
            fragments.append(f"{value} (3개월)")
        elif key == "단계3":
            fragments.append(f"{value} (1개월)")
        else:
            fragments.append(value)
    for section_name in ("section0.xml", "section1.xml"):
        section_xml = load_section(OUTPUT_FILE, section_name)
        for paragraph, text in paragraph_texts(section_xml):
            if any(fragment in text for fragment in fragments):
                assert paragraph.find("hp:linesegarray", NS) is None
