from pathlib import Path

from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.formatter import format_docx_with_profile
from app.documents.parser import parse_docx


def test_document_module_entry_points_exist(tmp_path: Path) -> None:
    assert callable(convert_doc_to_docx)
    assert callable(parse_docx)
    assert callable(format_docx_with_profile)
    assert callable(export_docx_to_pdf)
    assert issubclass(DocumentConversionError, RuntimeError)
    assert issubclass(DocumentExportError, RuntimeError)
