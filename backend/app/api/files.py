from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.models import FileRecord
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository

SUPPORTED_WORD_EXTENSIONS = {".doc", ".docx"}


def build_files_router(
    repository: JsonMetadataRepository,
    file_storage: LocalFileStorage,
) -> APIRouter:
    router = APIRouter(prefix="/files", tags=["files"])

    @router.post("", response_model=FileRecord, status_code=status.HTTP_201_CREATED)
    async def upload_file(file: UploadFile) -> FileRecord:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_WORD_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .doc and .docx files are supported.",
            )

        content = await file.read()
        file_id, stored_path, digest, size = file_storage.store_bytes(file.filename or "document", content)
        record = FileRecord(
            file_id=file_id,
            filename=file.filename or "document",
            mime_type=file.content_type or "application/octet-stream",
            size=size,
            sha256=digest,
            storage_path=str(stored_path),
        )
        return repository.add_file(record)

    @router.get("/{file_id}", response_model=FileRecord)
    def get_file(file_id: str) -> FileRecord:
        record = repository.get_file(file_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
        return record

    @router.get("/{file_id}/download")
    def download_file(file_id: str) -> FileResponse:
        record = repository.get_file(file_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

        stored_path = Path(record.storage_path)
        if not stored_path.exists() or not stored_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found.")

        return FileResponse(
            stored_path,
            media_type=record.mime_type,
            filename=record.filename,
        )

    return router
