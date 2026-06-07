from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.profiles.models import FormatProfile
from app.profiles.seed import profile_to_yaml
from tests.test_profiles import valid_profile_payload


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path)))


def test_profile_list_and_detail_include_builtin_ecnu(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    listed = client.get("/api/profiles")
    assert listed.status_code == 200
    profiles = listed.json()
    assert profiles[0]["profile_id"] == "ecnu_thesis"
    assert profiles[0]["status"] == "active"
    assert profiles[0]["current_version"] == "1.0.0"
    assert profiles[0]["source"] == "system"

    detail = client.get("/api/profiles/ecnu_thesis/versions/1.0.0")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["id"] == "ecnu_thesis"
    assert payload["page"]["margins_cm"]["left"] == 3.0
    assert client.get("/api/profiles/missing/versions/1.0.0").status_code == 404


def test_save_new_profile_version_and_reject_duplicate(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    payload = valid_profile_payload()

    created = client.post("/api/profiles", json=payload)
    assert created.status_code == 201
    assert created.json()["id"] == "sample_thesis"

    duplicate = client.post("/api/profiles", json=payload)
    assert duplicate.status_code == 409

    payload["version"] = "1.0.1"
    payload["name"] = "Sample Thesis Updated"
    saved = client.post("/api/profiles/sample_thesis/versions", json=payload)
    assert saved.status_code == 201

    mismatched = client.post("/api/profiles/other_profile/versions", json=payload)
    assert mismatched.status_code == 400

    listed = client.get("/api/profiles").json()
    sample = next(item for item in listed if item["profile_id"] == "sample_thesis")
    assert sample["current_version"] == "1.0.1"
    assert sample["name"] == "Sample Thesis Updated"
    assert client.get("/api/profiles/sample_thesis/versions/1.0.0").status_code == 200


def test_profile_yaml_import_export_and_invalid_import(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    payload = valid_profile_payload()
    yaml_text = profile_to_yaml(FormatProfile.model_validate(payload))

    imported = client.post("/api/profiles/import", content=yaml_text, headers={"Content-Type": "text/plain"})
    assert imported.status_code == 201
    assert imported.json()["id"] == "sample_thesis"

    exported = client.get("/api/profiles/sample_thesis/versions/1.0.0/export")
    assert exported.status_code == 200
    assert "sample_thesis" in exported.text

    invalid = client.post("/api/profiles/import", content="id: broken\n", headers={"Content-Type": "text/plain"})
    assert invalid.status_code == 422
    assert client.get("/api/profiles/broken/versions/1.0.0").status_code == 404


def test_archive_profile_keeps_versions_available(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    archived = client.post("/api/profiles/ecnu_thesis/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"

    detail = client.get("/api/profiles/ecnu_thesis/versions/1.0.0")
    assert detail.status_code == 200
    assert detail.json()["id"] == "ecnu_thesis"


def test_create_job_with_profile_reference_and_reject_missing_reference(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    uploaded = client.post("/api/files", files={"file": ("sample.docx", b"doc", "application/docx")})
    file_id = uploaded.json()["file_id"]

    created = client.post(
        "/api/jobs",
        json={
            "input_file_id": file_id,
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["profile_id"] == "ecnu_thesis"
    assert payload["profile_version"] == "1.0.0"

    unprofiled = client.post("/api/jobs", json={"input_file_id": file_id})
    assert unprofiled.status_code == 201
    assert unprofiled.json()["profile_id"] is None
    assert unprofiled.json()["profile_version"] is None

    missing = client.post(
        "/api/jobs",
        json={
            "input_file_id": file_id,
            "profile_id": "missing",
            "profile_version": "1.0.0",
        },
    )
    assert missing.status_code == 404

    partial = client.post("/api/jobs", json={"input_file_id": file_id, "profile_id": "ecnu_thesis"})
    assert partial.status_code == 400
