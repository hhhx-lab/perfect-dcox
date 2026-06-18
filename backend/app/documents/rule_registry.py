from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from app.models import ExtractionEvidence, QualityIssue
from app.profiles.models import FormatProfile, ProfileCapabilityCoverage, ProfileCapabilityStatus, ProfileRuleSourceKind


UnsupportedBehavior = Literal["block", "warn"]
VERIFIED_PROFILE_FIELDS_DETAIL_KEY = "verified_profile_fields"


@dataclass(frozen=True)
class RuleSpec:
    field_path: str
    formatter: ProfileCapabilityStatus
    qc: ProfileCapabilityStatus
    applier: str | None = None
    verifier: str | None = None
    frontend: ProfileCapabilityStatus = "supported"
    agent: ProfileCapabilityStatus = "supported"
    llm_final_review: ProfileCapabilityStatus = "supported"
    source: ProfileRuleSourceKind = "system"
    unsupported_behavior: UnsupportedBehavior = "warn"
    note: str | None = None


@dataclass(frozen=True)
class DocxRuleVerification:
    field_path: str
    check_key: str
    issue_ids: tuple[str, ...]
    statuses: tuple[str, ...]
    covered: bool


@dataclass(frozen=True)
class DocxRegistryVerificationResult:
    verifications: tuple[DocxRuleVerification, ...]
    missing_verifier_keys: tuple[str, ...]
    missing_field_paths: tuple[str, ...]

    @property
    def all_covered(self) -> bool:
        return not self.missing_verifier_keys and not self.missing_field_paths

    def public_summary(self) -> dict[str, object]:
        return {
            "all_covered": self.all_covered,
            "missing_verifier_keys": list(self.missing_verifier_keys),
            "missing_field_paths": list(self.missing_field_paths),
            "field_count": len(self.verifications),
            "fields": [
                {
                    "field_path": item.field_path,
                    "check_key": item.check_key,
                    "issue_ids": list(item.issue_ids),
                    "statuses": list(item.statuses),
                    "covered": item.covered,
                }
                for item in self.verifications
            ],
        }


@dataclass(frozen=True)
class DocxRuleVerifierDispatch:
    check_key: str
    field_paths: tuple[str, ...]
    issue_id: str | None
    status: str | None
    executed: bool
    error: str | None = None


@dataclass(frozen=True)
class DocxRegistryDispatchResult:
    dispatches: tuple[DocxRuleVerifierDispatch, ...]
    issues: tuple[QualityIssue, ...]

    @property
    def all_executed(self) -> bool:
        return all(item.executed for item in self.dispatches)

    @property
    def failed_check_keys(self) -> tuple[str, ...]:
        return tuple(item.check_key for item in self.dispatches if not item.executed)

    def public_summary(self) -> dict[str, object]:
        return {
            "all_executed": self.all_executed,
            "executed_check_keys": [item.check_key for item in self.dispatches if item.executed],
            "failed_check_keys": list(self.failed_check_keys),
            "dispatch_count": len(self.dispatches),
            "items": [
                {
                    "check_key": item.check_key,
                    "field_paths": list(item.field_paths),
                    "issue_id": item.issue_id,
                    "status": item.status,
                    "executed": item.executed,
                    "error": item.error,
                }
                for item in self.dispatches
            ],
        }


@dataclass(frozen=True)
class DocxFormatterDispatchItem:
    applier: str
    field_paths: tuple[str, ...]
    call_count: int

    @property
    def executed(self) -> bool:
        return self.call_count > 0


