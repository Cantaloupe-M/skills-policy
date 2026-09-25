import json
import os
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "safety_audit_brief_final.hwpx"
OVERVIEW_FILE = TASK_ROOT / "audit_overview.json"
ACTIONS_FILE = TASK_ROOT / "corrective_actions.json"
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

def test_overview_values_and_actions_are_present():
    section0_xml = load_section(OUTPUT_FILE, "section0.xml")
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    combined = section0_xml + section1_xml
    overview = json.loads(OVERVIEW_FILE.read_text(encoding="utf-8"))["summary"]
    actions = json.loads(ACTIONS_FILE.read_text(encoding="utf-8"))["immediate_actions"]
    severity_map = {"High": "즉시조치", "Medium": "계획보완", "Low": "모니터링"}
    for key, value in overview.items():
        if key == "점검일":
            assert value.replace("-", ".") in combined
        elif key == "위험등급":
            assert f'{value} ({severity_map[value]})' in combined
        else:
            assert value in combined
    for action in actions:
        assert action in section1_xml
    assert "현장명" in section0_xml
    assert "위험 등급" in section0_xml
    assert not re.search(r"\{\{[^}]+\}\}", combined)

def test_actions_keep_source_order():
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    actions = json.loads(ACTIONS_FILE.read_text(encoding="utf-8"))["immediate_actions"]
    indexes = [section1_xml.index(action) for action in actions]
    assert indexes == sorted(indexes)

def test_modified_paragraphs_do_not_keep_layout_cache():
    section0_xml = load_section(OUTPUT_FILE, "section0.xml")
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    overview = json.loads(OVERVIEW_FILE.read_text(encoding="utf-8"))["summary"]
    actions = json.loads(ACTIONS_FILE.read_text(encoding="utf-8"))["immediate_actions"]
    severity_map = {"High": "즉시조치", "Medium": "계획보완", "Low": "모니터링"}
    fragments = []
    for key, value in overview.items():
        if key == "점검일":
            fragments.append(value.replace("-", "."))
        elif key == "위험등급":
            fragments.append(f'{value} ({severity_map[value]})')
        else:
            fragments.append(value)
    fragments.extend(actions)
    for section_xml in (section0_xml, section1_xml):
        for paragraph, text in paragraph_texts(section_xml):
            if any(fragment in text for fragment in fragments):
                assert paragraph.find("hp:linesegarray", NS) is None
