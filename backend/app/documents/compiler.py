from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.documents.formatter import DocumentFormatError, FormatterExecutionTrace, format_docx_with_profile
from app.documents.template import TemplateBindingError, TemplateLoader
from app.profiles.models import FormatProfile


class DocumentCompileError(RuntimeError):
    pass


@dataclass(frozen=True)
class CompiledDocumentResult:
    candidate_path: Path
    template_applied: bool
    metadata: dict[str, object] = field(default_factory=dict)


class FormatCompiler:
    def __init__(self, template_loader: TemplateLoader | None = None) -> None:
        self.template_loader = template_loader or TemplateLoader()

    def compile(
        self,
        input_docx_path: Path,
        output_path: Path,
        profile: FormatProfile,
        template_path: Path | None = None,
    ) -> CompiledDocumentResult:
        source_for_formatting = input_docx_path
        template_applied = False
        metadata: dict[str, object] = {"profile_schema_version": profile.schema_version}

        if template_path is not None:
            template_applied = True
            composed_path = output_path.with_name(f"{output_path.stem}-templated.docx")
            try:
                self.template_loader.compose_with_body_slot(
                    template_path,
                    input_docx_path,
                    composed_path,
                    body_slot=profile.template_binding.body_slot,
                    placeholder_policy=profile.template_binding.placeholder_policy,
                )
            except TemplateBindingError as exc:
                raise DocumentCompileError(str(exc)) from exc
            source_for_formatting = composed_path
            metadata["template_path"] = str(template_path)
            metadata["body_slot"] = profile.template_binding.body_slot
            metadata["header_footer_inherited"] = profile.template_binding.inherit_header_footer

        try:
            formatter_trace = FormatterExecutionTrace()
            format_docx_with_profile(
                source_for_formatting,
                output_path,
                profile,
                preserve_header_footer=template_applied and profile.template_binding.inherit_header_footer,
                trace=formatter_trace,
            )
            metadata["formatter_registry"] = formatter_trace.public_summary()
        except DocumentFormatError as exc:
            raise DocumentCompileError(str(exc)) from exc
        except Exception as exc:
            raise DocumentCompileError(f"DOCX formatting failed: {exc}") from exc

        return CompiledDocumentResult(
            candidate_path=output_path,
            template_applied=template_applied,
            metadata=metadata,
        )
