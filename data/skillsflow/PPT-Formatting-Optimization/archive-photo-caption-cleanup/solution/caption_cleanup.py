from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

ET.register_namespace("a", NS["a"])
ET.register_namespace("p", NS["p"])
ET.register_namespace("r", NS["r"])
ET.register_namespace("", NS["rel"])


def qn(prefix: str, tag: str) -> str:
    return f"{{{NS[prefix]}}}{tag}"


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def get_slide_dimensions(unpack_dir: Path) -> tuple[int, int]:
    root = ET.parse(unpack_dir / "ppt" / "presentation.xml").getroot()
    sld_sz = root.find(".//p:sldSz", NS)
    if sld_sz is None:
        raise RuntimeError("Missing slide size in presentation.xml")
    return int(sld_sz.get("cx")), int(sld_sz.get("cy"))


def build_parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def find_parent_shape(element: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = element
    while current in parent_map:
        current = parent_map[current]
        if current.tag == qn("p", "sp"):
            return current
    return None


def find_parent_group(element: ET.Element, parent_map: dict[ET.Element, ET.Element]) -> ET.Element | None:
    current = element
    while current in parent_map:
        current = parent_map[current]
        if current.tag == qn("p", "grpSp"):
            return current
    return None


def ensure_child(parent: ET.Element, prefix: str, tag: str) -> ET.Element:
    child = parent.find(f"{prefix}:{tag}", NS)
    if child is None:
        child = ET.SubElement(parent, qn(prefix, tag))
    return child


def style_run_properties(rpr: ET.Element, style: dict[str, object]) -> None:
    rpr.set("sz", str(style["size"]))
    rpr.set("b", "1" if style.get("bold") else "0")
    rpr.set("i", "1" if style.get("italic") else "0")
    rpr.set("dirty", "0")

    solid_fill = rpr.find("a:solidFill", NS)
    if solid_fill is None:
        solid_fill = ET.Element(qn("a", "solidFill"))
        rpr.insert(0, solid_fill)
    for child in list(solid_fill):
        solid_fill.remove(child)
    ET.SubElement(solid_fill, qn("a", "srgbClr"), {"val": str(style["color"])})

    for tag in ("latin", "ea", "cs"):
        font_node = rpr.find(f"a:{tag}", NS)
        if font_node is None:
            font_node = ET.SubElement(rpr, qn("a", tag))
        font_node.set("typeface", str(style["font"]))


def rewrite_caption_paragraph(paragraph: ET.Element, clean_text: str, style: dict[str, object]) -> None:
    for child in list(paragraph):
        paragraph.remove(child)
    ppr = ET.SubElement(paragraph, qn("a", "pPr"))
    ppr.set("algn", "ctr")
    run = ET.SubElement(paragraph, qn("a", "r"))
    rpr = ET.SubElement(run, qn("a", "rPr"), {"lang": "en-US", "altLang": "zh-CN"})
    style_run_properties(rpr, style)
    ET.SubElement(run, qn("a", "t")).text = clean_text
    end_rpr = ET.SubElement(paragraph, qn("a", "endParaRPr"), {"lang": "en-US"})
    style_run_properties(end_rpr, style)


def adjust_text_body(shape: ET.Element) -> None:
    tx_body = shape.find("p:txBody", NS)
    if tx_body is None:
        tx_body = ET.SubElement(shape, qn("p", "txBody"))
        ET.SubElement(tx_body, qn("a", "bodyPr"))
        ET.SubElement(tx_body, qn("a", "lstStyle"))
    body_pr = tx_body.find("a:bodyPr", NS)
    if body_pr is None:
        body_pr = ET.Element(qn("a", "bodyPr"))
        tx_body.insert(0, body_pr)
    body_pr.set("lIns", "0")
    body_pr.set("rIns", "0")
    body_pr.set("anchor", "ctr")
    body_pr.set("wrap", "none")


def adjust_shape_position(shape: ET.Element, slide_width: int, slide_height: int, style: dict[str, object]) -> None:
    sp_pr = ensure_child(shape, "p", "spPr")
    xfrm = sp_pr.find("a:xfrm", NS)
    if xfrm is None:
        xfrm = ET.Element(qn("a", "xfrm"))
        sp_pr.insert(0, xfrm)
    off = xfrm.find("a:off", NS)
    if off is None:
        off = ET.SubElement(xfrm, qn("a", "off"))
    ext = xfrm.find("a:ext", NS)
    if ext is None:
        ext = ET.SubElement(xfrm, qn("a", "ext"))

    font_height = int(style["size"]) * 127
    shape_height = int(font_height * 1.35)
    bottom_margin = int(slide_height * 0.02)

    off.set("x", "0")
    off.set("y", str(slide_height - shape_height - bottom_margin))
    ext.set("cx", str(slide_width))
    ext.set("cy", str(shape_height))
    adjust_text_body(shape)


def adjust_group_position(group: ET.Element, caption_shape: ET.Element, slide_width: int, slide_height: int, style: dict[str, object]) -> None:
    group_pr = group.find("p:grpSpPr", NS)
    if group_pr is None:
        group_pr = ET.SubElement(group, qn("p", "grpSpPr"))
    xfrm = group_pr.find("a:xfrm", NS)
    if xfrm is None:
        xfrm = ET.SubElement(group_pr, qn("a", "xfrm"))
    off = ensure_child(xfrm, "a", "off")
    ext = ensure_child(xfrm, "a", "ext")
    ch_off = ensure_child(xfrm, "a", "chOff")
    ch_ext = ensure_child(xfrm, "a", "chExt")

    font_height = int(style["size"]) * 127
    badge_height = int(font_height * 1.0)
    gap = int(font_height * 0.35)
    shape_height = int(font_height * 1.35)
    group_height = badge_height + gap + shape_height
    bottom_margin = int(slide_height * 0.02)

    off.set("x", "0")
    off.set("y", str(slide_height - group_height - bottom_margin))
    ext.set("cx", str(slide_width))
    ext.set("cy", str(group_height))
    ch_off.set("x", "0")
    ch_off.set("y", "0")
    ch_ext.set("cx", str(slide_width))
    ch_ext.set("cy", str(group_height))

    sp_pr = ensure_child(caption_shape, "p", "spPr")
    shape_xfrm = sp_pr.find("a:xfrm", NS)
    if shape_xfrm is None:
        shape_xfrm = ET.Element(qn("a", "xfrm"))
        sp_pr.insert(0, shape_xfrm)
    shape_off = ensure_child(shape_xfrm, "a", "off")
    shape_ext = ensure_child(shape_xfrm, "a", "ext")
    shape_off.set("x", "0")
    shape_off.set("y", str(group_height - shape_height))
    shape_ext.set("cx", str(slide_width))
    shape_ext.set("cy", str(shape_height))
    adjust_text_body(caption_shape)


def paragraph_text(paragraph: ET.Element) -> str:
    return normalize_text("".join(node.text or "" for node in paragraph.findall(".//a:t", NS)))


def find_caption_paragraph(root: ET.Element, raw_caption: str) -> ET.Element:
    target = normalize_text(raw_caption)
    for paragraph in root.findall(".//a:p", NS):
        if paragraph_text(paragraph) == target:
            return paragraph
    raise RuntimeError(f"Caption '{raw_caption}' not found")


def load_alias_map(config: dict[str, object]) -> dict[str, str]:
    alias_file = config.get("alias_map_file")
    if not alias_file:
        return {}

    field_cfg = config.get("alias_fields", {})
    raw_field = str(field_cfg.get("raw", "raw"))
    canonical_field = str(field_cfg.get("canonical", "canonical"))
    status_field = field_cfg.get("status")
    ignore_values = {normalize_text(str(value)).lower() for value in config.get("alias_ignore_status_values", [])}

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


def resolve_clean_text(slide_cfg: dict[str, object], alias_map: dict[str, str]) -> str:
    raw = normalize_text(str(slide_cfg["caption_raw"]))
    return normalize_text(alias_map.get(raw, str(slide_cfg["caption_clean"])))


def ordered_clean_captions(config: dict[str, object], alias_map: dict[str, str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for slide_cfg in config["slides"]:
        clean = resolve_clean_text(slide_cfg, alias_map)
        if clean not in seen:
            seen.add(clean)
            ordered.append(clean)
    return ordered


def render_summary_slide_xml(title: str, bullets: list[str]) -> str:
    bullet_chunks: list[str] = []
    for text in bullets:
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        bullet_chunks.append(
            f"""          <a:p>
            <a:pPr lvl=\"0\">
              <a:buAutoNum type=\"arabicPeriod\"/>
            </a:pPr>
            <a:r>
              <a:rPr sz=\"1800\" dirty=\"0\">
                <a:solidFill>
                  <a:srgbClr val=\"000000\"/>
                </a:solidFill>
                <a:latin typeface=\"Arial\"/>
                <a:ea typeface=\"Arial\"/>
                <a:cs typeface=\"Arial\"/>
              </a:rPr>
              <a:t>{escaped}</a:t>
            </a:r>
          </a:p>"""
        )
    bullets_block = "\n".join(bullet_chunks)
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id=\"1\" name=\"\"/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x=\"0\" y=\"0\"/>
          <a:ext cx=\"0\" cy=\"0\"/>
          <a:chOff x=\"0\" y=\"0\"/>
          <a:chExt cx=\"0\" cy=\"0\"/>
        </a:xfrm>
      </p:grpSpPr>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id=\"2\" name=\"Title\"/>
          <p:cNvSpPr>
            <a:spLocks noGrp=\"1\"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph type=\"title\"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x=\"457200\" y=\"274638\"/>
            <a:ext cx=\"8229600\" cy=\"1143000\"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
          <a:p>
            <a:r>
              <a:rPr sz=\"3200\" b=\"1\" dirty=\"0\">
                <a:solidFill>
                  <a:srgbClr val=\"000000\"/>
                </a:solidFill>
                <a:latin typeface=\"Arial\"/>
                <a:ea typeface=\"Arial\"/>
                <a:cs typeface=\"Arial\"/>
              </a:rPr>
              <a:t>{title}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr>
          <p:cNvPr id=\"3\" name=\"Content\"/>
          <p:cNvSpPr>
            <a:spLocks noGrp=\"1\"/>
          </p:cNvSpPr>
          <p:nvPr>
            <p:ph type=\"body\" idx=\"1\"/>
          </p:nvPr>
        </p:nvSpPr>
        <p:spPr>
          <a:xfrm>
            <a:off x=\"457200\" y=\"1600200\"/>
            <a:ext cx=\"8229600\" cy=\"4525963\"/>
          </a:xfrm>
        </p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:lstStyle/>
{bullets_block}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sld>"""


def append_summary_slide(unpack_dir: Path, title: str, bullets: list[str]) -> None:
    slides_dir = unpack_dir / "ppt" / "slides"
    slide_files = sorted(slides_dir.glob("slide*.xml"), key=lambda path: int(''.join(ch for ch in path.stem if ch.isdigit())))
    next_slide_num = len(slide_files) + 1

    (slides_dir / f"slide{next_slide_num}.xml").write_text(
        render_summary_slide_xml(title, bullets),
        encoding="utf-8",
    )

    rels_dir = slides_dir / "_rels"
    rels_dir.mkdir(exist_ok=True)
    (rels_dir / f"slide{next_slide_num}.xml.rels").write_text(
        """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout2.xml\"/>
</Relationships>""",
        encoding="utf-8",
    )

    content_types_path = unpack_dir / "[Content_Types].xml"
    ct_root = ET.parse(content_types_path).getroot()
    override = ET.Element(qn("ct", "Override"))
    override.set("PartName", f"/ppt/slides/slide{next_slide_num}.xml")
    override.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
    ct_root.append(override)
    ET.ElementTree(ct_root).write(content_types_path, encoding="utf-8", xml_declaration=True)

    rels_path = unpack_dir / "ppt" / "_rels" / "presentation.xml.rels"
    rels_root = ET.parse(rels_path).getroot()
    existing_ids = [int(rel.get("Id")[3:]) for rel in rels_root.findall("rel:Relationship", NS)]
    next_rid = max(existing_ids) + 1
    relationship = ET.Element(qn("rel", "Relationship"))
    relationship.set("Id", f"rId{next_rid}")
    relationship.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
    relationship.set("Target", f"slides/slide{next_slide_num}.xml")
    rels_root.append(relationship)
    ET.ElementTree(rels_root).write(rels_path, encoding="utf-8", xml_declaration=True)

    pres_path = unpack_dir / "ppt" / "presentation.xml"
    pres_root = ET.parse(pres_path).getroot()
    sld_id_lst = pres_root.find(".//p:sldIdLst", NS)
    if sld_id_lst is None:
        raise RuntimeError("sldIdLst missing in presentation.xml")
    existing_sld_ids = [int(node.get("id")) for node in sld_id_lst.findall("p:sldId", NS)]
    next_sld_id = max(existing_sld_ids) + 1 if existing_sld_ids else 256
    sld_id = ET.Element(qn("p", "sldId"))
    sld_id.set("id", str(next_sld_id))
    sld_id.set(qn("r", "id"), f"rId{next_rid}")
    sld_id_lst.append(sld_id)
    ET.ElementTree(pres_root).write(pres_path, encoding="utf-8", xml_declaration=True)

    app_path = unpack_dir / "docProps" / "app.xml"
    if app_path.exists():
        app_root = ET.parse(app_path).getroot()
        slides_node = app_root.find(".//{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides")
        if slides_node is not None:
            slides_node.text = str(next_slide_num)
        ET.ElementTree(app_root).write(app_path, encoding="utf-8", xml_declaration=True)


def replace_existing_summary_slide(unpack_dir: Path, slide_number_value: int, title: str, bullets: list[str]) -> None:
    slide_path = unpack_dir / "ppt" / "slides" / f"slide{slide_number_value}.xml"
    slide_path.write_text(render_summary_slide_xml(title, bullets), encoding="utf-8")


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    config = json.loads((script_dir / "task_config.json").read_text(encoding="utf-8"))
    unpack_script = script_dir / "tools" / "ooxml" / "unpack.py"
    pack_script = script_dir / "tools" / "ooxml" / "pack.py"

    input_pptx = Path("/root") / str(config["input_file"])
    output_pptx = Path("/root") / str(config["output_file"])
    unpack_dir = Path("/root") / "task_work" / input_pptx.stem

    if unpack_dir.exists():
        shutil.rmtree(unpack_dir)
    unpack_dir.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(["python3", str(unpack_script), str(input_pptx), str(unpack_dir)], check=True)
    slide_width, slide_height = get_slide_dimensions(unpack_dir)
    alias_map = load_alias_map(config)

    for slide_cfg in config["slides"]:
        slide_number_value = int(slide_cfg["slide_number"])
        slide_path = unpack_dir / "ppt" / "slides" / f"slide{slide_number_value}.xml"
        tree = ET.parse(slide_path)
        root = tree.getroot()

        paragraph = find_caption_paragraph(root, str(slide_cfg["caption_raw"]))
        clean_text = resolve_clean_text(slide_cfg, alias_map)
        rewrite_caption_paragraph(paragraph, clean_text, config["style"])

        parent_map = build_parent_map(root)
        shape = find_parent_shape(paragraph, parent_map)
        if shape is None:
            raise RuntimeError(f"Shape not found for slide {slide_number_value}")
        if slide_cfg.get("container_mode") == "group":
            group = find_parent_group(shape, parent_map)
            if group is None:
                raise RuntimeError(f"Group container not found for slide {slide_number_value}")
            adjust_group_position(group, shape, slide_width, slide_height, config["style"])
        else:
            adjust_shape_position(shape, slide_width, slide_height, config["style"])
        tree.write(slide_path, encoding="utf-8", xml_declaration=True)

    bullets = ordered_clean_captions(config, alias_map)
    if config["summary_mode"] == "append":
        append_summary_slide(unpack_dir, str(config["summary_title"]), bullets)
    else:
        replace_existing_summary_slide(
            unpack_dir,
            int(config["summary_slide_number"]),
            str(config["summary_title"]),
            bullets,
        )

    if output_pptx.exists():
        output_pptx.unlink()
    subprocess.run(["python3", str(pack_script), str(unpack_dir), str(output_pptx)], check=True)


if __name__ == "__main__":
    main()
