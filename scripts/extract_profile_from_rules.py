#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.agents.requirements import OpenAICompatibleRequirementProvider, RequirementSessionService  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.models import FileRecord, RequirementSessionAttachment  # noqa: E402
from app.profiles.seed import profile_to_yaml  # noqa: E402
from app.storage.repository import JsonMetadataRepository  # noqa: E402


def main() -> int:
    _load_env_files()
    args = _parse_args()
    settings = Settings()
    if not settings.llm_configured:
        raise SystemExit("LLM_API_KEY and LLM_MODEL are required; cannot analyze formatting rules without LLM.")

    rules_path = args.rules.expanduser().resolve()
    if not rules_path.exists():
        raise SystemExit(f"Rule document does not exist: {rules_path}")

    storage_root = args.storage_root.expanduser().resolve() if args.storage_root else settings.file_storage_root.resolve()
    repository = JsonMetadataRepository(storage_root / "metadata.json")
    file_record = _register_file(repository, rules_path)
    service = RequirementSessionService(
        repository,
        storage_root,
        settings.soffice_bin,
        provider=OpenAICompatibleRequirementProvider(settings),
    )
    session = service.create_session(
        "document",
        file_id=file_record.file_id,
        attachments=[
            RequirementSessionAttachment(
                file_id=file_record.file_id,
                source_kind="rule_document",
                filename=file_record.filename,
            )
        ],
    )
    if session.profile_draft is None:
        raise SystemExit("Requirement session did not produce a profile draft.")

    output_path = args.output.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".json":
        output_path.write_text(
            json.dumps(session.profile_draft.model_dump(mode="json", exclude_none=True), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    else:
        output_path.write_text(profile_to_yaml(session.profile_draft), encoding="utf-8")

    summary_path = args.summary_output.expanduser().resolve() if args.summary_output else None
    if summary_path:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(_session_summary(session, output_path), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                "status": session.status,
                "session_id": session.session_id,
                "profile_output": str(output_path),
                "missing_fields": session.missing_fields,
                "rule_count": len(session.requirement_summary.items) if session.requirement_summary else 0,
                "evidence_count": len(session.evidence),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a FormatProfile from a rule document using the same LLM Agent path as the backend."
    )
    parser.add_argument("--rules", required=True, type=Path, help="Rule document path (.doc or .docx).")
    parser.add_argument("--output", required=True, type=Path, help="Profile YAML or JSON output path.")
    parser.add_argument("--summary-output", type=Path, help="Optional session summary JSON path.")
    parser.add_argument("--storage-root", type=Path, help="Optional storage root; defaults to FILE_STORAGE_ROOT.")
    return parser.parse_args()


def _register_file(repository: JsonMetadataRepository, path: Path) -> FileRecord:
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    file_id = f"file_rules_{digest[:16]}"
    existing = repository.get_file(file_id)
    if existing is not None and Path(existing.storage_path).resolve() == path:
        return existing
    record = FileRecord(
        file_id=file_id,
        filename=path.name,
        mime_type=_mime_type(path),
        size=len(content),
        sha256=digest,
        storage_path=str(path),
    )
    return repository.add_file(record)


def _mime_type(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if path.suffix.lower() == ".doc":
        return "application/msword"
    return "application/octet-stream"


def _session_summary(session: Any, output_path: Path) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "status": session.status,
        "profile_output": str(output_path),
        "missing_fields": session.missing_fields,
        "items": [item.model_dump(mode="json") for item in (session.requirement_summary.items if session.requirement_summary else [])],
        "evidence": [item.model_dump(mode="json") for item in session.evidence],
        "uncertain_items": [item.model_dump(mode="json") for item in session.uncertain_items],
    }


def _load_env_files() -> None:
    for path in (ROOT / ".env", BACKEND / ".env"):
        if path.exists():
            load_dotenv(path, override=False)


if __name__ == "__main__":
    raise SystemExit(main())
