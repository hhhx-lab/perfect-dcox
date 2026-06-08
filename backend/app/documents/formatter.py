from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from app.profiles.models import HeadingSettings, TextAlignment, TextFont
from app.profiles.models import FormatProfile
from app.documents.structure import ParagraphRole, _heading_level, classify_document
from app.documents.ooxml import enable_update_fields


class DocumentFormatError(RuntimeError):
    pass


def format_docx_with_profile(input_path: Path, output_path: Path, profile: FormatProfile) -> Path:
    try:
        document = Document(input_path)
    except Exception as exc:
        raise DocumentFormatError(f"DOCX formatting failed to open input: {exc}") from exc

    _apply_page_settings(document, profile)
    _apply_basic_page_numbers(document, profile)
    _replace_manual_toc_with_refreshable_field(document)
    _insert_missing_table_captions(document)
    structure = classify_document(document)
    for index, paragraph in enumerate(document.paragraphs):
        if _paragraph_has_toc_field(paragraph):
            continue
        classification = structure.role_for(index)
        if classification.role == ParagraphRole.EMPTY:
            continue
        if classification.role == ParagraphRole.TOC_TITLE:
            _apply_heading_paragraph(paragraph, profile, 2)
        elif classification.role == ParagraphRole.TOC_ITEM:
            continue
        elif classification.role == ParagraphRole.DOCUMENT_TITLE:
            _apply_heading_paragraph(paragraph, profile, 1)
        elif classification.role in {
            ParagraphRole.HEADING,
            ParagraphRole.REFERENCE_HEADING,
            ParagraphRole.ACKNOWLEDGEMENT_HEADING,
        }:
            _apply_heading_paragraph(paragraph, profile, classification.heading_level or 1)
        elif classification.role == ParagraphRole.ABSTRACT_HEADING:
            _apply_abstract_heading(paragraph, profile)
        elif classification.role == ParagraphRole.ABSTRACT_BODY:
            _apply_abstract_body(paragraph, profile)
        elif classification.role == ParagraphRole.KEYWORDS:
            _apply_keywords_paragraph(paragraph, profile)
        elif classification.role == ParagraphRole.TABLE_CAPTION:
            _apply_caption_paragraph(paragraph, profile.table.caption.font)
        elif classification.role == ParagraphRole.FIGURE_CAPTION:
            _apply_caption_paragraph(paragraph, profile.figure.caption.font)
        elif classification.role == ParagraphRole.EQUATION:
            _apply_equation_paragraph(paragraph, profile)
        elif classification.role == ParagraphRole.REFERENCE_ITEM:
            _apply_reference_paragraph(paragraph, profile)
        else:
            _apply_body_paragraph(paragraph, profile)
    for table in document.tables:
        _apply_basic_three_line_table(table)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    enable_update_fields(output_path)
    return output_path


def _apply_page_settings(document: Document, profile: FormatProfile) -> None:
    for section in document.sections:
        _apply_section_size(section, profile)
        section.top_margin = Cm(profile.page.margins_cm.top)
        section.bottom_margin = Cm(profile.page.margins_cm.bottom)
        section.left_margin = Cm(profile.page.margins_cm.left)
        section.right_margin = Cm(profile.page.margins_cm.right)
        section.gutter = Cm(profile.page.margins_cm.gutter)


def _apply_section_size(section, profile: FormatProfile) -> None:
    if profile.page.size == "A4":
        width_cm, height_cm = 21.0, 29.7
    else:
        width_cm, height_cm = 21.59, 27.94
    if profile.page.orientation == "landscape":
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Cm(height_cm)
        section.page_height = Cm(width_cm)
    else:
        section.orientation = WD_ORIENT.PORTRAIT
        section.page_width = Cm(width_cm)
        section.page_height = Cm(height_cm)


def _apply_basic_page_numbers(document: Document, profile: FormatProfile) -> None:
    for section in document.sections:
        _apply_header(section, profile)
        if not profile.header_footer.footer_page_number:
            _remove_supported_page_number(section.footer)
            continue
        footer = section.footer
        paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        paragraph.text = ""
        paragraph.paragraph_format.left_indent = None
        paragraph.paragraph_format.first_line_indent = None
        _apply_paragraph_alignment(paragraph, profile.header_footer.footer_alignment)
        run = paragraph.add_run()
        _append_page_field(run)
        _apply_runs_font(paragraph, profile.header_footer.font)


def _remove_supported_page_number(footer) -> None:
    for paragraph in footer.paragraphs:
        if "PAGE" in paragraph._p.xml and "fldChar" in paragraph._p.xml:
            paragraph.text = ""


def _apply_header(section, profile: FormatProfile) -> None:
    text = (profile.header_footer.header_text or "").strip()
    if not text:
        return
    paragraph = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
    paragraph.text = text
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None
    _apply_paragraph_alignment(paragraph, profile.header_footer.header_alignment)
    _apply_runs_font(paragraph, profile.header_footer.font)


