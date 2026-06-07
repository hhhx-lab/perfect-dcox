from __future__ import annotations

from pathlib import Path

from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.formatter import DocumentFormatError, format_docx_with_profile
from app.documents.parser import DocumentParseError, parse_docx
from app.models import FileRecord
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"


class DocumentFormattingError(RuntimeError):
    pass


class DocumentFormattingService:
    def __init__(self, repository: JsonMetadataRepository, storage: LocalFileStorage, soffice_bin: str | None) -> None:
        self.repository = repository
        self.storage = storage
        self.soffice_bin = soffice_bin

    def format_job(
        self,
        input_file_id: str,
        profile_id: str,
        profile_version: str,
        include_pdf: bool = False,
    ) -> list[FileRecord]:
        input_record = self.repository.get_file(input_file_id)
        if input_record is None:
            raise DocumentFormattingError(f"Input file not found: {input_file_id}")
        profile = self.repository.get_profile_version(profile_id, profile_version)
        if profile is None:
            raise DocumentFormattingError(f"Profile version not found: {profile_id} {profile_version}")

        input_path = Path(input_record.storage_path)
        work_dir = self.storage.root / "work" / input_file_id
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            docx_input = convert_doc_to_docx(input_path, work_dir, self.soffice_bin)
            parse_docx(docx_input)
            formatted_path = work_dir / f"{input_path.stem}-formatted.docx"
            format_docx_with_profile(docx_input, formatted_path, profile)
            outputs = [
                self.storage.store_generated_file(
                    formatted_path,
                    filename=f"{Path(input_record.filename).stem}-formatted.docx",
                    mime_type=DOCX_MIME,
                )
            ]
            if include_pdf:
                pdf_path = export_docx_to_pdf(formatted_path, work_dir, self.soffice_bin)
                outputs.append(
                    self.storage.store_generated_file(
                        pdf_path,
                        filename=f"{Path(input_record.filename).stem}-formatted.pdf",
                        mime_type=PDF_MIME,
                    )
                )
        except (DocumentConversionError, DocumentParseError, DocumentFormatError, DocumentExportError) as exc:
            raise DocumentFormattingError(str(exc)) from exc

        for record in outputs:
            self.repository.add_file(record)
        return outputs
