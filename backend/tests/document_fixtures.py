from __future__ import annotations

from pathlib import Path

from docx import Document


def create_minimal_thesis_docx(path: Path) -> Path:
    document = Document()
    document.add_heading("第一章 绪论", level=1)
    document.add_paragraph("这是一段正文内容，用于验证格式化后文本不会丢失。")
    document.add_paragraph("Table 1 Sample table")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Header A"
    table.cell(0, 1).text = "Header B"
    table.cell(1, 0).text = "Value A"
    table.cell(1, 1).text = "Value B"
    document.add_paragraph("图 1 示例图片标题")
    document.add_paragraph("E = mc^2")
    document.add_paragraph("参考文献")
    document.add_paragraph("[1] Author. Title.")
    document.save(path)
    return path


def read_docx_text(path: Path) -> list[str]:
    return [paragraph.text for paragraph in Document(path).paragraphs]
