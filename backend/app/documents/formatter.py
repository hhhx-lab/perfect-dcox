from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from app.profiles.models import HeadingSettings, TextAlignment, TextFont
from app.profiles.models import FormatProfile


class DocumentFormatError(RuntimeError):
    pass


def format_docx_with_profile(input_path: Path, output_path: Path, profile: FormatProfile) -> Path:
    try:
        document = Document(input_path)
    except Exception as exc:
        raise DocumentFormatError(f"DOCX formatting failed to open input: {exc}") from exc

    _apply_page_settings(document, profile)
    for paragraph in document.paragraphs:
        heading = _matching_heading(profile, paragraph.text, paragraph.style.name if paragraph.style else "")
        if heading:
            paragraph.style = f"Heading {heading.level}"
            _apply_paragraph_alignment(paragraph, heading.alignment)
            _apply_runs_font(paragraph, heading.font)
        else:
            _apply_body_paragraph(paragraph, profile)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path


def _apply_page_settings(document: Document, profile: FormatProfile) -> None:
    for section in document.sections:
        section.top_margin = Cm(profile.page.margins_cm.top)
        section.bottom_margin = Cm(profile.page.margins_cm.bottom)
        section.left_margin = Cm(profile.page.margins_cm.left)
        section.right_margin = Cm(profile.page.margins_cm.right)
        section.gutter = Cm(profile.page.margins_cm.gutter)


def _apply_body_paragraph(paragraph, profile: FormatProfile) -> None:
    if not paragraph.text.strip():
        return
    paragraph.paragraph_format.first_line_indent = Cm(profile.body.first_line_indent_chars * 0.37)
    paragraph.paragraph_format.line_spacing = profile.body.line_spacing
    _apply_paragraph_alignment(paragraph, profile.body.alignment)
    _apply_runs_font(paragraph, profile.body.font)


def _matching_heading(profile: FormatProfile, text: str, style_name: str) -> HeadingSettings | None:
    stripped = text.strip()
    if not stripped:
        return None
    level = None
    if style_name.lower().startswith("heading"):
        match = re.search(r"(\\d+)", style_name)
        level = int(match.group(1)) if match else 1
    elif re.match(r"^第[一二三四五六七八九十百0-9]+[章节]", stripped):
        level = 1
    elif re.match(r"^[0-9]+\\.[0-9]+", stripped):
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
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), font.chinese)


def _apply_paragraph_alignment(paragraph, alignment: TextAlignment) -> None:
    mapping = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justified": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    paragraph.alignment = mapping[alignment]
