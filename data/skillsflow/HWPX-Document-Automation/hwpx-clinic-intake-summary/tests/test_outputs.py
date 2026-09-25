import json
import os
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "clinic_intake_ready.hwpx"
DATA_FILE = TASK_ROOT / "patient_intake.json"
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

def test_required_values_present_and_repeated_value_updated():
    section_xml = load_section(OUTPUT_FILE, "section0.xml")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    assert data["환자명"] in section_xml
    assert f'{data["생년월일"]} (35세)' in section_xml
    assert data["방문일"] in section_xml
    assert data["진료팀"] in section_xml
    assert "010-4421-7783" in section_xml
    assert data["증상요약"] in section_xml
    assert data["보험상태"] in section_xml
    assert section_xml.count(data["환자명"]) >= 2
    assert "확인 메모: 수기 서명 칸은 비워 두세요." in section_xml
    assert not re.search(r"\{\{[^}]+\}\}", section_xml)

def test_modified_paragraphs_do_not_keep_layout_cache():
    section_xml = load_section(OUTPUT_FILE, "section0.xml")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    fragments = [
        data["환자명"],
        f'{data["생년월일"]} (35세)',
        data["방문일"],
        data["진료팀"],
        "010-4421-7783",
        data["증상요약"],
        data["보험상태"],
    ]
    for paragraph, text in paragraph_texts(section_xml):
        if any(fragment in text for fragment in fragments):
            assert paragraph.find("hp:linesegarray", NS) is None
