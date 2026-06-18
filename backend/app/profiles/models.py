from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ProfileStatus = Literal["draft", "active", "archived"]
ProfileSource = Literal["system", "user", "imported"]
Orientation = Literal["portrait", "landscape"]
TextAlignment = Literal["left", "center", "right", "justified"]
FontWeight = Literal["normal", "bold"]
CaptionPosition = Literal["above", "below"]
EquationNumbering = Literal["none", "left", "right"]
QualityStrictness = Literal["lenient", "standard", "strict"]
PlaceholderPolicy = Literal["fail", "preserve", "remove"]
DocumentGridType = Literal["none", "line", "line_and_character"]
CaptionNumbering = Literal["continuous", "chapter", "section"]
FigurePlacement = Literal["inline", "floating", "anchored"]
TableBorderStyle = Literal["three_line", "full_grid", "minimal", "custom"]
UnitSpacingPolicy = Literal["preserve", "space", "no_space"]
PageNumberFormat = Literal["arabic", "roman_lower", "roman_upper", "none"]
ProfileCapabilityStatus = Literal["supported", "partial", "extract_only", "template_delegated", "unsupported"]
ProfileRuleSourceKind = Literal["agent", "style_sample_docx", "rule_document", "natural_language", "visual", "system"]


class MarginSettings(StrictModel):
    top: float = Field(gt=0, le=10)
    bottom: float = Field(gt=0, le=10)
    left: float = Field(gt=0, le=10)
    right: float = Field(gt=0, le=10)
    gutter: float = Field(default=0, ge=0, le=10)


class PageSettings(StrictModel):
    size: Literal["A4", "Letter"]
    orientation: Orientation
    margins_cm: MarginSettings


class FontDefaults(StrictModel):
    default_chinese: str = Field(min_length=1)
    default_latin: str = Field(min_length=1)
    default_size_pt: float = Field(gt=0, le=72)


class TextFont(StrictModel):
    chinese: str = Field(min_length=1)
    latin: str = Field(min_length=1)
    size_pt: float = Field(gt=0, le=72)
    weight: FontWeight = "normal"
    color: str = Field(default="000000", pattern=r"^[0-9A-Fa-f]{6}$")

    @field_validator("color", mode="before")
    @classmethod
    def normalize_color(cls, value: str) -> str:
        return str(value).strip().lstrip("#").upper()


class BodySettings(StrictModel):
    font: TextFont
    first_line_indent_chars: float = Field(ge=0, le=10)
    line_spacing: float = Field(gt=0, le=5)
    alignment: TextAlignment
    space_before_pt: float = Field(default=0, ge=0, le=72)
    space_after_pt: float = Field(default=0, ge=0, le=72)


class HeadingSettings(StrictModel):
    level: int = Field(ge=1, le=9)
    font: TextFont
    alignment: TextAlignment
    numbering: str = Field(min_length=1)
    line_spacing: float | None = Field(default=None, gt=0, le=5)
    space_before_pt: float = Field(default=0, ge=0, le=72)
    space_after_pt: float = Field(default=0, ge=0, le=72)
    first_line_indent_chars: float = Field(default=0, ge=0, le=10)
    keep_with_next: bool = False
    page_break_before: bool = False


class CharacterRange(StrictModel):
    min: int = Field(ge=0)
    max: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> CharacterRange:
        if self.max < self.min:
            raise ValueError("max must be greater than or equal to min")
        return self


class AbstractSettings(StrictModel):
    length_range_chars: CharacterRange
    title_font: TextFont
    body_font: TextFont


class CaptionSettings(StrictModel):
    position: CaptionPosition
    prefix: str = Field(min_length=1)
    font: TextFont
    bilingual: bool = False
    english_prefix: str | None = None
    separator: str = Field(default=" ")
    numbering: CaptionNumbering = "chapter"


class TableSettings(StrictModel):
    caption: CaptionSettings
    border_style: TableBorderStyle = "three_line"
    header_repeat: bool = True
    autofit: bool = True
    notes_position: Literal["none", "below", "above"] = "below"
    enforce_caption_above: bool = True


