from __future__ import annotations

from dataclasses import dataclass, field
import base64
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Protocol
from urllib import request

from pypdf import PdfReader

from app.core.config import Settings
from app.llm.openai_compat import parse_chat_completion_content
from app.profiles.models import FormatProfile


class FinalLayoutReviewError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinalLayoutReviewPayload:
    pdf_path: Path
    profile_id: str
    profile_name: str
    checks: dict[str, bool]
    text_excerpt: str
    page_count: int
    page_images: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FinalLayoutReviewResult:
    passed: bool
    summary: str
    issues: list[str] = field(default_factory=list)


class FinalLayoutReviewer(Protocol):
    def review_pdf(self, payload: FinalLayoutReviewPayload) -> FinalLayoutReviewResult:
        """Return an LLM judgment for final PDF layout health."""


class OpenAICompatibleFinalLayoutReviewer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def review_pdf(self, payload: FinalLayoutReviewPayload) -> FinalLayoutReviewResult:
        if not (self.settings.llm_api_key and self.settings.llm_model):
            raise FinalLayoutReviewError("LLM_API_KEY and LLM_MODEL are required for final layout review.")
        base_url = (self.settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        content: list[dict[str, object]] = [
            {
                "type": "text",
                "text": (
                    "You are the final layout reviewer for a Word/PDF formatting pipeline. "
                    "Check only visual/layout health: garbled text, abnormal blank pages, overlap, "
                    "table/figure overflow, broken headers/footers, and suspicious TOC/page-number output. "
                    "Return strict JSON: {\"passed\": boolean, \"summary\": string, \"issues\": string[]}.\n"
                    f"Profile: {payload.profile_name} ({payload.profile_id})\n"
                    f"Checks: {json.dumps(payload.checks, ensure_ascii=False)}\n"
                    f"Page count: {payload.page_count}\n"
                    f"Extracted text excerpt:\n{payload.text_excerpt[:4000]}"
                ),
            }
        ]
        for image in payload.page_images[:3]:
            content.append({"type": "image_url", "image_url": {"url": image}})
        body = {
            "model": self.settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON. Do not edit the document.",
                },
                {"role": "user", "content": content},
            ],
            "temperature": 0,
            "stream": True,
            "response_format": {"type": "json_object"},
        }
        raw_request = request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(raw_request, timeout=self.settings.llm_timeout_seconds) as response:  # noqa: S310 - operator configured endpoint.
                content_text = parse_chat_completion_content(response.read())
            parsed = json.loads(content_text)
        except Exception as exc:  # noqa: BLE001 - surface provider details.
            raise FinalLayoutReviewError(f"Final layout LLM review failed: {exc}") from exc
        return FinalLayoutReviewResult(
            passed=bool(parsed.get("passed")),
            summary=str(parsed.get("summary") or ""),
            issues=[str(item) for item in parsed.get("issues", []) if str(item).strip()],
        )


def build_final_layout_payload(pdf_path: Path, profile: FormatProfile) -> FinalLayoutReviewPayload:
    page_count, text_excerpt = _pdf_text_excerpt(pdf_path)
    return FinalLayoutReviewPayload(
        pdf_path=pdf_path,
        profile_id=profile.id,
        profile_name=profile.name,
        checks={
            "garbled_text": profile.llm_final_review.check_garbled_text,
            "blank_pages": profile.llm_final_review.check_blank_pages,
            "overlap": profile.llm_final_review.check_overlap,
            "table_figure_overflow": profile.llm_final_review.check_table_figure_overflow,
        },
        text_excerpt=text_excerpt,
        page_count=page_count,
        page_images=_render_pdf_page_images(pdf_path),
    )


def _pdf_text_excerpt(pdf_path: Path) -> tuple[int, str]:
    try:
        reader = PdfReader(str(pdf_path))
        parts: list[str] = []
        for page in reader.pages[:5]:
            parts.append(page.extract_text() or "")
        return len(reader.pages), "\n".join(parts).strip()
    except Exception:
        return 0, ""


def _render_pdf_page_images(pdf_path: Path) -> list[str]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return []
    with TemporaryDirectory() as tmp_dir:
        output_prefix = Path(tmp_dir) / "page"
        completed = subprocess.run(
            [pdftoppm, "-png", "-r", "110", "-f", "1", "-l", "3", str(pdf_path), str(output_prefix)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return []
        images: list[str] = []
        for image_path in sorted(Path(tmp_dir).glob("page-*.png")):
            encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
            images.append(f"data:image/png;base64,{encoded}")
        return images
