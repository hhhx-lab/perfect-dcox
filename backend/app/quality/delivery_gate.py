from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from docx import Document

from app.documents.ooxml import OoxmlDocumentFeatures, OoxmlInspectionError, inspect_ooxml_features
from app.documents.rule_registry import (
    DocxRegistryDispatchResult,
    DocxRegistryVerificationResult,
    blocking_unsupported_capabilities,
    execute_docx_rule_verifiers,
    field_path_has_blocking_capability_gap,
    verify_docx_rule_registry_coverage,
)
from app.documents.formatter import DocumentFormatError, format_docx_with_profile
from app.models import QualityIssue, QualitySummary
from app.profiles.models import FormatProfile, ProfileCapabilityCoverage, ProfileUnsupportedRule
from app.quality.final_layout_review import (
    FinalLayoutReviewError,
    FinalLayoutReviewer,
    build_final_layout_payload,
)
from app.quality.inspection import QualityInspectionError, inspect_docx_quality, inspect_pdf_quality


class InternalDeliveryGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class InternalDeliveryGateResult:
    passed: bool
    docx_path: Path
    issues: list[QualityIssue] = field(default_factory=list)
    summary: QualitySummary = field(default_factory=QualitySummary)
    failure_reason: str | None = None
    auto_fixed: bool = False
    registry_verification: dict[str, object] = field(default_factory=dict)

    def public_summary(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "auto_fixed": self.auto_fixed,
            "remaining_issue_count": self.summary.remaining_issue_count,
            "counts": self.summary.counts,
            "failure_reason": self.failure_reason,
            "rule_registry": self.registry_verification,
        }


