from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.service import DocumentFormattingError, DocumentFormattingService
from app.main import create_app
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
