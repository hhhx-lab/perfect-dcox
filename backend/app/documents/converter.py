from __future__ import annotations

from pathlib import Path
import subprocess


class DocumentConversionError(RuntimeError):
    pass


def convert_doc_to_docx(input_path: Path, output_dir: Path, soffice_bin: str | None) -> Path:
    if input_path.suffix.lower() == ".docx":
        return input_path
    if input_path.suffix.lower() != ".doc":
        raise DocumentConversionError(f"Unsupported legacy conversion input: {input_path.name}")
    if not soffice_bin:
        raise DocumentConversionError("SOFFICE_BIN is required to convert legacy .doc files.")
    soffice_path = Path(soffice_bin)
    if not soffice_path.exists():
        raise DocumentConversionError(f"SOFFICE_BIN does not exist: {soffice_bin}")
    if not input_path.exists():
        raise DocumentConversionError(f"Input file does not exist: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(soffice_path),
        "--headless",
        "--convert-to",
        "docx",
        "--outdir",
        str(output_dir),
        str(input_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output_path = output_dir / f"{input_path.stem}.docx"
    if completed.returncode != 0 or not output_path.exists():
        detail = (completed.stderr or completed.stdout or "no LibreOffice output").strip()
        raise DocumentConversionError(f"DOC to DOCX conversion failed: {detail}")
    return output_path
