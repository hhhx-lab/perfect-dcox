import pytest
from docx import Document
from docx.shared import Cm
from pydantic import ValidationError

from app.documents.formatter import format_docx_with_profile
from app.models import (
    FixAction,
    FixLoopRecord,
    FixPlan,
    QualityIssue,
    QualityReport,
    QualitySummary,
)
from app.profiles.seed import load_builtin_profiles
from app.quality.inspection import inspect_docx_quality, inspect_pdf_quality
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_minimal_thesis_docx


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


def test_repository_persists_quality_reports_and_fix_loop_lineage(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    issue = QualityIssue(
        issue_id="issue_font",
        status="warning",
        check_key="docx.body.font",
        title="Body font needs review.",
        profile_rule_ref="body.font",
        location="paragraph[2]",
        recommendation="Apply body paragraph style.",
        fixable=True,
    )
    report = QualityReport(
        report_id="qr_123",
        job_id="job_123",
        profile_id="ecnu_thesis",
        profile_version="1.0.0",
        output_file_ids=["file_docx"],
        summary=QualitySummary.from_issues([issue]),
        issues=[issue],
    )
    action = FixAction(action="apply_body_paragraph_style", target_issue_ids=["issue_font"])
    loop = FixLoopRecord(
        fix_loop_id="fl_123",
        original_report_id="qr_123",
        fix_plan_id="fp_123",
        selected_issue_ids=["issue_font"],
        selected_actions=[action],
        status="confirmed",
    )

    repository.add_quality_report(report)
    repository.add_quality_fix_loop(loop)
    loaded_report = JsonMetadataRepository(tmp_path / "metadata.json").get_quality_report("qr_123")
    loaded_loop = JsonMetadataRepository(tmp_path / "metadata.json").get_quality_fix_loop("fl_123")

    assert loaded_report == report
    assert loaded_loop == loop
    assert loaded_report.summary.counts["warning"] == 1

    loaded_loop.status = "completed"
    loaded_loop.new_job_id = "job_fix_123"
    loaded_loop.new_output_file_ids = ["file_fixed_docx"]
    loaded_loop.updated_report_id = "qr_fixed"
    updated_loop = repository.update_quality_fix_loop(loaded_loop)

    reloaded_loop = JsonMetadataRepository(tmp_path / "metadata.json").get_quality_fix_loop("fl_123")
    assert reloaded_loop == updated_loop
    assert reloaded_loop.original_report_id == "qr_123"
    assert reloaded_loop.updated_report_id == "qr_fixed"
    assert updated_loop.updated_at >= loop.updated_at


def test_repository_handles_legacy_metadata_without_quality_collections(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(
        '{"files": {}, "jobs": {}, "profiles": {}, "profile_versions": {}, "profile_extractions": {}}',
        encoding="utf-8",
    )
    repository = JsonMetadataRepository(metadata_path)

    assert repository.list_quality_reports() == []
    assert repository.get_quality_report("qr_missing") is None
    assert repository.list_quality_fix_loops() == []
    assert repository.get_quality_fix_loop("fl_missing") is None


def test_quality_report_serializes_issues_by_status_without_hiding_unsupported() -> None:
    issues = [
        QualityIssue(issue_id="issue_pass", status="pass", check_key="docx.open", title="DOCX opens"),
        QualityIssue(issue_id="issue_warning", status="warning", check_key="pdf.blank", title="Blank page warning"),
        QualityIssue(issue_id="issue_fail", status="fail", check_key="docx.font", title="Font mismatch"),
        QualityIssue(
            issue_id="issue_unsupported",
            status="unsupported",
            check_key="docx.page_number",
            title="Page number cannot be judged",
            recommendation="Review page numbering manually.",
        ),
    ]
    report = QualityReport(
        report_id="qr_grouped",
        job_id="job_grouped",
        profile_id="ecnu_thesis",
        profile_version="1.0.0",
        output_file_ids=["file_docx"],
        summary=QualitySummary.from_issues(issues),
        issues=issues,
    )

    payload = report.model_dump(mode="json")

    assert [issue.issue_id for issue in report.issues_by_status["warning"]] == ["issue_warning"]
    assert payload["issues_by_status"]["unsupported"][0]["issue_id"] == "issue_unsupported"
    assert payload["summary"]["remaining_issue_count"] == 3
    assert payload["summary"]["all_compliant"] is False


def test_docx_quality_inspection_passes_profiled_output_and_marks_page_numbers_unsupported(tmp_path) -> None:
    profile = load_builtin_profiles()["ecnu_thesis"]
    source = create_minimal_thesis_docx(tmp_path / "source.docx")
    formatted = format_docx_with_profile(source, tmp_path / "formatted.docx", profile)

    issues = inspect_docx_quality(formatted, profile)
    by_key = {issue.check_key: issue for issue in issues}

    assert by_key["docx.page.margins"].status == "pass"
    assert by_key["docx.body.style"].status == "pass"
    assert by_key["docx.heading.style"].status == "pass"
    assert by_key["docx.table.borders"].status == "pass"
    assert by_key["docx.captions"].status == "pass"
    assert by_key["docx.raw_latex"].status == "pass"
    assert by_key["docx.page_number"].status == "unsupported"
    assert by_key["docx.page_number"].recommendation


def test_docx_quality_inspection_detects_margin_and_latex_failures(tmp_path) -> None:
    profile = load_builtin_profiles()["ecnu_thesis"]
    source = create_minimal_thesis_docx(tmp_path / "source.docx")
    document = Document(source)
    document.sections[0].top_margin = Cm(1.0)
    document.add_paragraph(r"Inline residue: $E = mc^2$")
    broken = tmp_path / "broken.docx"
    document.save(broken)

    issues = inspect_docx_quality(broken, profile)
    by_key = {issue.check_key: issue for issue in issues}

    assert by_key["docx.page.margins"].status == "fail"
    assert by_key["docx.page.margins"].profile_rule_ref == "page.margins_cm"
    assert by_key["docx.raw_latex"].status == "fail"
    assert by_key["docx.raw_latex"].location == "paragraph[8]"


def test_pdf_quality_inspection_passes_basic_deliverability(tmp_path) -> None:
    pdf = tmp_path / "deliverable.pdf"
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 48 >> stream\n"
        b"BT /F1 12 Tf 72 720 Td (Hello thesis text) Tj ET\n"
        b"endstream endobj\n"
        b"%%EOF"
    )

    issues = inspect_pdf_quality(pdf)
    by_key = {issue.check_key: issue for issue in issues}

    assert by_key["pdf.openability"].status == "pass"
    assert by_key["pdf.page_count"].status == "pass"
    assert by_key["pdf.page_count"].details["page_count"] == 1
    assert by_key["pdf.text_extractability"].status == "pass"
    assert by_key["pdf.blank_pages"].status == "pass"


def test_pdf_quality_inspection_flags_unreadable_and_blank_pdf(tmp_path) -> None:
    corrupt = tmp_path / "corrupt.pdf"
    corrupt.write_bytes(b"not a pdf")
    blank = tmp_path / "blank.pdf"
    blank.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 0 >> stream\n\nendstream endobj\n"
        b"%%EOF"
    )

    corrupt_by_key = {issue.check_key: issue for issue in inspect_pdf_quality(corrupt)}
    blank_by_key = {issue.check_key: issue for issue in inspect_pdf_quality(blank)}

    assert corrupt_by_key["pdf.openability"].status == "fail"
    assert corrupt_by_key["pdf.page_count"].status == "fail"
    assert blank_by_key["pdf.openability"].status == "pass"
    assert blank_by_key["pdf.text_extractability"].status == "fail"
    assert blank_by_key["pdf.blank_pages"].status == "warning"
