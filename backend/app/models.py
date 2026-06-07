from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.profiles.models import FormatProfile


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
    profile_id: str | None = None
    profile_version: str | None = None
    status: JobStatus = "queued"
    progress: int = 0
    current_step: str | None = None
    output_file_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


ExtractionStatus = Literal["queued", "running", "completed", "failed", "needs_review"]
ExtractionSourceType = Literal["document", "natural_language"]


class ExtractionEvidence(BaseModel):
    field_path: str
    source: ExtractionSourceType
    quote: str | None = None
    note: str | None = None
    confidence: float = Field(ge=0, le=1)


class UncertainItem(BaseModel):
    field_path: str
    message: str
    suggestion: str


class ProfileExtractionRecord(BaseModel):
    extraction_id: str
    source_type: ExtractionSourceType
    file_id: str | None = None
    natural_language: str | None = None
    status: ExtractionStatus = "queued"
    profile_draft: FormatProfile | None = None
    uncertain_items: list[UncertainItem] = Field(default_factory=list)
    evidence: list[ExtractionEvidence] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
