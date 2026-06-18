from __future__ import annotations

from app.documents.service import DocumentFormattingError, DocumentFormattingService
from app.models import JobRecord
from app.quality.final_layout_review import FinalLayoutReviewer
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


def process_placeholder_job(
    repository: JsonMetadataRepository,
    job_id: str,
    storage: LocalFileStorage | None = None,
    soffice_bin: str | None = None,
    final_layout_reviewer: FinalLayoutReviewer | None = None,
) -> JobRecord:
    record = repository.get_job(job_id)
    if record is None:
        raise ValueError(f"Job not found: {job_id}")

    record.status = "running"
    record.progress = 50
    record.current_step = "Running document export pipeline"
    record.error_message = None
    record.delivery_gate_summary = {}
    repository.update_job(record)

    if record.profile_id and record.profile_version:
        if storage is None:
            record.status = "failed"
            record.progress = 100
            record.current_step = "Document storage unavailable"
            record.error_message = "Document formatting requires local file storage."
            return repository.update_job(record)
        try:
            record.current_step = "Compiling DOCX and running internal delivery gate"
            repository.update_job(record)
            service = DocumentFormattingService(repository, storage, soffice_bin, final_layout_reviewer=final_layout_reviewer)
            outputs = service.format_job(
                record.input_file_id,
                record.profile_id,
                record.profile_version,
                include_pdf="pdf" in record.output_formats,
                template_file_id=record.template_file_id,
            )
        except DocumentFormattingError as exc:
            message = str(exc)
            if "delivery gate" in message.lower() or "internal qc" in message.lower():
                record.status = "quality_failed"
            elif "pdf" in message.lower() or "soffice" in message.lower():
                record.status = "export_failed"
            else:
                record.status = "failed"
            record.progress = 100
            record.current_step = "Document export pipeline failed"
            record.error_message = message
            return repository.update_job(record)

        record.status = "completed"
        record.progress = 100
        record.current_step = "Final DOCX/PDF delivery completed"
        record.output_file_ids = [output.file_id for output in outputs]
        record.delivery_gate_summary = getattr(service, "last_delivery_gate_summary", {})
        record.error_message = None
        return repository.update_job(record)

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


def process_next_queued_job(
    repository: JsonMetadataRepository,
    storage: LocalFileStorage | None = None,
    soffice_bin: str | None = None,
    final_layout_reviewer: FinalLayoutReviewer | None = None,
) -> JobRecord | None:
    for record in repository.list_jobs():
        if record.status == "queued":
            return process_placeholder_job(
                repository,
                record.job_id,
                storage=storage,
                soffice_bin=soffice_bin,
                final_layout_reviewer=final_layout_reviewer,
            )
    return None
