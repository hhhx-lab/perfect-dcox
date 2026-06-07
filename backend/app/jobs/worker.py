from __future__ import annotations

from app.models import JobRecord
from app.storage.repository import JsonMetadataRepository


def process_placeholder_job(repository: JsonMetadataRepository, job_id: str) -> JobRecord:
    record = repository.get_job(job_id)
    if record is None:
        raise ValueError(f"Job not found: {job_id}")

    record.status = "running"
    record.progress = 50
    record.current_step = "Running placeholder format job"
    record.error_message = None
    repository.update_job(record)

    if repository.get_file(record.input_file_id) is None:
        record.status = "failed"
        record.progress = 100
        record.current_step = "Input file missing"
        record.error_message = "Input file is no longer available."
        return repository.update_job(record)

    record.status = "completed"
    record.progress = 100
    record.current_step = "Placeholder format job completed"
    record.error_message = None
    return repository.update_job(record)


def process_next_queued_job(repository: JsonMetadataRepository) -> JobRecord | None:
    for record in repository.list_jobs():
        if record.status == "queued":
            return process_placeholder_job(repository, record.job_id)
    return None
