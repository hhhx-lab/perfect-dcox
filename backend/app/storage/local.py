from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.files_dir = self.root / "files"

    def ensure_ready(self) -> None:
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def store_bytes(self, filename: str, content: bytes) -> tuple[str, Path, str, int]:
        self.ensure_ready()
        suffix = Path(filename).suffix.lower()
        file_id = f"file_{uuid4().hex}"
        stored_name = f"{file_id}{suffix}"
        target_path = self.files_dir / stored_name
        target_path.write_bytes(content)
        return file_id, target_path, hashlib.sha256(content).hexdigest(), len(content)
