from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

CONFIG = json.loads(Path(__file__).with_name("task_config.json").read_text(encoding="utf-8"))
INPUT_PPTX = Path("/root") / CONFIG["input_file"]
OUTPUT_PPTX = Path("/root") / CONFIG["output_file"]

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def slide_number(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        (n for n in zipf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")),
        key=slide_number,
    )


def load_slide(zipf: zipfile.ZipFile, slide_names: list[str], slide_index: int) -> ET.Element:
    return ET.fromstring(zipf.read(slide_names[slide_index - 1]))


def get_slide_dimensions(zipf: zipfile.ZipFile) -> tuple[int, int]:
    root = ET.fromstring(zipf.read("ppt/presentation.xml"))
    sld_sz = root.find(".//p:sldSz", NS)
    assert sld_sz is not None, "Missing slide size in presentation.xml"
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def paragraph_text(paragraph: ET.Element) -> str:
    return normalize_text("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)))


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_parent_shape(element: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = element
    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("}sp"):
            return current
    return None


def find_parent_group(element: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = element
    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("}grpSp"):
            return current
    return None


def find_paragraphs(slide: ET.Element, expected_text: str) -> list[ET.Element]:
    expected = normalize_text(expected_text)
    return [paragraph for paragraph in slide.findall(".//a:p", NS) if paragraph_text(paragraph).strip() == expected.strip()]


def collect_texts_except(slide: ET.Element, excluded: set[str]) -> list[str]:
    texts: list[str] = []
    for paragraph in slide.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if not text or text in excluded:
            continue
        texts.append(text)
    return texts


def assert_run_style(run: ET.Element) -> None:
    style = CONFIG["style"]
    rpr = run.find("a:rPr", NS)
    assert rpr is not None, "Caption run is missing run properties"
    _sz_val = int(rpr.get("sz") or 0)
    assert abs(_sz_val - int(style["size"])) <= 100, f"Caption font size mismatch: got {_sz_val}, expected {style['size']}"
    expected_bold = "1" if style.get("bold") else "0"
    assert rpr.get("b") in (None, expected_bold), "Caption bold setting is incorrect"
    expected_italic = "1" if style.get("italic") else "0"
    assert rpr.get("i") in (None, expected_italic), "Caption italic setting is incorrect"
    solid = rpr.find("a:solidFill/a:srgbClr", NS)
    _act_clr = solid.get("val", "") if solid is not None else ""
    assert _act_clr.upper().lstrip('00') == style["color"].upper().lstrip('00') or abs(int(_act_clr, 16) - int(style["color"], 16)) <= 5, f"Caption color mismatch: got {_act_clr}, expected {style['color']}"
    latin = rpr.find("a:latin", NS)
    assert latin is not None and latin.get("typeface") == style["font"], "Caption font face is incorrect"
    ea = rpr.find("a:ea", NS)
    if ea is not None:
        assert ea.get("typeface") == style["font"], "Caption EA font face is incorrect"
    cs = rpr.find("a:cs", NS)
    if cs is not None:
        assert cs.get("typeface") == style["font"], "Caption CS font face is incorrect"


def assert_caption_position(slide: ET.Element, paragraph: ET.Element, slide_cfg: dict[str, object], slide_width: int, slide_height: int) -> None:
    parent_map = build_parent_map(slide)
    shape = find_parent_shape(paragraph, parent_map)
    assert shape is not None, "Caption shape is missing"

    if slide_cfg.get("container_mode") == "group":
        container = find_parent_group(shape, parent_map)
        assert container is not None, "Caption group container is missing"
        xfrm = container.find("p:grpSpPr/a:xfrm", NS)
    else:
        xfrm = shape.find("p:spPr/a:xfrm", NS)
    assert xfrm is not None, "Caption transform is missing"

    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    assert off is not None and ext is not None, "Caption offset/extent is missing"
    container_x = int(off.get("x"))
    container_y = int(off.get("y"))
    container_w = int(ext.get("cx"))
    container_h = int(ext.get("cy"))
    assert container_w >= int(slide_width * 0.9), "Caption container should be widened for a single-line label"
    bottom_band = int(slide_height * 0.2)
    min_y = slide_height - container_h - bottom_band
    max_y = slide_height - int(container_h * 0.7)
    assert min_y <= container_y <= max_y, "Caption container should be near the bottom of the slide"
    left_gap = container_x
    right_gap = slide_width - (container_x + container_w)
    assert abs(left_gap - right_gap) <= int(slide_width * 0.1), "Caption container should be horizontally centered"

    ppr = paragraph.find("a:pPr", NS)
    assert ppr is not None and ppr.get("algn") == "ctr", "Caption paragraph should be centered"
    body_pr = shape.find("p:txBody/a:bodyPr", NS)
    assert body_pr is not None, "Caption body properties are missing"
    l_ins = int(body_pr.get("lIns") or 0)
    r_ins = int(body_pr.get("rIns") or 0)
    assert abs(l_ins - r_ins) <= max(1, int(container_w * 0.1)), "Caption should be centered within its box"
    assert "\n" not in paragraph_text(paragraph), "Caption should stay on a single line"


def expected_unique_captions() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for slide_cfg in CONFIG["slides"]:
        caption = normalize_text(str(slide_cfg["caption_clean"]))
        if caption not in seen:
            seen.add(caption)
            ordered.append(caption)
    return ordered


def load_alias_pairs() -> dict[str, str]:
    alias_file = CONFIG.get("alias_map_file")
    if not alias_file:
        return {}

    field_cfg = CONFIG.get("alias_fields", {})
    raw_field = str(field_cfg.get("raw", "raw"))
    canonical_field = str(field_cfg.get("canonical", "canonical"))
    status_field = field_cfg.get("status")
    ignore_values = {normalize_text(str(value)).lower() for value in CONFIG.get("alias_ignore_status_values", [])}

    mapping: dict[str, str] = {}
    with (Path("/root") / str(alias_file)).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                continue
            raw = normalize_text(row.get(raw_field, ""))
            canonical = normalize_text(row.get(canonical_field, ""))
            status = normalize_text(row.get(str(status_field), "")).lower() if status_field else ""
            if status_field and status in ignore_values:
                continue
            if not raw or not canonical:
                continue
            mapping.setdefault(raw, canonical)
    return mapping


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "The cleaned PPTX was not created"
    assert OUTPUT_PPTX.stat().st_size > 0, "The cleaned PPTX is empty"


def test_slide_count_matches_requirement() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        assert len(iter_slide_names(zipf)) == CONFIG["output_slide_count"], "Unexpected number of slides in output"


def test_cleaned_captions_exist_and_match_expected_text() -> None:
    alias_pairs = load_alias_pairs()
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_cfg in CONFIG["slides"]:
            expected = normalize_text(alias_pairs.get(normalize_text(str(slide_cfg["caption_raw"])), str(slide_cfg["caption_clean"])))
            slide = load_slide(zipf, slide_names, int(slide_cfg["slide_number"]))
            matches = find_paragraphs(slide, expected)
            assert len(matches) == 1, f"Slide {slide_cfg['slide_number']} should contain exactly one cleaned caption"
            runs = matches[0].findall("a:r", NS)
            assert runs, f"Slide {slide_cfg['slide_number']} cleaned caption should contain text runs"
            for run in runs:
                assert_run_style(run)


def test_cleaned_captions_are_repositioned() -> None:
    alias_pairs = load_alias_pairs()
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        slide_width, slide_height = get_slide_dimensions(zipf)
        for slide_cfg in CONFIG["slides"]:
            expected = normalize_text(alias_pairs.get(normalize_text(str(slide_cfg["caption_raw"])), str(slide_cfg["caption_clean"])))
            slide = load_slide(zipf, slide_names, int(slide_cfg["slide_number"]))
            paragraph = find_paragraphs(slide, expected)[0]
            assert_caption_position(slide, paragraph, slide_cfg, slide_width, slide_height)


def test_non_caption_text_stays_unchanged() -> None:
    raw_captions = {normalize_text(str(slide["caption_raw"])) for slide in CONFIG["slides"]}
    clean_captions = {normalize_text(str(slide["caption_clean"])) for slide in CONFIG["slides"]}
    with zipfile.ZipFile(INPUT_PPTX, "r") as zipf_in, zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf_out:
        slide_names_in = iter_slide_names(zipf_in)
        slide_names_out = iter_slide_names(zipf_out)
        for slide_cfg in CONFIG["slides"]:
            slide_no = int(slide_cfg["slide_number"])
            slide_in = load_slide(zipf_in, slide_names_in, slide_no)
            slide_out = load_slide(zipf_out, slide_names_out, slide_no)
            texts_in = collect_texts_except(slide_in, raw_captions)
            texts_out = collect_texts_except(slide_out, clean_captions)
            assert texts_in == texts_out, f"Slide {slide_no} non-caption text changed"


def test_preserved_texts_survive_when_present() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_cfg in CONFIG["slides"]:
            preserve_texts = [normalize_text(text) for text in slide_cfg.get("preserve_texts", [])]
            if not preserve_texts:
                continue
            slide = load_slide(zipf, slide_names, int(slide_cfg["slide_number"]))
            for text in preserve_texts:
                assert find_paragraphs(slide, text), f"Slide {slide_cfg['slide_number']} should preserve '{text}'"


def test_final_summary_slide_title_and_bullets() -> None:
    expected = expected_unique_captions()
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        assert len(slide_names) >= CONFIG["summary_slide_number"], "Summary slide number exceeds slide count"
        summary = load_slide(zipf, slide_names, CONFIG["summary_slide_number"])
    assert find_paragraphs(summary, CONFIG["summary_title"]), "Final summary slide title is incorrect"
    bullet_titles: list[str] = []
    for paragraph in summary.findall(".//a:p", NS):
        text = paragraph_text(paragraph)
        if not text or text == CONFIG["summary_title"]:
            continue
        bullet_titles.append(text)
        ppr = paragraph.find("a:pPr", NS)
        assert ppr is not None, "Summary bullet paragraph is missing paragraph properties"
        assert ppr.find("a:buAutoNum", NS) is not None, "Summary bullet paragraph must use auto-numbered bullets"
    assert set(b.strip() for b in bullet_titles) == set(b.strip() for b in expected), f"Summary bullets must contain: {expected}"
    assert len(bullet_titles) == len(set(bullet_titles)), "Summary slide should not contain duplicate captions"


def test_append_or_replace_behavior() -> None:
    with zipfile.ZipFile(INPUT_PPTX, "r") as zipf_in, zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf_out:
        count_in = len(iter_slide_names(zipf_in))
        count_out = len(iter_slide_names(zipf_out))
    if CONFIG["summary_mode"] == "append":
        assert count_out == count_in + 1, "Output should add exactly one final summary slide"
    else:
        assert count_out == count_in, "Output should refresh the existing final slide instead of adding one"


def test_standardized_aliases_used_when_mapping_exists() -> None:
    alias_pairs = load_alias_pairs()
    if not alias_pairs:
        return
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        slide_texts: list[str] = []
        for slide_cfg in CONFIG["slides"]:
            slide = load_slide(zipf, slide_names, int(slide_cfg["slide_number"]))
            slide_texts.extend(paragraph_text(paragraph) for paragraph in slide.findall(".//a:p", NS) if paragraph_text(paragraph))
        summary = load_slide(zipf, slide_names, CONFIG["summary_slide_number"])
        slide_texts.extend(paragraph_text(paragraph) for paragraph in summary.findall(".//a:p", NS) if paragraph_text(paragraph))
    for canonical in alias_pairs.values():
        assert normalize_text(canonical) in slide_texts, "Canonical caption should appear in the output"
    for raw, canonical in alias_pairs.items():
        if raw != canonical:
            assert raw not in slide_texts, f"Raw alias '{raw}' should be replaced by its canonical wording"
