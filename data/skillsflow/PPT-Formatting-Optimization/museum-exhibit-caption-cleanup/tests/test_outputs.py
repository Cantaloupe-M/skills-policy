from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

CONFIG = {'input_file': 'Museum-Exhibit-Board.pptx', 'output_file': 'Museum-Exhibit-Board_cleaned.pptx', 'summary_mode': 'append', 'summary_title': 'Exhibit Index', 'summary_slide_number': 7, 'output_slide_count': 7, 'style': {'font': 'Arial', 'size': 1500, 'color': '6F6C64', 'bold': False, 'italic': False}, 'slides': [{'slide_number': 2, 'caption_raw': 'Bronze Ritual Vessel from Late Shang', 'caption_clean': 'Bronze Ritual Vessel from Late Shang'}, {'slide_number': 3, 'caption_raw': 'Gilt Reliquary with Lotus Pedestal', 'caption_clean': 'Gilt Reliquary with Lotus Pedestal'}, {'slide_number': 4, 'caption_raw': 'Bronze Ritual Vessel from Late Shang', 'caption_clean': 'Bronze Ritual Vessel from Late Shang'}, {'slide_number': 5, 'caption_raw': 'Painted Funeral Banner of Lady Dai', 'caption_clean': 'Painted Funeral Banner of Lady Dai'}, {'slide_number': 6, 'caption_raw': 'Celadon Ewer with Phoenix Spout', 'caption_clean': 'Celadon Ewer with Phoenix Spout'}]}
INPUT_PPTX = Path("/root") / CONFIG["input_file"]
OUTPUT_PPTX = Path("/root") / CONFIG["output_file"]

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def iter_slide_names(zipf: zipfile.ZipFile) -> list[str]:
    def key(name: str) -> int:
        match = re.search(r"slide(\d+)\.xml$", name)
        return int(match.group(1)) if match else 0

    return sorted(
        [name for name in zipf.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
        key=key,
    )


def load_slide(zipf: zipfile.ZipFile, slide_names: list[str], slide_number: int) -> ET.Element:
    return ET.fromstring(zipf.read(slide_names[slide_number - 1]))


def get_slide_dimensions(zipf: zipfile.ZipFile) -> tuple[int, int]:
    presentation = ET.fromstring(zipf.read("ppt/presentation.xml"))
    sld_sz = presentation.find(".//p:sldSz", NS)
    assert sld_sz is not None, "Missing slide size in presentation.xml"
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def paragraph_text(paragraph: ET.Element) -> str:
    return normalize_text("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)))


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_parent_shape(paragraph: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = paragraph
    while current in parent_map:
        current = parent_map[current]
        if current.tag.endswith("}sp"):
            return current
    return None


def find_paragraphs(slide: ET.Element, expected_text: str) -> list[ET.Element]:
    expected = normalize_text(expected_text)
    return [p for p in slide.findall(".//a:p", NS) if paragraph_text(p).strip() == expected.strip()]


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


def assert_caption_position(slide: ET.Element, paragraph: ET.Element, slide_width: int, slide_height: int) -> None:
    shape = find_parent_shape(paragraph, build_parent_map(slide))
    assert shape is not None, "Caption shape is missing"
    xfrm = shape.find("p:spPr/a:xfrm", NS)
    assert xfrm is not None, "Caption transform is missing"
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    assert off is not None and ext is not None, "Caption shape offset/extent is missing"
    shape_x = int(off.get("x"))
    shape_y = int(off.get("y"))
    shape_w = int(ext.get("cx"))
    shape_h = int(ext.get("cy"))
    assert shape_w >= int(slide_width * 0.9), "Caption box should be widened for a single-line label"
    bottom_band = int(slide_height * 0.2)
    min_y = slide_height - shape_h - bottom_band
    max_y = slide_height - int(shape_h * 0.7)
    assert min_y <= shape_y <= max_y, "Caption box should be near the bottom of the slide"
    left_gap = shape_x
    right_gap = slide_width - (shape_x + shape_w)
    assert abs(left_gap - right_gap) <= int(slide_width * 0.1), "Caption box should be horizontally centered"
    ppr = paragraph.find("a:pPr", NS)
    assert ppr is not None and ppr.get("algn") == "ctr", "Caption paragraph should be centered"
    body_pr = shape.find("p:txBody/a:bodyPr", NS)
    assert body_pr is not None, "Caption body properties are missing"
    l_ins = int(body_pr.get("lIns") or 0)
    r_ins = int(body_pr.get("rIns") or 0)
    assert abs(l_ins - r_ins) <= max(1, int(shape_w * 0.1)), "Caption should be centered within its box"
    assert "\n" not in paragraph_text(paragraph), "Caption should stay on a single line"


def expected_unique_captions() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for slide_cfg in CONFIG["slides"]:
        caption = normalize_text(slide_cfg["caption_clean"])
        if caption not in seen:
            seen.add(caption)
            ordered.append(caption)
    return ordered


def test_output_exists() -> None:
    assert OUTPUT_PPTX.exists(), "The cleaned PPTX was not created"
    assert OUTPUT_PPTX.stat().st_size > 0, "The cleaned PPTX is empty"


def test_slide_count_matches_requirement() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        assert len(iter_slide_names(zipf)) == CONFIG["output_slide_count"], "Unexpected number of slides in output"


def test_cleaned_captions_exist_and_match_expected_text() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_cfg in CONFIG["slides"]:
            slide = load_slide(zipf, slide_names, slide_cfg["slide_number"])
            matches = find_paragraphs(slide, slide_cfg["caption_clean"])
            assert len(matches) == 1, f"Slide {slide_cfg['slide_number']} should contain exactly one cleaned caption"
            runs = matches[0].findall("a:r", NS)
            assert runs, f"Slide {slide_cfg['slide_number']} cleaned caption should contain text runs"
            for run in runs:
                assert_run_style(run)


def test_cleaned_captions_are_repositioned() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        slide_width, slide_height = get_slide_dimensions(zipf)
        for slide_cfg in CONFIG["slides"]:
            slide = load_slide(zipf, slide_names, slide_cfg["slide_number"])
            paragraph = find_paragraphs(slide, slide_cfg["caption_clean"])[0]
            assert_caption_position(slide, paragraph, slide_width, slide_height)


def test_non_caption_text_stays_unchanged() -> None:
    raw_captions = {normalize_text(slide["caption_raw"]) for slide in CONFIG["slides"]}
    clean_captions = {normalize_text(slide["caption_clean"]) for slide in CONFIG["slides"]}
    with zipfile.ZipFile(INPUT_PPTX, "r") as zipf_in, zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf_out:
        slide_names_in = iter_slide_names(zipf_in)
        slide_names_out = iter_slide_names(zipf_out)
        for slide_cfg in CONFIG["slides"]:
            slide_no = slide_cfg["slide_number"]
            slide_in = load_slide(zipf_in, slide_names_in, slide_no)
            slide_out = load_slide(zipf_out, slide_names_out, slide_no)
            texts_in = collect_texts_except(slide_in, raw_captions)
            texts_out = collect_texts_except(slide_out, clean_captions)
            assert texts_in == texts_out, f"Slide {slide_no} non-caption text changed"


def test_existing_notes_survive_when_present() -> None:
    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        for slide_cfg in CONFIG["slides"]:
            note = slide_cfg.get("note")
            if not note:
                continue
            slide = load_slide(zipf, slide_names, slide_cfg["slide_number"])
            assert find_paragraphs(slide, note), f"Slide {slide_cfg['slide_number']} note text should remain unchanged"


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
    alias_file = CONFIG.get("alias_map_file")
    if not alias_file:
        return
    alias_rows: list[tuple[str, str]] = []
    with (Path("/root") / alias_file).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            alias_rows.append((normalize_text(row["raw"]), normalize_text(row["canonical"])))

    with zipfile.ZipFile(OUTPUT_PPTX, "r") as zipf:
        slide_names = iter_slide_names(zipf)
        slide_texts: list[str] = []
        for slide_cfg in CONFIG["slides"]:
            slide = load_slide(zipf, slide_names, slide_cfg["slide_number"])
            slide_texts.extend(paragraph_text(p) for p in slide.findall(".//a:p", NS) if paragraph_text(p))
        summary = load_slide(zipf, slide_names, CONFIG["summary_slide_number"])
        slide_texts.extend(paragraph_text(p) for p in summary.findall(".//a:p", NS) if paragraph_text(p))

    for slide_cfg in CONFIG["slides"]:
        assert normalize_text(slide_cfg["caption_clean"]) in slide_texts, "Canonical caption should appear in the output"
    for raw, canonical in alias_rows:
        if raw != canonical:
            assert raw not in slide_texts, f"Raw alias '{raw}' should be replaced by its canonical wording"
