from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Callable
from urllib import error, request

from app.core.config import Settings
from app.llm.openai_compat import parse_chat_completion_content


@dataclass(frozen=True)
class LLMConnectivityResult:
    configured: bool
    reachable: bool
    status: str
    model: str | None
    base_url: str
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


UrlOpen = Callable[..., Any]


def check_llm_connectivity(settings: Settings, opener: UrlOpen = request.urlopen) -> LLMConnectivityResult:
    if not settings.llm_configured:
        return LLMConnectivityResult(
            configured=False,
            reachable=False,
            status="not_configured",
            model=settings.llm_model,
            base_url=_base_url(settings),
            error_message="LLM_API_KEY and LLM_MODEL are required before Agent extraction or final layout review can run.",
        )

    base_url = _base_url(settings)
    body = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "Return only a short plain response."},
            {"role": "user", "content": "Reply with ok."},
        ],
        "temperature": 0,
        "stream": True,
    }
    raw_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with opener(raw_request, timeout=settings.llm_health_timeout_seconds) as response:  # noqa: S310 - operator configured endpoint.
            content = parse_chat_completion_content(response.read())
        if not content.strip():
            raise ValueError("LLM response did not contain assistant content.")
    except error.HTTPError as exc:
        return LLMConnectivityResult(
            configured=True,
            reachable=False,
            status="unreachable",
            model=settings.llm_model,
            base_url=base_url,
            error_message=_http_error_message(exc),
        )
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint should surface provider details.
        return LLMConnectivityResult(
            configured=True,
            reachable=False,
            status="unreachable",
            model=settings.llm_model,
            base_url=base_url,
            error_message=f"{type(exc).__name__}: {exc}",
        )
    return LLMConnectivityResult(
        configured=True,
        reachable=True,
        status="reachable",
        model=settings.llm_model,
        base_url=base_url,
    )


def unverified_llm_status(settings: Settings) -> dict[str, object]:
    if not settings.llm_configured:
        return {
            "configured": False,
            "reachable": False,
            "status": "not_configured",
            "model": settings.llm_model,
            "base_url": _base_url(settings),
            "error_message": None,
        }
    return {
        "configured": True,
        "reachable": None,
        "status": "configured_unverified",
        "model": settings.llm_model,
        "base_url": _base_url(settings),
        "error_message": None,
    }


def _base_url(settings: Settings) -> str:
    return (settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")

def _http_error_message(exc: error.HTTPError) -> str:
    detail = ""
    try:
        detail = exc.read(500).decode("utf-8", errors="replace").strip()
    except Exception:
        detail = ""
    reason = f" {exc.reason}" if getattr(exc, "reason", None) else ""
    suffix = f": {detail}" if detail else ""
    return f"HTTP {exc.code}{reason}{suffix}"
