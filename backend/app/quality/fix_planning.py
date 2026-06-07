from __future__ import annotations

from uuid import uuid4

from app.models import FixAction, FixPlan, IssueExplanation, QualityIssue, QualityReport


FIX_ACTION_BY_CHECK_KEY = {
    "docx.page.margins": "reapply_profile_formatting",
    "docx.body.style": "apply_body_paragraph_style",
    "docx.heading.style": "apply_heading_style",
    "docx.table.borders": "apply_table_borders",
}


class FixPlanService:
    def create_fix_plan(self, report: QualityReport) -> FixPlan:
        explanations: list[IssueExplanation] = []
        actions: list[FixAction] = []
        manual_review_issue_ids: list[str] = []
        for issue in report.issues:
            if issue.status not in {"warning", "fail", "unsupported"}:
                continue
            action_name = FIX_ACTION_BY_CHECK_KEY.get(issue.check_key) if issue.fixable else None
            automatic_repair_allowed = action_name is not None and issue.status != "unsupported"
            explanations.append(_explain_issue(issue, automatic_repair_allowed))
            if automatic_repair_allowed and action_name:
                actions.append(
                    FixAction(
                        action=action_name,
                        target_issue_ids=[issue.issue_id],
                        params={
                            "check_key": issue.check_key,
                            "profile_rule_ref": issue.profile_rule_ref,
                        },
                        requires_user_confirmation=True,
                    )
                )
            else:
                manual_review_issue_ids.append(issue.issue_id)
        return FixPlan(
            fix_plan_id=f"fp_{uuid4().hex}",
            report_id=report.report_id,
            actions=actions,
            explanations=explanations,
            manual_review_issue_ids=manual_review_issue_ids,
            explanation="Deterministic fallback fix plan generated from quality issue metadata.",
        )


def _explain_issue(issue: QualityIssue, automatic_repair_allowed: bool) -> IssueExplanation:
    if issue.status == "unsupported":
        guidance = issue.recommendation or "Review this item manually."
        return IssueExplanation(
            issue_id=issue.issue_id,
            reason=f"The current checker cannot judge {issue.title}",
            impact="The report keeps this item visible so it is not mistaken for a pass.",
            automatic_repair_allowed=False,
            manual_review_guidance=f"The system cannot judge or repair this automatically. {guidance}",
        )
    return IssueExplanation(
        issue_id=issue.issue_id,
        reason=issue.description or issue.title,
        impact=_impact_for_status(issue),
        automatic_repair_allowed=automatic_repair_allowed,
        manual_review_guidance=(
            "Review the proposed formatting action before confirming."
            if automatic_repair_allowed
            else issue.recommendation or "Review this issue manually."
        ),
    )


def _impact_for_status(issue: QualityIssue) -> str:
    if issue.status == "fail":
        return "This issue may make the output fail the selected thesis profile."
    return "This issue may need user review before the output can be treated as compliant."
