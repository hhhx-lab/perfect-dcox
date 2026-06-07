from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.models import ExtractionEvidence, ProfileExtractionRecord, UncertainItem
from app.profiles.seed import load_builtin_profiles
from app.storage.repository import JsonMetadataRepository


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path)))


def test_create_profile_extraction_from_natural_language(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post("/api/profile-extractions", json={"source_type": "natural_language", "natural_language": "A4, 宋体小四"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["extraction_id"].startswith("extract_")
    assert payload["source_type"] == "natural_language"
    assert payload["natural_language"] == "A4, 宋体小四"
    assert payload["status"] == "queued"


def test_create_profile_extraction_rejects_empty_source(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post("/api/profile-extractions", json={"source_type": "natural_language", "natural_language": "  "})

    assert response.status_code == 400
    assert "Either file_id or natural_language" in response.text


def test_create_profile_extraction_from_document_file(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    uploaded = client.post("/api/files", files={"file": ("rules.docx", b"docx bytes", "application/docx")})
    file_id = uploaded.json()["file_id"]

    response = client.post("/api/profile-extractions", json={"source_type": "document", "file_id": file_id})

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_type"] == "document"
    assert payload["file_id"] == file_id
    assert payload["natural_language"] is None


def test_create_profile_extraction_rejects_invalid_document_request(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    missing_file_id = client.post("/api/profile-extractions", json={"source_type": "document"})
    missing_file = client.post("/api/profile-extractions", json={"source_type": "document", "file_id": "file_missing"})
    mixed = client.post(
        "/api/profile-extractions",
        json={"source_type": "natural_language", "file_id": "file_x", "natural_language": "A4"},
    )

    assert missing_file_id.status_code == 400
    assert missing_file.status_code == 400
    assert mixed.status_code == 400


def test_get_profile_extraction_returns_queued_job(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    created = client.post(
        "/api/profile-extractions",
        json={"source_type": "natural_language", "natural_language": "A4, 宋体小四"},
    ).json()

    loaded = client.get(f"/api/profile-extractions/{created['extraction_id']}")

    assert loaded.status_code == 200
    payload = loaded.json()
    assert payload["extraction_id"] == created["extraction_id"]
    assert payload["status"] == "queued"
    assert payload["profile_draft"] is None


def test_get_profile_extraction_rejects_missing_job(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/profile-extractions/extract_missing")

    assert response.status_code == 404


def test_get_profile_extraction_returns_completed_result(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    profile = load_builtin_profiles()["ecnu_thesis"].model_copy(update={"id": "api_extracted", "status": "draft"})
    repository.add_profile_extraction(
        ProfileExtractionRecord(
            extraction_id="extract_completed",
            source_type="natural_language",
            natural_language="A4",
            status="completed",
            profile_draft=profile,
            uncertain_items=[
                UncertainItem(field_path="page_number.position", message="页码位置缺少 schema 字段。", suggestion="人工确认。")
            ],
            evidence=[
                ExtractionEvidence(field_path="page.size", source="natural_language", quote="A4", confidence=0.9)
            ],
        )
    )

    response = client.get("/api/profile-extractions/extract_completed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["profile_draft"]["id"] == "api_extracted"
    assert payload["uncertain_items"][0]["field_path"] == "page_number.position"
    assert payload["evidence"][0]["quote"] == "A4"


def test_get_profile_extraction_returns_failed_result(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    repository.add_profile_extraction(
        ProfileExtractionRecord(
            extraction_id="extract_failed",
            source_type="natural_language",
            natural_language="A4",
            status="failed",
            error_message="Agent output must be valid JSON or YAML.",
        )
    )

    response = client.get("/api/profile-extractions/extract_failed")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "failed"
    assert payload["error_message"] == "Agent output must be valid JSON or YAML."
