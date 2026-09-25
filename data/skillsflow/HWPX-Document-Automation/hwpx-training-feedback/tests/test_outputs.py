import json
import os
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "training_feedback_ready.hwpx"
DATA_FILE = TASK_ROOT / "training_feedback.json"
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
    transformed = {
        **data,
        "참석자수": "32",
        "만족도": "4.5점 (5.0점 만점)",
        "종합의견": data["종합의견"] + " 후속 심화반 검토 요망.",
    }
    for key, value in transformed.items():
        assert value in combined
    assert "32명" not in combined
    assert "4.5/5.0" not in combined
    assert "비고: 익명 수집됨" in section0_xml
    assert not re.search(r"\{\{[^}]+\}\}", combined)

def test_modified_paragraphs_do_not_keep_layout_cache():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    fragments = [
        data["교육명"],
        data["교육일시"],
        data["장소"],
        data["강사"],
        "32",
        "4.5점 (5.0점 만점)",
        data["유익내용"],
        data["개선사항"],
        data["희망교육"],
        data["강사평가"],
        data["자료평가"],
        data["실습평가"],
        data["종합의견"] + " 후속 심화반 검토 요망.",
    ]
    for section_name in ("section0.xml", "section1.xml"):
        section_xml = load_section(OUTPUT_FILE, section_name)
        for paragraph, text in paragraph_texts(section_xml):
            if any(fragment in text for fragment in fragments):
                assert paragraph.find("hp:linesegarray", NS) is None