@dataclass(frozen=True)
class DocxFormatterDispatchResult:
    items: tuple[DocxFormatterDispatchItem, ...]
    unexpected_appliers: tuple[str, ...] = ()

    @property
    def all_registered_appliers_executed(self) -> bool:
        return all(item.executed for item in self.items)

    @property
    def executed_appliers(self) -> tuple[str, ...]:
        return tuple(item.applier for item in self.items if item.executed)

    @property
    def missing_registered_appliers(self) -> tuple[str, ...]:
        return tuple(item.applier for item in self.items if not item.executed)

    @property
    def executed_field_paths(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    field_path
                    for item in self.items
                    if item.executed
                    for field_path in item.field_paths
                }
            )
        )

    @property
    def not_executed_field_paths(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    field_path
                    for item in self.items
                    if not item.executed
                    for field_path in item.field_paths
                }
            )
        )

    def public_summary(self) -> dict[str, object]:
        return {
            "registered_applier_count": len(self.items),
            "all_registered_appliers_executed": self.all_registered_appliers_executed,
            "executed_appliers": list(self.executed_appliers),
            "missing_registered_appliers": list(self.missing_registered_appliers),
            "unexpected_appliers": list(self.unexpected_appliers),
            "executed_field_paths": list(self.executed_field_paths),
            "not_executed_field_paths": list(self.not_executed_field_paths),
            "items": [
                {
                    "applier": item.applier,
                    "field_paths": list(item.field_paths),
                    "call_count": item.call_count,
                    "executed": item.executed,
                }
                for item in self.items
            ],
        }


def _supported(
    field_path: str,
    *,
    applier: str,
    verifier: str,
    note: str | None = None,
) -> RuleSpec:
    return RuleSpec(
        field_path=field_path,
        formatter="supported",
        qc="supported",
        applier=applier,
        verifier=verifier,
        note=note,
    )


def _partial(
    field_path: str,
    *,
    applier: str | None,
    verifier: str | None,
    note: str,
    unsupported_behavior: UnsupportedBehavior = "warn",
) -> RuleSpec:
    return RuleSpec(
        field_path=field_path,
        formatter="partial",
        qc="partial",
        applier=applier,
        verifier=verifier,
        unsupported_behavior=unsupported_behavior,
        note=note,
    )


def _delegated(field_path: str, *, verifier: str | None, note: str) -> RuleSpec:
    return RuleSpec(
        field_path=field_path,
        formatter="template_delegated",
        qc="template_delegated" if verifier is None else "supported",
        verifier=verifier,
        unsupported_behavior="warn",
        note=note,
    )


