from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.jobs.worker import process_placeholder_job
from app.models import JobRecord
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


class CreateJobRequest(BaseModel):
    input_file_id: str
    job_type: str = "placeholder_format"
    profile_id: str | None = None
    profile_version: str | None = None


def build_jobs_router(
    repository: JsonMetadataRepository,
    file_storage: LocalFileStorage | None = None,
    soffice_bin: str | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/jobs", tags=["jobs"])

    @router.post("", response_model=JobRecord, status_code=status.HTTP_201_CREATED)
    def create_job(payload: CreateJobRequest) -> JobRecord:
        if repository.get_file(payload.input_file_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Input file not found.")
        if bool(payload.profile_id) != bool(payload.profile_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="profile_id and profile_version must be provided together.",
            )
        if payload.profile_id and payload.profile_version:
            profile = repository.get_profile_version(payload.profile_id, payload.profile_version)
            if profile is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile version not found.")

        record = repository.add_job(
            JobRecord(
                job_id=f"job_{uuid4().hex}",
                job_type=payload.job_type,
                input_file_id=payload.input_file_id,
                profile_id=payload.profile_id,
                profile_version=payload.profile_version,
                status="queued",
                progress=0,
                current_step="Waiting for document formatter",
            )
        )
        if record.profile_id and record.profile_version:
            return process_placeholder_job(
                repository,
                record.job_id,
                storage=file_storage,
                soffice_bin=soffice_bin,
            )
        return record

    @router.get("/{job_id}", response_model=JobRecord)
    def get_job(job_id: str) -> JobRecord:
        record = repository.get_job(job_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return record

    return router