class FigureSettings(StrictModel):
    caption: CaptionSettings
    placement: FigurePlacement = "inline"
    half_column_max_mm: float = Field(default=60, gt=0, le=300)
    full_width_min_mm: float = Field(default=100, gt=0, le=300)
    full_width_max_mm: float = Field(default=130, gt=0, le=300)
    enforce_caption_below: bool = True

    @model_validator(mode="after")
    def validate_width_ranges(self) -> FigureSettings:
        if self.full_width_max_mm <= self.full_width_min_mm:
            raise ValueError("full_width_max_mm must be greater than full_width_min_mm")
        if self.half_column_max_mm >= self.full_width_min_mm:
            raise ValueError("half_column_max_mm must be less than full_width_min_mm")
        return self


class EquationSettings(StrictModel):
    alignment: TextAlignment
    numbering: EquationNumbering
    font: str = Field(min_length=1)


class ReferenceSettings(StrictModel):
    style: str = Field(min_length=1)
    font: TextFont
    hanging_indent_chars: float = Field(ge=0, le=10)


class NotesSettings(StrictModel):
    font: TextFont = Field(
        default_factory=lambda: TextFont(
            chinese="SimSun",
            latin="Times New Roman",
            size_pt=9.0,
            weight="normal",
            color="000000",
        )
    )
    line_spacing: float = Field(default=1.0, gt=0, le=5)
    space_before_pt: float = Field(default=0, ge=0, le=72)
    space_after_pt: float = Field(default=0, ge=0, le=72)


class AppendixSettings(StrictModel):
    title_font: TextFont = Field(
        default_factory=lambda: TextFont(
            chinese="SimHei",
            latin="Times New Roman",
            size_pt=12.0,
            weight="bold",
            color="000000",
        )
    )
    body_font: TextFont = Field(
        default_factory=lambda: TextFont(
            chinese="SimSun",
            latin="Times New Roman",
            size_pt=12.0,
            weight="normal",
            color="000000",
        )
    )
    title_alignment: TextAlignment = "left"
    body_alignment: TextAlignment = "justified"
    body_line_spacing: float = Field(default=1.5, gt=0, le=5)
    body_first_line_indent_chars: float = Field(default=2, ge=0, le=10)


class HeaderFooterSettings(StrictModel):
    header_text: str | None = None
    header_alignment: TextAlignment = "center"
    footer_text: str | None = None
    footer_page_number: bool = True
    footer_alignment: TextAlignment = "center"
    font: TextFont
    different_first_page: bool = False
    different_odd_even: bool = False
    page_number_format: PageNumberFormat = "arabic"
    page_number_start: int = Field(default=1, ge=0, le=10000)


class QualitySettings(StrictModel):
    check_margins: bool = True
    check_fonts: bool = True
    check_line_spacing: bool = True
    check_headings: bool = True
    check_references: bool = True
    strictness: QualityStrictness = "standard"


class ProfileRuleEvidence(StrictModel):
    field_path: str = Field(min_length=1)
    source: str = Field(min_length=1)
    quote: str | None = None
    note: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class ProfileUnsupportedRule(StrictModel):
    field_path: str = Field(min_length=1)
    message: str = Field(min_length=1)
    suggestion: str | None = None
    source: str | None = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class ProfileSourceDocument(StrictModel):
    file_id: str | None = None
    filename: str | None = None
    source_kind: ProfileRuleSourceKind
    extracted_at: datetime | None = None
    note: str | None = None


class ProfileCapabilityCoverage(StrictModel):
    field_path: str = Field(min_length=1)
    frontend: ProfileCapabilityStatus = "supported"
    agent: ProfileCapabilityStatus = "supported"
    formatter: ProfileCapabilityStatus = "supported"
    qc: ProfileCapabilityStatus = "supported"
    llm_final_review: ProfileCapabilityStatus = "supported"
    source: ProfileRuleSourceKind = "system"
    locked_by_user: bool = False
    unsupported_behavior: Literal["block", "warn"] = "block"
    note: str | None = None


class ProfileManualOverride(StrictModel):
    field_path: str = Field(min_length=1)
    old_value: object | None = None
    new_value: object | None = None
    source: Literal["visual", "conversation"] = "visual"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMFinalReviewSettings(StrictModel):
    enabled: bool = True
    required: bool = True
    check_garbled_text: bool = True
    check_blank_pages: bool = True
    check_overlap: bool = True
    check_table_figure_overflow: bool = True