class InternalDeliveryGateService:
    def __init__(self, final_layout_reviewer: FinalLayoutReviewer | None = None) -> None:
        self.final_layout_reviewer = final_layout_reviewer

    def validate_docx(
        self,
        candidate_path: Path,
        profile: FormatProfile,
        work_dir: Path,
        *,
        inherited_header_footer: bool = False,
    ) -> InternalDeliveryGateResult:
        unsupported = _blocking_unsupported_rules(candidate_path, profile)
        unsupported_coverage = _blocking_unsupported_capabilities(candidate_path, profile)
        if unsupported or unsupported_coverage:
            issues = [
                QualityIssue(
                    issue_id=f"unsupported_profile_rule_{index}",
                    status="unsupported",
                    check_key="profile.unsupported_rule",
                    title="Profile contains unsupported rules.",
                    description=item.message,
                    profile_rule_ref=item.field_path,
                    recommendation=item.suggestion or "Remove or manually resolve unsupported rules before export.",
                    fixable=False,
                )
                for index, item in enumerate(unsupported, start=1)
            ]
            issues.extend(
                QualityIssue(
                    issue_id=f"unsupported_profile_capability_{index}",
                    status="unsupported",
                    check_key="profile.capability_coverage",
                    title="Profile contains a rule without formatter/QC support.",
                    description=(
                        f"{item.field_path} is declared as formatter={item.formatter}, "
                        f"qc={item.qc}; this field cannot be counted as compliant."
                    ),
                    profile_rule_ref=item.field_path,
                    recommendation="Remove the rule, mark it for manual handling, or implement formatter and QC support.",
                    fixable=False,
                )
                for index, item in enumerate(unsupported_coverage, start=1)
            )
            return _failed_result(candidate_path, issues, "Profile contains unsupported rules that cannot be verified.")

        try:
            issues = inspect_docx_quality(candidate_path, profile, inherited_header_footer=inherited_header_footer)
        except QualityInspectionError as exc:
            raise InternalDeliveryGateError(str(exc)) from exc
        registry_dispatch = execute_docx_rule_verifiers(
            candidate_path,
            profile,
            inherited_header_footer=inherited_header_footer,
        )
        if not registry_dispatch.all_executed:
            dispatch_issue = _registry_dispatch_issue(registry_dispatch)
            return _failed_result(
                candidate_path,
                [*issues, dispatch_issue],
                dispatch_issue.description or dispatch_issue.title,
                registry_verification={"dispatch": registry_dispatch.public_summary()},
            )
        registry_verification = verify_docx_rule_registry_coverage(issues)
        registry_summary = _registry_summary(registry_verification, registry_dispatch)
        if not registry_verification.all_covered:
            coverage_issue = _registry_coverage_issue(registry_verification)
            return _failed_result(
                candidate_path,
                [*issues, coverage_issue],
                coverage_issue.description or coverage_issue.title,
                registry_verification=registry_summary,
            )
        summary = QualitySummary.from_issues(issues)
        if summary.all_compliant:
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=candidate_path,
                issues=issues,
                summary=summary,
                registry_verification=registry_summary,
            )

        if not profile.delivery_gate.allow_auto_fix:
            return _failed_result(
                candidate_path,
                issues,
                _first_remaining_reason(issues),
                registry_verification=registry_summary,
            )

        fixed_path = work_dir / f"{candidate_path.stem}-gate-fixed.docx"
        try:
            format_docx_with_profile(
                candidate_path,
                fixed_path,
                profile,
                preserve_header_footer=inherited_header_footer,
            )
            fixed_issues = inspect_docx_quality(fixed_path, profile, inherited_header_footer=inherited_header_footer)
        except (DocumentFormatError, QualityInspectionError) as exc:
            raise InternalDeliveryGateError(f"Internal QC auto-fix failed: {exc}") from exc
        fixed_registry_dispatch = execute_docx_rule_verifiers(
            fixed_path,
            profile,
            inherited_header_footer=inherited_header_footer,
        )
        if not fixed_registry_dispatch.all_executed:
            dispatch_issue = _registry_dispatch_issue(fixed_registry_dispatch, after_auto_fix=True)
            return _failed_result(
                fixed_path,
                [*fixed_issues, dispatch_issue],
                dispatch_issue.description or dispatch_issue.title,
                auto_fixed=True,
                registry_verification={"dispatch": fixed_registry_dispatch.public_summary()},
            )
        fixed_registry_verification = verify_docx_rule_registry_coverage(fixed_issues)
        fixed_registry_summary = _registry_summary(fixed_registry_verification, fixed_registry_dispatch)
        if not fixed_registry_verification.all_covered:
            coverage_issue = _registry_coverage_issue(fixed_registry_verification, after_auto_fix=True)
            return _failed_result(
                fixed_path,
                [*fixed_issues, coverage_issue],
                coverage_issue.description or coverage_issue.title,
                auto_fixed=True,
                registry_verification=fixed_registry_summary,
            )
        fixed_summary = QualitySummary.from_issues(fixed_issues)
        if fixed_summary.all_compliant:
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=fixed_path,
                issues=fixed_issues,
                summary=fixed_summary,
                auto_fixed=True,
                registry_verification=fixed_registry_summary,
            )
        return _failed_result(
            fixed_path,
            fixed_issues,
            _first_remaining_reason(fixed_issues),
            auto_fixed=True,
            registry_verification=fixed_registry_summary,
        )

    def validate_pdf(self, pdf_path: Path) -> InternalDeliveryGateResult:
        issues = inspect_pdf_quality(pdf_path)
        summary = QualitySummary.from_issues(issues)
        if summary.all_compliant:
            return InternalDeliveryGateResult(passed=True, docx_path=pdf_path, issues=issues, summary=summary)
        return _failed_result(pdf_path, issues, _first_remaining_reason(issues))

    def validate_final_layout(self, pdf_path: Path, profile: FormatProfile) -> InternalDeliveryGateResult:
        if not profile.llm_final_review.enabled:
            issue = QualityIssue(
                issue_id="llm_layout_review_disabled",
                status="pass",
                severity="info",
                check_key="llm.layout_review",
                title="Final LLM layout review is disabled by the profile.",
                profile_rule_ref="llm_final_review.enabled",
            )
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=pdf_path,
                issues=[issue],
                summary=QualitySummary.from_issues([issue]),
            )
        if self.final_layout_reviewer is None:
            issue = QualityIssue(
                issue_id="llm_layout_review_unavailable",
                status="fail" if profile.llm_final_review.required else "warning",
                severity="high" if profile.llm_final_review.required else "medium",
                check_key="llm.layout_review",
                title="Final LLM layout reviewer is not configured.",
                description="Final LLM layout reviewer is not configured; the profile requires final LLM layout review.",
                profile_rule_ref="llm_final_review.required",
                recommendation="Configure LLM_API_KEY and LLM_MODEL, or disable required final layout review for this profile.",
                fixable=False,
            )
            if profile.llm_final_review.required:
                return _failed_result(pdf_path, [issue], issue.description or issue.title)
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=pdf_path,
                issues=[issue],
                summary=QualitySummary.from_issues([issue]),
                failure_reason=issue.description,
            )
        try:
            result = self.final_layout_reviewer.review_pdf(build_final_layout_payload(pdf_path, profile))
        except FinalLayoutReviewError as exc:
            issue = QualityIssue(
                issue_id="llm_layout_review_failed",
                status="fail" if profile.llm_final_review.required else "warning",
                severity="high" if profile.llm_final_review.required else "medium",
                check_key="llm.layout_review",
                title="Final LLM layout review failed to run.",
                description=str(exc),
                profile_rule_ref="llm_final_review",
                recommendation="Inspect LLM connectivity and model support for PDF/page-image review.",
                fixable=False,
            )
            if profile.llm_final_review.required:
                return _failed_result(pdf_path, [issue], str(exc))
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=pdf_path,
                issues=[issue],
                summary=QualitySummary.from_issues([issue]),
                failure_reason=str(exc),
            )

        if result.passed:
            issue = QualityIssue(
                issue_id="llm_layout_review",
                status="pass",
                severity="info",
                check_key="llm.layout_review",
                title="Final LLM layout review passed.",
                description=result.summary,
                profile_rule_ref="llm_final_review",
                details={"issues": result.issues},
            )
            return InternalDeliveryGateResult(
                passed=True,
                docx_path=pdf_path,
                issues=[issue],
                summary=QualitySummary.from_issues([issue]),
            )
        issue = QualityIssue(
            issue_id="llm_layout_review",
            status="fail",
            severity="high",
            check_key="llm.layout_review",
            title="Final LLM layout review found blocking layout issues.",
            description=result.summary or "; ".join(result.issues),
            profile_rule_ref="llm_final_review",
            recommendation="Re-run formatting or inspect the final PDF before publishing downloads.",
            fixable=False,
            details={"issues": result.issues},
        )
        return _failed_result(pdf_path, [issue], issue.description or issue.title)


