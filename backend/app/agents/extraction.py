from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from docx import Document

from app.core.config import Settings
from app.documents.converter import DocumentConversionError, convert_doc_to_docx
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


class RuleExtractionProvider(Protocol):
    def extract(self, source_text: str, source_meta: dict[str, str]) -> str:
        """Return raw structured Agent output for downstream parsing."""


class ConfiguredLLMRuleExtractionProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def extract(self, source_text: str, source_meta: dict[str, str]) -> str:
        if not self.settings.llm_api_key or not self.settings.llm_model:
            raise ExtractionSourceError("LLM_API_KEY and LLM_MODEL are required for profile extraction.")
        raise ExtractionSourceError("Live LLM extraction provider is not implemented in this local MVP.")


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


def extract_rule_source_text(record: FileRecord, work_dir: Path, soffice_bin: str | None) -> str:
    input_path = Path(record.storage_path)
    try:
        docx_path = convert_doc_to_docx(input_path, work_dir, soffice_bin)
    except DocumentConversionError as exc:
        raise ExtractionSourceError(str(exc)) from exc

    try:
        document = Document(docx_path)
    except Exception as exc:  # noqa: BLE001 - python-docx exposes multiple low-level parse exceptions.
        raise ExtractionSourceError(f"Rule document text extraction failed: {exc}") from exc

    parts: list[str] = []
    parts.extend(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    parts.append(cell_text)
    if not parts:
        raise ExtractionSourceError("Rule document does not contain extractable text.")
    return "\n".join(parts)
