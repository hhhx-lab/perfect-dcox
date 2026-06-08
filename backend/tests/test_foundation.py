from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.jobs.worker import process_placeholder_job
from app.main import create_app
from app.storage.repository import JsonMetadataRepository


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY=None, LLM_MODEL=None, SOFFICE_BIN=None)))


def test_health_does_not_require_optional_services(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["llm_configured"] is False
    assert payload["services"]["soffice_configured"] is False


def test_upload_docx_and_retrieve_metadata(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/files",
        files={
            "file": (
                "sample.docx",
                b"word bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["file_id"].startswith("file_")
    assert payload["filename"] == "sample.docx"
    assert payload["size"] == len(b"word bytes")
    assert len(payload["sha256"]) == 64
    assert Path(payload["storage_path"]).exists()

    loaded = client.get(f"/api/files/{payload['file_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["sha256"] == payload["sha256"]

    downloaded = client.get(f"/api/files/{payload['file_id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == b"word bytes"
    assert downloaded.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "sample.docx" in downloaded.headers["content-disposition"]


def test_upload_legacy_doc_and_reject_unsupported_file(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    legacy = client.post("/api/files", files={"file": ("legacy.doc", b"legacy", "application/msword")})
    rejected = client.post("/api/files", files={"file": ("notes.txt", b"nope", "text/plain")})

    assert legacy.status_code == 201
    assert rejected.status_code == 400
    assert client.get("/api/files/file_missing").status_code == 404
    assert client.get("/api/files/file_missing/download").status_code == 404


def test_create_job_and_retrieve_status(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    uploaded = client.post("/api/files", files={"file": ("sample.docx", b"doc", "application/docx")})
    file_id = uploaded.json()["file_id"]

    created = client.post("/api/jobs", json={"input_file_id": file_id})

    assert created.status_code == 201
    payload = created.json()
    assert payload["job_id"].startswith("job_")
    assert payload["status"] == "queued"
    loaded = client.get(f"/api/jobs/{payload['job_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["input_file_id"] == file_id
    assert client.post("/api/jobs", json={"input_file_id": "file_missing"}).status_code == 404
    assert client.get("/api/jobs/job_missing").status_code == 404


def test_placeholder_worker_completes_or_fails(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    uploaded = client.post("/api/files", files={"file": ("sample.docx", b"doc", "application/docx")})
    file_id = uploaded.json()["file_id"]
    job = client.post("/api/jobs", json={"input_file_id": file_id}).json()
    repository = JsonMetadataRepository(tmp_path / "metadata.json")

    completed = process_placeholder_job(repository, job["job_id"])
    assert completed.status == "completed"
    assert completed.progress == 100

    failing_job = client.post("/api/jobs", json={"input_file_id": file_id}).json()
    data = repository._load()
    data["files"].pop(file_id)
    repository._save(data)

    failed = process_placeholder_job(repository, failing_job["job_id"])
    assert failed.status == "failed"
    assert failed.error_message
