from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from docx import Document
from pydantic import ValidationError
import yaml

from app.core.config import Settings
from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.models import ExtractionEvidence, ExtractionSourceType, FileRecord, UncertainItem
from app.profiles.models import FormatProfile
from app.storage.repository import JsonMetadataRepository

SUPPORTED_RULE_SOURCE_EXTENSIONS = {".doc", ".docx"}


class ExtractionSourceError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedExtractionSource:
    source_type: ExtractionSourceType
    text: str
    file_record: FileRecord | None = None


@dataclass(frozen=True)
class ParsedAgentExtraction:
    profile_draft: FormatProfile
    uncertain_items: list[UncertainItem]
    evidence: list[ExtractionEvidence]


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


def parse_agent_extraction_output(raw_output: str) -> ParsedAgentExtraction:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        try:
            parsed = yaml.safe_load(raw_output)
        except yaml.YAMLError as exc:
            raise ExtractionSourceError(f"Agent output must be valid JSON or YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ExtractionSourceError("Agent output must be a structured object.")

    missing = [key for key in ("profile_draft", "uncertain_items", "evidence") if key not in parsed]
    if missing:
        raise ExtractionSourceError(f"Agent output missing required section(s): {', '.join(missing)}")
    try:
        profile = FormatProfile.model_validate(parsed["profile_draft"])
    except ValidationError as exc:
        raise ExtractionSourceError(f"Agent profile_draft failed schema validation: {exc}") from exc
    try:
        uncertain_items = [UncertainItem.model_validate(item) for item in parsed["uncertain_items"]]
        evidence = [ExtractionEvidence.model_validate(item) for item in parsed["evidence"]]
    except ValidationError as exc:
        raise ExtractionSourceError(f"Agent review metadata failed validation: {exc}") from exc
    if not evidence:
        raise ExtractionSourceError("Agent output evidence must contain at least one item.")
    return ParsedAgentExtraction(profile_draft=profile, uncertain_items=uncertain_items, evidence=evidence)
