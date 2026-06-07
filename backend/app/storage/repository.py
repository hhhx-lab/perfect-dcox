from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.models import FileRecord, JobRecord, ProfileExtractionRecord, utc_now
from app.profiles.models import FormatProfile, ProfileSummary


class DuplicateProfileVersionError(ValueError):
    pass


class JsonMetadataRepository:
    def __init__(self, metadata_path: Path) -> None:
        self.metadata_path = metadata_path
        self._lock = Lock()

    def _empty(self) -> dict[str, dict[str, Any]]:
        return {"files": {}, "jobs": {}, "profiles": {}, "profile_versions": {}, "profile_extractions": {}}

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.metadata_path.exists():
            return self._empty()
        data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return {
            "files": data.get("files", {}),
            "jobs": data.get("jobs", {}),
            "profiles": data.get("profiles", {}),
            "profile_versions": data.get("profile_versions", {}),
            "profile_extractions": data.get("profile_extractions", {}),
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

    def add_profile_extraction(self, record: ProfileExtractionRecord) -> ProfileExtractionRecord:
        with self._lock:
            data = self._load()
            data["profile_extractions"][record.extraction_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def get_profile_extraction(self, extraction_id: str) -> ProfileExtractionRecord | None:
        data = self._load()
        raw = data["profile_extractions"].get(extraction_id)
        return ProfileExtractionRecord.model_validate(raw) if raw else None

    def list_profile_extractions(self) -> list[ProfileExtractionRecord]:
        data = self._load()
        return [ProfileExtractionRecord.model_validate(raw) for raw in data["profile_extractions"].values()]

    def update_profile_extraction(self, record: ProfileExtractionRecord) -> ProfileExtractionRecord:
        record.updated_at = utc_now()
        with self._lock:
            data = self._load()
            data["profile_extractions"][record.extraction_id] = record.model_dump(mode="json")
            self._save(data)
        return record

    def list_profiles(self) -> list[ProfileSummary]:
        data = self._load()
        return [ProfileSummary.model_validate(raw) for raw in data["profiles"].values()]

    def get_profile_summary(self, profile_id: str) -> ProfileSummary | None:
        data = self._load()
        raw = data["profiles"].get(profile_id)
        return ProfileSummary.model_validate(raw) if raw else None

    def get_profile_version(self, profile_id: str, version: str) -> FormatProfile | None:
        data = self._load()
        raw = data["profile_versions"].get(profile_id, {}).get(version)
        return FormatProfile.model_validate(raw["profile"]) if raw else None

    def save_profile_version(self, profile: FormatProfile) -> FormatProfile:
        with self._lock:
            data = self._load()
            versions = data["profile_versions"].setdefault(profile.id, {})
            if profile.version in versions:
                raise DuplicateProfileVersionError(f"Profile {profile.id} version {profile.version} already exists.")

            now = utc_now()
            versions[profile.version] = {
                "profile_id": profile.id,
                "version": profile.version,
                "profile": profile.model_dump(mode="json"),
                "created_at": now.isoformat(),
            }
            data["profiles"][profile.id] = ProfileSummary(
                profile_id=profile.id,
                name=profile.name,
                status=profile.status,
                current_version=profile.version,
                source=profile.source,
                updated_at=now,
            ).model_dump(mode="json")
            self._save(data)
        return profile

    def archive_profile(self, profile_id: str) -> ProfileSummary | None:
        with self._lock:
            data = self._load()
            raw = data["profiles"].get(profile_id)
            if raw is None:
                return None
            raw["status"] = "archived"
            raw["updated_at"] = utc_now().isoformat()
            data["profiles"][profile_id] = raw
            self._save(data)
        return ProfileSummary.model_validate(raw)