RULE_SPECS: tuple[RuleSpec, ...] = (
    _supported("page.size", applier="_apply_section_size", verifier="docx.page.setup"),
    _supported("page.orientation", applier="_apply_section_size", verifier="docx.page.setup"),
    _supported("page.margins_cm", applier="_apply_page_settings", verifier="docx.page.margins"),
    _supported("page.gutter", applier="_apply_page_settings", verifier="docx.page.margins"),
    _supported("document_grid", applier="_apply_document_grid", verifier="docx.document_grid"),
    _supported("body.font.chinese", applier="_apply_body_paragraph", verifier="docx.body.font.chinese"),
    _supported("body.font.latin", applier="_apply_body_paragraph", verifier="docx.body.font.latin"),
    _supported("body.font.size_pt", applier="_apply_body_paragraph", verifier="docx.body.font.size"),
    _supported("body.font.color", applier="_apply_body_paragraph", verifier="docx.body.font.color"),
    _supported("body.line_spacing", applier="_apply_body_paragraph", verifier="docx.body.line_spacing"),
    _supported("body.first_line_indent_chars", applier="_apply_body_paragraph", verifier="docx.body.first_line_indent"),
    _supported("body.space_before_pt", applier="_apply_body_paragraph", verifier="docx.body.space_before"),
    _supported("body.space_after_pt", applier="_apply_body_paragraph", verifier="docx.body.space_after"),
    _supported("body.alignment", applier="_apply_body_paragraph", verifier="docx.body.alignment"),
    _supported("headings", applier="_apply_heading_paragraph", verifier="docx.heading.style"),
    _supported("headings.font", applier="_apply_heading_paragraph", verifier="docx.heading.style"),
    _supported("headings.font.chinese", applier="_apply_heading_paragraph", verifier="docx.heading.font.chinese"),
    _supported("headings.font.latin", applier="_apply_heading_paragraph", verifier="docx.heading.font.latin"),
    _supported("headings.font.size_pt", applier="_apply_heading_paragraph", verifier="docx.heading.font.size"),
    _supported("headings.font.color", applier="_apply_heading_paragraph", verifier="docx.heading.font.color"),
    _supported("headings.font.weight", applier="_apply_heading_paragraph", verifier="docx.heading.font.weight"),
    _supported("headings.alignment", applier="_apply_heading_paragraph", verifier="docx.heading.alignment"),
    _supported("headings.line_spacing", applier="_apply_heading_paragraph", verifier="docx.heading.line_spacing"),
    _supported("headings.space_before_pt", applier="_apply_heading_paragraph", verifier="docx.heading.space_before"),
    _supported("headings.space_after_pt", applier="_apply_heading_paragraph", verifier="docx.heading.space_after"),
    _supported("headings.first_line_indent_chars", applier="_apply_heading_paragraph", verifier="docx.heading.first_line_indent"),
    _supported("headings.numbering", applier="_apply_heading_numbering", verifier="docx.heading_numbering"),
    _supported("headings.pagination", applier="_apply_heading_paragraph", verifier="docx.heading.pagination"),
    _supported("headings.keep_with_next", applier="_apply_heading_paragraph", verifier="docx.heading.pagination"),
    _supported("headings.page_break_before", applier="_apply_heading_paragraph", verifier="docx.heading.pagination"),
    _supported("toc", applier="_ensure_toc", verifier="docx.toc.fields"),
    _supported("toc.enabled", applier="_ensure_toc", verifier="docx.toc.enabled"),
    _supported("toc.title", applier="_ensure_toc", verifier="docx.toc.title"),
    _supported("toc.include_levels", applier="_ensure_toc", verifier="docx.toc.include_levels"),
    _supported("toc.show_page_numbers", applier="_ensure_toc", verifier="docx.toc.show_page_numbers"),
    _supported("toc.right_align_page_numbers", applier="_ensure_toc", verifier="docx.toc.right_align_page_numbers"),
    _supported("toc.use_hyperlinks", applier="_ensure_toc", verifier="docx.toc.use_hyperlinks"),
    _supported("toc.update_fields_on_open", applier="_ensure_toc", verifier="docx.toc.update_fields_on_open"),
    _supported("header_footer", applier="_apply_basic_page_numbers", verifier="docx.header_footer"),
    _supported("header_footer.header_text", applier="_apply_basic_page_numbers", verifier="docx.header_footer.header_text"),
    _supported("header_footer.header_alignment", applier="_apply_basic_page_numbers", verifier="docx.header_footer.header_alignment"),
    _supported("header_footer.footer_text", applier="_apply_basic_page_numbers", verifier="docx.header_footer.footer_text"),
    _supported("header_footer.footer_alignment", applier="_apply_basic_page_numbers", verifier="docx.header_footer.footer_alignment"),
    _supported("header_footer.different_first_page", applier="_apply_basic_page_numbers", verifier="docx.header_footer.different_first_page"),
    _supported("header_footer.different_odd_even", applier="_apply_basic_page_numbers", verifier="docx.header_footer.different_odd_even"),
    _supported("header_footer.page_number", applier="_apply_footer_page_number", verifier="docx.page_number"),
    _supported("header_footer.footer_page_number", applier="_apply_footer_page_number", verifier="docx.page_number.field"),
    _supported("header_footer.page_number_format", applier="_apply_footer_page_number", verifier="docx.page_number.format"),
    _supported("header_footer.page_number_start", applier="_apply_footer_page_number", verifier="docx.page_number.start"),
    _supported("abstract", applier="_apply_abstract_body", verifier="docx.role_styles"),
    _supported("table.caption", applier="_ensure_table_captions", verifier="docx.captions"),
    _supported("table.caption.position", applier="_ensure_table_captions", verifier="docx.table.caption.position"),
    _supported("table.caption.bilingual", applier="_ensure_bilingual_caption_near", verifier="docx.table.caption.bilingual"),
    _supported("table.border_style", applier="_apply_table_rules", verifier="docx.table.border_style"),
    _supported("table.header_repeat", applier="_apply_table_rules", verifier="docx.table.header_repeat"),
    _supported("figure.caption", applier="_ensure_figure_captions", verifier="docx.captions"),
    _supported("figure.caption.position", applier="_ensure_figure_captions", verifier="docx.figure.caption.position"),
    _supported("figure.caption.bilingual", applier="_ensure_bilingual_caption_near", verifier="docx.figure.caption.bilingual"),
    _supported("figure.size_rules", applier="_apply_figure_size_rules", verifier="docx.figure.size"),
    _partial(
        "equations",
        applier="_apply_equation_paragraph",
        verifier="docx.equations",
        note="Formula paragraphs are supported; full OMML semantic rewriting remains partial.",
    ),
    _supported("references", applier="_apply_reference_paragraph", verifier="docx.role_styles"),
    _partial(
        "references.style",
        applier="_apply_reference_paragraph",
        verifier="docx.role_styles",
        note="Reference paragraph styling is supported; full bibliographic content validation remains partial.",
    ),
    _supported("notes", applier="_apply_notes", verifier="docx.notes"),
    _supported("notes.font", applier="_apply_notes", verifier="docx.notes"),
    _supported("appendix", applier="_apply_appendix_heading", verifier="docx.appendix"),
    _supported("appendix.title_font", applier="_apply_appendix_heading", verifier="docx.appendix"),
    _supported("appendix.body_font", applier="_apply_appendix_body", verifier="docx.appendix"),
    _partial(
        "list_numbering",
        applier=None,
        verifier="docx.numbering",
        note="Existing numbering is inspected; complex list-numbering synthesis is not fully deterministic.",
    ),
    _supported("unit_rules", applier="_normalize_body_text", verifier="docx.unit_rules"),
    _delegated("template_binding", verifier=None, note="Template binding is handled by TemplateLoader before formatting."),
    _delegated(
        "template_binding.body_slot",
        verifier="docx.template.body_slot",
        note="Template body-slot application is handled by TemplateLoader; QC verifies no consumed slot marker remains.",
    ),
    _delegated(
        "template_binding.placeholder_policy",
        verifier="docx.template.placeholders",
        note="Template placeholder handling is delegated to TemplateLoader; QC verifies no unresolved placeholders remain in final DOCX.",
    ),
    _supported("delivery_gate", applier="InternalDeliveryGateService", verifier="InternalDeliveryGateService"),
    _supported("llm_final_review", applier="OpenAICompatibleFinalLayoutReviewer", verifier="llm.layout_review"),
    _delegated("outputs", verifier="InternalDeliveryGateService", note="Requested output formats are handled by job/batch export orchestration."),
)


