from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class BodySettings(StrictModel):
    font: TextFont
    first_line_indent_chars: float = Field(ge=0, le=10)
    line_spacing: float = Field(gt=0, le=5)
    alignment: TextAlignment


class HeadingSettings(StrictModel):
    level: int = Field(ge=1, le=9)
    font: TextFont
    alignment: TextAlignment
    numbering: str = Field(min_length=1)


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


class CaptionContainer(StrictModel):
    caption: CaptionSettings


class EquationSettings(StrictModel):
    alignment: TextAlignment
    numbering: EquationNumbering
    font: str = Field(min_length=1)


class ReferenceSettings(StrictModel):
    style: str = Field(min_length=1)
    font: TextFont
    hanging_indent_chars: float = Field(ge=0, le=10)


class QualitySettings(StrictModel):
    check_margins: bool = True
    check_fonts: bool = True
    check_line_spacing: bool = True
    check_headings: bool = True
    check_references: bool = True
    strictness: QualityStrictness = "standard"


class FormatProfile(StrictModel):
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
    table: CaptionContainer
    figure: CaptionContainer
    equations: EquationSettings
    references: ReferenceSettings
    quality: QualitySettings


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
