from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import RGBColor
from pypdf import PdfReader

from app.documents.ooxml import OoxmlDocumentFeatures, OoxmlInspectionError, inspect_ooxml_features
from app.documents.structure import DocumentStructure, ParagraphRole, classify_document
from app.models import QualityIssue
from app.profiles.models import FormatProfile, TextAlignment, TextFont


class QualityInspectionError(RuntimeError):
    pass


def inspect_docx_quality(path: Path, profile: FormatProfile) -> list[QualityIssue]:
    try:
        document = Document(path)
    except Exception as exc:
        raise QualityInspectionError(f"DOCX quality inspection failed to open input: {exc}") from exc

    structure = classify_document(document)
    try:
        features = inspect_ooxml_features(path)
    except OoxmlInspectionError as exc:
        features = None
        feature_issue = QualityIssue(
            issue_id="docx_ooxml_features",
            status="fail",
            severity="high",
            check_key="docx.ooxml.features",
            title="DOCX internal OOXML feature inspection failed.",
            description=str(exc),
            recommendation="Regenerate the DOCX before claiming compliance.",
            fixable=False,
        )
    else:
        feature_issue = _inspect_ooxml_feature_inventory(features)
    return [
        _inspect_page_setup(document, profile),
        _inspect_margins(document, profile),
        _inspect_header_footer(document, profile),
        _inspect_body_style(document, structure, profile),
        _inspect_heading_style(document, structure, profile),
        _inspect_table_borders(document),
        _inspect_captions(document, structure),
        _inspect_role_style_consistency(document, structure, profile),
        _inspect_raw_latex(document),
        _inspect_basic_page_numbers(document, profile),
        feature_issue,
        _inspect_field_update_policy(features),
        _inspect_toc_fields(document, structure, features),
        _inspect_section_complexity(features),
        _inspect_notes_support(features),
        _inspect_image_caption_pairing(document, structure, features, profile),
        _inspect_list_numbering(features),
    ]


def inspect_pdf_quality(path: Path) -> list[QualityIssue]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return [
            _pdf_openability_issue(False, f"PDF cannot be read from disk: {exc}"),
            _pdf_page_count_issue(0, readable=False),
            _pdf_text_extractability_issue(False, readable=False),
            _pdf_blank_pages_issue(0, has_text=False, readable=False),
        ]

    readable = data.startswith(b"%PDF") and b"%%EOF" in data[-2048:]
    pypdf_info = _read_pdf_text_info(data) if readable else None
    page_count = pypdf_info[0] if pypdf_info is not None else (_count_pdf_pages(data) if readable else 0)
    has_text = pypdf_info[1] if pypdf_info is not None else (_pdf_has_literal_text(data) if readable else False)
    return [
        _pdf_openability_issue(readable, None),
        _pdf_page_count_issue(page_count, readable=readable),
        _pdf_text_extractability_issue(has_text, readable=readable),
        _pdf_blank_pages_issue(page_count, has_text, readable=readable),
    ]


def _pdf_openability_issue(readable: bool, detail: str | None) -> QualityIssue:
    if readable:
        return QualityIssue(
            issue_id="pdf_openability",
            status="pass",
            severity="info",
            check_key="pdf.openability",
            title="PDF file has a readable PDF envelope.",
        )
    return QualityIssue(
        issue_id="pdf_openability",
        status="fail",
        severity="high",
        check_key="pdf.openability",
        title="PDF file cannot be opened by the lightweight checker.",
        description=detail or "The file does not look like a complete PDF.",
        recommendation="Regenerate the PDF and inspect the export tool logs.",
        fixable=False,
    )


def _pdf_page_count_issue(page_count: int, readable: bool) -> QualityIssue:
    if not readable or page_count <= 0:
        return QualityIssue(
            issue_id="pdf_page_count",
            status="fail",
            severity="high",
            check_key="pdf.page_count",
            title="PDF page count could not be confirmed.",
            description=f"Detected page_count={page_count}.",
            recommendation="Regenerate the PDF and confirm it contains at least one page.",
            details={"page_count": page_count},
            fixable=False,
        )
    return QualityIssue(
        issue_id="pdf_page_count",
        status="pass",
        severity="info",
        check_key="pdf.page_count",
        title="PDF page count is greater than zero.",
        details={"page_count": page_count},
    )


