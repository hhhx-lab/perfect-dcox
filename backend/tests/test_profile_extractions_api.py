from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


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
