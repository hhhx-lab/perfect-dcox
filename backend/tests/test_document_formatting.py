from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import RGBColor
from docx.shared import Pt

from app.documents.formatter import format_docx_with_profile
from app.documents.ooxml import inspect_ooxml_features
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
    assert "PAGE" in section.footer.paragraphs[0]._p.xml
    assert read_docx_text(formatted) == read_docx_text(source)


def test_formatter_applies_profile_font_color(tmp_path: Path) -> None:
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    output = tmp_path / "formatted.docx"
    profile = load_builtin_profiles()["ecnu_thesis"]
    profile.body.font.color = "000000"
    for heading in profile.headings:
        heading.font.color = "000000"

    formatted = format_docx_with_profile(source, output, profile)

    document = Document(formatted)
    body = document.paragraphs[1]
    heading = document.paragraphs[0]
    assert body.runs[0].font.color.rgb == RGBColor(0, 0, 0)
    assert heading.runs[0].font.color.rgb == RGBColor(0, 0, 0)


def test_formatter_applies_profile_page_setup_header_and_page_number_toggle(tmp_path: Path) -> None:
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    output = tmp_path / "formatted.docx"
    base_profile = load_builtin_profiles()["ecnu_thesis"]
    profile = base_profile.model_copy(
        update={
            "page": base_profile.page.model_copy(update={"size": "Letter", "orientation": "landscape"}),
            "header_footer": base_profile.header_footer.model_copy(
                update={
                    "header_text": "测试模板页眉",
                    "header_alignment": "right",
                    "footer_page_number": False,
                }
            ),
        }
    )

    formatted = format_docx_with_profile(source, output, profile)

    document = Document(formatted)
    section = document.sections[0]
    assert section.orientation == WD_ORIENT.LANDSCAPE
    assert round(section.page_width.cm, 1) == 27.9
    assert round(section.page_height.cm, 1) == 21.6
    assert "测试模板页眉" in "\n".join(paragraph.text for paragraph in section.header.paragraphs)
    assert all("PAGE" not in paragraph._p.xml for paragraph in section.footer.paragraphs)
    assert inspect_ooxml_features(formatted).has_update_fields is True


def test_formatter_replaces_manual_toc_and_infers_table_captions(tmp_path: Path) -> None:
    source = tmp_path / "manual-toc.docx"
    document = Document()
    document.add_heading("论文题目", level=1)
    document.add_paragraph("目录")
    document.add_paragraph("摘要")
    document.add_paragraph("1、引言")
    document.add_paragraph("参考文献")
    document.add_paragraph("摘要")
    document.add_paragraph("摘要正文。")
    document.add_paragraph("1、引言")
    document.add_paragraph("表 1 给出一个课程化比较。")
    table = document.add_table(rows=1, cols=1)
    table.cell(0, 0).text = "示例"
    document.save(source)

    formatted = format_docx_with_profile(source, tmp_path / "formatted.docx", load_builtin_profiles()["ecnu_thesis"])

    features = inspect_ooxml_features(formatted)
    formatted_doc = Document(formatted)
    text = read_docx_text(formatted)
    assert features.has_update_fields is True
    assert features.toc_field_count >= 1
    assert any("摘要" in item and "1、引言" in item for item in text)
    assert "表 1 课程化比较" in text
    caption = next(paragraph for paragraph in formatted_doc.paragraphs if paragraph.text == "表 1 课程化比较")
    assert caption.alignment == WD_ALIGN_PARAGRAPH.CENTER


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


def test_formatter_preserves_toc_items_as_body_font_not_abstract_font(tmp_path: Path) -> None:
    source = tmp_path / "toc.docx"
    document = Document()
    document.add_heading("国内 RISC-V 架构现状及发展趋势", level=1)
    document.add_paragraph("目录")
    document.add_paragraph("摘要")
    document.add_paragraph("1、引言")
    document.add_paragraph("2、计算机系统结构视角下的 RISC-V")
    document.add_paragraph("参考文献")
    document.add_paragraph("致谢")
    document.add_paragraph("摘要")
    document.add_paragraph("摘要正文。")
    document.add_paragraph("关键词：RISC-V")
    document.add_paragraph("Abstract")
    document.add_paragraph("English abstract.")
    document.add_paragraph("Keywords: RISC-V")
    document.add_paragraph("1、引言")
    document.add_paragraph("正文段落。")
    document.save(source)

    formatted = format_docx_with_profile(source, tmp_path / "formatted.docx", load_builtin_profiles()["ecnu_thesis"])

    formatted_doc = Document(formatted)
    toc_field = next(paragraph for paragraph in formatted_doc.paragraphs if "TOC" in paragraph._p.xml)
    body = next(paragraph for paragraph in formatted_doc.paragraphs if paragraph.text == "正文段落。")
    assert "1、引言" in toc_field.text
    assert not any(
        paragraph.text in {"2、计算机系统结构视角下的 RISC-V", "参考文献", "致谢"} and paragraph._p.xml != toc_field._p.xml
        for paragraph in formatted_doc.paragraphs[:8]
    )
    assert body.runs[0].font.size == Pt(12)