def registered_rule_specs() -> list[RuleSpec]:
    return list(RULE_SPECS)


def find_supported_rule_specs_without_handlers(specs: list[RuleSpec] | None = None) -> list[RuleSpec]:
    missing: list[RuleSpec] = []
    for spec in specs or registered_rule_specs():
        if spec.formatter == "supported" and not spec.applier:
            missing.append(spec)
            continue
        if spec.qc == "supported" and not spec.verifier:
            missing.append(spec)
    return missing


def resolve_rule_applier(spec: RuleSpec) -> Callable[..., object] | None:
    if not spec.applier:
        return None
    return _resolve_named_handler(spec.applier)


def resolve_rule_verifier(spec: RuleSpec) -> Callable[..., object] | None:
    if not spec.verifier:
        return None
    if spec.verifier.startswith("docx."):
        return _docx_check_verifier(spec.verifier)
    if spec.verifier == "llm.layout_review":
        return _llm_layout_review_verifier
    return _resolve_named_handler(spec.verifier)


def find_supported_rule_specs_without_callables(specs: list[RuleSpec] | None = None) -> list[RuleSpec]:
    missing: list[RuleSpec] = []
    for spec in specs or registered_rule_specs():
        if spec.formatter == "supported" and not callable(resolve_rule_applier(spec)):
            missing.append(spec)
            continue
        if spec.qc == "supported" and not callable(resolve_rule_verifier(spec)):
            missing.append(spec)
    return missing


def supported_docx_verifier_check_keys(specs: list[RuleSpec] | None = None) -> list[str]:
    return sorted(
        {
            spec.verifier
            for spec in specs or registered_rule_specs()
            if spec.qc == "supported" and spec.verifier and spec.verifier.startswith("docx.")
        }
    )


