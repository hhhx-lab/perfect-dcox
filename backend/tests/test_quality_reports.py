import pytest
from pydantic import ValidationError

from app.models import (
    FixAction,
    FixLoopRecord,
    FixPlan,
    QualityIssue,
    QualityReport,
    QualitySummary,
)


def test_quality_report_models_serialize_status_groups_and_issue_metadata() -> None:
    issue = QualityIssue(
        issue_id="issue_margin_top",
        status="fail",
        severity="high",
        check_key="docx.page.margin.top",
        title="Top margin does not match profile.",
        description="Expected 2.5 cm, found 1.9 cm.",
        profile_rule_ref="page.margins_cm.top",
        location="section[0]",
        recommendation="Reapply the selected profile margins.",
        fixable=True,
    )
    summary = QualitySummary.from_issues([issue])
    report = QualityReport(
        report_id="qr_123",
        job_id="job_123",
        profile_id="ecnu_thesis",
        profile_version="1.0.0",
        output_file_ids=["file_docx"],
        summary=summary,
        issues=[issue],
    )

    payload = report.model_dump(mode="json")

    assert payload["summary"]["counts"]["fail"] == 1
    assert payload["summary"]["remaining_issue_count"] == 1
    assert payload["summary"]["all_compliant"] is False
    assert payload["issues"][0]["profile_rule_ref"] == "page.margins_cm.top"
    assert payload["issues"][0]["location"] == "section[0]"
    assert payload["issues"][0]["recommendation"] == "Reapply the selected profile margins."
    assert payload["created_at"]
    assert payload["updated_at"]


def test_quality_summary_counts_all_supported_statuses() -> None:
    issues = [
        QualityIssue(issue_id="pass_1", status="pass", check_key="docx.open", title="Openable"),
        QualityIssue(issue_id="fixed_1", status="fixed", check_key="docx.table", title="Table fixed"),
        QualityIssue(issue_id="warning_1", status="warning", check_key="pdf.blank", title="Possible blank page"),
        QualityIssue(issue_id="fail_1", status="fail", check_key="docx.font", title="Font mismatch"),
        QualityIssue(
            issue_id="unsupported_1",
            status="unsupported",
            check_key="docx.page_number",
            title="Page number unsupported",
        ),
    ]

    summary = QualitySummary.from_issues(issues)

    assert summary.counts == {"pass": 1, "fixed": 1, "warning": 1, "fail": 1, "unsupported": 1}
    assert summary.remaining_issue_count == 3
    assert summary.all_compliant is False


def test_fix_plan_and_fix_loop_models_preserve_confirmation_and_lineage() -> None:
    action = FixAction(
        action="reapply_profile_formatting",
        target_issue_ids=["issue_margin_top"],
        params={"scope": "document"},
        requires_user_confirmation=True,
    )
    plan = FixPlan(
        fix_plan_id="fp_123",
        report_id="qr_original",
        actions=[action],
        manual_review_issue_ids=["issue_page_number"],
    )
    loop = FixLoopRecord(
        fix_loop_id="fl_123",
        original_report_id="qr_original",
        fix_plan_id="fp_123",
        selected_issue_ids=["issue_margin_top"],
        selected_actions=[action],
        status="pending_confirmation",
        new_job_id=None,
        new_output_file_ids=[],
        updated_report_id=None,
    )

    assert plan.requires_user_confirmation is True
    assert loop.original_report_id == "qr_original"
    assert loop.updated_report_id is None
    assert loop.selected_actions[0].target_issue_ids == ["issue_margin_top"]


def test_quality_and_fix_models_reject_unknown_statuses() -> None:
    with pytest.raises(ValidationError):
        QualityIssue(issue_id="bad", status="ok", check_key="docx.open", title="Bad status")

    with pytest.raises(ValidationError):
        FixLoopRecord(
            fix_loop_id="fl_bad",
            original_report_id="qr_original",
            fix_plan_id="fp_123",
            selected_issue_ids=["issue_margin_top"],
            selected_actions=[],
            status="done",
        )
