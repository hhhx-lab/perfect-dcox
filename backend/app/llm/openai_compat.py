from __future__ import annotations

import json
from typing import Any


class ChatCompletionParseError(ValueError):
    pass


def parse_chat_completion_content(raw_body: bytes) -> str:
    text = raw_body.decode("utf-8", errors="replace").strip()
    if not text:
        raise ChatCompletionParseError("LLM response body is empty.")
    if text.startswith("data:"):
        return _parse_sse_content(text)
    return _parse_json_content(text)


def _parse_json_content(text: str) -> str:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChatCompletionParseError("LLM response is neither JSON nor event-stream.") from exc
    content_parts = _content_parts_from_payload(payload)
    if not content_parts:
        raise ChatCompletionParseError("LLM response did not contain assistant content.")
    return "".join(content_parts).strip()


def _parse_sse_content(text: str) -> str:
    content_parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if data == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        content_parts.extend(_content_parts_from_payload(payload))
    if not content_parts:
        raise ChatCompletionParseError("LLM event-stream did not contain assistant content.")
    return "".join(content_parts).strip()


def _content_parts_from_payload(payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return []
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return []
    parts: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        for container_key in ("message", "delta"):
            container = choice.get(container_key)
            if isinstance(container, dict):
                parts.extend(_coerce_content(container.get("content")))
        parts.extend(_coerce_content(choice.get("text")))
    return parts


def _coerce_content(content: Any) -> list[str]:
    if content is None:
        return []
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return parts
    return [str(content)]
