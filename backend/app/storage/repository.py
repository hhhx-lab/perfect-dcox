from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.models import FileRecord, JobRecord, utc_now


class JsonMetadataRepository:
    def __init__(self, metadata_path: Path) -> None:
        self.metadata_path = metadata_path
        self._lock = Lock()

    def _empty(self) -> dict[str, dict[str, Any]]:
        return {"files": {}, "jobs": {}}

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.metadata_path.exists():
            return self._empty()
        data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return {
            "files": data.get("files", {}),
            "jobs": data.get("jobs", {}),
        }

    def _save(self, data: dict[str, dict[str, Any]]) -> None:
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.metadata_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.metadata_path)

    def add_file(self, record: FileRecord) -> FileRecord:
        with self._lock:
            data = self._load()
            data["files"][record.file_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def get_file(self, file_id: str) -> FileRecord | None:
        data = self._load()
        raw = data["files"].get(file_id)
        return FileRecord.model_validate(raw) if raw else None

    def list_files(self) -> list[FileRecord]:
        data = self._load()
        return [FileRecord.model_validate(raw) for raw in data["files"].values()]

    def add_job(self, record: JobRecord) -> JobRecord:
        with self._lock:
            data = self._load()
            data["jobs"][record.job_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def get_job(self, job_id: str) -> JobRecord | None:
        data = self._load()
        raw = data["jobs"].get(job_id)
        return JobRecord.model_validate(raw) if raw else None

    def list_jobs(self) -> list[JobRecord]:
        data = self._load()
        return [JobRecord.model_validate(raw) for raw in data["jobs"].values()]

    def update_job(self, record: JobRecord) -> JobRecord:
        record.updated_at = utc_now()
        with self._lock:
            data = self._load()
            data["jobs"][record.job_id] = record.model_dump(mode="json")
            self._save(data)
        return record
