from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.jobs.worker import process_placeholder_job
from app.llm.diagnostics import LLMConnectivityResult, check_llm_connectivity
from app.llm.openai_compat import ChatCompletionParseError, parse_chat_completion_content
from app.main import create_app
from app.storage.repository import JsonMetadataRepository


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY=None, LLM_MODEL=None, SOFFICE_BIN=None)))


def test_default_cors_origins_include_vite_fallback_ports(tmp_path: Path) -> None:
    settings = Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY=None, LLM_MODEL=None, SOFFICE_BIN=None)

    assert "http://127.0.0.1:5173" in settings.cors_origins
    assert "http://127.0.0.1:5180" in settings.cors_origins
    assert "http://localhost:5199" in settings.cors_origins


def test_health_does_not_require_optional_services(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["services"]["llm_configured"] is False
    assert payload["services"]["llm_status"]["status"] == "not_configured"
    assert payload["services"]["soffice_configured"] is False


def test_health_marks_configured_llm_as_unverified_without_live_check(tmp_path: Path) -> None:
    client = TestClient(
        create_app(Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY="test-key", LLM_MODEL="test-model", SOFFICE_BIN=None))
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["services"]["llm_configured"] is True
    assert payload["services"]["llm_status"]["status"] == "configured_unverified"
    assert payload["services"]["llm_status"]["reachable"] is None


def test_llm_health_endpoint_reports_diagnostic_result(monkeypatch, tmp_path: Path) -> None:
    def fake_check(settings: Settings) -> LLMConnectivityResult:
        return LLMConnectivityResult(
            configured=True,
            reachable=False,
            status="unreachable",
            model=settings.llm_model,
            base_url="https://example.test/v1",
            error_message="HTTP 403 Forbidden",
        )

    monkeypatch.setattr("app.main.check_llm_connectivity", fake_check)
    client = TestClient(
        create_app(Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY="test-key", LLM_MODEL="test-model", SOFFICE_BIN=None))
    )

    response = client.get("/api/health/llm")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unreachable"
    assert payload["reachable"] is False
    assert payload["error_message"] == "HTTP 403 Forbidden"


def test_llm_connectivity_checker_passes_with_chat_completion_payload(tmp_path: Path) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"ok"}}]}'

    def fake_opener(raw_request, timeout: int):
        assert timeout == 3
        assert raw_request.full_url == "https://example.test/v1/chat/completions"
        return FakeResponse()

    result = check_llm_connectivity(
        Settings(
            FILE_STORAGE_ROOT=tmp_path,
            LLM_API_KEY="test-key",
            LLM_MODEL="test-model",
            LLM_BASE_URL="https://example.test/v1",
            LLM_HEALTH_TIMEOUT_SECONDS=3,
        ),
        opener=fake_opener,
    )

    assert result.status == "reachable"
    assert result.reachable is True


def test_parse_chat_completion_content_supports_event_stream() -> None:
    content = parse_chat_completion_content(
        b'data: {"choices":[{"delta":{"content":"{\\"ok\\":"}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"true}"}}]}\n\n'
        b"data: [DONE]\n\n"
    )

    assert content == '{"ok":true}'


def test_parse_chat_completion_content_rejects_empty_event_stream() -> None:
    try:
        parse_chat_completion_content(
            b'data: {"choices":[],"usage":{"completion_tokens":0}}\n\n'
            b"data: [DONE]\n\n"
        )
    except ChatCompletionParseError as error:
        assert "event-stream did not contain assistant content" in str(error)
    else:
        raise AssertionError("Expected empty event-stream to fail.")


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