def _blocking_unsupported_rules(candidate_path: Path, profile: FormatProfile) -> list[ProfileUnsupportedRule]:
    if not profile.delivery_gate.fail_on_unsupported_rules:
        return []
    context = _UnsupportedApplicabilityContext(candidate_path)
    return [
        item
        for item in profile.unsupported_rules
        if context.applies(item.field_path)
        and field_path_has_blocking_capability_gap(item.field_path)
    ]


def _blocking_unsupported_capabilities(candidate_path: Path, profile: FormatProfile) -> list[ProfileCapabilityCoverage]:
    context = _UnsupportedApplicabilityContext(candidate_path)
    return [
        item
        for item in blocking_unsupported_capabilities(profile)
        if context.applies(item.field_path)
    ]


class _UnsupportedApplicabilityContext:
    def __init__(self, candidate_path: Path) -> None:
        self.candidate_path = candidate_path
        self._features: OoxmlDocumentFeatures | None | bool = False
        self._has_appendix: bool | None = None

    def applies(self, field_path: str) -> bool:
        if _field_path_contains(field_path, {"notes", "footnote", "footnotes", "endnote", "endnotes"}):
            return self.has_notes()
        if _field_path_contains(field_path, {"appendix"}):
            return self.has_appendix()
        return True

    def has_notes(self) -> bool:
        features = self.features()
        if features is None:
            return True
        return (features.footnote_count + features.endnote_count) > 0

    def has_appendix(self) -> bool:
        if self._has_appendix is not None:
            return self._has_appendix
        try:
            document = Document(self.candidate_path)
        except Exception:
            self._has_appendix = True
            return self._has_appendix
        appendix_heading = re.compile(r"^\s*(附录|appendix\b)", flags=re.IGNORECASE)
        self._has_appendix = any(
            bool(appendix_heading.match(paragraph.text.strip()))
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )
        return self._has_appendix

    def features(self) -> OoxmlDocumentFeatures | None:
        if self._features is False:
            try:
                self._features = inspect_ooxml_features(self.candidate_path)
            except OoxmlInspectionError:
                self._features = None
        return self._features if isinstance(self._features, OoxmlDocumentFeatures) else None


