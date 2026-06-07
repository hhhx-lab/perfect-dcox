from __future__ import annotations

from pathlib import Path
import subprocess


class DocumentExportError(RuntimeError):
    pass


def export_docx_to_pdf(input_path: Path, output_dir: Path, soffice_bin: str | None) -> Path:
    if not soffice_bin:
        raise DocumentExportError("SOFFICE_BIN is required to export DOCX to PDF.")
    soffice_path = Path(soffice_bin)
    if not soffice_path.exists():
        raise DocumentExportError(f"SOFFICE_BIN does not exist: {soffice_bin}")
    if not input_path.exists():
        raise DocumentExportError(f"Input DOCX does not exist: {input_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(soffice_path),
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output_path = output_dir / f"{input_path.stem}.pdf"
    if completed.returncode != 0 or not output_path.exists():
        detail = (completed.stderr or completed.stdout or "no LibreOffice output").strip()
        raise DocumentExportError(f"DOCX to PDF export failed: {detail}")
    return output_path
