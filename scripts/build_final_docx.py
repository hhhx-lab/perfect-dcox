#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import Settings  # noqa: E402
from app.documents.compiler import FormatCompiler  # noqa: E402
from app.documents.converter import convert_doc_to_docx  # noqa: E402
from app.documents.exporter import export_docx_to_pdf  # noqa: E402
from app.profiles.models import FormatProfile  # noqa: E402
from app.quality.delivery_gate import InternalDeliveryGateService  # noqa: E402
from app.quality.final_layout_review import OpenAICompatibleFinalLayoutReviewer  # noqa: E402


def main() -> int:
    args = _parse_args()
    settings = Settings()
    profile = _load_profile(args.profile)
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    template_path = args.template.expanduser().resolve() if args.template else None
    pdf_output_path = args.pdf_output.expanduser().resolve() if args.pdf_output else None

    if not input_path.exists():
        raise SystemExit(f"Input file does not exist: {input_path}")
    if template_path and not template_path.exists():
        raise SystemExit(f"Template file does not exist: {template_path}")

    work_dir_context = TemporaryDirectory(prefix="perfect-docx-build-") if args.work_dir is None else None
    try:
        work_dir = args.work_dir.expanduser().resolve() if args.work_dir else Path(work_dir_context.name)
        work_dir.mkdir(parents=True, exist_ok=True)

        docx_input = convert_doc_to_docx(input_path, work_dir, settings.soffice_bin)
        candidate_path = work_dir / f"{input_path.stem}-candidate.docx"
        compiled = FormatCompiler().compile(docx_input, candidate_path, profile, template_path=template_path)
        inherited_header_footer = bool(compiled.metadata.get("header_footer_inherited"))
        reviewer = OpenAICompatibleFinalLayoutReviewer(settings) if settings.llm_configured else None
        gate = InternalDeliveryGateService(final_layout_reviewer=reviewer)

        docx_gate = gate.validate_docx(
            compiled.candidate_path,
            profile,
            work_dir,
            inherited_header_footer=inherited_header_footer,
        )
        if not docx_gate.passed:
            _print_summary(
                {
                    "status": "quality_failed",
                    "failure_reason": docx_gate.failure_reason,
                    "docx_gate": docx_gate.public_summary(),
                    "compile": _compile_summary(compiled.metadata),
                }
            )
            return 2

        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(docx_gate.docx_path, output_path)
        result: dict[str, Any] = {
            "status": "completed",
            "docx_output": str(output_path),
            "docx_gate": docx_gate.public_summary(),
            "compile": _compile_summary(compiled.metadata),
        }

        if args.include_pdf or pdf_output_path:
            if pdf_output_path is None:
                pdf_output_path = output_path.with_suffix(".pdf")
            pdf_path = export_docx_to_pdf(output_path, work_dir, settings.soffice_bin)
            if profile.delivery_gate.require_pdf_inspection:
                pdf_gate = gate.validate_pdf(pdf_path)
                result["pdf_gate"] = pdf_gate.public_summary()
                if not pdf_gate.passed:
                    _print_summary({**result, "status": "quality_failed", "failure_reason": pdf_gate.failure_reason})
                    return 3
            layout_gate = gate.validate_final_layout(pdf_path, profile)
            result["llm_layout_review"] = layout_gate.public_summary()
            if not layout_gate.passed:
                _print_summary(
                    {
                        **result,
                        "status": "failed",
                        "failure_reason": layout_gate.failure_reason,
                    }
                )
                return 4
            pdf_output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdf_path, pdf_output_path)
            result["pdf_output"] = str(pdf_output_path)

        _print_summary(result)
        return 0
    finally:
        if work_dir_context is not None:
            work_dir_context.cleanup()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a final DOCX/PDF with the same compiler and internal delivery gate as the backend service."
    )
    parser.add_argument("--profile", required=True, type=Path, help="Profile YAML or JSON path.")
    parser.add_argument("--input", required=True, type=Path, help="Input .doc or .docx path.")
    parser.add_argument("--output", required=True, type=Path, help="Final DOCX output path.")
    parser.add_argument("--template", type=Path, help="Optional template DOCX path.")
    parser.add_argument("--include-pdf", action="store_true", help="Also export and validate PDF next to output DOCX.")
    parser.add_argument("--pdf-output", type=Path, help="Explicit final PDF output path; implies --include-pdf.")
    parser.add_argument("--work-dir", type=Path, help="Optional persistent work directory for candidate/debug files.")
    return parser.parse_args()


def _load_profile(path: Path) -> FormatProfile:
    raw_text = path.expanduser().resolve().read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        raw = json.loads(raw_text)
    else:
        raw = yaml.safe_load(raw_text)
    if not isinstance(raw, dict):
        raise SystemExit(f"Profile must be a mapping: {path}")
    return FormatProfile.model_validate(raw)


def _compile_summary(metadata: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in metadata.items()
        if key in {"profile_schema_version", "template_path", "body_slot", "header_footer_inherited", "formatter_registry"}
    }


def _print_summary(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
