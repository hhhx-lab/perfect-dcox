import pytest
from pydantic import ValidationError

from app.profiles.models import FormatProfile
from app.profiles.seed import load_builtin_profiles, profile_to_yaml
from app.storage.repository import DuplicateProfileVersionError, JsonMetadataRepository


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
        "header_footer": {
            "header_text": None,
            "header_alignment": "center",
            "footer_page_number": True,
            "footer_alignment": "center",
            "font": {
                "chinese": "SimSun",
                "latin": "Times New Roman",
                "size_pt": 10.5,
                "weight": "normal",
            },
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


def test_ecnu_builtin_profile_is_loaded_from_yaml() -> None:
    profiles = load_builtin_profiles()

    ecnu = profiles["ecnu_thesis"]
    assert ecnu.status == "active"
    assert ecnu.version == "1.0.0"
    assert ecnu.source == "system"
    assert ecnu.page.size == "A4"
    assert ecnu.page.margins_cm.top == 2.5
    assert ecnu.page.margins_cm.bottom == 2.0
    assert ecnu.page.margins_cm.left == 3.0
    assert ecnu.page.margins_cm.right == 2.5
    assert ecnu.fonts.default_chinese == "SimSun"
    assert ecnu.fonts.default_latin == "Times New Roman"
    assert ecnu.body.line_spacing == 1.5
    assert ecnu.body.first_line_indent_chars == 2
    assert ecnu.abstract.length_range_chars.min == 300
    assert ecnu.abstract.length_range_chars.max == 500
    assert ecnu.table.caption.position == "above"
    assert ecnu.figure.caption.position == "below"
    assert ecnu.header_footer.footer_page_number is True
    assert ecnu.quality.check_fonts is True


def test_profile_yaml_round_trip_preserves_validated_fields() -> None:
    ecnu = load_builtin_profiles()["ecnu_thesis"]

    exported = profile_to_yaml(ecnu)
    reloaded = FormatProfile.model_validate(__import__("yaml").safe_load(exported))

    assert reloaded == ecnu
    assert "ecnu_thesis" in exported


def test_invalid_character_range_is_rejected() -> None:
    payload = valid_profile_payload()
    payload["abstract"]["length_range_chars"] = {"min": 500, "max": 300}  # type: ignore[index]

    with pytest.raises(ValidationError) as exc:
        FormatProfile.model_validate(payload)

    assert "max must be greater than or equal to min" in str(exc.value)


def test_repository_persists_profile_versions_and_rejects_duplicates(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    ecnu = load_builtin_profiles()["ecnu_thesis"]
    updated = ecnu.model_copy(update={"version": "1.0.1", "name": "ECNU Updated"})

    repository.save_profile_version(ecnu)
    repository.save_profile_version(updated)

    summaries = repository.list_profiles()
    assert len(summaries) == 1
    assert summaries[0].profile_id == "ecnu_thesis"
    assert summaries[0].current_version == "1.0.1"
    assert summaries[0].name == "ECNU Updated"
    assert repository.get_profile_version("ecnu_thesis", "1.0.0") == ecnu
    assert repository.get_profile_version("ecnu_thesis", "1.0.1") == updated

    with pytest.raises(DuplicateProfileVersionError):
        repository.save_profile_version(updated)


def test_repository_archives_profile_without_deleting_versions(tmp_path) -> None:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    ecnu = load_builtin_profiles()["ecnu_thesis"]

    repository.save_profile_version(ecnu)
    archived = repository.archive_profile("ecnu_thesis")

    assert archived is not None
    assert archived.status == "archived"
    assert repository.get_profile_version("ecnu_thesis", "1.0.0") == ecnu


def test_repository_handles_legacy_metadata_without_profile_keys(tmp_path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"files": {}, "jobs": {}}', encoding="utf-8")
    repository = JsonMetadataRepository(metadata_path)

    assert repository.list_profiles() == []
