from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.profiles.models import FormatProfile


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FileRecord(BaseModel):
    file_id: str
    filename: str
    mime_type: str
    size: int
    sha256: str
    storage_path: str
    created_at: datetime = Field(default_factory=utc_now)


JobStatus = Literal[
    "queued",
    "running",
    "completed",
    "quality_failed",
    "manual_review_required",
    "export_failed",
    "failed",
]


class JobRecord(BaseModel):
    job_id: str
    job_type: str
    input_file_id: str
    profile_id: str | None = None
    profile_version: str | None = None
    status: JobStatus = "queued"
    progress: int = 0
    current_step: str | None = None
    output_file_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


BatchStatus = Literal[
    "queued",
    "running",
    "partially_completed",
    "completed",
    "quality_failed",
    "manual_review_required",
    "export_failed",
    "failed",
]


class DeliveryManifestItem(BaseModel):
    input_file_id: str
    job_id: str
    final_docx_file_id: str | None = None
    final_pdf_file_id: str | None = None
    quality_report_id: str | None = None
    fix_loop_ids: list[str] = Field(default_factory=list)
    download_urls: dict[str, str] = Field(default_factory=dict)
    delivery_status: Literal["completed", "manual_review_required", "failed"] = "completed"


class BatchFormatRun(BaseModel):
    batch_id: str
    profile_id: str
    profile_version: str
    input_file_ids: list[str] = Field(min_length=1)
    job_ids: list[str] = Field(default_factory=list)
    status: BatchStatus = "queued"
    delivery_manifest_id: str | None = None
    manifest_download_url: str | None = None
    items: list[DeliveryManifestItem] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


ExtractionStatus = Literal["queued", "running", "completed", "failed", "needs_review"]
ExtractionSourceType = Literal["document", "natural_language"]
RequirementSessionSourceType = Literal["conversation", "document"]
RequirementSessionStatus = Literal[
    "collecting",
    "needs_user_answer",
    "ready_for_confirmation",
    "confirmed",
    "failed",
]
RequirementMessageRole = Literal["user", "agent", "system"]
RequirementRuleSource = Literal["conversation", "document", "system_default", "user_confirmed"]


class ExtractionEvidence(BaseModel):
    field_path: str
    source: ExtractionSourceType
    quote: str | None = None
    note: str | None = None
    confidence: float = Field(ge=0, le=1)


class UncertainItem(BaseModel):
    field_path: str
    message: str
    suggestion: str


class RequirementSessionMessage(BaseModel):
    role: RequirementMessageRole
    content: str
    created_at: datetime = Field(default_factory=utc_now)


class RequirementRuleItem(BaseModel):
    field_path: str
    label: str
    value: str
    source: RequirementRuleSource
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    needs_confirmation: bool = False
    supported: bool = True


class RequirementSummary(BaseModel):
    items: list[RequirementRuleItem] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_or_uncertain_rules: list[UncertainItem] = Field(default_factory=list)


class RequirementSession(BaseModel):
    session_id: str
    source_type: RequirementSessionSourceType
    status: RequirementSessionStatus = "collecting"
    file_id: str | None = None
    natural_language: str | None = None
    messages: list[RequirementSessionMessage] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    requirement_summary: RequirementSummary | None = None
    profile_draft: FormatProfile | None = None
    evidence: list[ExtractionEvidence] = Field(default_factory=list)
    uncertain_items: list[UncertainItem] = Field(default_factory=list)
    confirmed_profile_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProfileExtractionRecord(BaseModel):
    extraction_id: str
    source_type: ExtractionSourceType
    file_id: str | None = None
    natural_language: str | None = None
    status: ExtractionStatus = "queued"
    profile_draft: FormatProfile | None = None
    uncertain_items: list[UncertainItem] = Field(default_factory=list)
    evidence: list[ExtractionEvidence] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


QualityStatus = Literal["pass", "fixed", "warning", "fail", "unsupported"]
QualitySeverity = Literal["info", "low", "medium", "high"]
FixActionName = Literal[
    "reapply_profile_formatting",
    "apply_table_borders",
    "apply_body_paragraph_style",
    "apply_heading_style",
    "mark_manual_review",
]
FixLoopStatus = Literal["pending_confirmation", "confirmed", "running", "completed", "failed"]

QUALITY_STATUSES: tuple[QualityStatus, ...] = ("pass", "fixed", "warning", "fail", "unsupported")
REMAINING_QUALITY_STATUSES: set[QualityStatus] = {"warning", "fail", "unsupported"}


class QualityIssue(BaseModel):
    issue_id: str
    status: QualityStatus
    check_key: str
    title: str
    severity: QualitySeverity = "medium"
    description: str | None = None
    profile_rule_ref: str | None = None
    location: str | None = None
    recommendation: str | None = None
    fixable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class QualitySummary(BaseModel):
    counts: dict[QualityStatus, int] = Field(
        default_factory=lambda: {status: 0 for status in QUALITY_STATUSES}
    )
    remaining_issue_count: int = 0
    all_compliant: bool = True

    @classmethod
    def from_issues(cls, issues: list[QualityIssue]) -> "QualitySummary":
        counts = {status: 0 for status in QUALITY_STATUSES}
        for issue in issues:
            counts[issue.status] += 1
        remaining_issue_count = sum(counts[status] for status in REMAINING_QUALITY_STATUSES)
        return cls(
            counts=counts,
            remaining_issue_count=remaining_issue_count,
            all_compliant=remaining_issue_count == 0,
        )


class QualityReport(BaseModel):
    report_id: str
    job_id: str | None = None
    profile_id: str
    profile_version: str
    output_file_ids: list[str] = Field(default_factory=list)
    summary: QualitySummary
    issues: list[QualityIssue] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @computed_field
    @property
    def issues_by_status(self) -> dict[QualityStatus, list[QualityIssue]]:
        grouped: dict[QualityStatus, list[QualityIssue]] = {status: [] for status in QUALITY_STATUSES}
        for issue in self.issues:
            grouped[issue.status].append(issue)
        return grouped


class FixAction(BaseModel):
    action: FixActionName
    target_issue_ids: list[str] = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    requires_user_confirmation: bool = True

    @model_validator(mode="after")
    def require_confirmation(self) -> "FixAction":
        if not self.requires_user_confirmation:
            raise ValueError("Fix actions must require user confirmation.")
        return self


class IssueExplanation(BaseModel):
    issue_id: str
    reason: str
    impact: str
    automatic_repair_allowed: bool
    manual_review_guidance: str


class FixPlan(BaseModel):
    fix_plan_id: str
    report_id: str
    actions: list[FixAction] = Field(default_factory=list)
    explanations: list[IssueExplanation] = Field(default_factory=list)
    manual_review_issue_ids: list[str] = Field(default_factory=list)
    explanation: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @property
    def requires_user_confirmation(self) -> bool:
        return any(action.requires_user_confirmation for action in self.actions)


class FixLoopRecord(BaseModel):
    fix_loop_id: str
    original_report_id: str
    fix_plan_id: str
    selected_issue_ids: list[str] = Field(default_factory=list)
    selected_actions: list[FixAction] = Field(default_factory=list)
    status: FixLoopStatus = "pending_confirmation"
    new_job_id: str | None = None
    new_output_file_ids: list[str] = Field(default_factory=list)
    updated_report_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
