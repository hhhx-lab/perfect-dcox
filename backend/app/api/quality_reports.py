from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.models import FixLoopRecord, FixPlan, QualityReport
from app.quality.fix_execution import FixLoopExecutionError, FixLoopExecutionService
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
    fix_execution_service: FixLoopExecutionService | None = None,
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

    @router.get("/{report_id}/download")
    def download_quality_report(report_id: str, format: str = "json") -> Response:
        report = report_service.repository.get_quality_report(report_id)
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality report not found.")
        if format == "json":
            return Response(
                content=json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
                media_type="application/json; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{report.report_id}.json"'},
            )
        if format == "markdown":
            return Response(
                content=_report_to_markdown(report),
                media_type="text/markdown; charset=utf-8",
                headers={"Content-Disposition": f'attachment; filename="{report.report_id}.md"'},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be json or markdown.")

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

    @router.post("/{report_id}/fix-loops/{fix_loop_id}/execute", response_model=FixLoopRecord)
    def execute_fix_loop(report_id: str, fix_loop_id: str) -> FixLoopRecord:
        if fix_execution_service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Fix-loop execution service is not configured.",
            )
        loop = report_service.repository.get_quality_fix_loop(fix_loop_id)
        if loop is None or loop.original_report_id != report_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fix loop not found.")
        try:
            return fix_execution_service.execute(fix_loop_id)
        except FixLoopExecutionError as error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    return router


def _report_to_markdown(report: QualityReport) -> str:
    lines = [
        f"# Quality Report {report.report_id}",
        "",
        f"- Job: {report.job_id or 'N/A'}",
        f"- Profile: {report.profile_id} v{report.profile_version}",
        f"- Outputs: {', '.join(report.output_file_ids)}",
        f"- All compliant: {report.summary.all_compliant}",
        f"- Remaining issues: {report.summary.remaining_issue_count}",
        "",
        "## Counts",
        "",
    ]
    for status_name, count in report.summary.counts.items():
        lines.append(f"- {status_name}: {count}")
    lines.extend(["", "## Issues", ""])
    for issue in report.issues:
        lines.extend(
            [
                f"### {issue.issue_id} - {issue.title}",
                "",
                f"- Status: {issue.status}",
                f"- Severity: {issue.severity}",
                f"- Check: {issue.check_key}",
                f"- Rule: {issue.profile_rule_ref or 'N/A'}",
                f"- Location: {issue.location or 'N/A'}",
                f"- Fixable: {issue.fixable}",
                f"- Description: {issue.description or 'N/A'}",
                f"- Recommendation: {issue.recommendation or 'N/A'}",
                "",
            ]
        )
    return "\n".join(lines)
