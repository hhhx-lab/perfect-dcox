from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.service import DocumentFormattingError, DocumentFormattingService
from app.jobs.worker import process_next_queued_job, process_placeholder_job
from app.main import create_app
from app.models import JobRecord
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