class ProfileSectionRule(StrictModel):
    key: str = Field(min_length=1)
    title: str | None = None
    start_on_new_page: bool = False
    required: bool = False
    style_ref: str | None = None


class DocumentGridSettings(StrictModel):
    enabled: bool = False
    type: DocumentGridType = "none"
    characters_per_line: int | None = Field(default=None, ge=1, le=80)
    lines_per_page: int | None = Field(default=None, ge=1, le=80)
    snap_to_grid: bool = False


class TocSettings(StrictModel):
    enabled: bool = True
    title: str = Field(default="目录", min_length=1)
    include_levels: int = Field(default=3, ge=1, le=9)
    show_page_numbers: bool = True
    right_align_page_numbers: bool = True
    use_hyperlinks: bool = True
    update_fields_on_open: bool = True


class ListNumberingSettings(StrictModel):
    ordered_pattern: str = Field(default="1.")
    unordered_marker: str = Field(default="·")
    multilevel_enabled: bool = True
    restart_per_section: bool = False


class NumberingSettings(StrictModel):
    enabled: bool = True
    heading_pattern: str | None = None
    restart_per_section: bool = False


class UnitRulesSettings(StrictModel):
    enforce_consistency: bool = True
    measurement_units: list[str] = Field(default_factory=lambda: ["mm", "cm", "m", "kg", "s"])
    currency_units: list[str] = Field(default_factory=lambda: ["元", "万元", "CNY", "USD"])
    unit_spacing: UnitSpacingPolicy = "preserve"
    use_si_symbols: bool = True
    normalize_fullwidth_numbers: bool = True


class TemplateBindingSettings(StrictModel):
    template_file_id: str | None = None
    template_name: str | None = None
    body_slot: str | None = "{{BODY}}"
    fixed_sections: list[str] = Field(default_factory=list)
    inherit_header_footer: bool = True
    placeholder_policy: PlaceholderPolicy = "fail"


class DeliveryGateSettings(StrictModel):
    require_internal_qc: bool = True
    allow_auto_fix: bool = True
    require_pdf_inspection: bool = True
    fail_on_unsupported_rules: bool = True


class FormatProfile(StrictModel):
    schema_version: str = Field(default="1.0.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9_.-]+)?$")
    status: ProfileStatus
    source: ProfileSource
    description: str | None = None
    page: PageSettings
    fonts: FontDefaults
    body: BodySettings
    headings: list[HeadingSettings] = Field(min_length=1)
    abstract: AbstractSettings
    table: TableSettings
    figure: FigureSettings
    equations: EquationSettings
    references: ReferenceSettings
    notes: NotesSettings = Field(default_factory=NotesSettings)
    appendix: AppendixSettings = Field(default_factory=AppendixSettings)
    header_footer: HeaderFooterSettings
    quality: QualitySettings
    document_grid: DocumentGridSettings = Field(default_factory=DocumentGridSettings)
    toc: TocSettings = Field(default_factory=TocSettings)
    sections: list[ProfileSectionRule] = Field(default_factory=list)
    list_numbering: ListNumberingSettings = Field(default_factory=ListNumberingSettings)
    numbering: NumberingSettings = Field(default_factory=NumberingSettings)
    unit_rules: UnitRulesSettings = Field(default_factory=UnitRulesSettings)
    template_binding: TemplateBindingSettings = Field(default_factory=TemplateBindingSettings)
    delivery_gate: DeliveryGateSettings = Field(default_factory=DeliveryGateSettings)
    source_documents: list[ProfileSourceDocument] = Field(default_factory=list)
    capability_coverage: list[ProfileCapabilityCoverage] = Field(default_factory=list)
    manual_overrides: list[ProfileManualOverride] = Field(default_factory=list)
    locked_fields: list[str] = Field(default_factory=list)
    llm_final_review: LLMFinalReviewSettings = Field(default_factory=LLMFinalReviewSettings)
    rule_evidence: list[ProfileRuleEvidence] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    unsupported_rules: list[ProfileUnsupportedRule] = Field(default_factory=list)


class ProfileSummary(StrictModel):
    profile_id: str
    name: str
    status: ProfileStatus
    current_version: str
    source: ProfileSource
    updated_at: datetime


class ProfileVersionRecord(StrictModel):
    profile_id: str
    version: str
    profile: FormatProfile
    created_at: datetime
