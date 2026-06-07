from pathlib import Path

from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.formatter import format_docx_with_profile
from app.documents.parser import parse_docx
from tests.document_fixtures import create_minimal_thesis_docx, read_docx_text


def test_document_module_entry_points_exist(tmp_path: Path) -> None:
    assert callable(convert_doc_to_docx)
    assert callable(parse_docx)
    assert callable(format_docx_with_profile)
    assert callable(export_docx_to_pdf)
    assert issubclass(DocumentConversionError, RuntimeError)
    assert issubclass(DocumentExportError, RuntimeError)


def test_minimal_docx_fixture_preserves_expected_text(tmp_path: Path) -> None:
    path = create_minimal_thesis_docx(tmp_path / "sample.docx")

    text = read_docx_text(path)

    assert path.exists()
    assert "第一章 绪论" in text
    assert "这是一段正文内容，用于验证格式化后文本不会丢失。" in text
    assert "参考文献" in text