def supported_docx_field_paths_by_verifier(specs: list[RuleSpec] | None = None) -> dict[str, list[str]]:
    field_paths_by_verifier: dict[str, list[str]] = {}
    for spec in specs or registered_rule_specs():
        if spec.qc != "supported" or not spec.verifier or not spec.verifier.startswith("docx."):
            continue
        field_paths_by_verifier.setdefault(spec.verifier, []).append(spec.field_path)
    return {check_key: sorted(field_paths) for check_key, field_paths in field_paths_by_verifier.items()}


def annotate_docx_quality_issues_with_registry_fields(issues: list[QualityIssue]) -> list[QualityIssue]:
    fields_by_check_key = supported_docx_field_paths_by_verifier()
    annotated: list[QualityIssue] = []
    for issue in issues:
        field_paths = fields_by_check_key.get(issue.check_key)
        if not field_paths:
            annotated.append(issue)
            continue
        existing = issue.details.get(VERIFIED_PROFILE_FIELDS_DETAIL_KEY, [])
        merged = sorted({*field_paths, *(str(item) for item in existing)})
        annotated.append(
            issue.model_copy(
                update={
                    "details": {
                        **issue.details,
                        VERIFIED_PROFILE_FIELDS_DETAIL_KEY: merged,
                    }
                }
            )
        )
    return annotated


def supported_docx_formatter_applier_names(specs: list[RuleSpec] | None = None) -> list[str]:
    return sorted(
        {
            spec.applier
            for spec in specs or registered_rule_specs()
            if spec.formatter == "supported" and spec.applier and spec.applier.startswith("_")
        }
    )


def docx_formatter_field_paths_by_applier(specs: list[RuleSpec] | None = None) -> dict[str, list[str]]:
    field_paths_by_applier: dict[str, list[str]] = {}
    for spec in specs or registered_rule_specs():
        if spec.formatter not in {"supported", "partial"} or not spec.applier or not spec.applier.startswith("_"):
            continue
        field_paths_by_applier.setdefault(spec.applier, []).append(spec.field_path)
    return {applier: sorted(field_paths) for applier, field_paths in field_paths_by_applier.items()}


def summarize_docx_formatter_dispatch(
    call_counts: dict[str, int],
    specs: list[RuleSpec] | None = None,
) -> DocxFormatterDispatchResult:
    fields_by_applier = docx_formatter_field_paths_by_applier(specs)
    items = tuple(
        DocxFormatterDispatchItem(
            applier=applier,
            field_paths=tuple(fields_by_applier[applier]),
            call_count=call_counts.get(applier, 0),
        )
        for applier in sorted(fields_by_applier)
    )
    unexpected_appliers = tuple(sorted(set(call_counts) - set(fields_by_applier)))
    return DocxFormatterDispatchResult(items=items, unexpected_appliers=unexpected_appliers)


def find_supported_docx_verifier_keys_missing_from_issues(
    issues: list[QualityIssue],
    specs: list[RuleSpec] | None = None,
) -> list[str]:
    return list(verify_docx_rule_registry_coverage(issues, specs).missing_verifier_keys)


def execute_docx_rule_verifiers(
    docx_path: str | Path,
    profile: FormatProfile,
    *,
    inherited_header_footer: bool = False,
    specs: list[RuleSpec] | None = None,
) -> DocxRegistryDispatchResult:
    dispatches: list[DocxRuleVerifierDispatch] = []
    issues: list[QualityIssue] = []
    for check_key, field_paths in supported_docx_field_paths_by_verifier(specs).items():
        verifier = _docx_check_verifier(check_key)
        try:
            issue = verifier(
                docx_path,
                profile,
                inherited_header_footer=inherited_header_footer,
            )
        except Exception as exc:
            dispatches.append(
                DocxRuleVerifierDispatch(
                    check_key=check_key,
                    field_paths=tuple(field_paths),
                    issue_id=None,
                    status=None,
                    executed=False,
                    error=str(exc),
                )
            )
            continue
        if not isinstance(issue, QualityIssue):
            dispatches.append(
                DocxRuleVerifierDispatch(
                    check_key=check_key,
                    field_paths=tuple(field_paths),
                    issue_id=None,
                    status=None,
                    executed=False,
                    error=f"Verifier returned unsupported result type: {type(issue).__name__}",
                )
            )
            continue
        issues.append(issue)
        dispatches.append(
            DocxRuleVerifierDispatch(
                check_key=check_key,
                field_paths=tuple(field_paths),
                issue_id=issue.issue_id,
                status=issue.status,
                executed=True,
            )
        )
    return DocxRegistryDispatchResult(dispatches=tuple(dispatches), issues=tuple(issues))