def _pdf_text_extractability_issue(has_text: bool, readable: bool) -> QualityIssue:
    if readable and has_text:
        return QualityIssue(
            issue_id="pdf_text_extractability",
            status="pass",
            severity="info",
            check_key="pdf.text_extractability",
            title="PDF contains extractable text.",
        )
    return QualityIssue(
        issue_id="pdf_text_extractability",
        status="fail",
        severity="high",
        check_key="pdf.text_extractability",
        title="PDF text extractability could not be confirmed.",
        description="The lightweight checker did not find literal text drawing operators.",
        recommendation="Inspect the PDF with codex-pdf-inspect or regenerate from DOCX.",
        fixable=False,
    )


def _pdf_blank_pages_issue(page_count: int, has_text: bool, readable: bool) -> QualityIssue:
    if not readable:
        return QualityIssue(
            issue_id="pdf_blank_pages",
            status="unsupported",
            check_key="pdf.blank_pages",
            title="Blank-page check cannot run because the PDF is unreadable.",
            recommendation="Regenerate the PDF first.",
        )
    if page_count > 0 and not has_text:
        return QualityIssue(
            issue_id="pdf_blank_pages",
            status="warning",
            check_key="pdf.blank_pages",
            title="PDF may contain blank or image-only pages.",
            description="A page was detected, but no literal text was found.",
            recommendation="Open the PDF and review whether pages are blank or scanned-only.",
            fixable=False,
        )
    return QualityIssue(
        issue_id="pdf_blank_pages",
        status="pass",
        severity="info",
        check_key="pdf.blank_pages",
        title="No obvious blank-page warning detected by the lightweight checker.",
    )


def _inspect_margins(document: Document, profile: FormatProfile) -> QualityIssue:
    expected = profile.page.margins_cm
    mismatches: list[str] = []
    for index, section in enumerate(document.sections):
        actual = {
            "top": section.top_margin.cm,
            "bottom": section.bottom_margin.cm,
            "left": section.left_margin.cm,
            "right": section.right_margin.cm,
            "gutter": section.gutter.cm if section.gutter else 0,
        }
        for key, expected_value in expected.model_dump().items():
            if not _close_cm(actual[key], expected_value):
                mismatches.append(f"section[{index}].{key}: expected {expected_value:.2f} cm, found {actual[key]:.2f} cm")
    if mismatches:
        return QualityIssue(
            issue_id="docx_page_margins",
            status="fail",
            severity="high",
            check_key="docx.page.margins",
            title="DOCX page margins do not match the profile.",
            description="; ".join(mismatches),
            profile_rule_ref="page.margins_cm",
            location="sections",
            recommendation="Reapply profile page settings.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_page_margins",
        status="pass",
        severity="info",
        check_key="docx.page.margins",
        title="DOCX page margins match the profile.",
        profile_rule_ref="page.margins_cm",
    )


def _inspect_page_setup(document: Document, profile: FormatProfile) -> QualityIssue:
    expected_width, expected_height = _expected_page_size_cm(profile)
    mismatches: list[str] = []
    for index, section in enumerate(document.sections):
        if not _close_cm(section.page_width.cm, expected_width, tolerance=0.15):
            mismatches.append(f"section[{index}].width expected {expected_width:.2f} cm, found {section.page_width.cm:.2f} cm")
        if not _close_cm(section.page_height.cm, expected_height, tolerance=0.15):
            mismatches.append(f"section[{index}].height expected {expected_height:.2f} cm, found {section.page_height.cm:.2f} cm")
    if mismatches:
        return QualityIssue(
            issue_id="docx_page_setup",
            status="fail",
            severity="high",
            check_key="docx.page.setup",
            title="DOCX page size or orientation does not match the profile.",
            description="; ".join(mismatches),
            profile_rule_ref="page.size; page.orientation",
            location="sections",
            recommendation="Reapply profile page size and orientation settings.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_page_setup",
        status="pass",
        severity="info",
        check_key="docx.page.setup",
        title="DOCX page size and orientation match the profile.",
        profile_rule_ref="page.size; page.orientation",
    )


def _expected_page_size_cm(profile: FormatProfile) -> tuple[float, float]:
    if profile.page.size == "A4":
        width_cm, height_cm = 21.0, 29.7
    else:
        width_cm, height_cm = 21.59, 27.94
    if profile.page.orientation == "landscape":
        return height_cm, width_cm
    return width_cm, height_cm


