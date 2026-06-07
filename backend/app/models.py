from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FileRecord(BaseModel):
    file_id: str
    filename: str
    mime_type: str
    size: int
    sha256: str
    storage_path: str
    created_at: datetime = Field(default_factory=utc_now)


JobStatus = Literal["queued", "running", "completed", "failed"]


class JobRecord(BaseModel):
    job_id: str
    job_type: str
    input_file_id: str
    status: JobStatus = "queued"
    progress: int = 0
    current_step: str | None = None
    output_file_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
