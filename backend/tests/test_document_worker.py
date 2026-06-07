from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


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
