from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models import FixLoopRecord, FixPlan, QualityReport
from app.quality.fix_planning import FixPlanSafetyError, FixPlanService, validate_fix_plan
from app.quality.service import QualityReportError, QualityReportService


class CreateQualityReportRequest(BaseModel):
    profile_id: str
    profile_version: str
    output_file_ids: list[str] = Field(min_length=1)
    job_id: str | None = None


class ConfirmFixLoopRequest(BaseModel):
    fix_plan_id: str
    selected_issue_ids: list[str] = Field(min_length=1)


def build_quality_reports_router(
    report_service: QualityReportService,
    fix_plan_service: FixPlanService | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/quality-reports", tags=["quality-reports"])
    planner = fix_plan_service or FixPlanService()

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

    @router.post("/{report_id}/fix-plan", response_model=FixPlan, status_code=status.HTTP_201_CREATED)
    def create_fix_plan(report_id: str) -> FixPlan:
        report = report_service.repository.get_quality_report(report_id)
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality report not found.")
        plan = planner.create_fix_plan(report)
        try:
            return validate_fix_plan(plan, {issue.issue_id for issue in report.issues})
        except FixPlanSafetyError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    @router.post("/{report_id}/fix-loops", response_model=FixLoopRecord, status_code=status.HTTP_201_CREATED)
    def confirm_fix_loop(report_id: str, payload: ConfirmFixLoopRequest) -> FixLoopRecord:
        report = report_service.repository.get_quality_report(report_id)
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality report not found.")
        issue_by_id = {issue.issue_id: issue for issue in report.issues}
        missing = [issue_id for issue_id in payload.selected_issue_ids if issue_id not in issue_by_id]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Selected issue ids do not exist in report: {', '.join(missing)}",
            )
        plan = planner.create_fix_plan(report)
        selected_actions = [
            action
            for action in plan.actions
            if any(issue_id in payload.selected_issue_ids for issue_id in action.target_issue_ids)
        ]
        record = FixLoopRecord(
            fix_loop_id=f"fl_{uuid4().hex}",
            original_report_id=report.report_id,
            fix_plan_id=payload.fix_plan_id,
            selected_issue_ids=payload.selected_issue_ids,
            selected_actions=selected_actions,
            status="confirmed",
        )
        return report_service.repository.add_quality_fix_loop(record)

    return router
