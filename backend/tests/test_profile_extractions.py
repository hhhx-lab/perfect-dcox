import pytest
from pydantic import ValidationError

from app.models import ExtractionEvidence, ProfileExtractionRecord, UncertainItem
from app.profiles.seed import load_builtin_profiles


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
