from __future__ import annotations

from pathlib import Path

from app.profiles.models import FormatProfile


class DocumentFormatError(RuntimeError):
    pass


def format_docx_with_profile(input_path: Path, output_path: Path, profile: FormatProfile) -> Path:
    raise DocumentFormatError("DOCX formatting is not implemented yet.")