def verify_docx_rule_registry_coverage(
    issues: list[QualityIssue],
    specs: list[RuleSpec] | None = None,
) -> DocxRegistryVerificationResult:
    issues_by_check_key: dict[str, list[QualityIssue]] = {}
    for issue in issues:
        issues_by_check_key.setdefault(issue.check_key, []).append(issue)

    verifications: list[DocxRuleVerification] = []
    missing_verifier_keys: set[str] = set()
    missing_field_paths: list[str] = []
    for spec in specs or registered_rule_specs():
        if spec.qc != "supported" or not spec.verifier or not spec.verifier.startswith("docx."):
            continue
        matched = issues_by_check_key.get(spec.verifier, [])
        covered = any(_issue_verifies_field_path(issue, spec.field_path) for issue in matched)
        if not covered:
            missing_verifier_keys.add(spec.verifier)
            missing_field_paths.append(spec.field_path)
        verifications.append(
            DocxRuleVerification(
                field_path=spec.field_path,
                check_key=spec.verifier,
                issue_ids=tuple(issue.issue_id for issue in matched),
                statuses=tuple(issue.status for issue in matched),
                covered=covered,
            )
        )

    return DocxRegistryVerificationResult(
        verifications=tuple(verifications),
        missing_verifier_keys=tuple(sorted(missing_verifier_keys)),
        missing_field_paths=tuple(sorted(missing_field_paths)),
    )


def _issue_verifies_field_path(issue: QualityIssue, field_path: str) -> bool:
    verified = issue.details.get(VERIFIED_PROFILE_FIELDS_DETAIL_KEY, [])
    if not isinstance(verified, list):
        return False
    return any(_field_covered(field_path, {str(item)}) for item in verified)


def _resolve_named_handler(name: str) -> Callable[..., object] | None:
    if name == "InternalDeliveryGateService":
        from app.quality.delivery_gate import InternalDeliveryGateService

        return InternalDeliveryGateService
    if name == "OpenAICompatibleFinalLayoutReviewer":
        from app.quality.final_layout_review import OpenAICompatibleFinalLayoutReviewer

        return OpenAICompatibleFinalLayoutReviewer

    from app.documents import formatter

    handler = getattr(formatter, name, None)
    return handler if callable(handler) else None


def _docx_check_verifier(check_key: str) -> Callable[..., object]:
    def verify_docx_check(
        docx_path: str | Path,
        profile: FormatProfile,
        *,
        inherited_header_footer: bool = False,
    ) -> object:
        from app.quality.inspection import inspect_docx_quality

        for issue in inspect_docx_quality(Path(docx_path), profile, inherited_header_footer=inherited_header_footer):
            if issue.check_key == check_key:
                return issue
        raise KeyError(f"DOCX quality check not found: {check_key}")

    verify_docx_check.__name__ = f"verify_{check_key.replace('.', '_')}"
    return verify_docx_check


def _llm_layout_review_verifier(pdf_path: str | Path, profile: FormatProfile, reviewer) -> object:
    from app.quality.final_layout_review import build_final_layout_payload

    return reviewer.review_pdf(build_final_layout_payload(Path(pdf_path), profile))