def _inspect_header_footer(document: Document, profile: FormatProfile) -> QualityIssue:
    mismatches: list[str] = []
    expected_header = (profile.header_footer.header_text or "").strip()
    for index, section in enumerate(document.sections):
        header_text = "\n".join(paragraph.text.strip() for paragraph in section.header.paragraphs if paragraph.text.strip())
        if expected_header and expected_header not in header_text:
            mismatches.append(f"section[{index}] missing header text")
        has_page = _section_has_page_field(section)
        if profile.header_footer.footer_page_number and not has_page:
            mismatches.append(f"section[{index}] missing footer page number")
        if not profile.header_footer.footer_page_number and has_page:
            mismatches.append(f"section[{index}] has unexpected footer page number")
    if mismatches:
        return QualityIssue(
            issue_id="docx_header_footer",
            status="fail",
            severity="high",
            check_key="docx.header_footer",
            title="DOCX header/footer rules do not match the profile.",
            description="; ".join(mismatches),
            profile_rule_ref="header_footer",
            location="sections",
            recommendation="Apply supported header text and footer page-number rules.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_header_footer",
        status="pass",
        severity="info",
        check_key="docx.header_footer",
        title="DOCX header/footer rules match supported profile checks.",
        profile_rule_ref="header_footer",
    )


def _count_pdf_pages(data: bytes) -> int:
    text = data.decode("latin-1", errors="ignore")
    type_page_refs = len(re.findall(r"/Type\s*/Page\b", text))
    if type_page_refs:
        return type_page_refs
    count_values = [int(match) for match in re.findall(r"/Count\s+(\d+)", text)]
    return max(count_values, default=0)


def _pdf_has_literal_text(data: bytes) -> bool:
    text = data.decode("latin-1", errors="ignore")
    return bool(re.search(r"\([^()]{2,}\)\s*T[Jj]", text) or re.search(r"<[0-9A-Fa-f]{4,}>\s*T[Jj]", text))


def _read_pdf_text_info(data: bytes) -> tuple[int, bool] | None:
    try:
        reader = PdfReader(BytesIO(data))
        page_count = len(reader.pages)
        text_chars = 0
        for page in reader.pages:
            text_chars += len((page.extract_text() or "").strip())
        return page_count, text_chars > 0
    except Exception:
        return None


def _inspect_body_style(document: Document, structure: DocumentStructure, profile: FormatProfile) -> QualityIssue:
    paragraph = _first_paragraph_with_role(document, structure, {ParagraphRole.BODY})
    if paragraph is None:
        return QualityIssue(
            issue_id="docx_body_style",
            status="unsupported",
            check_key="docx.body.style",
            title="No body paragraph could be selected for style inspection.",
            profile_rule_ref="body",
            recommendation="Review body text manually.",
        )

    mismatches: list[str] = []
    fmt = paragraph.paragraph_format
    expected_indent = profile.body.first_line_indent_chars * 0.37
    actual_indent = fmt.first_line_indent.cm if fmt.first_line_indent else 0
    if not _close_cm(actual_indent, expected_indent):
        mismatches.append(f"first line indent expected {expected_indent:.2f} cm, found {actual_indent:.2f} cm")
    if fmt.line_spacing != profile.body.line_spacing:
        mismatches.append(f"line spacing expected {profile.body.line_spacing}, found {fmt.line_spacing}")
    run = next((r for r in paragraph.runs if r.text.strip()), None)
    if run is None:
        mismatches.append("body paragraph has no text run")
    else:
        mismatches.extend(_run_style_mismatches(run, profile.body.font, "body run"))

    if mismatches:
        return QualityIssue(
            issue_id="docx_body_style",
            status="warning",
            check_key="docx.body.style",
            title="DOCX body paragraph style needs review.",
            description="; ".join(mismatches),
            profile_rule_ref="body",
            location=_paragraph_location(document, paragraph),
            recommendation="Apply the body paragraph style from the selected profile.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_body_style",
        status="pass",
        severity="info",
        check_key="docx.body.style",
        title="DOCX body paragraph style matches the profile.",
        profile_rule_ref="body",
        location=_paragraph_location(document, paragraph),
    )


