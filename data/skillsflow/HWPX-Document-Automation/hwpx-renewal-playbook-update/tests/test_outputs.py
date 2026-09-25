import csv
import json
import os
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

TASK_ROOT = Path(os.environ.get("HWPX_TASK_ROOT", "/root"))
OUTPUT_FILE = TASK_ROOT / "renewal_playbook_updated.hwpx"
UPDATE_FILE = TASK_ROOT / "renewal_update.json"
FOLLOWUPS_FILE = TASK_ROOT / "followups.csv"
NS = {"hp": "http://www.hancom.co.kr/hwpml/2010/HWPML"}

def load_section(hwpx_path: Path, section_name: str) -> str:
    with zipfile.ZipFile(hwpx_path) as zf:
        return zf.read(f"Contents/{section_name}").decode("utf-8")

def paragraph_texts(section_xml: str):
    root = ET.fromstring(section_xml)
    for paragraph in root.findall(".//hp:p", NS):
        yield paragraph, "".join((node.text or "") for node in paragraph.findall(".//hp:t", NS))

def followup_items():
    with FOLLOWUPS_FILE.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = sorted(reader, key=lambda row: int(row["sequence"]))
    return [row["item"] for row in rows]

def test_output_exists_and_is_zip():
    assert OUTPUT_FILE.exists()
    assert zipfile.is_zipfile(OUTPUT_FILE)

def test_required_updates_present_and_old_values_removed():
    update = json.loads(UPDATE_FILE.read_text(encoding="utf-8"))
    section0_xml = load_section(OUTPUT_FILE, "section0.xml")
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    new_window = f'{update["window_start"]} ~ {update["window_end"]}'
    required = [
        update["customer"],
        update["owner_name"],
        new_window,
        update["band"],
        update["escalation_email"],
        update["note"],
        *followup_items(),
    ]
    for value in required:
        assert value in section0_xml or value in section1_xml
    for old_value in [
        "Northwind Retail",
        "이전담당자",
        "2025-04-01 ~ 2025-04-15",
        "Standard-18M",
        "ops-old@northwind.example",
        "기존 메모를 새 메모로 바꾸세요.",
        "old follow-up alpha",
        "old follow-up beta",
        "old follow-up gamma",
    ]:
        assert old_value not in section0_xml + section1_xml

def test_followups_keep_csv_order_and_appendix_is_preserved():
    section1_xml = load_section(OUTPUT_FILE, "section1.xml")
    items = followup_items()
    indexes = [section1_xml.index(item) for item in items]
    assert indexes == sorted(indexes)
    assert "이 부록 문단은 그대로 유지해야 합니다." in section1_xml

def test_modified_paragraphs_do_not_keep_layout_cache():
    update = json.loads(UPDATE_FILE.read_text(encoding="utf-8"))
    new_window = f'{update["window_start"]} ~ {update["window_end"]}'
    fragments = [
        update["customer"],
        update["owner_name"],
        new_window,
        update["band"],
        update["escalation_email"],
        update["note"],
        *followup_items(),
    ]
    for section_name in ("section0.xml", "section1.xml"):
        section_xml = load_section(OUTPUT_FILE, section_name)
        for paragraph, text in paragraph_texts(section_xml):
            if any(fragment in text for fragment in fragments):
                assert paragraph.find("hp:linesegarray", NS) is None
