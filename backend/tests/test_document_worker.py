from pathlib import Path

from docx import Document
from docx.shared import Cm
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.service import DocumentFormattingError, DocumentFormattingService
from app.jobs.worker import process_next_queued_job, process_placeholder_job
from app.main import create_app
from app.models import FileRecord, JobRecord
from app.profiles.seed import load_builtin_profiles
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_minimal_thesis_docx


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path)))


def test_register_generated_output_file_metadata(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = tmp_path / "formatted.docx"
    source.write_bytes(b"formatted-docx")

    record = storage.store_generated_file(
        source,
        filename="formatted.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(record)

    loaded = repository.get_file(record.file_id)
    assert loaded is not None
    assert loaded.filename == "formatted.docx"
    assert loaded.size == len(b"formatted-docx")
    assert Path(loaded.storage_path).exists()

    client = build_client(tmp_path)
    response = client.get(f"/api/files/{record.file_id}")
    assert response.status_code == 200
    assert response.json()["filename"] == "formatted.docx"


def test_formatting_service_creates_docx_output_record(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    repository.save_profile_version(load_builtin_profiles()["ecnu_thesis"])
    service = DocumentFormattingService(repository, storage, soffice_bin=None)

    outputs = service.format_job(input_record.file_id, "ecnu_thesis", "1.0.0")

    assert len(outputs) == 1
    assert outputs[0].filename.endswith(".docx")
    assert repository.get_file(outputs[0].file_id) is not None


def test_formatting_service_pdf_export_failure_is_diagnostic(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    repository.save_profile_version(load_builtin_profiles()["ecnu_thesis"])
    service = DocumentFormattingService(repository, storage, soffice_bin=None)

    try:
        service.format_job(input_record.file_id, "ecnu_thesis", "1.0.0", include_pdf=True)
    except DocumentFormattingError as error:
        assert "SOFFICE_BIN" in str(error)
    else:
        raise AssertionError("Expected PDF export failure when SOFFICE_BIN is missing.")


def test_worker_runs_document_engine_for_profile_referenced_job(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    repository.save_profile_version(load_builtin_profiles()["ecnu_thesis"])
    job = repository.add_job(
        JobRecord(
            job_id="job_profiled",
            job_type="placeholder_format",
            input_file_id=input_record.file_id,
            profile_id="ecnu_thesis",
            profile_version="1.0.0",
        )
    )

    completed = process_placeholder_job(repository, job.job_id, storage=storage, soffice_bin=None)

    assert completed.status == "completed"
    assert completed.progress == 100
    assert completed.output_file_ids
    assert repository.get_file(completed.output_file_ids[0]) is not None


def test_profiled_job_api_runs_document_engine_immediately(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")

    uploaded = client.post(
        "/api/files",
        files={
            "file": (
                "input.docx",
                source.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
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
    assert payload["status"] == "completed"
    assert payload["progress"] == 100
    assert payload["output_file_ids"]
    output = client.get(f"/api/files/{payload['output_file_ids'][0]}")
    assert output.status_code == 200
    assert output.json()["filename"].endswith("-formatted.docx")


def test_batch_api_processes_multiple_profiled_documents_with_delivery_manifest(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    source_a = create_minimal_thesis_docx(tmp_path / "input-a.docx")
    source_b = create_minimal_thesis_docx(tmp_path / "input-b.docx")
    uploaded_ids: list[str] = []
    for path in (source_a, source_b):
        response = client.post(
            "/api/files",
            files={
                "file": (
                    path.name,
                    path.read_bytes(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert response.status_code == 201
        uploaded_ids.append(response.json()["file_id"])

    created = client.post(
        "/api/batches",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "input_file_ids": uploaded_ids,
            "output_formats": ["docx", "pdf"],
            "auto_quality": True,
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["batch_id"].startswith("batch_")
    assert payload["status"] == "completed"
    assert payload["delivery_manifest_id"].startswith("manifest_")
    assert payload["manifest_download_url"].endswith(f"/api/batches/{payload['batch_id']}/manifest")
    assert len(payload["job_ids"]) == 2
    assert len(payload["items"]) == 2
    for item in payload["items"]:
        assert item["input_file_id"] in uploaded_ids
        assert item["job_id"].startswith("job_")
        assert item["final_docx_file_id"].startswith("file_")
        assert item["final_pdf_file_id"].startswith("file_")
        assert item["quality_report_id"].startswith("qr_")
        assert item["delivery_status"] == "completed"
        assert item["download_urls"]["docx"].endswith(f"/api/files/{item['final_docx_file_id']}/download")
        assert item["download_urls"]["pdf"].endswith(f"/api/files/{item['final_pdf_file_id']}/download")

    loaded = client.get(f"/api/batches/{payload['batch_id']}")
    assert loaded.status_code == 200
    assert loaded.json() == payload
    manifest = client.get(f"/api/batches/{payload['batch_id']}/manifest")
    assert manifest.status_code == 200
    assert manifest.json()["batch_id"] == payload["batch_id"]


def test_batch_api_auto_fix_retries_safe_quality_issues(tmp_path: Path, monkeypatch) -> None:
    client = build_client(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "broken-margin.docx")
    uploaded = client.post(
        "/api/files",
        files={
            "file": (
                source.name,
                source.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201

    def fake_process_placeholder_job(repository, job_id, storage=None, soffice_bin=None):
        job = repository.get_job(job_id)
        assert job is not None
        assert storage is not None
        broken_doc = Document(source)
        broken_doc.sections[0].top_margin = Cm(1.0)
        broken_output = tmp_path / "worker-broken-output.docx"
        broken_doc.save(broken_output)
        record = storage.store_generated_file(
            broken_output,
            filename="worker-broken-output.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        repository.add_file(record)
        job.status = "completed"
        job.progress = 100
        job.current_step = "Fake worker produced an output that still needs safe repair"
        job.output_file_ids = [record.file_id]
        return repository.update_job(job)

    monkeypatch.setattr("app.api.batches.process_placeholder_job", fake_process_placeholder_job)

    created = client.post(
        "/api/batches",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "input_file_ids": [uploaded.json()["file_id"]],
            "output_formats": ["docx"],
            "auto_quality": True,
            "auto_fix": True,
        },
    )

    assert created.status_code == 201
    payload = created.json()
    item = payload["items"][0]
    assert payload["status"] == "completed"
    assert item["delivery_status"] == "completed"
    assert item["fix_loop_ids"]
    report = client.get(f"/api/quality-reports/{item['quality_report_id']}").json()
    assert report["summary"]["all_compliant"] is True
    output_meta = client.get(f"/api/files/{item['final_docx_file_id']}").json()
    fixed_doc = Document(output_meta["storage_path"])
    assert round(fixed_doc.sections[0].top_margin.cm, 1) == 2.5


def test_worker_requests_pdf_output_when_soffice_is_configured(tmp_path: Path, monkeypatch) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    job = repository.add_job(
        JobRecord(
            job_id="job_pdf",
            job_type="placeholder_format",
            input_file_id=input_record.file_id,
            profile_id="ecnu_thesis",
            profile_version="1.0.0",
        )
    )
    captured: dict[str, bool] = {}

    class FakeDocumentFormattingService:
        def __init__(self, repository, storage, soffice_bin) -> None:
            self.soffice_bin = soffice_bin

        def format_job(self, input_file_id, profile_id, profile_version, include_pdf=False):
            captured["include_pdf"] = include_pdf
            return [
                FileRecord(
                    file_id="file_docx",
                    filename="input-formatted.docx",
                    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    size=1,
                    sha256="0" * 64,
                    storage_path=str(tmp_path / "input-formatted.docx"),
                ),
                FileRecord(
                    file_id="file_pdf",
                    filename="input-formatted.pdf",
                    mime_type="application/pdf",
                    size=1,
                    sha256="1" * 64,
                    storage_path=str(tmp_path / "input-formatted.pdf"),
                ),
            ]

    monkeypatch.setattr("app.jobs.worker.DocumentFormattingService", FakeDocumentFormattingService)

    completed = process_placeholder_job(repository, job.job_id, storage=storage, soffice_bin="/usr/bin/soffice")

    assert captured["include_pdf"] is True
    assert completed.status == "completed"
    assert completed.output_file_ids == ["file_docx", "file_pdf"]


def test_worker_reports_formatting_failure(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    repository.save_profile_version(load_builtin_profiles()["ecnu_thesis"])
    job = repository.add_job(
        JobRecord(
            job_id="job_missing_input",
            job_type="placeholder_format",
            input_file_id="file_missing",
            profile_id="ecnu_thesis",
            profile_version="1.0.0",
        )
    )

    failed = process_placeholder_job(repository, job.job_id, storage=storage, soffice_bin=None)

    assert failed.status == "failed"
    assert failed.progress == 100
    assert "Input file" in (failed.error_message or "")


def test_next_queued_job_processes_profiled_formatting_job(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    repository.save_profile_version(load_builtin_profiles()["ecnu_thesis"])
    repository.add_job(
        JobRecord(
            job_id="job_next",
            job_type="placeholder_format",
            input_file_id=input_record.file_id,
            profile_id="ecnu_thesis",
            profile_version="1.0.0",
        )
    )

    completed = process_next_queued_job(repository, storage=storage, soffice_bin=None)

    assert completed is not None
    assert completed.status == "completed"
    assert completed.output_file_ids


def test_worker_reports_missing_profile_version(tmp_path: Path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    input_record = storage.store_generated_file(
        source,
        filename="input.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(input_record)
    job = repository.add_job(
        JobRecord(
            job_id="job_missing_profile",
            job_type="placeholder_format",
            input_file_id=input_record.file_id,
            profile_id="missing",
            profile_version="1.0.0",
        )
    )

    failed = process_placeholder_job(repository, job.job_id, storage=storage, soffice_bin=None)

    assert failed.status == "failed"
    assert "Profile version not found" in (failed.error_message or "")