def test_formatter_preserves_empty_and_unrecognized_paragraphs(tmp_path: Path) -> None:
    source = tmp_path / "input.docx"
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("一个无法归类但必须保留的段落")
    document.save(source)
    output = tmp_path / "formatted.docx"

    formatted = format_docx_with_profile(source, output, load_builtin_profiles()["ecnu_thesis"])

    assert read_docx_text(formatted) == ["", "一个无法归类但必须保留的段落"]


def test_formatter_uses_document_structure_instead_of_template_specific_regexes(tmp_path: Path) -> None:
    source = tmp_path / "mixed.docx"
    document = Document()
    document.add_heading("国内 RISC-V 架构现状及发展趋势", level=1)
    document.add_paragraph("目录")
    document.add_paragraph("摘要")
    document.add_paragraph("1、引言")
    document.add_paragraph("2、计算机系统结构视角下的 RISC-V")
    document.add_paragraph("参考文献")
    document.add_paragraph("致谢")
    document.add_paragraph("摘要")
    document.add_paragraph("RISC-V 是近年来计算机系统结构领域最受关注的开放指令集之一。")
    document.add_paragraph("关键词：RISC-V；计算机系统结构；国产处理器")
    document.add_paragraph("Abstract")
    document.add_paragraph("RISC-V has become one of the most influential open instruction set architectures.")
    document.add_paragraph("Keywords: RISC-V; computer architecture")
    document.add_paragraph("1、引言")
    document.add_paragraph("RISC-V 的出现，使指令集架构重新成为系统结构课程中适合讨论的主题。")
    document.add_paragraph("2.1 ISA 与微体系结构的分层")
    document.add_paragraph("系统结构课程常用 CPU 执行时间公式说明这一点：")
    equation = document.add_paragraph("E = mc^2")
    equation.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph("表 1 给出一个课程化比较。")
    document.add_paragraph("表 1 RISC-V、Arm 与 x86 对比")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "维度"
    table.cell(0, 1).text = "RISC-V"
    table.cell(1, 0).text = "生态"
    table.cell(1, 1).text = "开放标准"
    document.add_paragraph("参考文献")
    document.add_paragraph("[1] RISC-V International. Specifications [E]. https://riscv.org/specifications, 2026.")
    document.add_paragraph("[2] XUANTIE-RV. OpenC910 Core [E]. https://github.com/XUANTIE-RV/openc910.")
    document.add_paragraph("致谢")
    document.save(source)
    output = tmp_path / "formatted.docx"

    formatted = format_docx_with_profile(source, output, load_builtin_profiles()["ecnu_thesis"])

    formatted_doc = Document(formatted)
    by_text = {paragraph.text: paragraph for paragraph in formatted_doc.paragraphs if paragraph.text}
    toc_field = next(paragraph for paragraph in formatted_doc.paragraphs if "TOC" in paragraph._p.xml)
    abstract_body = by_text["RISC-V 是近年来计算机系统结构领域最受关注的开放指令集之一。"]
    body = by_text["RISC-V 的出现，使指令集架构重新成为系统结构课程中适合讨论的主题。"]
    keywords = by_text["关键词：RISC-V；计算机系统结构；国产处理器"]
    chapter_heading = next(paragraph for paragraph in formatted_doc.paragraphs if paragraph.text == "1、引言")
    section_heading = by_text["2.1 ISA 与微体系结构的分层"]
    table_prose = by_text["表 1 给出一个课程化比较。"]
    table_caption = by_text["表 1 RISC-V、Arm 与 x86 对比"]
    reference = by_text["[1] RISC-V International. Specifications [E]. https://riscv.org/specifications, 2026."]

    assert "摘要" in toc_field.text
    assert "1、引言" in toc_field.text

    assert round(body.paragraph_format.first_line_indent.cm, 2) == 0.74
    assert body.paragraph_format.left_indent is None
    assert body.paragraph_format.line_spacing == 1.5
    assert body.runs[0].font.size == Pt(12)
    assert body.runs[0].font.bold is False

    assert abstract_body.paragraph_format.left_indent is None
    assert abstract_body.runs[0].font.size == Pt(10.5)
    assert abstract_body.runs[0].font.bold is False
    assert keywords.alignment != WD_ALIGN_PARAGRAPH.CENTER

    assert chapter_heading.style.name == "Heading 2"
    assert section_heading.style.name == "Heading 2"
    assert chapter_heading.runs[0].font.bold is True

    assert table_prose.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert table_prose.runs[0].font.size == Pt(10.5)
    assert table_caption.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert table_caption.runs[0].font.size == Pt(10.5)

    assert reference.alignment != WD_ALIGN_PARAGRAPH.CENTER
    assert reference.paragraph_format.first_line_indent.cm < 0
    assert reference.paragraph_format.left_indent.cm > 0


def qn(name: str) -> str:
    from docx.oxml.ns import qn as docx_qn

    return docx_qn(name)
