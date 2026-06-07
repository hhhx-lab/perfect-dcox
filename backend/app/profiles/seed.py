from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.profiles.models import FormatProfile


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_profile_yaml(path: Path) -> FormatProfile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Profile seed must be a mapping: {path}")
    return FormatProfile.model_validate(raw)


def profile_to_yaml(profile: FormatProfile) -> str:
    data: dict[str, Any] = profile.model_dump(mode="json", exclude_none=True)
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def load_builtin_profiles(seed_dir: Path | None = None) -> dict[str, FormatProfile]:
    root = seed_dir or project_root() / "profiles"
    profiles: dict[str, FormatProfile] = {}
    for path in sorted(root.glob("*.yaml")):
        profile = load_profile_yaml(path)
        profiles[profile.id] = profile
    return profiles