def _inspect_heading_style(document: Document, structure: DocumentStructure, profile: FormatProfile) -> QualityIssue:
    selected = _first_paragraph_with_classification(
        document,
        structure,
        {
            ParagraphRole.DOCUMENT_TITLE,
            ParagraphRole.HEADING,
            ParagraphRole.REFERENCE_HEADING,
            ParagraphRole.ACKNOWLEDGEMENT_HEADING,
        },
    )
    paragraph = selected[0] if selected else None
    classification = selected[1] if selected else None
    if paragraph is None:
        return QualityIssue(
            issue_id="docx_heading_style",
            status="unsupported",
            check_key="docx.heading.style",
            title="No heading paragraph could be selected for style inspection.",
            profile_rule_ref="headings",
            recommendation="Review heading styles manually.",
        )
    heading_level = classification.heading_level if classification and classification.heading_level else 1
    heading_rule = next((heading for heading in profile.headings if heading.level == heading_level), profile.headings[0])
    run = next((r for r in paragraph.runs if r.text.strip()), None)
    mismatches: list[str] = []
    if paragraph.alignment != _alignment_value(heading_rule.alignment):
        mismatches.append(f"heading alignment expected {heading_rule.alignment}")
    if run is None:
        mismatches.append("heading paragraph has no text run")
    else:
        mismatches.extend(_run_style_mismatches(run, heading_rule.font, "heading run"))

    if mismatches:
        return QualityIssue(
            issue_id="docx_heading_style",
            status="warning",
            check_key="docx.heading.style",
            title="DOCX heading style needs review.",
            description="; ".join(mismatches),
            profile_rule_ref="headings[1]",
            location=_paragraph_location(document, paragraph),
            recommendation="Apply heading style rules from the selected profile.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_heading_style",
        status="pass",
        severity="info",
        check_key="docx.heading.style",
        title="DOCX heading style matches the profile.",
        profile_rule_ref="headings[1]",
        location=_paragraph_location(document, paragraph),
    )


def _inspect_table_borders(document: Document) -> QualityIssue:
    if not document.tables:
        return QualityIssue(
            issue_id="docx_table_borders",
            status="pass",
            severity="info",
            check_key="docx.table.borders",
            title="DOCX table-border check is not applicable because no tables were detected.",
            profile_rule_ref="table",
        )
    for index, table in enumerate(document.tables):
        borders = table._tbl.tblPr.xpath("./w:tblBorders")
        if not borders:
            return QualityIssue(
                issue_id="docx_table_borders",
                status="warning",
                check_key="docx.table.borders",
                title="DOCX table border rules need review.",
                description=f"table[{index}] does not define tblBorders.",
                profile_rule_ref="table",
                location=f"table[{index}]",
                recommendation="Apply basic three-line table borders.",
                fixable=True,
            )
        border = borders[0]
        missing = [edge for edge in ("top", "bottom", "insideH") if not border.xpath(f"./*[local-name()='{edge}']")]
        if missing:
            return QualityIssue(
                issue_id="docx_table_borders",
                status="warning",
                check_key="docx.table.borders",
                title="DOCX table border rules need review.",
                description=f"table[{index}] is missing {', '.join(missing)} borders.",
                profile_rule_ref="table",
                location=f"table[{index}]",
                recommendation="Apply basic three-line table borders.",
                fixable=True,
            )
    return QualityIssue(
        issue_id="docx_table_borders",
        status="pass",
        severity="info",
        check_key="docx.table.borders",
        title="DOCX table border rules are present.",
        profile_rule_ref="table",
    )


def _inspect_captions(document: Document, structure: DocumentStructure) -> QualityIssue:
    captions = [
        paragraph
        for paragraph, classification in _paragraphs_with_classifications(document, structure)
        if classification.role in {ParagraphRole.TABLE_CAPTION, ParagraphRole.FIGURE_CAPTION}
    ]
    if not captions:
        if not document.tables and len(document.inline_shapes) == 0:
            return QualityIssue(
                issue_id="docx_captions",
                status="pass",
                severity="info",
                check_key="docx.captions",
                title="DOCX caption check is not applicable because no tables or images were detected.",
                profile_rule_ref="table.caption; figure.caption",
            )
        missing_targets: list[str] = []
        if document.tables:
            missing_targets.append(f"{len(document.tables)} table(s)")
        if len(document.inline_shapes):
            missing_targets.append(f"{len(document.inline_shapes)} image(s)")
        return QualityIssue(
            issue_id="docx_captions",
            status="warning",
            check_key="docx.captions",
            title="No figure or table captions were detected for existing visual objects.",
            description=f"Detected {', '.join(missing_targets)} but no supported captions.",
            recommendation="Add table/figure captions or review whether captions are intentionally omitted.",
            fixable=False,
        )
    mismatches = [
        _paragraph_location(document, paragraph)
        for paragraph in captions
        if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER
    ]
    if mismatches:
        return QualityIssue(
            issue_id="docx_captions",
            status="warning",
            check_key="docx.captions",
            title="DOCX caption alignment needs review.",
            description=f"Captions not centered: {', '.join(mismatches)}",
            profile_rule_ref="table.caption; figure.caption",
            location=", ".join(mismatches),
            recommendation="Center figure and table captions.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_captions",
        status="pass",
        severity="info",
        check_key="docx.captions",
        title="DOCX captions match supported profile checks.",
        profile_rule_ref="table.caption; figure.caption",
    )


