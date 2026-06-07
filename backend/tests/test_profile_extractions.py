import pytest
from pydantic import ValidationError

from app.agents.extraction import ExtractionSourceError, extract_rule_source_text, resolve_extraction_source
from app.models import ExtractionEvidence, ProfileExtractionRecord, UncertainItem
from app.models import FileRecord
from app.profiles.seed import load_builtin_profiles
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_minimal_thesis_docx


def test_profile_extraction_record_serializes_review_payload() -> None:
    profile = load_builtin_profiles()["ecnu_thesis"].model_copy(update={"id": "ecnu_extracted", "status": "draft"})

    record = ProfileExtractionRecord(
        extraction_id="extract_123",
        source_type="natural_language",
        natural_language="A4, 宋体小四，1.5 倍行距",
        status="completed",
        profile_draft=profile,
        uncertain_items=[
            UncertainItem(
                field_path="headings.1.font.size_pt",
                message="标题字号未区分层级。",
                suggestion="按小四处理，用户确认后保存。",
            )
        ],
        evidence=[
            ExtractionEvidence(
                field_path="page.size",
                source="natural_language",
                quote="A4",
                confidence=0.96,
            )
        ],
    )

    payload = record.model_dump(mode="json")

    assert payload["status"] == "completed"
    assert payload["profile_draft"]["status"] == "draft"
    assert payload["uncertain_items"][0]["field_path"] == "headings.1.font.size_pt"
    assert payload["evidence"][0]["confidence"] == 0.96
    assert payload["created_at"]
    assert payload["updated_at"]


def test_profile_extraction_evidence_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        ExtractionEvidence(field_path="page.size", source="document", quote="A4", confidence=1.5)


def test_repository_persists_profile_extraction_jobs(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    record = ProfileExtractionRecord(
        extraction_id="extract_123",
        source_type="natural_language",
        natural_language="A4, 宋体小四，1.5 倍行距",
    )

    repository.add_profile_extraction(record)
    loaded = repository.get_profile_extraction("extract_123")
    assert loaded == record

    loaded.status = "failed"
    loaded.error_message = "LLM output is invalid JSON."
    updated = repository.update_profile_extraction(loaded)

    reloaded_repository = JsonMetadataRepository(tmp_path / "metadata.json")
    assert reloaded_repository.get_profile_extraction("extract_123") == updated
    assert reloaded_repository.list_profile_extractions()[0].error_message == "LLM output is invalid JSON."
    assert updated.updated_at >= record.updated_at


def test_repository_round_trips_completed_profile_extraction_result(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    profile = load_builtin_profiles()["ecnu_thesis"].model_copy(
        update={"id": "ecnu_agent_draft", "status": "draft", "source": "imported"}
    )
    record = ProfileExtractionRecord(
        extraction_id="extract_completed",
        source_type="document",
        file_id="file_rules",
        status="completed",
        profile_draft=profile,
        uncertain_items=[
            UncertainItem(
                field_path="equations.numbering",
                message="公式编号位置需要确认。",
                suggestion="沿用右编号。",
            )
        ],
        evidence=[
            ExtractionEvidence(
                field_path="body.line_spacing",
                source="document",
                quote="行距1.5倍",
                confidence=0.91,
            )
        ],
    )

    repository.add_profile_extraction(record)

    reloaded = JsonMetadataRepository(tmp_path / "metadata.json").get_profile_extraction("extract_completed")
    assert reloaded is not None
    assert reloaded.profile_draft is not None
    assert reloaded.profile_draft.id == "ecnu_agent_draft"
    assert reloaded.profile_draft.status == "draft"
    assert reloaded.uncertain_items[0].field_path == "equations.numbering"
    assert reloaded.evidence[0].quote == "行距1.5倍"


def test_repository_handles_legacy_metadata_without_extraction_jobs(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"files": {}, "jobs": {}, "profiles": {}, "profile_versions": {}}', encoding="utf-8")

    repository = JsonMetadataRepository(metadata_path)

    assert repository.list_profile_extractions() == []
    assert repository.get_profile_extraction("extract_missing") is None


def test_resolve_natural_language_extraction_source(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")

    source = resolve_extraction_source(repository, file_id=None, natural_language="  A4, 小四宋体  ")

    assert source.source_type == "natural_language"
    assert source.text == "A4, 小四宋体"
    assert source.file_record is None


def test_resolve_extraction_source_rejects_empty_request(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")

    with pytest.raises(ExtractionSourceError, match="Either file_id or natural_language"):
        resolve_extraction_source(repository, file_id=None, natural_language="  ")


def test_resolve_document_extraction_source_validates_file(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    repository.add_file(
        FileRecord(
            file_id="file_rules",
            filename="rules.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size=12,
            sha256="a" * 64,
            storage_path=str(tmp_path / "rules.docx"),
        )
    )

    source = resolve_extraction_source(repository, file_id="file_rules", natural_language=None)

    assert source.source_type == "document"
    assert source.file_record is not None
    assert source.file_record.filename == "rules.docx"


def test_resolve_document_extraction_source_rejects_missing_or_unsupported_file(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    repository.add_file(
        FileRecord(
            file_id="file_txt",
            filename="rules.txt",
            mime_type="text/plain",
            size=12,
            sha256="b" * 64,
            storage_path=str(tmp_path / "rules.txt"),
        )
    )

    with pytest.raises(ExtractionSourceError, match="Rule source file not found"):
        resolve_extraction_source(repository, file_id="file_missing", natural_language=None)
    with pytest.raises(ExtractionSourceError, match="Only .doc and .docx"):
        resolve_extraction_source(repository, file_id="file_txt", natural_language=None)


def test_extract_rule_source_text_from_docx(tmp_path) -> None:
    docx_path = create_minimal_thesis_docx(tmp_path / "rules.docx")
    record = FileRecord(
        file_id="file_rules",
        filename="rules.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=docx_path.stat().st_size,
        sha256="c" * 64,
        storage_path=str(docx_path),
    )

    text = extract_rule_source_text(record, tmp_path / "work", soffice_bin=None)

    assert "第一章 绪论" in text
    assert "Header A" in text
    assert "Value B" in text


def test_extract_rule_source_text_from_doc_requires_soffice(tmp_path) -> None:
    legacy_doc = tmp_path / "rules.doc"
    legacy_doc.write_bytes(b"legacy")
    record = FileRecord(
        file_id="file_rules",
        filename="rules.doc",
        mime_type="application/msword",
        size=legacy_doc.stat().st_size,
        sha256="d" * 64,
        storage_path=str(legacy_doc),
    )

    with pytest.raises(ExtractionSourceError, match="SOFFICE_BIN"):
        extract_rule_source_text(record, tmp_path / "work", soffice_bin=None)
