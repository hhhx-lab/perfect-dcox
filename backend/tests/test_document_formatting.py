from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

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


def test_formatter_applies_special_paragraphs_and_table_borders(tmp_path: Path) -> None:
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    output = tmp_path / "formatted.docx"
    profile = load_builtin_profiles()["ecnu_thesis"]

    formatted = format_docx_with_profile(source, output, profile)

    document = Document(formatted)
    table_caption = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("Table 1"))
    figure_caption = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("图 1"))
    equation = next(paragraph for paragraph in document.paragraphs if "E = mc" in paragraph.text)
    reference = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("[1]"))
    assert table_caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert figure_caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert equation.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert reference.paragraph_format.first_line_indent.cm < 0
    assert reference.paragraph_format.left_indent.cm > 0

    borders = document.tables[0]._tbl.tblPr.xpath("./w:tblBorders")
    assert borders
    assert borders[0].xpath("./*[local-name()='top']")
    assert borders[0].xpath("./*[local-name()='bottom']")


def test_formatter_preserves_empty_and_unrecognized_paragraphs(tmp_path: Path) -> None:
    source = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("一个无法归类但必须保留的段落")
    document.save(source)
    output = tmp_path / "formatted.docx"

    formatted = format_docx_with_profile(source, output, load_builtin_profiles()["ecnu_thesis"])

    assert read_docx_text(formatted) == ["", "一个无法归类但必须保留的段落"]


def qn(name: str) -> str:
    from docx.oxml.ns import qn as docx_qn

    return docx_qn(name)
