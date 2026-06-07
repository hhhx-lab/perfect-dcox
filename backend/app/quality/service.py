from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.models import FileRecord, QualityIssue, QualityReport, QualitySummary
from app.profiles.models import FormatProfile
from app.quality.inspection import inspect_docx_quality, inspect_pdf_quality
from app.storage.repository import JsonMetadataRepository


class QualityReportError(RuntimeError):
    pass


class QualityReportService:
    def __init__(self, repository: JsonMetadataRepository) -> None:
        self.repository = repository

    def create_report(
        self,
        profile_id: str,
        profile_version: str,
        output_file_ids: list[str],
        job_id: str | None = None,
    ) -> QualityReport:
        profile = self.repository.get_profile_version(profile_id, profile_version)
        if profile is None:
            raise QualityReportError("Profile version not found.")
        if not output_file_ids:
            raise QualityReportError("At least one output file is required.")

        issues: list[QualityIssue] = []
        for file_id in output_file_ids:
            record = self.repository.get_file(file_id)
            if record is None:
                raise QualityReportError(f"Output file not found: {file_id}")
            issues.extend(_inspect_output_file(record, profile))

        report = QualityReport(
            report_id=f"qr_{uuid4().hex}",
            job_id=job_id,
            profile_id=profile_id,
            profile_version=profile_version,
            output_file_ids=output_file_ids,
            summary=QualitySummary.from_issues(issues),
            issues=issues,
        )
        return self.repository.add_quality_report(report)


def _inspect_output_file(record: FileRecord, profile: FormatProfile) -> list[QualityIssue]:
    path = Path(record.storage_path)
    lower_name = record.filename.lower()
    if lower_name.endswith(".docx") or record.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return inspect_docx_quality(path, profile)
    if lower_name.endswith(".pdf") or record.mime_type == "application/pdf":
        return inspect_pdf_quality(path)
    return [
        QualityIssue(
            issue_id=f"unsupported_output_{record.file_id}",
            status="unsupported",
            check_key="output.unsupported_type",
            title="Output file type is not supported by quality inspection.",
            description=f"{record.filename} ({record.mime_type})",
            location=record.file_id,
            recommendation="Inspect DOCX and PDF outputs, or add a checker for this file type.",
        )
    ]
