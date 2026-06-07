from pathlib import Path
from types import SimpleNamespace

import pytest

from app.documents.converter import DocumentConversionError, convert_doc_to_docx
from app.documents.exporter import DocumentExportError, export_docx_to_pdf
from app.documents.formatter import format_docx_with_profile
from app.documents.parser import DocumentParseError, parse_docx
from tests.document_fixtures import create_minimal_thesis_docx, read_docx_text


def test_document_module_entry_points_exist(tmp_path: Path) -> None:
    assert callable(convert_doc_to_docx)
    assert callable(parse_docx)
    assert callable(format_docx_with_profile)
    assert callable(export_docx_to_pdf)
    assert issubclass(DocumentConversionError, RuntimeError)
    assert issubclass(DocumentExportError, RuntimeError)


def test_minimal_docx_fixture_preserves_expected_text(tmp_path: Path) -> None:
    path = create_minimal_thesis_docx(tmp_path / "sample.docx")

    text = read_docx_text(path)

    assert path.exists()
    assert "第一章 绪论" in text
    assert "这是一段正文内容，用于验证格式化后文本不会丢失。" in text
    assert "参考文献" in text


def test_doc_conversion_requires_configured_soffice(tmp_path: Path) -> None:
    legacy_doc = tmp_path / "legacy.doc"
    legacy_doc.write_bytes(b"legacy")

    with pytest.raises(DocumentConversionError) as exc:
        convert_doc_to_docx(legacy_doc, tmp_path / "converted", None)

    assert "SOFFICE_BIN" in str(exc.value)


def test_doc_conversion_invokes_soffice_and_returns_docx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    legacy_doc = tmp_path / "legacy.doc"
    legacy_doc.write_bytes(b"legacy")
    fake_soffice = tmp_path / "soffice"
    fake_soffice.write_text("#!/bin/sh\n", encoding="utf-8")
    output_dir = tmp_path / "converted"
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        calls.append(command)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "legacy.docx").write_bytes(b"converted")
        return SimpleNamespace(returncode=0, stderr="", stdout="ok")

    monkeypatch.setattr("app.documents.converter.subprocess.run", fake_run)

    converted = convert_doc_to_docx(legacy_doc, output_dir, str(fake_soffice))

    assert converted == output_dir / "legacy.docx"
    assert calls
    assert "--headless" in calls[0]
    assert "--convert-to" in calls[0]


def test_docx_input_bypasses_legacy_conversion(tmp_path: Path) -> None:
    docx = create_minimal_thesis_docx(tmp_path / "sample.docx")

    assert convert_doc_to_docx(docx, tmp_path / "converted", None) == docx


def test_doc_conversion_rejects_missing_input(tmp_path: Path) -> None:
    fake_soffice = tmp_path / "soffice"
    fake_soffice.write_text("#!/bin/sh\n", encoding="utf-8")

    with pytest.raises(DocumentConversionError) as exc:
        convert_doc_to_docx(tmp_path / "missing.doc", tmp_path / "converted", str(fake_soffice))

    assert "Input file does not exist" in str(exc.value)


def test_parse_docx_returns_structure_summary(tmp_path: Path) -> None:
    path = create_minimal_thesis_docx(tmp_path / "sample.docx")

    summary = parse_docx(path)

    assert summary["paragraph_count"] >= 6
    assert summary["table_count"] == 1
    assert summary["image_count"] == 0
    assert "第一章 绪论" in summary["heading_candidates"]
    assert "这是一段正文内容，用于验证格式化后文本不会丢失。" in summary["all_text"]
    assert summary["paragraph_styles"]


def test_parse_docx_rejects_corrupt_input(tmp_path: Path) -> None:
    corrupt = tmp_path / "broken.docx"
    corrupt.write_bytes(b"not a zip")

    with pytest.raises(DocumentParseError) as exc:
        parse_docx(corrupt)

    assert "DOCX parse failed" in str(exc.value)
