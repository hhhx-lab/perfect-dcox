from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.models import JobRecord
from app.storage.repository import JsonMetadataRepository


class CreateJobRequest(BaseModel):
    input_file_id: str
    job_type: str = "placeholder_format"


def build_jobs_router(repository: JsonMetadataRepository) -> APIRouter:
    router = APIRouter(prefix="/jobs", tags=["jobs"])

    @router.post("", response_model=JobRecord, status_code=status.HTTP_201_CREATED)
    def create_job(payload: CreateJobRequest) -> JobRecord:
        if repository.get_file(payload.input_file_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Input file not found.")

        record = JobRecord(
            job_id=f"job_{uuid4().hex}",
            job_type=payload.job_type,
            input_file_id=payload.input_file_id,
            status="queued",
            progress=0,
            current_step="Waiting for placeholder worker",
        )
        return repository.add_job(record)

    @router.get("/{job_id}", response_model=JobRecord)
    def get_job(job_id: str) -> JobRecord:
        record = repository.get_job(job_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
        return record

    return router
