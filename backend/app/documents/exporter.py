from __future__ import annotations

from pathlib import Path


class DocumentExportError(RuntimeError):
    pass


def export_docx_to_pdf(input_path: Path, output_dir: Path, soffice_bin: str | None) -> Path:
    raise DocumentExportError("PDF export is not implemented yet.")
