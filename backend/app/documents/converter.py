from __future__ import annotations

from pathlib import Path


class DocumentConversionError(RuntimeError):
    pass


def convert_doc_to_docx(input_path: Path, output_dir: Path, soffice_bin: str | None) -> Path:
    raise DocumentConversionError("DOC conversion is not implemented yet.")