def _inspect_role_style_consistency(
    document: Document,
    structure: DocumentStructure,
    profile: FormatProfile,
) -> QualityIssue:
    mismatches: list[str] = []
    for paragraph, classification in _paragraphs_with_classifications(document, structure):
        role = classification.role
        if role == ParagraphRole.BODY:
            fmt = paragraph.paragraph_format
            first_line = fmt.first_line_indent.cm if fmt.first_line_indent else 0
            left = fmt.left_indent.cm if fmt.left_indent else 0
            if first_line < -0.05 and left > 0.05:
                mismatches.append(f"{_paragraph_location(document, paragraph)} body has reference-style hanging indent")
            if paragraph.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                mismatches.append(f"{_paragraph_location(document, paragraph)} body is centered like a caption or equation")
            if paragraph.style and paragraph.style.name.startswith("Heading"):
                mismatches.append(f"{_paragraph_location(document, paragraph)} body is using a Word heading style")
        elif role == ParagraphRole.TOC_ITEM:
            run = next((r for r in paragraph.runs if r.text.strip()), None)
            if run:
                mismatches.extend(_run_style_mismatches(run, profile.body.font, f"{_paragraph_location(document, paragraph)} toc item"))
        elif role in {
            ParagraphRole.DOCUMENT_TITLE,
            ParagraphRole.HEADING,
            ParagraphRole.REFERENCE_HEADING,
            ParagraphRole.ACKNOWLEDGEMENT_HEADING,
        }:
            if not (paragraph.style and paragraph.style.name.startswith("Heading")):
                mismatches.append(f"{_paragraph_location(document, paragraph)} heading is not using a Word heading style")
        elif role in {ParagraphRole.TABLE_CAPTION, ParagraphRole.FIGURE_CAPTION}:
            if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER:
                mismatches.append(f"{_paragraph_location(document, paragraph)} caption is not centered")
        elif role == ParagraphRole.EQUATION:
            if paragraph.alignment != _alignment_value(profile.equations.alignment):
                mismatches.append(f"{_paragraph_location(document, paragraph)} equation alignment expected {profile.equations.alignment}")
        elif role == ParagraphRole.REFERENCE_ITEM:
            fmt = paragraph.paragraph_format
            first_line = fmt.first_line_indent.cm if fmt.first_line_indent else 0
            left = fmt.left_indent.cm if fmt.left_indent else 0
            if not (first_line < -0.05 and left > 0.05):
                mismatches.append(f"{_paragraph_location(document, paragraph)} reference item is missing hanging indent")

    if mismatches:
        return QualityIssue(
            issue_id="docx_role_styles",
            status="warning",
            check_key="docx.role_styles",
            title="DOCX paragraph roles and applied styles need review.",
            description="; ".join(mismatches[:12]),
            profile_rule_ref="body; headings; captions; equations; references",
            recommendation="Re-run profile formatting or review paragraphs whose detected document role does not match their applied Word style.",
            fixable=False,
            details={"mismatch_count": len(mismatches)},
        )
    return QualityIssue(
        issue_id="docx_role_styles",
        status="pass",
        severity="info",
        check_key="docx.role_styles",
        title="DOCX paragraph roles match supported applied style checks.",
        profile_rule_ref="body; headings; captions; equations; references",
    )


def _inspect_raw_latex(document: Document) -> QualityIssue:
    for index, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text
        if _contains_raw_latex(text):
            return QualityIssue(
                issue_id="docx_raw_latex",
                status="fail",
                severity="high",
                check_key="docx.raw_latex",
                title="DOCX contains raw LaTeX residue.",
                description=text,
                location=f"paragraph[{index}]",
                recommendation="Convert formulas to Word-readable equation formatting before final delivery.",
                fixable=False,
            )
    return QualityIssue(
        issue_id="docx_raw_latex",
        status="pass",
        severity="info",
        check_key="docx.raw_latex",
        title="No raw LaTeX residue detected in DOCX paragraphs.",
    )


def _inspect_basic_page_numbers(document: Document, profile: FormatProfile) -> QualityIssue:
    if not profile.header_footer.footer_page_number:
        return QualityIssue(
            issue_id="docx_page_number",
            status="pass",
            severity="info",
            check_key="docx.page_number",
            title="DOCX page number check is disabled by the selected profile.",
            profile_rule_ref="header_footer.footer_page_number",
        )
    missing_sections: list[str] = []
    for index, section in enumerate(document.sections):
        if not _section_has_page_field(section):
            missing_sections.append(f"section[{index}]")
    if missing_sections:
        return QualityIssue(
            issue_id="docx_page_number",
            status="fail",
            severity="high",
            check_key="docx.page_number",
            title="DOCX page number field was not found in every section footer.",
            description=", ".join(missing_sections),
            profile_rule_ref="page.numbering",
            recommendation="Apply supported centered footer PAGE fields before final delivery.",
            fixable=True,
        )
    return QualityIssue(
        issue_id="docx_page_number",
        status="pass",
        severity="info",
        check_key="docx.page_number",
        title="DOCX contains supported footer PAGE fields.",
        profile_rule_ref="page.numbering",
    )