def build_capability_coverage(
    profile: FormatProfile,
    evidence: list[ExtractionEvidence],
    locked_fields: list[str],
) -> list[ProfileCapabilityCoverage]:
    evidence_sources = {
        item.field_path: _coverage_source_from_evidence(item.source)
        for item in evidence
    }
    field_paths = sorted({*(item.field_path for item in RULE_SPECS), *(item.field_path for item in evidence), *profile.missing_fields})
    locked = set(locked_fields)
    unsupported = {item.field_path for item in profile.unsupported_rules}
    coverage: list[ProfileCapabilityCoverage] = []
    for field_path in field_paths:
        spec = _rule_spec_for_field_path(field_path)
        is_unsupported = any(_field_covered(field_path, {item}) or _field_covered(item, {field_path}) for item in unsupported)
        if spec is None:
            formatter_status: ProfileCapabilityStatus = "unsupported"
            qc_status: ProfileCapabilityStatus = "unsupported"
            llm_status: ProfileCapabilityStatus = "unsupported"
            unsupported_behavior: UnsupportedBehavior = "block"
            source: ProfileRuleSourceKind = evidence_sources.get(field_path, "system")
            note = "未在规则注册表中声明，不能作为合规支持字段。"
        elif is_unsupported:
            formatter_status = "unsupported"
            qc_status = "unsupported"
            llm_status = spec.llm_final_review
            unsupported_behavior = "block"
            source = evidence_sources.get(field_path, spec.source)
            note = "Profile unsupported_rules 标记该字段当前不支持。"
        else:
            formatter_status = spec.formatter
            qc_status = spec.qc
            llm_status = spec.llm_final_review
            unsupported_behavior = spec.unsupported_behavior
            source = evidence_sources.get(field_path, spec.source)
            note = spec.note or "由规则能力注册表生成的支持状态。"
        coverage.append(
            ProfileCapabilityCoverage(
                field_path=field_path,
                frontend="supported",
                agent="supported",
                formatter=formatter_status,
                qc=qc_status,
                llm_final_review=llm_status,
                source=source,
                locked_by_user=_field_locked(field_path, locked),
                unsupported_behavior=unsupported_behavior,
                note=note,
            )
        )
    return coverage


def blocking_unsupported_capabilities(profile: FormatProfile) -> list[ProfileCapabilityCoverage]:
    if not profile.delivery_gate.fail_on_unsupported_rules:
        return []
    blocking_statuses = {"unsupported", "extract_only"}
    return [
        item
        for item in profile.capability_coverage
        if item.unsupported_behavior == "block"
        and (item.formatter in blocking_statuses or item.qc in blocking_statuses)
        and field_path_has_blocking_capability_gap(item.field_path)
    ]


def field_path_has_blocking_capability_gap(field_path: str) -> bool:
    current_spec = _rule_spec_for_field_path(field_path)
    if current_spec is None:
        return True
    return (
        current_spec.unsupported_behavior == "block"
        and (current_spec.formatter in {"unsupported", "extract_only"} or current_spec.qc in {"unsupported", "extract_only"})
    )


def _coverage_source_from_evidence(source: str) -> str:
    if source in {"style_sample_docx", "rule_document", "natural_language"}:
        return source
    if source == "document":
        return "rule_document"
    return "agent"


def _rule_spec_for_field_path(field_path: str) -> RuleSpec | None:
    matching = [spec for spec in RULE_SPECS if _field_matches_registered_spec(field_path, spec.field_path)]
    if not matching:
        return None
    return sorted(matching, key=lambda spec: len(spec.field_path), reverse=True)[0]


def _field_locked(field_path: str, locked_fields: set[str]) -> bool:
    normalized = _normalize_field_path(field_path)
    normalized_locked = {_normalize_field_path(item) for item in locked_fields}
    return normalized in normalized_locked or any(
        normalized.startswith(f"{item}.") or item.startswith(f"{normalized}.") for item in normalized_locked
    )


def _field_covered(field: str, covered: set[str]) -> bool:
    normalized = _normalize_field_path(field)
    normalized_covered = {_normalize_field_path(item) for item in covered}
    return normalized in normalized_covered or any(
        normalized.startswith(f"{item}.") or item.startswith(f"{normalized}.") for item in normalized_covered
    )


def _field_matches_registered_spec(field_path: str, spec_field_path: str) -> bool:
    return _normalize_field_path(field_path) == _normalize_field_path(spec_field_path)


def _normalize_field_path(field_path: str) -> str:
    return re.sub(r"\[\d+\]", "", field_path)
