from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models import QualityReport
from app.quality.service import QualityReportError, QualityReportService


class CreateQualityReportRequest(BaseModel):
    profile_id: str
    profile_version: str
    output_file_ids: list[str] = Field(min_length=1)
    job_id: str | None = None


def build_quality_reports_router(
    report_service: QualityReportService,
) -> APIRouter:
    router = APIRouter(prefix="/quality-reports", tags=["quality-reports"])

    @router.post("", response_model=QualityReport, status_code=status.HTTP_201_CREATED)
    def create_quality_report(payload: CreateQualityReportRequest) -> QualityReport:
        try:
            return report_service.create_report(
                profile_id=payload.profile_id,
                profile_version=payload.profile_version,
                output_file_ids=payload.output_file_ids,
                job_id=payload.job_id,
            )
        except QualityReportError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @router.get("/{report_id}", response_model=QualityReport)
    def get_quality_report(report_id: str) -> QualityReport:
        report = report_service.repository.get_quality_report(report_id)
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality report not found.")
        return report

    return router
