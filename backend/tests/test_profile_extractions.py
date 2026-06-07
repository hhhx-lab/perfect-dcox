import pytest
from pydantic import ValidationError

from app.models import ExtractionEvidence, ProfileExtractionRecord, UncertainItem
from app.profiles.seed import load_builtin_profiles
from app.storage.repository import JsonMetadataRepository


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