def _inspect_ooxml_feature_inventory(features: OoxmlDocumentFeatures) -> QualityIssue:
    return QualityIssue(
        issue_id="docx_ooxml_features",
        status="pass",
        severity="info",
        check_key="docx.ooxml.features",
        title="DOCX internal OOXML feature inventory completed.",
        details={
            "section_count": features.section_count,
            "toc_field_count": features.toc_field_count,
            "footnote_count": features.footnote_count,
            "endnote_count": features.endnote_count,
            "inline_image_count": features.inline_image_count,
            "anchored_image_count": features.anchored_image_count,
            "numbering_reference_count": features.numbering_reference_count,
            "omml_equation_count": features.omml_equation_count,
        },
    )


def _inspect_field_update_policy(features: OoxmlDocumentFeatures | None) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_field_update_policy",
            status="unsupported",
            check_key="docx.fields.update_policy",
            title="DOCX field update policy cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )
    fields_requiring_refresh = features.toc_field_count + features.page_field_count
    if fields_requiring_refresh > 0 and not features.has_update_fields:
        return QualityIssue(
            issue_id="docx_field_update_policy",
            status="warning",
            check_key="docx.fields.update_policy",
            title="DOCX fields exist but automatic field refresh is not enabled.",
            description=f"Detected {fields_requiring_refresh} supported field reference(s).",
            profile_rule_ref="fields.update_on_open",
            recommendation="Enable Word updateFields so TOC and PAGE fields can refresh during final export/open.",
            fixable=True,
            details={"fields_requiring_refresh": fields_requiring_refresh},
        )
    return QualityIssue(
        issue_id="docx_field_update_policy",
        status="pass",
        severity="info",
        check_key="docx.fields.update_policy",
        title="DOCX field update policy is safe for supported fields.",
        details={"has_update_fields": features.has_update_fields, "fields_requiring_refresh": fields_requiring_refresh},
    )


def _inspect_toc_fields(
    document: Document,
    structure: DocumentStructure,
    features: OoxmlDocumentFeatures | None,
) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_toc_fields",
            status="unsupported",
            check_key="docx.toc.fields",
            title="DOCX table-of-contents fields cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )

    toc_text_paragraphs = [
        _paragraph_location(document, paragraph)
        for paragraph, classification in _paragraphs_with_classifications(document, structure)
        if classification.role in {ParagraphRole.TOC_TITLE, ParagraphRole.TOC_ITEM}
    ]
    if not toc_text_paragraphs and features.toc_field_count == 0:
        return QualityIssue(
            issue_id="docx_toc_fields",
            status="pass",
            severity="info",
            check_key="docx.toc.fields",
            title="DOCX TOC check is not applicable because no TOC was detected.",
        )
    if features.toc_field_count > 0 and features.has_update_fields:
        return QualityIssue(
            issue_id="docx_toc_fields",
            status="pass",
            severity="info",
            check_key="docx.toc.fields",
            title="DOCX TOC fields are present and configured for refresh.",
            profile_rule_ref="toc",
            details={
                "toc_field_count": features.toc_field_count,
                "simple_toc_field_count": features.simple_toc_field_count,
                "complex_toc_field_count": features.complex_toc_field_count,
            },
        )
    if features.toc_field_count > 0:
        return QualityIssue(
            issue_id="docx_toc_fields",
            status="warning",
            check_key="docx.toc.fields",
            title="DOCX TOC fields exist but may be stale.",
            description="TOC field codes were detected without updateFields enabled.",
            profile_rule_ref="toc",
            recommendation="Enable field refresh and export again.",
            fixable=True,
            details={"toc_field_count": features.toc_field_count},
        )
    return QualityIssue(
        issue_id="docx_toc_fields",
        status="warning",
        check_key="docx.toc.fields",
        title="Manual TOC-like text was detected without a Word TOC field.",
        description=", ".join(toc_text_paragraphs[:8]),
        profile_rule_ref="toc",
        recommendation="Review the table of contents manually or replace it with a refreshable Word TOC field.",
        fixable=False,
        details={"toc_text_paragraph_count": len(toc_text_paragraphs)},
    )


