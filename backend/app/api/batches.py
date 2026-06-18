from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.jobs.worker import process_placeholder_job
from app.models import BatchFormatRun, DeliveryManifestItem, JobRecord
from app.quality.final_layout_review import FinalLayoutReviewer
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


class CreateBatchRequest(BaseModel):
    profile_id: str
    profile_version: str
    template_file_id: str | None = None
    input_file_ids: list[str] = Field(min_length=1)
    output_formats: list[str] = Field(default_factory=lambda: ["docx"])
    auto_quality: bool = True
    auto_fix: bool = True


def build_batches_router(
    repository: JsonMetadataRepository,
    file_storage: LocalFileStorage,
    soffice_bin: str | None = None,
    final_layout_reviewer: FinalLayoutReviewer | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/batches", tags=["batches"])

    @router.post("", response_model=BatchFormatRun, status_code=status.HTTP_201_CREATED)
    def create_batch(payload: CreateBatchRequest) -> BatchFormatRun:
        if repository.get_profile_version(payload.profile_id, payload.profile_version) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile version not found.")
        if payload.template_file_id and repository.get_file(payload.template_file_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template file not found.")
        missing = [file_id for file_id in payload.input_file_ids if repository.get_file(file_id) is None]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input files not found: {', '.join(missing)}",
            )
        if any(fmt not in {"docx", "pdf"} for fmt in payload.output_formats):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="output_formats supports docx and pdf only.")

        batch = repository.add_batch_format_run(
            BatchFormatRun(
                batch_id=f"batch_{uuid4().hex}",
                profile_id=payload.profile_id,
                profile_version=payload.profile_version,
                template_file_id=payload.template_file_id,
                output_formats=payload.output_formats,
                input_file_ids=payload.input_file_ids,
                status="running",
            )
        )

        items: list[DeliveryManifestItem] = []
        job_ids: list[str] = []
        failures: list[str] = []
        for file_id in payload.input_file_ids:
            job = repository.add_job(
                JobRecord(
                    job_id=f"job_{uuid4().hex}",
                    job_type="batch_format",
                    input_file_id=file_id,
                    profile_id=payload.profile_id,
                    profile_version=payload.profile_version,
                    template_file_id=payload.template_file_id,
                    output_formats=payload.output_formats,
                    status="queued",
                    progress=0,
                    current_step="Waiting for batch document formatter",
                )
            )
            completed = process_placeholder_job(
                repository,
                job.job_id,
                storage=file_storage,
                soffice_bin=soffice_bin,
                final_layout_reviewer=final_layout_reviewer,
            )
            job_ids.append(completed.job_id)
            item = _delivery_item_for_job(completed, repository)
            items.append(item)
            if item.delivery_status == "failed":
                failures.append(completed.job_id)

        batch.job_ids = job_ids
        batch.items = items
        if failures and len(failures) == len(items):
            batch.status = "failed"
            batch.error_message = f"All batch jobs failed: {', '.join(failures)}"
        elif failures:
            batch.status = "partially_completed"
            batch.error_message = f"Some batch jobs failed: {', '.join(failures)}"
        elif any(item.delivery_status == "manual_review_required" for item in items):
            batch.status = "quality_failed"
        else:
            batch.status = "completed"
        batch.delivery_manifest_id = f"manifest_{batch.batch_id}"
        batch.manifest_download_url = f"/api/batches/{batch.batch_id}/manifest"
        _write_manifest(file_storage, batch)
        return repository.update_batch_format_run(batch)

    @router.get("/{batch_id}", response_model=BatchFormatRun)
    def get_batch(batch_id: str) -> BatchFormatRun:
        batch = repository.get_batch_format_run(batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
        return batch

    @router.get("/{batch_id}/manifest")
    def download_batch_manifest(batch_id: str):
        from fastapi.responses import FileResponse

        batch = repository.get_batch_format_run(batch_id)
        if batch is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
        manifest_path = file_storage.manifests_dir / f"{batch.batch_id}.json"
        if not manifest_path.exists():
            _write_manifest(file_storage, batch)
        return FileResponse(
            manifest_path,
            media_type="application/json",
            filename=f"{batch.batch_id}-delivery-manifest.json",
        )

    return router


def _delivery_item_for_job(
    job: JobRecord,
    repository: JsonMetadataRepository,
) -> DeliveryManifestItem:
    docx_id = _first_output(job.output_file_ids, repository, ".docx")
    pdf_id = _first_output(job.output_file_ids, repository, ".pdf")
    delivery_status: str = "completed"
    failure_reason = job.error_message
    if job.status in {"failed", "export_failed"}:
        delivery_status = "failed"
    elif job.status == "quality_failed":
        delivery_status = "manual_review_required"
    elif job.status != "completed" or docx_id is None:
        delivery_status = "failed"
        failure_reason = failure_reason or "Final DOCX output was not produced."
    return DeliveryManifestItem(
        input_file_id=job.input_file_id,
        job_id=job.job_id,
        final_docx_file_id=docx_id,
        final_pdf_file_id=pdf_id,
        quality_report_id=None,
        fix_loop_ids=[],
        download_urls=_download_urls(docx_id, pdf_id),
        delivery_status=delivery_status,  # type: ignore[arg-type]
        failure_reason=failure_reason,
        delivery_gate_summary=job.delivery_gate_summary,
    )


def _first_output(output_file_ids: list[str], repository: JsonMetadataRepository, suffix: str) -> str | None:
    for file_id in output_file_ids:
        record = repository.get_file(file_id)
        if record and record.filename.lower().endswith(suffix):
            return file_id
    return None


def _download_urls(docx_id: str | None, pdf_id: str | None) -> dict[str, str]:
    urls: dict[str, str] = {}
    if docx_id:
        urls["docx"] = f"/api/files/{docx_id}/download"
    if pdf_id:
        urls["pdf"] = f"/api/files/{pdf_id}/download"
    return urls


def _write_manifest(file_storage: LocalFileStorage, batch: BatchFormatRun) -> None:
    file_storage.ensure_ready()
    manifest_path = file_storage.manifests_dir / f"{batch.batch_id}.json"
    manifest_path.write_text(
        json.dumps(batch.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
