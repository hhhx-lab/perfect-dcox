from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.models import ExtractionSourceType, FileRecord
from app.storage.repository import JsonMetadataRepository

SUPPORTED_RULE_SOURCE_EXTENSIONS = {".doc", ".docx"}


class ExtractionSourceError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedExtractionSource:
    source_type: ExtractionSourceType
    text: str
    file_record: FileRecord | None = None


def resolve_extraction_source(
    repository: JsonMetadataRepository,
    file_id: str | None,
    natural_language: str | None,
) -> ResolvedExtractionSource:
    text = (natural_language or "").strip()
    if file_id:
        record = repository.get_file(file_id)
        if record is None:
            raise ExtractionSourceError(f"Rule source file not found: {file_id}")
        suffix = Path(record.filename).suffix.lower()
        if suffix not in SUPPORTED_RULE_SOURCE_EXTENSIONS:
            raise ExtractionSourceError("Only .doc and .docx rule source files are supported.")
        return ResolvedExtractionSource(source_type="document", text="", file_record=record)
    if text:
        return ResolvedExtractionSource(source_type="natural_language", text=text)
    raise ExtractionSourceError("Either file_id or natural_language is required for profile extraction.")
