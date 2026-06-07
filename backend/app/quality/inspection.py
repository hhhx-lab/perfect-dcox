from __future__ import annotations

from pathlib import Path
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from app.models import QualityIssue
from app.profiles.models import FormatProfile


class QualityInspectionError(RuntimeError):
    pass


def inspect_docx_quality(path: Path, profile: FormatProfile) -> list[QualityIssue]:
    try:
        document = Document(path)
    except Exception as exc:
        raise QualityInspectionError(f"DOCX quality inspection failed to open input: {exc}") from exc

    return [
        _inspect_margins(document, profile),
        _inspect_body_style(document, profile),
        _inspect_heading_style(document, profile),
        _inspect_table_borders(document),
        _inspect_captions(document),
        _inspect_raw_latex(document),
        _page_number_unsupported_issue(),
    ]


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


def _inspect_body_style(document: Document, profile: FormatProfile) -> QualityIssue:
    paragraph = next((p for p in document.paragraphs if _is_body_candidate(p.text)), None)
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
    elif not _run_font_matches(run, profile.body.font.chinese, profile.body.font.latin):
        mismatches.append("body run font does not match profile")

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


def _inspect_heading_style(document: Document, profile: FormatProfile) -> QualityIssue:
    paragraph = next((p for p in document.paragraphs if p.text.strip() and p.style and p.style.name.startswith("Heading")), None)
    if paragraph is None:
        return QualityIssue(
            issue_id="docx_heading_style",
            status="unsupported",
            check_key="docx.heading.style",
            title="No heading paragraph could be selected for style inspection.",
            profile_rule_ref="headings",
            recommendation="Review heading styles manually.",
        )
    heading_rule = next((heading for heading in profile.headings if heading.level == 1), profile.headings[0])
    run = next((r for r in paragraph.runs if r.text.strip()), None)
    mismatches: list[str] = []
    if paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER:
        mismatches.append("heading alignment is not centered")
    if run is None:
        mismatches.append("heading paragraph has no text run")
    elif not _run_font_matches(run, heading_rule.font.chinese, heading_rule.font.latin):
        mismatches.append("heading run font does not match profile")

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
            status="unsupported",
            check_key="docx.table.borders",
            title="No table is available for border inspection.",
            recommendation="Review table rules manually if the document should contain tables.",
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


def _inspect_captions(document: Document) -> QualityIssue:
    captions = [p for p in document.paragraphs if _is_table_caption(p.text.strip()) or _is_figure_caption(p.text.strip())]
    if not captions:
        return QualityIssue(
            issue_id="docx_captions",
            status="unsupported",
            check_key="docx.captions",
            title="No figure or table captions were detected.",
            recommendation="Review captions manually if the document should contain figures or tables.",
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


def _page_number_unsupported_issue() -> QualityIssue:
    return QualityIssue(
        issue_id="docx_page_number",
        status="unsupported",
        check_key="docx.page_number",
        title="Page number presence cannot be reliably judged by the current DOCX checker.",
        profile_rule_ref="page.numbering",
        recommendation="Open the formatted DOCX or exported PDF and review page numbering manually.",
    )


def _close_cm(actual: float, expected: float, tolerance: float = 0.08) -> bool:
    return abs(actual - expected) <= tolerance


def _run_font_matches(run, expected_chinese: str, expected_latin: str) -> bool:
    east_asia = run._element.rPr.rFonts.get(qn("w:eastAsia")) if run._element.rPr is not None and run._element.rPr.rFonts is not None else None
    return run.font.name == expected_latin and east_asia == expected_chinese


def _paragraph_location(document: Document, paragraph) -> str:
    for index, candidate in enumerate(document.paragraphs, start=1):
        if candidate._p is paragraph._p:
            return f"paragraph[{index}]"
    return "paragraph[unknown]"


def _is_body_candidate(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if _is_table_caption(stripped) or _is_figure_caption(stripped):
        return False
    if stripped in {"参考文献", "References"} or stripped.startswith("["):
        return False
    if re.match(r"^第[一二三四五六七八九十百0-9]+[章节]", stripped):
        return False
    return True


def _is_table_caption(text: str) -> bool:
    return bool(re.match(r"^(表\s*\d+|Table\s+\d+)", text, re.IGNORECASE))


def _is_figure_caption(text: str) -> bool:
    return bool(re.match(r"^(图\s*\d+|Figure\s+\d+)", text, re.IGNORECASE))


def _contains_raw_latex(text: str) -> bool:
    return bool(
        re.search(r"(?<!\\)\$[^$]+\$(?!\\)", text)
        or re.search(r"\\(?:begin|end|frac|sum|int|sqrt|left|right|[()[\]])", text)
    )