def _append_page_field(run) -> None:
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def _replace_manual_toc_with_refreshable_field(document: Document) -> None:
    paragraphs = list(document.paragraphs)
    texts = [paragraph.text.strip() for paragraph in paragraphs]
    toc_index = next((index for index, paragraph in enumerate(paragraphs) if paragraph.text.strip() in {"目录", "Contents"}), None)
    if toc_index is None:
        return
    real_abstract_index = _first_real_abstract_heading_index(paragraphs, texts, toc_index)
    if real_abstract_index is not None:
        end_index = real_abstract_index
    else:
        end_index = toc_index + 1
        while end_index < len(paragraphs):
            text = paragraphs[end_index].text.strip()
            if not text:
                end_index += 1
                continue
            if _heading_level(text, paragraphs[end_index].style.name if paragraphs[end_index].style else ""):
                break
            end_index += 1
    if end_index <= toc_index + 1:
        return

    toc_entries = [paragraph.text.strip() for paragraph in paragraphs[toc_index + 1 : end_index] if paragraph.text.strip()]
    toc_paragraph = paragraphs[toc_index]
    _clear_paragraph_runs(toc_paragraph)
    toc_paragraph.text = ""
    _append_toc_field(toc_paragraph.add_run(), toc_entries)
    _apply_paragraph_alignment(toc_paragraph, "left")
    for paragraph in paragraphs[toc_index + 1 : end_index]:
        paragraph._element.getparent().remove(paragraph._element)


def _first_real_abstract_heading_index(paragraphs: list, texts: list[str], toc_index: int) -> int | None:
    for index, text in enumerate(texts):
        if index <= toc_index or text not in {"摘要", "Abstract"}:
            continue
        style_name = paragraphs[index].style.name if paragraphs[index].style else ""
        following = [item for item in texts[index + 1 : index + 5] if item]
        next_text = following[0] if following else ""
        has_nearby_keywords = any(item.startswith(("关键词", "Keywords:")) for item in following)
        if _looks_like_toc_entry(next_text):
            continue
        if style_name.lower().startswith("heading") or has_nearby_keywords or len(next_text) > 0:
            return index
    return None


def _looks_like_toc_entry(text: str) -> bool:
    if text in {"摘要", "Abstract", "参考文献", "References", "致谢", "Acknowledgements", "Acknowledgments"}:
        return True
    return _heading_level(text, "") is not None


def _append_toc_field(run, entries: list[str]) -> None:
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-3" \h \z \u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "\n".join(entries) if entries else "目录"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text)
    run._r.append(end)


def _clear_paragraph_runs(paragraph) -> None:
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)


def _paragraph_has_toc_field(paragraph) -> bool:
    xml = paragraph._p.xml.upper()
    return "TOC" in xml and ("FLDCHAR" in xml or "FLDSIMPLE" in xml)


def _insert_missing_table_captions(document: Document) -> None:
    existing_numbers = _existing_table_caption_numbers(document)
    table_index = 0
    previous_text = ""
    for child in list(document.element.body):
        if child.tag == qn("w:p"):
            previous_text = _paragraph_xml_text(child).strip() or previous_text
            continue
        if child.tag != qn("w:tbl"):
            continue
        table_index += 1
        inferred_number = _table_number_from_text(previous_text) or table_index
        if inferred_number in existing_numbers or _previous_sibling_is_table_caption(child):
            continue
        caption_text = _caption_text_from_preceding_sentence(previous_text, inferred_number)
        if caption_text is None:
            continue
        caption = _caption_paragraph_xml(caption_text)
        child.addprevious(caption)
        existing_numbers.add(inferred_number)


def _existing_table_caption_numbers(document: Document) -> set[int]:
    numbers: set[int] = set()
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not _is_table_caption(text):
            continue
        match = re.match(r"^表\s*(\d+)[\s：:、.-]+\S+", text)
        if match:
            numbers.add(int(match.group(1)))
    return numbers


def _previous_sibling_is_table_caption(table_element) -> bool:
    previous = table_element.getprevious()
    while previous is not None:
        if previous.tag != qn("w:p"):
            previous = previous.getprevious()
            continue
        text = _paragraph_xml_text(previous).strip()
        if not text:
            previous = previous.getprevious()
            continue
        return _is_table_caption(text)
    return False


def _caption_text_from_preceding_sentence(text: str, number: int) -> str | None:
    stripped = text.strip()
    if not stripped or not re.search(rf"表\s*{number}(?!\d)", stripped):
        return None
    cleaned = re.sub(rf"^.*?表\s*{number}\s*", "", stripped)
    cleaned = re.sub(r"^(给出|根据|如下|所示|见|列出|显示|说明|概括了?|展示|为)\s*", "", cleaned)
    cleaned = re.sub(r"^(一个|一项|一种|一份|若干)\s*", "", cleaned)
    cleaned = re.sub(r"[。；;，,：:]+$", "", cleaned).strip()
    cleaned = re.sub(r"\[[0-9,\]\[]+$", "", cleaned).strip()
    if len(cleaned) < 2:
        cleaned = "表格"
    if len(cleaned) > 32:
        cleaned = cleaned[:32].rstrip("，,、；;。")
    return f"表 {number} {cleaned}"