def _inspect_section_complexity(features: OoxmlDocumentFeatures | None) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_sections",
            status="unsupported",
            check_key="docx.sections",
            title="DOCX sections cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )
    if features.section_count <= 1:
        return QualityIssue(
            issue_id="docx_sections",
            status="pass",
            severity="info",
            check_key="docx.sections",
            title="DOCX has a single supported section.",
            details={"section_count": features.section_count},
        )
    return QualityIssue(
        issue_id="docx_sections",
        status="pass",
        severity="info",
        check_key="docx.sections",
        title="DOCX has multiple sections and supported section-level checks ran across all sections.",
        recommendation="If the profile expects mixed portrait/landscape sections or section-specific page numbering, review those requirements manually.",
        details={"section_count": features.section_count},
    )


def _inspect_notes_support(features: OoxmlDocumentFeatures | None) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_notes",
            status="unsupported",
            check_key="docx.notes",
            title="DOCX footnotes/endnotes cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )
    count = features.footnote_count + features.endnote_count
    if count == 0:
        return QualityIssue(
            issue_id="docx_notes",
            status="pass",
            severity="info",
            check_key="docx.notes",
            title="DOCX footnote/endnote check is not applicable because none were detected.",
        )
    return QualityIssue(
        issue_id="docx_notes",
        status="unsupported",
        severity="high",
        check_key="docx.notes",
        title="DOCX contains footnotes or endnotes that require manual review.",
        description=f"Detected {features.footnote_count} footnote(s) and {features.endnote_count} endnote(s).",
        profile_rule_ref="footnotes; endnotes",
        recommendation="Review note formatting manually; the current formatter preserves note content but does not yet guarantee note style compliance.",
        fixable=False,
        details={"footnote_count": features.footnote_count, "endnote_count": features.endnote_count},
    )


def _inspect_image_caption_pairing(
    document: Document,
    structure: DocumentStructure,
    features: OoxmlDocumentFeatures | None,
    profile: FormatProfile,
) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_visual_caption_pairing",
            status="unsupported",
            check_key="docx.visuals.caption_pairing",
            title="DOCX visual caption pairing cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )
    table_captions = [
        paragraph
        for paragraph, classification in _paragraphs_with_classifications(document, structure)
        if classification.role == ParagraphRole.TABLE_CAPTION
    ]
    figure_captions = [
        paragraph
        for paragraph, classification in _paragraphs_with_classifications(document, structure)
        if classification.role == ParagraphRole.FIGURE_CAPTION
    ]
    total_images = features.inline_image_count + features.anchored_image_count
    if not document.tables and total_images == 0:
        return QualityIssue(
            issue_id="docx_visual_caption_pairing",
            status="pass",
            severity="info",
            check_key="docx.visuals.caption_pairing",
            title="DOCX visual caption pairing is not applicable because no tables or images were detected.",
        )
    if features.anchored_image_count:
        return QualityIssue(
            issue_id="docx_visual_caption_pairing",
            status="unsupported",
            severity="high",
            check_key="docx.visuals.caption_pairing",
            title="DOCX contains floating/anchored images that require manual layout review.",
            description=f"Detected {features.anchored_image_count} anchored image(s).",
            profile_rule_ref="figure.caption; image.layout",
            recommendation="Review image anchoring and nearby captions in Word before treating the export as compliant.",
            fixable=False,
            details={"anchored_image_count": features.anchored_image_count},
        )
    missing: list[str] = []
    if len(document.tables) > len(table_captions):
        missing.append(f"{len(document.tables) - len(table_captions)} table caption(s)")
    if features.inline_image_count > len(figure_captions):
        missing.append(f"{features.inline_image_count - len(figure_captions)} figure caption(s)")
    if missing:
        return QualityIssue(
            issue_id="docx_visual_caption_pairing",
            status="warning",
            check_key="docx.visuals.caption_pairing",
            title="DOCX visual objects may be missing captions.",
            description=", ".join(missing),
            profile_rule_ref="table.caption; figure.caption",
            recommendation="Add or review captions so each table/image has a profile-compliant caption.",
            fixable=False,
            details={
                "table_count": len(document.tables),
                "table_caption_count": len(table_captions),
                "inline_image_count": features.inline_image_count,
                "figure_caption_count": len(figure_captions),
                "table_caption_position": profile.table.caption.position,
                "figure_caption_position": profile.figure.caption.position,
            },
        )
    return QualityIssue(
        issue_id="docx_visual_caption_pairing",
        status="pass",
        severity="info",
        check_key="docx.visuals.caption_pairing",
        title="DOCX table/image counts have matching supported captions.",
        profile_rule_ref="table.caption; figure.caption",
        details={
            "table_count": len(document.tables),
            "table_caption_count": len(table_captions),
            "inline_image_count": features.inline_image_count,
            "figure_caption_count": len(figure_captions),
        },
    )


