from pathlib import Path
import os
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("FILE_STORAGE_ROOT", "/tmp/perfect-docx")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.main import app
