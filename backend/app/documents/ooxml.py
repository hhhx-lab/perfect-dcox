from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET


class OoxmlInspectionError(RuntimeError):
    pass


NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


@dataclass(frozen=True)
class OoxmlDocumentFeatures:
    section_count: int = 0
    has_update_fields: bool = False
    toc_field_count: int = 0
    simple_toc_field_count: int = 0
    complex_toc_field_count: int = 0
    toc_instructions: tuple[str, ...] = ()
    page_field_count: int = 0
    footnote_count: int = 0
    endnote_count: int = 0
    inline_image_count: int = 0
    anchored_image_count: int = 0
    numbering_reference_count: int = 0
    omml_equation_count: int = 0
    document_grid_types: tuple[str | None, ...] = ()
    document_grid_line_pitches: tuple[int | None, ...] = ()
    document_grid_char_spaces: tuple[int | None, ...] = ()
    page_number_formats: tuple[str | None, ...] = ()
    page_number_starts: tuple[int | None, ...] = ()
    even_and_odd_headers: bool = False
    table_header_repeat_count: int = 0
    inline_image_width_mm: tuple[float, ...] = ()
    raw_part_names: set[str] = field(default_factory=set)


def inspect_ooxml_features(path: Path) -> OoxmlDocumentFeatures:
    try:
        with ZipFile(path) as package:
            names = set(package.namelist())
            document_root = _read_xml(package, "word/document.xml")
            settings_root = _read_optional_xml(package, "word/settings.xml")
            footnotes_root = _read_optional_xml(package, "word/footnotes.xml")
            endnotes_root = _read_optional_xml(package, "word/endnotes.xml")
    except (BadZipFile, KeyError, ET.ParseError, OSError) as exc:
        raise OoxmlInspectionError(f"DOCX OOXML inspection failed: {exc}") from exc

    return OoxmlDocumentFeatures(
        section_count=len(document_root.findall(".//w:sectPr", NS)),
        has_update_fields=_has_update_fields(settings_root),
        toc_field_count=_count_toc_fields(document_root),
        simple_toc_field_count=_count_simple_toc_fields(document_root),
        complex_toc_field_count=_count_complex_toc_fields(document_root),
        toc_instructions=_toc_instructions(document_root),
        page_field_count=_count_field_instr(document_root, "PAGE"),
        footnote_count=_count_note_references(document_root, footnotes_root, "footnote"),
        endnote_count=_count_note_references(document_root, endnotes_root, "endnote"),
        inline_image_count=len(document_root.findall(".//wp:inline", NS)),
        anchored_image_count=len(document_root.findall(".//wp:anchor", NS)),
        numbering_reference_count=len(document_root.findall(".//w:numPr", NS)),
        omml_equation_count=len(
            document_root.findall(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath")
        )
        + len(document_root.findall(".//{http://schemas.openxmlformats.org/officeDocument/2006/math}oMathPara")),
        document_grid_types=_document_grid_values(document_root, "type"),
        document_grid_line_pitches=_document_grid_int_values(document_root, "linePitch"),
        document_grid_char_spaces=_document_grid_int_values(document_root, "charSpace"),
        page_number_formats=_page_number_values(document_root, "fmt"),
        page_number_starts=_page_number_int_values(document_root, "start"),
        even_and_odd_headers=_has_even_and_odd_headers(settings_root),
        table_header_repeat_count=len(document_root.findall(".//w:tblHeader", NS)),
        inline_image_width_mm=_inline_image_width_mm(document_root),
        raw_part_names=names,
    )


def enable_update_fields(path: Path, *, enabled: bool = True, even_and_odd_headers: bool = False) -> None:
    try:
        with ZipFile(path) as source_package:
            root = _read_optional_xml(source_package, "word/settings.xml")
            if root is None:
                root = ET.Element(f"{{{NS['w']}}}settings")
            update = root.find("w:updateFields", NS)
            if enabled and update is None:
                update = ET.Element(f"{{{NS['w']}}}updateFields")
                root.insert(0, update)
            if enabled and update is not None:
                update.set(f"{{{NS['w']}}}val", "true")
            elif update is not None:
                root.remove(update)
            even_odd = root.find("w:evenAndOddHeaders", NS)
            if even_and_odd_headers and even_odd is None:
                even_odd = ET.Element(f"{{{NS['w']}}}evenAndOddHeaders")
                root.insert(0, even_odd)
            elif not even_and_odd_headers and even_odd is not None:
                root.remove(even_odd)
            settings_bytes = _xml_bytes(root)

            with NamedTemporaryFile(delete=False, suffix=".docx", dir=path.parent) as tmp_file:
                tmp_path = Path(tmp_file.name)
            try:
                with ZipFile(tmp_path, "w") as target_package:
                    copied: set[str] = set()
                    for item in source_package.infolist():
                        if item.filename in copied or item.filename == "word/settings.xml":
                            continue
                        copied.add(item.filename)
                        target_package.writestr(item, source_package.read(item.filename))
                    target_package.writestr("word/settings.xml", settings_bytes)
                tmp_path.replace(path)
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
    except (BadZipFile, ET.ParseError, OSError) as exc:
        raise OoxmlInspectionError(f"DOCX field update patch failed: {exc}") from exc


def _read_xml(package: ZipFile, name: str) -> ET.Element:
    return ET.fromstring(package.read(name))


def _read_optional_xml(package: ZipFile, name: str) -> ET.Element | None:
    if name not in package.namelist():
        return None
    return ET.fromstring(package.read(name))


def _xml_bytes(root: ET.Element) -> bytes:
    ET.register_namespace("w", NS["w"])
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _has_update_fields(root: ET.Element | None) -> bool:
    if root is None:
        return False
    update = root.find("w:updateFields", NS)
    if update is None:
        return False
    value = update.get(f"{{{NS['w']}}}val")
    return value in {None, "true", "1", "on"}


def _has_even_and_odd_headers(root: ET.Element | None) -> bool:
    if root is None:
        return False
    setting = root.find("w:evenAndOddHeaders", NS)
    if setting is None:
        return False
    value = setting.get(f"{{{NS['w']}}}val")
    return value in {None, "true", "1", "on"}


def _count_toc_fields(root: ET.Element) -> int:
    return _count_simple_toc_fields(root) + _count_complex_toc_fields(root)


def _count_simple_toc_fields(root: ET.Element) -> int:
    count = 0
    for field in root.findall(".//w:fldSimple", NS):
        instr = field.get(f"{{{NS['w']}}}instr") or ""
        if "TOC" in instr.upper():
            count += 1
    return count


def _count_complex_toc_fields(root: ET.Element) -> int:
    count = 0
    for instr in root.findall(".//w:instrText", NS):
        if "TOC" in (instr.text or "").upper():
            count += 1
    return count


def _toc_instructions(root: ET.Element) -> tuple[str, ...]:
    instructions: list[str] = []
    for field in root.findall(".//w:fldSimple", NS):
        instr = field.get(f"{{{NS['w']}}}instr") or ""
        if "TOC" in instr.upper():
            instructions.append(instr)
    for instr in root.findall(".//w:instrText", NS):
        text = instr.text or ""
        if "TOC" in text.upper():
            instructions.append(text)
    return tuple(instructions)


def _count_field_instr(root: ET.Element, instruction: str) -> int:
    needle = instruction.upper()
    count = 0
    for field in root.findall(".//w:fldSimple", NS):
        instr = field.get(f"{{{NS['w']}}}instr") or ""
        if needle in instr.upper():
            count += 1
    for instr in root.findall(".//w:instrText", NS):
        if needle in (instr.text or "").upper():
            count += 1
    return count


def _document_grid_values(root: ET.Element, attr: str) -> tuple[str | None, ...]:
    return tuple(item.get(f"{{{NS['w']}}}{attr}") for item in root.findall(".//w:sectPr/w:docGrid", NS))


def _document_grid_int_values(root: ET.Element, attr: str) -> tuple[int | None, ...]:
    values: list[int | None] = []
    for item in root.findall(".//w:sectPr/w:docGrid", NS):
        raw = item.get(f"{{{NS['w']}}}{attr}")
        values.append(int(raw) if raw and raw.isdigit() else None)
    return tuple(values)


def _page_number_values(root: ET.Element, attr: str) -> tuple[str | None, ...]:
    return tuple(item.get(f"{{{NS['w']}}}{attr}") for item in root.findall(".//w:sectPr/w:pgNumType", NS))


def _page_number_int_values(root: ET.Element, attr: str) -> tuple[int | None, ...]:
    values: list[int | None] = []
    for item in root.findall(".//w:sectPr/w:pgNumType", NS):
        raw = item.get(f"{{{NS['w']}}}{attr}")
        values.append(int(raw) if raw and raw.isdigit() else None)
    return tuple(values)


def _inline_image_width_mm(root: ET.Element) -> tuple[float, ...]:
    values: list[float] = []
    for extent in root.findall(".//wp:inline/wp:extent", NS):
        raw = extent.get("cx")
        if raw and raw.isdigit():
            values.append(round(int(raw) / 36000, 3))
    return tuple(values)


def _count_note_references(document_root: ET.Element, notes_root: ET.Element | None, kind: str) -> int:
    if kind == "footnote":
        references = document_root.findall(".//w:footnoteReference", NS)
        notes = notes_root.findall(".//w:footnote", NS) if notes_root is not None else []
    else:
        references = document_root.findall(".//w:endnoteReference", NS)
        notes = notes_root.findall(".//w:endnote", NS) if notes_root is not None else []
    if references:
        return len([item for item in references if _note_id(item) not in {"-1", "0"}])
    return len([item for item in notes if _note_id(item) not in {"-1", "0"}])


def _note_id(element: ET.Element) -> str | None:
    return element.get(f"{{{NS['w']}}}id")
