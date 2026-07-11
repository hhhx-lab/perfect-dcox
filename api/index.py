from pathlib import Path
import os
import sys
from urllib.parse import parse_qsl, urlencode


PROJECT_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("FILE_STORAGE_ROOT", "/tmp/perfect-docx")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.main import app as fastapi_app


class VercelPathRewrite:
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/api/index":
            params = parse_qsl(scope.get("query_string", b"").decode(), keep_blank_values=True)
            path = next((value for key, value in params if key == "path"), "")
            if path:
                remaining = [(key, value) for key, value in params if key != "path"]
                rewritten = dict(scope)
                rewritten["path"] = f"/api/{path.lstrip('/')}"
                rewritten["raw_path"] = rewritten["path"].encode()
                rewritten["query_string"] = urlencode(remaining).encode()
                scope = rewritten
        await self.application(scope, receive, send)


app = VercelPathRewrite(fastapi_app)
