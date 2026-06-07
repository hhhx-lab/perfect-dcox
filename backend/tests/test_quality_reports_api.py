from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.formatter import format_docx_with_profile
from app.main import create_app
from app.profiles.seed import load_builtin_profiles
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_minimal_thesis_docx


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path)))


def add_formatted_docx_output(tmp_path: Path) -> str:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    profile = load_builtin_profiles()["ecnu_thesis"]
    source = create_minimal_thesis_docx(tmp_path / "source.docx")
    formatted = format_docx_with_profile(source, tmp_path / "formatted.docx", profile)
    record = storage.store_generated_file(
        formatted,
        filename="formatted.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(record)
    return record.file_id


def test_create_and_get_quality_report_for_formatted_output(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    file_id = add_formatted_docx_output(tmp_path)

    created = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": [file_id],
            "job_id": "job_quality",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["report_id"].startswith("qr_")
    assert payload["job_id"] == "job_quality"
    assert payload["summary"]["counts"]["pass"] >= 6
    assert payload["summary"]["counts"]["unsupported"] >= 1
    assert payload["summary"]["all_compliant"] is False
    assert payload["issues_by_status"]["unsupported"][0]["check_key"] == "docx.page_number"

    loaded = client.get(f"/api/quality-reports/{payload['report_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["report_id"] == payload["report_id"]


def test_create_quality_report_rejects_missing_output_or_profile(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    missing_output = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": ["file_missing"],
        },
    )
    missing_profile = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "missing",
            "profile_version": "1.0.0",
            "output_file_ids": ["file_missing"],
        },
    )

    assert missing_output.status_code == 400
    assert missing_profile.status_code == 400
