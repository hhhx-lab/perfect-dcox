from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.formatter import DocumentFormatError, format_docx_with_profile
from app.documents.service import DOCX_MIME, PDF_MIME
from app.models import FileRecord, FixAction, FixLoopRecord, JobRecord
from app.quality.fix_planning import WHITELISTED_ACTIONS
from app.quality.service import QualityReportService
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository


class FixLoopExecutionError(RuntimeError):
    pass


class FixLoopExecutionService:
    def __init__(
        self,
        repository: JsonMetadataRepository,
        storage: LocalFileStorage,
        soffice_bin: str | None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.soffice_bin = soffice_bin

    def execute(self, fix_loop_id: str) -> FixLoopRecord:
        loop = self.repository.get_quality_fix_loop(fix_loop_id)
        if loop is None:
            raise FixLoopExecutionError("Fix loop not found.")
        if loop.status == "completed":
            return loop
        if loop.status not in {"confirmed", "failed"}:
            raise FixLoopExecutionError(f"Fix loop cannot be executed from status: {loop.status}")
        if not loop.selected_actions:
            raise FixLoopExecutionError("Fix loop has no executable selected actions.")

        report = self.repository.get_quality_report(loop.original_report_id)
        if report is None:
            raise FixLoopExecutionError("Original quality report not found.")
        profile = self.repository.get_profile_version(report.profile_id, report.profile_version)
        if profile is None:
            raise FixLoopExecutionError("Profile version not found.")
        source_record = self._select_docx_output(report.output_file_ids)

        self._validate_actions(loop.selected_actions)
        loop.status = "running"
        loop.error_message = None
        self.repository.update_quality_fix_loop(loop)

        job = self.repository.add_job(
            JobRecord(
                job_id=f"job_fix_{uuid4().hex}",
                job_type="quality_fix",
                input_file_id=source_record.file_id,
                profile_id=report.profile_id,
                profile_version=report.profile_version,
                status="running",
                progress=25,
                current_step="Applying selected fix-loop formatting actions",
            )
        )

        try:
            output_records = self._apply_actions(source_record, loop)
            job.status = "completed"
            job.progress = 100
            job.current_step = "Fix-loop formatting completed"
            job.output_file_ids = [record.file_id for record in output_records]
            job.error_message = None
            self.repository.update_job(job)
            updated_report = QualityReportService(self.repository).create_report(
                profile_id=report.profile_id,
                profile_version=report.profile_version,
                output_file_ids=job.output_file_ids,
                job_id=job.job_id,
            )
        except Exception as exc:
            job.status = "failed"
            job.progress = 100
            job.current_step = "Fix-loop formatting failed"
            job.error_message = str(exc)
            self.repository.update_job(job)
            loop.status = "failed"
            loop.new_job_id = job.job_id
            loop.error_message = str(exc)
            return self.repository.update_quality_fix_loop(loop)

        loop.status = "completed"
        loop.new_job_id = job.job_id
        loop.new_output_file_ids = job.output_file_ids
        loop.updated_report_id = updated_report.report_id
        loop.error_message = None
        return self.repository.update_quality_fix_loop(loop)

    def create_and_execute(self, original_report_id: str, selected_actions: list[FixAction]) -> FixLoopRecord:
        report = self.repository.get_quality_report(original_report_id)
        if report is None:
            raise FixLoopExecutionError("Original quality report not found.")
        if not selected_actions:
            raise FixLoopExecutionError("No safe fix-loop actions were selected.")
        self._validate_actions(selected_actions)
        loop = self.repository.add_quality_fix_loop(
            FixLoopRecord(
                fix_loop_id=f"fl_{uuid4().hex}",
                original_report_id=original_report_id,
                fix_plan_id=f"fp_auto_{uuid4().hex}",
                selected_issue_ids=sorted({issue_id for action in selected_actions for issue_id in action.target_issue_ids}),
                selected_actions=selected_actions,
                status="confirmed",
            )
        )
        return self.execute(loop.fix_loop_id)

    def _select_docx_output(self, output_file_ids: list[str]) -> FileRecord:
        for file_id in output_file_ids:
            record = self.repository.get_file(file_id)
            if record and _is_docx(record):
                return record
        raise FixLoopExecutionError("Original quality report has no DOCX output to repair.")

    def _apply_actions(self, source_record: FileRecord, loop: FixLoopRecord) -> list[FileRecord]:
        source_path = Path(source_record.storage_path)
        if not source_path.exists():
            raise FixLoopExecutionError("Original DOCX output is missing from storage.")

        work_dir = self.storage.root / "work" / loop.fix_loop_id
        work_dir.mkdir(parents=True, exist_ok=True)
        fixed_docx = work_dir / f"{Path(source_record.filename).stem}-fixed.docx"

        # Current whitelisted format actions are all safely satisfied by reapplying
        # the selected profile to the DOCX output without changing document content.
        report = self.repository.get_quality_report(loop.original_report_id)
        if report is None:
            raise FixLoopExecutionError("Original quality report not found.")
        profile = self.repository.get_profile_version(report.profile_id, report.profile_version)
        if profile is None:
            raise FixLoopExecutionError("Profile version not found.")
        try:
            format_docx_with_profile(source_path, fixed_docx, profile)
        except DocumentFormatError as exc:
            raise FixLoopExecutionError(str(exc)) from exc

        outputs = [
            self.storage.store_generated_file(
                fixed_docx,
                filename=f"{Path(source_record.filename).stem}-fixed.docx",
                mime_type=DOCX_MIME,
            )
        ]
        if self.soffice_bin:
            try:
                fixed_pdf = export_docx_to_pdf(fixed_docx, work_dir, self.soffice_bin)
            except DocumentExportError as exc:
                raise FixLoopExecutionError(str(exc)) from exc
            outputs.append(
                self.storage.store_generated_file(
                    fixed_pdf,
                    filename=f"{Path(source_record.filename).stem}-fixed.pdf",
                    mime_type=PDF_MIME,
                )
            )
        for record in outputs:
            self.repository.add_file(record)
        return outputs

    def _validate_actions(self, actions: list[FixAction]) -> None:
        unsafe = [action.action for action in actions if action.action not in WHITELISTED_ACTIONS]
        if unsafe:
            raise FixLoopExecutionError(f"Unsafe fix-loop actions rejected: {', '.join(unsafe)}")


def _is_docx(record: FileRecord) -> bool:
    return record.filename.lower().endswith(".docx") or record.mime_type == DOCX_MIME
