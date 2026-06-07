from pathlib import Path

from docx import Document
from app.documents.formatter import format_docx_with_profile
from app.profiles.seed import load_builtin_profiles
from tests.document_fixtures import create_minimal_thesis_docx, read_docx_text


def test_formatter_applies_ecnu_page_body_and_heading_rules(tmp_path: Path) -> None:
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    output = tmp_path / "formatted.docx"
    profile = load_builtin_profiles()["ecnu_thesis"]

    formatted = format_docx_with_profile(source, output, profile)

    document = Document(formatted)
    section = document.sections[0]
    assert round(section.top_margin.cm, 1) == 2.5
    assert round(section.bottom_margin.cm, 1) == 2.0
    assert round(section.left_margin.cm, 1) == 3.0
    assert round(section.right_margin.cm, 1) == 2.5

    body = document.paragraphs[1]
    assert round(body.paragraph_format.first_line_indent.cm, 2) == 0.74
    assert body.paragraph_format.line_spacing == 1.5
    assert body.runs[0].font.name == "Times New Roman"
    assert body.runs[0]._element.rPr.rFonts.get(qn("w:eastAsia")) == "SimSun"

    heading = document.paragraphs[0]
    assert heading.style.name == "Heading 1"
    assert heading.runs[0]._element.rPr.rFonts.get(qn("w:eastAsia")) == "SimHei"
    assert read_docx_text(formatted) == read_docx_text(source)


def qn(name: str) -> str:
    from docx.oxml.ns import qn as docx_qn

    return docx_qn(name)