def _inspect_list_numbering(features: OoxmlDocumentFeatures | None) -> QualityIssue:
    if features is None:
        return QualityIssue(
            issue_id="docx_numbering",
            status="unsupported",
            check_key="docx.numbering",
            title="DOCX numbering cannot be inspected.",
            recommendation="Regenerate the DOCX and rerun quality inspection.",
        )
    if features.numbering_reference_count == 0:
        return QualityIssue(
            issue_id="docx_numbering",
            status="pass",
            severity="info",
            check_key="docx.numbering",
            title="DOCX list-numbering check is not applicable because no numbering references were detected.",
        )
    return QualityIssue(
        issue_id="docx_numbering",
        status="pass",
        severity="info",
        check_key="docx.numbering",
        title="DOCX numbering references are preserved for supported list paragraphs.",
        recommendation="Review numbering manually if the profile requires a specific multilevel numbering scheme.",
        details={"numbering_reference_count": features.numbering_reference_count},
    )


def _section_has_page_field(section) -> bool:
    for paragraph in section.footer.paragraphs:
        xml = paragraph._p.xml
        if "PAGE" in xml and "fldChar" in xml:
            return True
    return False


def _close_cm(actual: float, expected: float, tolerance: float = 0.08) -> bool:
    return abs(actual - expected) <= tolerance


def _run_font_matches(run, expected_chinese: str, expected_latin: str) -> bool:
    east_asia = run._element.rPr.rFonts.get(qn("w:eastAsia")) if run._element.rPr is not None and run._element.rPr.rFonts is not None else None
    return run.font.name == expected_latin and east_asia == expected_chinese


def _run_style_mismatches(run, font: TextFont, label: str) -> list[str]:
    mismatches: list[str] = []
    if not _run_font_matches(run, font.chinese, font.latin):
        mismatches.append(f"{label} font does not match profile")
    actual_size = run.font.size.pt if run.font.size else None
    if actual_size is None or abs(actual_size - font.size_pt) > 0.1:
        mismatches.append(f"{label} size expected {font.size_pt:g} pt, found {actual_size:g} pt" if actual_size else f"{label} size expected {font.size_pt:g} pt, found inherited/auto")
    actual_bold = bool(run.font.bold)
    expected_bold = font.weight == "bold"
    if actual_bold != expected_bold:
        mismatches.append(f"{label} bold expected {expected_bold}, found {actual_bold}")
    if not _run_color_matches(run, font.color):
        actual = _run_color_value(run)
        mismatches.append(f"{label} color expected {font.color}, found {actual or 'auto/inherited'}")
    return mismatches


def _run_color_matches(run, expected_hex: str) -> bool:
    return run.font.color.rgb == RGBColor.from_string(expected_hex)


def _run_color_value(run) -> str | None:
    rgb = run.font.color.rgb
    return str(rgb) if rgb is not None else None


def _alignment_value(alignment: TextAlignment):
    mapping = {
        "left": WD_ALIGN_PARAGRAPH.LEFT,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
        "justified": WD_ALIGN_PARAGRAPH.JUSTIFY,
    }
    return mapping[alignment]


def _paragraphs_with_classifications(document: Document, structure: DocumentStructure):
    for index, paragraph in enumerate(document.paragraphs):
        yield paragraph, structure.role_for(index)


def _first_paragraph_with_classification(
    document: Document,
    structure: DocumentStructure,
    roles: set[ParagraphRole],
):
    return next(
        (
            (paragraph, classification)
            for paragraph, classification in _paragraphs_with_classifications(document, structure)
            if classification.role in roles
        ),
        None,
    )


def _first_paragraph_with_role(
    document: Document,
    structure: DocumentStructure,
    roles: set[ParagraphRole],
):
    selected = _first_paragraph_with_classification(document, structure, roles)
    return selected[0] if selected else None


def _paragraph_location(document: Document, paragraph) -> str:
    for index, candidate in enumerate(document.paragraphs, start=1):
        if candidate._p is paragraph._p:
            return f"paragraph[{index}]"
    return "paragraph[unknown]"


def _contains_raw_latex(text: str) -> bool:
    return bool(
        re.search(r"(?<!\\)\$[^$]+\$(?!\\)", text)
        or re.search(r"\\(?:begin|end|frac|sum|int|sqrt|left|right|[()[\]])", text)
    )
