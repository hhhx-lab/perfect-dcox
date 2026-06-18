from __future__ import annotations

from pathlib import Path

from app.documents.compiler import DocumentCompileError, FormatCompiler
from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.parser import DocumentParseError, parse_docx
from app.models import FileRecord
from app.quality.delivery_gate import InternalDeliveryGateError, InternalDeliveryGateService
from app.quality.final_layout_review import FinalLayoutReviewer
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"


class DocumentFormattingError(RuntimeError):
    pass


class DocumentFormattingService:
    def __init__(
        self,
        repository: JsonMetadataRepository,
        storage: LocalFileStorage,
        soffice_bin: str | None,
        final_layout_reviewer: FinalLayoutReviewer | None = None,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.soffice_bin = soffice_bin
        self.compiler = FormatCompiler()
        self.delivery_gate = InternalDeliveryGateService(final_layout_reviewer=final_layout_reviewer)
        self.last_delivery_gate_summary: dict[str, object] = {}

    def format_job(
        self,
        input_file_id: str,
        profile_id: str,
        profile_version: str,
        include_pdf: bool = False,
        template_file_id: str | None = None,
    ) -> list[FileRecord]:
        self.last_delivery_gate_summary = {}
        input_record = self.repository.get_file(input_file_id)
        if input_record is None:
            raise DocumentFormattingError(f"Input file not found: {input_file_id}")
        profile = self.repository.get_profile_version(profile_id, profile_version)
        if profile is None:
            raise DocumentFormattingError(f"Profile version not found: {profile_id} {profile_version}")
        template_path = self._resolve_template_path(template_file_id or profile.template_binding.template_file_id)

        input_path = Path(input_record.storage_path)
        work_dir = self.storage.root / "work" / input_file_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            docx_input = convert_doc_to_docx(input_path, work_dir, self.soffice_bin)
            parse_docx(docx_input)
            candidate_path = work_dir / f"{input_path.stem}-candidate.docx"
            compiled = self.compiler.compile(docx_input, candidate_path, profile, template_path=template_path)
            inherited_header_footer = bool(compiled.metadata.get("header_footer_inherited"))
            docx_gate = self.delivery_gate.validate_docx(
                compiled.candidate_path,
                profile,
                work_dir,
                inherited_header_footer=inherited_header_footer,
            )
            self.last_delivery_gate_summary["docx"] = docx_gate.public_summary()
            self.last_delivery_gate_summary["compile"] = {
                "template_applied": compiled.template_applied,
                **compiled.metadata,
            }
            if not docx_gate.passed:
                raise DocumentFormattingError(f"Internal delivery gate failed: {docx_gate.failure_reason}")

            final_docx_path = docx_gate.docx_path
            final_files: list[tuple[Path, str, str]] = [
                (
                    final_docx_path,
                    f"{Path(input_record.filename).stem}-formatted.docx",
                    DOCX_MIME,
                )
            ]
            if include_pdf:
                pdf_path = export_docx_to_pdf(final_docx_path, work_dir, self.soffice_bin)
                if profile.delivery_gate.require_pdf_inspection:
                    pdf_gate = self.delivery_gate.validate_pdf(pdf_path)
                    self.last_delivery_gate_summary["pdf"] = pdf_gate.public_summary()
                    if not pdf_gate.passed:
                        raise DocumentFormattingError(f"PDF delivery gate failed: {pdf_gate.failure_reason}")
                layout_gate = self.delivery_gate.validate_final_layout(pdf_path, profile)
                self.last_delivery_gate_summary["llm_layout_review"] = layout_gate.public_summary()
                if not layout_gate.passed:
                    raise DocumentFormattingError(f"Final LLM layout review failed: {layout_gate.failure_reason}")
                final_files.append(
                    (
                        pdf_path,
                        f"{Path(input_record.filename).stem}-formatted.pdf",
                        PDF_MIME,
                    )
                )
            outputs = [
                self.storage.store_generated_file(path, filename=filename, mime_type=mime_type)
                for path, filename, mime_type in final_files
            ]
        except (
            DocumentConversionError,
            DocumentParseError,
            DocumentCompileError,
            DocumentExportError,
            InternalDeliveryGateError,
        ) as exc:
            raise DocumentFormattingError(str(exc)) from exc

        for record in outputs:
            self.repository.add_file(record)
        return outputs

    def _resolve_template_path(self, template_file_id: str | None) -> Path | None:
        if not template_file_id:
            return None
        record = self.repository.get_file(template_file_id)
        if record is None:
            raise DocumentFormattingError(f"Template file not found: {template_file_id}")
        return Path(record.storage_path)
