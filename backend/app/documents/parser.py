from __future__ import annotations

from pathlib import Path


class DocumentParseError(RuntimeError):
    pass


def parse_docx(path: Path) -> dict[str, object]:
    raise DocumentParseError("DOCX parsing is not implemented yet.")