def _table_number_from_text(text: str) -> int | None:
    match = re.search(r"表\s*(\d+)", text)
    return int(match.group(1)) if match else None


def _paragraph_xml_text(paragraph_element) -> str:
    return "".join(node.text or "" for node in paragraph_element.xpath(".//w:t"))


def _caption_paragraph_xml(text: str):
    paragraph = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    ppr.append(jc)
    paragraph.append(ppr)
    run = OxmlElement("w:r")
    text_node = OxmlElement("w:t")
    text_node.text = text
    run.append(text_node)
    paragraph.append(run)
    return paragraph


def _apply_body_paragraph(paragraph, profile: FormatProfile) -> None:
    if not paragraph.text.strip():
        return
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = Cm(profile.body.first_line_indent_chars * 0.37)
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_paragraph_alignment(paragraph, profile.body.alignment)
    _apply_runs_font(paragraph, profile.body.font)


def _apply_heading_paragraph(paragraph, profile: FormatProfile, level: int) -> None:
    heading = _heading_rule(profile, level)
    paragraph.style = f"Heading {min(heading.level, 9)}"
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_paragraph_alignment(paragraph, heading.alignment)
    _apply_runs_font(paragraph, heading.font)


def _apply_abstract_heading(paragraph, profile: FormatProfile) -> None:
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _apply_runs_font(paragraph, profile.abstract.title_font)


def _apply_abstract_body(paragraph, profile: FormatProfile) -> None:
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_paragraph_alignment(paragraph, profile.body.alignment)
    _apply_runs_font(paragraph, profile.abstract.body_font)


def _apply_keywords_paragraph(paragraph, profile: FormatProfile) -> None:
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = None
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_paragraph_alignment(paragraph, "left")
    _apply_runs_font(paragraph, profile.abstract.body_font)


def _apply_caption_paragraph(paragraph, font: TextFont) -> None:
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _apply_runs_font(paragraph, font)


def _apply_equation_paragraph(paragraph, profile: FormatProfile) -> None:
    paragraph.paragraph_format.left_indent = None
    paragraph.paragraph_format.first_line_indent = Cm(0)
    _apply_paragraph_alignment(paragraph, profile.equations.alignment)


def _apply_reference_paragraph(paragraph, profile: FormatProfile) -> None:
    paragraph.paragraph_format.left_indent = Cm(profile.references.hanging_indent_chars * 0.37)
    paragraph.paragraph_format.first_line_indent = Cm(-profile.references.hanging_indent_chars * 0.37)
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_runs_font(paragraph, profile.references.font)


def _heading_rule(profile: FormatProfile, level: int) -> HeadingSettings:
    exact = next((heading for heading in profile.headings if heading.level == level), None)
    if exact is not None:
        return exact
    lower_or_equal = [heading for heading in profile.headings if heading.level <= level]
    if lower_or_equal:
        return sorted(lower_or_equal, key=lambda heading: heading.level)[-1]
    return profile.headings[0]


def _matching_heading(profile: FormatProfile, text: str, style_name: str) -> HeadingSettings | None:
    stripped = text.strip()
    if not stripped:
        return None
    level = None
    if style_name.lower().startswith("heading"):
        match = re.search(r"(\d+)", style_name)
        level = int(match.group(1)) if match else 1
    elif re.match(r"^第[一二三四五六七八九十百0-9]+[章节]", stripped):
        level = 1
    elif re.match(r"^[0-9]+\.[0-9]+", stripped):
        level = 2
    if level is None:
        return None
    return next((heading for heading in profile.headings if heading.level == level), profile.headings[0])


def _apply_runs_font(paragraph, font: TextFont) -> None:
    runs = paragraph.runs or [paragraph.add_run("")]
    for run in runs:
        run.font.name = font.latin
        run.font.size = Pt(font.size_pt)
        run.font.bold = font.weight == "bold"
        run.font.color.rgb = RGBColor.from_string(font.color)
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), font.chinese)


def _apply_paragraph_alignment(paragraph, alignment: TextAlignment) -> None:
    mapping = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justified": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    paragraph.alignment = mapping[alignment]


def _is_table_caption(text: str) -> bool:
    if re.search(r"(如下|所示|见|列出|显示|说明|给出)", text):
        return False
    return bool(re.match(r"^(表\s*\d+|Table\s+\d+)[\s：:、.-]+\S+", text, re.IGNORECASE))


def _is_figure_caption(text: str) -> bool:
    return bool(re.match(r"^(图\s*\d+|Figure\s+\d+)", text, re.IGNORECASE))


def _is_equation(text: str) -> bool:
    if not text:
        return False
    return any(symbol in text for symbol in ("=", "＋", "+", "-", "*", "/", "^")) and len(text) <= 120


def _apply_basic_three_line_table(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is not None:
        tbl_pr.remove(borders)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    for edge in ("left", "right", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "nil")
        borders.append(element)
    tbl_pr.append(borders)
