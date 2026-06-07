from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from app.models import FileRecord


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files_dir = self.root / "files"
        self.outputs_dir = self.root / "outputs"

    def ensure_ready(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def store_bytes(self, filename: str, content: bytes) -> tuple[str, Path, str, int]:
        self.ensure_ready()
        suffix = Path(filename).suffix.lower()
        file_id = f"file_{uuid4().hex}"
        stored_name = f"{file_id}{suffix}"
        target_path = self.files_dir / stored_name
        target_path.write_bytes(content)
        return file_id, target_path, hashlib.sha256(content).hexdigest(), len(content)

    def store_generated_file(self, source_path: Path, filename: str, mime_type: str) -> FileRecord:
        self.ensure_ready()
        suffix = Path(filename).suffix.lower() or source_path.suffix.lower()
        file_id = f"file_{uuid4().hex}"
        target_path = self.outputs_dir / f"{file_id}{suffix}"
        shutil.copyfile(source_path, target_path)
        content = target_path.read_bytes()
        return FileRecord(
            file_id=file_id,
            filename=filename,
            mime_type=mime_type,
            size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_path=str(target_path),
        )