def _field_path_contains(field_path: str, candidates: set[str]) -> bool:
    normalized = field_path.lower().replace("_", ".").replace("-", ".")
    segments = [segment for segment in re.split(r"[\.\[\]]+", normalized) if segment and not segment.isdigit()]
    return any(segment in candidates for segment in segments)


def _failed_result(
    docx_path: Path,
    issues: list[QualityIssue],
    failure_reason: str,
    auto_fixed: bool = False,
    registry_verification: dict[str, object] | None = None,
) -> InternalDeliveryGateResult:
    return InternalDeliveryGateResult(
        passed=False,
        docx_path=docx_path,
        issues=issues,
        summary=QualitySummary.from_issues(issues),
        failure_reason=failure_reason,
        auto_fixed=auto_fixed,
        registry_verification=registry_verification or {},
    )


def _registry_coverage_issue(
    registry_verification: DocxRegistryVerificationResult,
    *,
    after_auto_fix: bool = False,
) -> QualityIssue:
    suffix = " after auto-fix" if after_auto_fix else ""
    return QualityIssue(
        issue_id="registry_docx_verifier_coverage",
        status="fail",
        severity="high",
        check_key="profile.rule_registry.verifier_coverage",
        title=f"Rule registry DOCX verifier coverage is incomplete{suffix}.",
        description=(
            "Missing DOCX quality issue(s) for registered verifier key(s): "
            f"{', '.join(registry_verification.missing_verifier_keys)}; "
            "affected Profile field(s): "
            f"{', '.join(registry_verification.missing_field_paths)}"
        ),
        profile_rule_ref="rule_registry",
        recommendation="Add the missing field-level QC verifier output before publishing final downloads.",
        fixable=False,
        details=registry_verification.public_summary(),
    )


def _registry_dispatch_issue(
    registry_dispatch: DocxRegistryDispatchResult,
    *,
    after_auto_fix: bool = False,
) -> QualityIssue:
    suffix = " after auto-fix" if after_auto_fix else ""
    failed = [
        f"{item.check_key}: {item.error}"
        for item in registry_dispatch.dispatches
        if not item.executed
    ]
    return QualityIssue(
        issue_id="registry_docx_verifier_dispatch",
        status="fail",
        severity="high",
        check_key="profile.rule_registry.verifier_dispatch",
        title=f"Rule registry DOCX verifier dispatch failed{suffix}.",
        description="; ".join(failed[:12]) or "At least one registered DOCX verifier did not execute.",
        profile_rule_ref="rule_registry",
        recommendation="Fix the registered verifier callable before publishing final downloads.",
        fixable=False,
        details=registry_dispatch.public_summary(),
    )


def _registry_summary(
    registry_verification: DocxRegistryVerificationResult,
    registry_dispatch: DocxRegistryDispatchResult,
) -> dict[str, object]:
    summary = registry_verification.public_summary()
    summary["dispatch"] = registry_dispatch.public_summary()
    return summary


def _first_remaining_reason(issues: list[QualityIssue]) -> str:
    for issue in issues:
        if issue.status in {"warning", "fail", "unsupported"}:
            return issue.description or issue.title
    return "Internal delivery gate did not pass."
