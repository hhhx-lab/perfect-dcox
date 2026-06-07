import pytest
from pydantic import ValidationError

from app.profiles.models import FormatProfile


def valid_profile_payload() -> dict[str, object]:
    return {
        "id": "sample_thesis",
        "name": "Sample Thesis",
        "version": "1.0.0",
        "status": "active",
        "source": "system",
        "description": "A deterministic thesis formatting profile.",
        "page": {
            "size": "A4",
            "orientation": "portrait",
            "margins_cm": {
                "top": 2.5,
                "bottom": 2.0,
                "left": 3.0,
                "right": 2.5,
                "gutter": 0.0,
            },
        },
        "fonts": {
            "default_chinese": "SimSun",
            "default_latin": "Times New Roman",
            "default_size_pt": 12,
        },
        "body": {
            "font": {
                "chinese": "SimSun",
                "latin": "Times New Roman",
                "size_pt": 12,
                "weight": "normal",
            },
            "first_line_indent_chars": 2,
            "line_spacing": 1.5,
            "alignment": "justified",
        },
        "headings": [
            {
                "level": 1,
                "font": {
                    "chinese": "SimHei",
                    "latin": "Times New Roman",
                    "size_pt": 15,
                    "weight": "bold",
                },
                "alignment": "center",
                "numbering": "none",
            }
        ],
        "abstract": {
            "length_range_chars": {"min": 300, "max": 500},
            "title_font": {
                "chinese": "SimHei",
                "latin": "Times New Roman",
                "size_pt": 15,
                "weight": "bold",
            },
            "body_font": {
                "chinese": "SimSun",
                "latin": "Times New Roman",
                "size_pt": 10.5,
                "weight": "normal",
            },
        },
        "table": {
            "caption": {
                "position": "above",
                "prefix": "表",
                "font": {
                    "chinese": "SimSun",
                    "latin": "Times New Roman",
                    "size_pt": 10.5,
                    "weight": "normal",
                },
            }
        },
        "figure": {
            "caption": {
                "position": "below",
                "prefix": "图",
                "font": {
                    "chinese": "SimSun",
                    "latin": "Times New Roman",
                    "size_pt": 10.5,
                    "weight": "normal",
                },
            }
        },
        "equations": {
            "alignment": "center",
            "numbering": "right",
            "font": "Cambria Math",
        },
        "references": {
            "style": "GB/T 7714",
            "font": {
                "chinese": "SimSun",
                "latin": "Times New Roman",
                "size_pt": 10.5,
                "weight": "normal",
            },
            "hanging_indent_chars": 2,
        },
        "quality": {
            "check_margins": True,
            "check_fonts": True,
            "check_line_spacing": True,
            "check_headings": True,
            "check_references": True,
            "strictness": "standard",
        },
    }


def test_valid_profile_payload_is_accepted() -> None:
    profile = FormatProfile.model_validate(valid_profile_payload())

    assert profile.id == "sample_thesis"
    assert profile.page.margins_cm.left == 3.0
    assert profile.body.font.latin == "Times New Roman"


def test_missing_required_profile_field_is_rejected() -> None:
    payload = valid_profile_payload()
    payload.pop("page")

    with pytest.raises(ValidationError) as exc:
        FormatProfile.model_validate(payload)

    assert "page" in str(exc.value)


def test_invalid_enum_and_numeric_range_are_rejected() -> None:
    payload = valid_profile_payload()
    payload["page"]["orientation"] = "diagonal"  # type: ignore[index]
    payload["body"]["line_spacing"] = 0  # type: ignore[index]

    with pytest.raises(ValidationError) as exc:
        FormatProfile.model_validate(payload)

    message = str(exc.value)
    assert "orientation" in message
    assert "line_spacing" in message


def test_unknown_profile_fields_are_rejected() -> None:
    payload = valid_profile_payload()
    payload["prompt"] = "please format this like a thesis"

    with pytest.raises(ValidationError) as exc:
        FormatProfile.model_validate(payload)

    assert "Extra inputs are not permitted" in str(exc.value)
