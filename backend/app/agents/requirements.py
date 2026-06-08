from __future__ import annotations

import json
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import request
from uuid import uuid4

from pydantic import ValidationError

from app.agents.extraction import ExtractionSourceError, extract_rule_source_text
from app.core.config import Settings
from app.models import (
    ExtractionEvidence,
    RequirementRuleItem,
    RequirementSession,
    RequirementSessionMessage,
    RequirementSummary,
    UncertainItem,
)
from app.profiles.models import FormatProfile
from app.profiles.seed import load_builtin_profiles
from app.storage.repository import DuplicateProfileVersionError, JsonMetadataRepository

REQUIRED_FIELDS = [
    "page.size",
    "page.orientation",
    "page.margins_cm",
    "body.font.chinese",
    "body.font.latin",
    "body.font.size_pt",
    "body.font.color",
    "body.line_spacing",
    "body.first_line_indent_chars",
    "header_footer.footer_page_number",
    "outputs",
]
UNSUPPORTED_OVERRIDE_FIELDS = {
    "appendix": "附录",
    "cover": "封面",
    "toc": "目录",
    "notes": "脚注/尾注",
}
POINT_BY_CHINESE_SIZE = {
    "初号": 42.0,
    "小初": 36.0,
    "一号": 26.0,
    "小一": 24.0,
    "二号": 22.0,
    "小二": 18.0,
    "三号": 16.0,
    "小三": 15.0,
    "四号": 14.0,
    "小四": 12.0,
    "五号": 10.5,
    "小五": 9.0,
}
COLOR_BY_NAME = {
    "黑色": "000000",
    "黑": "000000",
    "black": "000000",
    "白色": "FFFFFF",
    "白": "FFFFFF",
    "white": "FFFFFF",
    "红色": "FF0000",
    "红": "FF0000",
    "red": "FF0000",
    "蓝色": "0000FF",
    "蓝": "0000FF",
    "blue": "0000FF",
    "绿色": "008000",
    "绿": "008000",
    "green": "008000",
}


class RequirementExtractionProvider(Protocol):
    def extract_summary(self, source_text: str, source_meta: dict[str, str], base_profile: FormatProfile) -> dict[str, Any]:
        """Return a structured requirement summary payload."""


class OpenAICompatibleRequirementProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def extract_summary(self, source_text: str, source_meta: dict[str, str], base_profile: FormatProfile) -> dict[str, Any]:
        if not (self.settings.llm_api_key and self.settings.llm_model):
            raise ExtractionSourceError("LLM_API_KEY and LLM_MODEL are required for live requirement extraction.")
        base_url = (self.settings.llm_base_url or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract thesis Word formatting requirements. Return only JSON with keys "
                        "items, uncertain_items, evidence, and profile_overrides. Do not invent unsupported rules. "
                        "Represent font colors as six-digit RGB hex strings in TextFont.color, for example 000000 for black."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "source_meta": source_meta,
                            "source_text": source_text[:16000],
                            "base_profile_schema_sample": base_profile.model_dump(mode="json"),
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        raw_request = request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(raw_request, timeout=self.settings.llm_timeout_seconds) as response:  # noqa: S310 - URL is configured by operator.
                response_payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - surface provider diagnostics to the session.
            raise ExtractionSourceError(f"Live LLM requirement extraction failed: {exc}") from exc
        try:
            content = response_payload["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ExtractionSourceError("Live LLM response did not contain valid structured JSON.") from exc


@dataclass(frozen=True)
class RequirementDraft:
    summary: RequirementSummary
    profile: FormatProfile
    evidence: list[ExtractionEvidence]
    uncertain_items: list[UncertainItem]


class RequirementSessionService:
    def __init__(
        self,
        repository: JsonMetadataRepository,
        storage_root: Path,
        soffice_bin: str | None,
        provider: RequirementExtractionProvider | None = None,
    ) -> None:
        self.repository = repository
        self.storage_root = storage_root
        self.soffice_bin = soffice_bin
        self.provider = provider

    def create_session(
        self,
        source_type: str,
        natural_language: str | None = None,
        file_id: str | None = None,
    ) -> RequirementSession:
        if source_type not in {"conversation", "document"}:
            raise ExtractionSourceError("source_type must be conversation or document.")
        if source_type == "conversation" and not (natural_language or "").strip():
            raise ExtractionSourceError("natural_language is required for conversation sessions.")
        if source_type == "document" and not file_id:
            raise ExtractionSourceError("file_id is required for document sessions.")

        source_text = self._source_text(source_type, natural_language, file_id, f"rs_{uuid4().hex}")
        draft = self._build_draft(source_text, source_type, file_id=file_id)
        messages = [
            RequirementSessionMessage(role="user", content=(natural_language or "已上传格式规则文档。").strip()),
            RequirementSessionMessage(role="agent", content=_agent_summary_message(draft)),
        ]
        status = "needs_user_answer" if draft.summary.missing_fields else "ready_for_confirmation"
        session = RequirementSession(
            session_id=f"rs_{uuid4().hex}",
            source_type=source_type,  # type: ignore[arg-type]
            status=status,
            file_id=file_id,
            natural_language=natural_language.strip() if natural_language else None,
            messages=messages,
            missing_fields=draft.summary.missing_fields,
            requirement_summary=draft.summary,
            profile_draft=draft.profile,
            evidence=draft.evidence,
            uncertain_items=draft.uncertain_items,
        )
        return self.repository.add_requirement_session(session)

    def add_message(self, session_id: str, content: str) -> RequirementSession:
        session = self._get_session(session_id)
        text = content.strip()
        if not text:
            raise ExtractionSourceError("Message content cannot be empty.")
        session.messages.append(RequirementSessionMessage(role="user", content=text))
        merged_text = "\n".join([session.natural_language or "", text])
        if session.source_type == "document" and session.file_id:
            merged_text = "\n".join([self._document_text(session.file_id, session.session_id), text])
        draft = self._build_draft(merged_text, session.source_type, file_id=session.file_id)
        session.requirement_summary = draft.summary
        session.profile_draft = draft.profile
        session.evidence = draft.evidence
        session.uncertain_items = draft.uncertain_items
        session.missing_fields = draft.summary.missing_fields
        session.status = "needs_user_answer" if session.missing_fields else "ready_for_confirmation"
        session.messages.append(RequirementSessionMessage(role="agent", content=_agent_summary_message(draft)))
        return self.repository.update_requirement_session(session)

    def confirm_session(
        self,
        session_id: str,
        profile_name: str,
        profile_version: str,
        profile_description: str | None = None,
    ) -> RequirementSession:
        session = self._get_session(session_id)
        if session.profile_draft is None:
            raise ExtractionSourceError("Requirement session has no profile draft to confirm.")
        if not profile_name.strip():
            raise ExtractionSourceError("profile_name is required.")
        profile = session.profile_draft.model_copy(deep=True)
        profile.id = _slugify_profile_id(profile_name)
        profile.name = profile_name.strip()
        profile.version = profile_version.strip()
        profile.description = profile_description or profile.description
        profile.status = "active"
        profile.source = "user"
        try:
            self.repository.save_profile_version(profile)
        except DuplicateProfileVersionError as exc:
            raise ExtractionSourceError(str(exc)) from exc
        except ValidationError as exc:
            raise ExtractionSourceError(str(exc)) from exc
        session.status = "confirmed"
        session.profile_draft = profile
        session.confirmed_profile_id = profile.id
        session.messages.append(RequirementSessionMessage(role="system", content=f"已确认并保存 Profile：{profile.name} v{profile.version}"))
        return self.repository.update_requirement_session(session)

    def _get_session(self, session_id: str) -> RequirementSession:
        session = self.repository.get_requirement_session(session_id)
        if session is None:
            raise ExtractionSourceError("Requirement session not found.")
        return session

    def _source_text(self, source_type: str, natural_language: str | None, file_id: str | None, work_id: str) -> str:
        if source_type == "conversation":
            return (natural_language or "").strip()
        if not file_id:
            raise ExtractionSourceError("file_id is required for document sessions.")
        return self._document_text(file_id, work_id)

    def _document_text(self, file_id: str, work_id: str) -> str:
        record = self.repository.get_file(file_id)
        if record is None:
            raise ExtractionSourceError(f"Rule source file not found: {file_id}")
        return extract_rule_source_text(record, self.storage_root / "work" / work_id, self.soffice_bin)

    def _build_draft(self, source_text: str, source_type: str, file_id: str | None) -> RequirementDraft:
        base = _base_profile()
        if self.provider is None:
            raise ExtractionSourceError("LLM requirement extraction is not configured; cannot analyze formatting rules.")
        payload = self.provider.extract_summary(
            source_text,
            {"source_type": source_type, "file_id": file_id or ""},
            base,
        )
        draft = _draft_from_provider_payload(payload, base, source_type)
        return _draft_with_deterministic_rules(
            source_text,
            draft,
            base,
            "document" if source_type == "document" else "conversation",
        )


def _base_profile() -> FormatProfile:
    return load_builtin_profiles()["ecnu_thesis"].model_copy(deep=True)


def _deterministic_draft(source_text: str, base: FormatProfile, source: str) -> RequirementDraft:
    profile = base.model_copy(deep=True)
    profile.id = "agent_profile_draft"
    profile.name = "Agent 拆解格式 Profile 草案"
    profile.version = "0.1.0"
    profile.status = "draft"
    profile.source = "imported"
    profile.description = "由 Agent 从格式需求中拆解生成；保存前请确认名称和版本。"

    text = _normalize_text(source_text)
    items: list[RequirementRuleItem] = []
    evidence: list[ExtractionEvidence] = []

    def add(field: str, label: str, value: str, quote: str, confidence: float = 0.86) -> None:
        items.append(
            RequirementRuleItem(
                field_path=field,
                label=label,
                value=value,
                source=source,  # type: ignore[arg-type]
                confidence=confidence,
                evidence=[quote] if quote else [],
            )
        )
        evidence.append(
            ExtractionEvidence(
                field_path=field,
                source="document" if source == "document" else "natural_language",
                quote=quote or value,
                confidence=confidence,
            )
        )

    def add_default(field: str, label: str, value: str, confidence: float = 0.55) -> None:
        items.append(
            RequirementRuleItem(
                field_path=field,
                label=label,
                value=value,
                source="system_default",
                confidence=confidence,
                evidence=[],
                needs_confirmation=True,
            )
        )

    if re.search(r"(?<![A-Za-z0-9])A4(?![A-Za-z0-9])", source_text, re.IGNORECASE):
        profile.page.size = "A4"
        add("page.size", "纸张", "A4", "A4")
    if re.search(r"(?<![A-Za-z0-9])letter(?![A-Za-z0-9])", text, re.IGNORECASE):
        profile.page.size = "Letter"
        add("page.size", "纸张", "Letter", "Letter")

    if re.search(r"(纵向|portrait)", text, re.IGNORECASE) and re.search(r"个别[^。；;\n]{0,24}(横向|landscape)", text, re.IGNORECASE):
        profile.page.orientation = "portrait"
        add("page.orientation", "页面方向", "portrait", "纵向为主，个别页面横向")
    elif re.search(r"(横向|landscape)", text, re.IGNORECASE):
        profile.page.orientation = "landscape"
        add("page.orientation", "页面方向", "landscape", "横向")
    elif "纵向" in text or "portrait" in text.lower() or "个别页面可以采用" in text:
        profile.page.orientation = "portrait"
        add("page.orientation", "页面方向", "portrait", "纵向")

    margin_matches = _extract_margins_cm(text)
    if margin_matches:
        for key, value in margin_matches.items():
            setattr(profile.page.margins_cm, key, value)
        add("page.margins_cm", "页边距", _margin_value(profile), _margin_quote(margin_matches))

    chinese_font = _first_match(text, ["宋体", "仿宋", "黑体", "楷体", "微软雅黑"])
    latin_font = _first_match(text, ["Times New Roman", "Arial", "Calibri", "Cambria"])
    size_pt = _extract_body_size_pt(text) or _extract_size_pt(text)
    if chinese_font:
        profile.body.font.chinese = _office_font(chinese_font)
        profile.fonts.default_chinese = _office_font(chinese_font)
        add("body.font.chinese", "中文正文字体", profile.body.font.chinese, chinese_font)
    if latin_font:
        profile.body.font.latin = latin_font
        profile.fonts.default_latin = latin_font
        add("body.font.latin", "英文字体", latin_font, latin_font)
    if size_pt:
        profile.body.font.size_pt = size_pt
        profile.fonts.default_size_pt = size_pt
        add("body.font.size_pt", "正文字号", f"{size_pt:g} pt", f"{size_pt:g}pt")

    title_size_pt = _extract_title_size_pt(text)
    section_heading_size_pt = _extract_section_heading_size_pt(text)
    if title_size_pt or re.search(r"中文题名[^。；;\n]{0,24}黑体", text):
        profile.headings[0].font.chinese = "SimHei"
        profile.headings[0].font.size_pt = title_size_pt or profile.headings[0].font.size_pt
        profile.headings[0].font.weight = "bold"
        add(
            "headings[1].font",
            "题名字体",
            f"黑体 {profile.headings[0].font.size_pt:g} pt",
            "中文题名",
            0.78,
        )
    if section_heading_size_pt or re.search(r"(各段标题|段标题|标题)[^。；;\n]{0,24}黑体", text):
        for heading in profile.headings[1:]:
            heading.font.chinese = "SimHei"
            heading.font.size_pt = section_heading_size_pt or heading.font.size_pt
            heading.font.weight = "bold"
        add(
            "headings[2].font",
            "段落标题字体",
            f"黑体 {profile.headings[min(1, len(profile.headings) - 1)].font.size_pt:g} pt",
            "各段标题",
            0.78,
        )
    if re.search(r"(理科|中文各层次)[^。；;\n]{0,80}(1、|1\.1)", text):
        profile.headings[0].numbering = "decimal-chinese-pause"
        if len(profile.headings) > 1:
            profile.headings[1].numbering = "decimal-dot"
        add("headings.numbering", "标题序号", "理科层级：1、 / 1.1 / 1.1.1", "理科中文层次", 0.8)

    body_color = _extract_body_or_general_font_color(text)
    heading_color = _extract_font_color(text, "标题")
    if body_color:
        _apply_color_to_profile_fonts(profile, body_color, include_headings=heading_color is None)
        add("body.font.color", "正文字色", f"#{body_color}", _color_quote(text, body_color))
    if heading_color:
        for heading in profile.headings:
            heading.font.color = heading_color
        add("headings.font.color", "标题字色", f"#{heading_color}", _color_quote(text, heading_color), 0.82)

    line_spacing = _extract_line_spacing(text)
    if line_spacing:
        profile.body.line_spacing = line_spacing
        add("body.line_spacing", "正文行距", f"{line_spacing:g}", f"{line_spacing:g} 倍行距")

    if re.search(r"首行缩进\s*2\s*(个)?字", text):
        profile.body.first_line_indent_chars = 2
        add("body.first_line_indent_chars", "首行缩进", "2 字符", "首行缩进 2 字符")

    header_text = _extract_header_text(source_text)
    if header_text:
        profile.header_footer.header_text = header_text
        add("header_footer.header_text", "页眉文字", header_text, header_text, 0.72)
    if "页眉" in text:
        alignment = _extract_alignment(text, "页眉")
        if alignment:
            profile.header_footer.header_alignment = alignment
            add("header_footer.header_alignment", "页眉对齐", alignment, f"页眉{_alignment_zh(alignment)}", 0.72)

    if "页码" in text:
        profile.header_footer.footer_page_number = not bool(re.search(r"(不|无需|不要|取消|无)\s*页码", text))
        add(
            "header_footer.footer_page_number",
            "页脚页码",
            "启用" if profile.header_footer.footer_page_number else "关闭",
            "页码",
            0.78,
        )
        alignment = _extract_alignment(text, "页码") or _extract_alignment(text, "页面底端")
        if alignment:
            profile.header_footer.footer_alignment = alignment
            add("header_footer.footer_alignment", "页码对齐", alignment, f"页码{_alignment_zh(alignment)}", 0.76)

    if not _field_covered("headings", {item.field_path for item in items}) and ("黑体" in text or "标题" in text):
        profile.headings[0].font.chinese = "SimHei"
        add("headings", "标题层级", "标题按层级套用黑体/加粗规则", "标题/黑体", 0.72)

    if re.search(r"表名[^。；;\n]{0,24}(正上方|上方)", text):
        profile.table.caption.position = "above"
        add("table.caption.position", "表题位置", "表格上方", "表名放在表格正上方", 0.82)
    elif "表" in text:
        add("table.caption", "表题", f"{profile.table.caption.prefix}题位于表格{_caption_position_zh(profile.table.caption.position)}", "表", 0.68)
    if re.search(r"图名[^。；;\n]{0,24}(正下方|下方)", text):
        profile.figure.caption.position = "below"
        add("figure.caption.position", "图题位置", "图片下方", "图名放在图件正下方", 0.82)
    elif "图" in text:
        add("figure.caption", "图题", f"{profile.figure.caption.prefix}题位于图片{_caption_position_zh(profile.figure.caption.position)}", "图", 0.68)
    if re.search(r"公式[^。；;\n]{0,24}(居中|独立成行)", text):
        profile.equations.alignment = "center"
        add("equations.alignment", "公式对齐", "center", "公式应独立成行居中", 0.78)
    if "参考文献" in text or "GB/T 7714" in source_text:
        profile.references.style = "GB/T 7714"
        add("references.style", "参考文献", profile.references.style, "参考文献", 0.78)

    add("outputs", "输出格式", "DOCX + PDF", "默认输出 Word/PDF", 0.66)

    covered = {item.field_path for item in items}
    if not _field_covered("headings", covered):
        add_default("headings", "标题层级", "使用基础标题默认规则，保存前可编辑。")
    if not _field_covered("body.font.color", covered):
        add_default("body.font.color", "正文字色", f"#{profile.body.font.color}")
    if not _field_covered("table.caption", covered):
        add_default("table.caption", "表题", f"{profile.table.caption.prefix}题位于表格{_caption_position_zh(profile.table.caption.position)}。")
    if not _field_covered("figure.caption", covered):
        add_default("figure.caption", "图题", f"{profile.figure.caption.prefix}题位于图片{_caption_position_zh(profile.figure.caption.position)}。")
    if not _field_covered("references.style", covered):
        add_default("references.style", "参考文献", profile.references.style)
    covered = {item.field_path for item in items}
    missing = [field for field in REQUIRED_FIELDS if not _field_covered(field, covered)]
    uncertain = [
        UncertainItem(
            field_path=field,
            message=f"{field} 未在输入中明确识别。",
            suggestion="请在对话中补充，或接受草案默认值后保存为 Profile。",
        )
        for field in missing
    ]
    return RequirementDraft(
        summary=RequirementSummary(items=items, missing_fields=missing, unsupported_or_uncertain_rules=uncertain),
        profile=profile,
        evidence=evidence,
        uncertain_items=uncertain,
    )


def _draft_from_provider_payload(payload: dict[str, Any], base: FormatProfile, source_type: str) -> RequirementDraft:
    profile = base.model_copy(deep=True)
    payload = _normalize_provider_payload(payload, base, source_type)
    overrides = payload.get("profile_overrides") or {}
    if not isinstance(overrides, dict):
        raise ExtractionSourceError("profile_overrides must be an object.")
    try:
        profile = _profile_with_overrides(profile, overrides)
        profile.id = "agent_profile_draft"
        profile.name = "Agent 拆解格式 Profile 草案"
        profile.version = "0.1.0"
        profile.status = "draft"
        profile.source = "imported"
        profile = FormatProfile.model_validate(profile.model_dump(mode="json"))
        items = [RequirementRuleItem.model_validate(item) for item in payload.get("items", [])]
        evidence = [
            ExtractionEvidence(
                **{
                    **item,
                    "source": "document" if source_type == "document" else "natural_language",
                }
            )
            for item in payload.get("evidence", [])
        ]
        uncertain = [UncertainItem.model_validate(item) for item in payload.get("uncertain_items", [])]
    except ValidationError as exc:
        raise ExtractionSourceError(f"Requirement provider output failed schema validation: {exc}") from exc
    covered = {item.field_path for item in items}
    missing = [field for field in REQUIRED_FIELDS if not _field_covered(field, covered)]
    return RequirementDraft(
        summary=RequirementSummary(items=items, missing_fields=missing, unsupported_or_uncertain_rules=uncertain),
        profile=profile,
        evidence=evidence,
        uncertain_items=uncertain,
    )


def _normalize_provider_payload(payload: dict[str, Any], base: FormatProfile, source_type: str) -> dict[str, Any]:
    normalized = dict(payload)
    normalized_items = [_normalize_provider_item(item, source_type) for item in payload.get("items", []) if isinstance(item, dict)]
    normalized["items"] = [item for item in normalized_items if item["field_path"]]
    normalized_evidence = [
        _normalize_provider_evidence(item, source_type) for item in payload.get("evidence", []) if isinstance(item, dict)
    ]
    normalized["evidence"] = [item for item in normalized_evidence if item["field_path"]]
    unsupported = _unsupported_uncertain_items(payload.get("profile_overrides") or {})
    normalized["uncertain_items"] = [
        _normalize_uncertain_item(item)
        for item in [*(payload.get("uncertain_items") or []), *unsupported]
        if isinstance(item, dict)
    ]
    overrides = payload.get("profile_overrides") or {}
    if isinstance(overrides, dict):
        normalized["profile_overrides"] = _normalize_profile_overrides(overrides, base)
    return normalized


def _unsupported_uncertain_items(overrides: Any) -> list[dict[str, str]]:
    if not isinstance(overrides, dict):
        return []
    items: list[dict[str, str]] = []
    for field_path, label in UNSUPPORTED_OVERRIDE_FIELDS.items():
        if field_path not in overrides:
            continue
        items.append(
            {
                "field_path": field_path,
                "message": f"LLM 识别到{label}规则，但当前 Profile schema 还不能自动执行该类规则。",
                "suggestion": f"导出后在质量报告中保留人工复核，或后续扩展 {field_path} schema。",
            }
        )
    return items


def _normalize_uncertain_item(item: dict[str, Any]) -> dict[str, str]:
    field_path = str(item.get("field_path") or item.get("field") or item.get("id") or "general").strip() or "general"
    if field_path == "unknown":
        field_path = "general"
    message = str(item.get("message") or item.get("question") or item.get("reason") or f"{field_path} 需要确认。").strip()
    suggestion = str(item.get("suggestion") or item.get("hint") or "请补充该规则，或确认使用当前 Profile 草案。").strip()
    return {"field_path": field_path, "message": message, "suggestion": suggestion}


def _normalize_provider_item(item: dict[str, Any], source_type: str) -> dict[str, Any]:
    field_path = str(item.get("field_path") or item.get("field") or item.get("path") or "").strip()
    value = item.get("value")
    label = str(item.get("label") or _field_label(field_path) or field_path or "格式规则")
    source = item.get("source")
    if source not in {"conversation", "document", "system_default", "user_confirmed"}:
        source = "document" if source_type == "document" else "conversation"
    confidence = item.get("confidence")
    if confidence is None:
        confidence = 0.78
    evidence = item.get("evidence") or item.get("quotes") or []
    if isinstance(evidence, str):
        evidence = [evidence]
    return {
        "field_path": field_path,
        "label": label,
        "value": str(value if value is not None else ""),
        "source": source,
        "confidence": confidence,
        "evidence": evidence,
        "needs_confirmation": bool(item.get("needs_confirmation", False)),
        "supported": bool(item.get("supported", True)),
    }


def _normalize_provider_evidence(item: dict[str, Any], source_type: str) -> dict[str, Any]:
    return {
        "field_path": str(item.get("field_path") or item.get("field") or item.get("path") or "").strip(),
        "source": "document" if source_type == "document" else "natural_language",
        "quote": item.get("quote") or item.get("evidence") or item.get("text"),
        "note": item.get("note"),
        "confidence": item.get("confidence", 0.78),
    }


def _normalize_profile_overrides(overrides: dict[str, Any], base: FormatProfile) -> dict[str, Any]:
    data = base.model_dump(mode="json")
    overrides = dict(overrides)
    for field_path in UNSUPPORTED_OVERRIDE_FIELDS:
        overrides.pop(field_path, None)
    title_override = overrides.pop("title", None)
    if isinstance(title_override, dict):
        headings = overrides.setdefault("headings", [])
        if not isinstance(headings, list):
            headings = []
            overrides["headings"] = headings
        if not headings:
            headings.append({"level": 1})
        if isinstance(headings[0], dict):
            _deep_merge(headings[0], title_override)
    unknown_top_level = sorted(set(overrides) - set(data))
    if unknown_top_level:
        raise ExtractionSourceError(f"profile_overrides contains unsupported top-level field(s): {', '.join(unknown_top_level)}")
    allowed = _filter_to_shape(overrides, data)
    _normalize_font_defaults(allowed.get("fonts"))
    _normalize_font_container((allowed.get("body") or {}).get("font"))
    _normalize_font_container((allowed.get("abstract") or {}).get("title_font"))
    _normalize_font_container((allowed.get("abstract") or {}).get("body_font"))
    _normalize_font_container(((allowed.get("table") or {}).get("caption") or {}).get("font"))
    _normalize_font_container(((allowed.get("figure") or {}).get("caption") or {}).get("font"))
    _normalize_font_container((allowed.get("references") or {}).get("font"))
    _normalize_font_container((allowed.get("header_footer") or {}).get("font"))

    headings = allowed.get("headings")
    if isinstance(headings, list):
        base_headings = data["headings"]
        normalized_headings = []
        for index, heading in enumerate(headings[: len(base_headings)]):
            if not isinstance(heading, dict):
                continue
            merged = dict(base_headings[index])
            _deep_merge(merged, _filter_to_shape(heading, merged))
            _normalize_font_container(merged.get("font"))
            normalized_headings.append(merged)
        if normalized_headings:
            allowed["headings"] = normalized_headings + base_headings[len(normalized_headings) :]
        else:
            allowed.pop("headings", None)
    return allowed


def _filter_to_shape(source: Any, shape: Any) -> Any:
    if isinstance(source, dict) and isinstance(shape, dict):
        result: dict[str, Any] = {}
        for key, value in source.items():
            if key not in shape:
                continue
            result[key] = _filter_to_shape(value, shape[key])
        return result
    if isinstance(source, list) and isinstance(shape, list) and shape:
        return [_filter_to_shape(item, shape[min(index, len(shape) - 1)]) for index, item in enumerate(source)]
    return source


def _normalize_font_container(font: Any) -> None:
    if not isinstance(font, dict):
        return
    size_hao = font.pop("size_hao", None)
    if "size_pt" not in font and size_hao:
        font["size_pt"] = _point_from_chinese_size(str(size_hao))
    if "latin" not in font:
        font["latin"] = "Times New Roman"
    if "weight" not in font:
        font["weight"] = "normal"
    if "color" in font:
        font["color"] = str(font["color"]).strip().lstrip("#").upper()


def _normalize_font_defaults(fonts: Any) -> None:
    if not isinstance(fonts, dict):
        return
    size_hao = fonts.pop("size_hao", None)
    if "default_size_pt" not in fonts and size_hao:
        fonts["default_size_pt"] = _point_from_chinese_size(str(size_hao))


def _deep_merge(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _point_from_chinese_size(label: str) -> float:
    return POINT_BY_CHINESE_SIZE.get(label.replace("号", ""), 10.5)


def _field_label(field_path: str) -> str:
    labels = {
        "page.size": "纸张",
        "page.orientation": "页面方向",
        "page.margins_cm": "页边距",
        "body.font.chinese": "正文中文字体",
        "body.font.latin": "正文英文字体",
        "body.font.size_pt": "正文字号",
        "body.line_spacing": "正文行距",
        "body.first_line_indent_chars": "首行缩进",
        "header_footer.footer_page_number": "页脚页码",
        "header_footer.footer_alignment": "页码对齐",
        "table.caption.position": "表题位置",
        "figure.caption.position": "图题位置",
        "equations.alignment": "公式对齐",
        "references.style": "参考文献",
    }
    return labels.get(field_path, field_path)


def _draft_with_deterministic_rules(
    source_text: str,
    draft: RequirementDraft,
    base: FormatProfile,
    source: str,
) -> RequirementDraft:
    deterministic = _deterministic_draft(source_text, base, source)
    direct_items = [item for item in deterministic.summary.items if item.source != "system_default"]
    direct_fields = {item.field_path for item in direct_items}
    profile = draft.profile.model_copy(deep=True)
    for field in direct_fields:
        _apply_deterministic_profile_field(profile, deterministic.profile, field)

    items = [item for item in draft.summary.items if not _field_covered_by_any(item.field_path, direct_fields)]
    covered = {item.field_path for item in items}
    for item in deterministic.summary.items:
        if item.source == "system_default" and _field_covered(item.field_path, covered):
            continue
        items.append(item)
        covered.add(item.field_path)

    evidence = [
        item
        for item in draft.evidence
        if not _field_covered_by_any(item.field_path, direct_fields)
    ]
    evidence.extend(deterministic.evidence)

    covered = {item.field_path for item in items}
    missing = [field for field in REQUIRED_FIELDS if not _field_covered(field, covered)]
    uncertain = [
        item
        for item in [*draft.uncertain_items, *deterministic.uncertain_items]
        if not _field_covered(item.field_path, covered)
    ]
    return RequirementDraft(
        summary=RequirementSummary(items=items, missing_fields=missing, unsupported_or_uncertain_rules=uncertain),
        profile=profile,
        evidence=evidence,
        uncertain_items=uncertain,
    )


def _apply_deterministic_profile_field(target: FormatProfile, source: FormatProfile, field: str) -> None:
    if field == "page.size":
        target.page.size = source.page.size
    elif field == "page.orientation":
        target.page.orientation = source.page.orientation
    elif field == "page.margins_cm":
        target.page.margins_cm = source.page.margins_cm.model_copy(deep=True)
    elif field == "body.font.chinese":
        target.body.font.chinese = source.body.font.chinese
        target.fonts.default_chinese = source.fonts.default_chinese
    elif field == "body.font.latin":
        target.body.font.latin = source.body.font.latin
        target.fonts.default_latin = source.fonts.default_latin
    elif field == "body.font.size_pt":
        target.body.font.size_pt = source.body.font.size_pt
        target.fonts.default_size_pt = source.fonts.default_size_pt
    elif field == "body.font.color":
        target.body.font.color = source.body.font.color
    elif field == "body.line_spacing":
        target.body.line_spacing = source.body.line_spacing
    elif field == "body.first_line_indent_chars":
        target.body.first_line_indent_chars = source.body.first_line_indent_chars
    elif field == "headings[1].font":
        if target.headings and source.headings:
            target.headings[0].font = source.headings[0].font.model_copy(deep=True)
    elif field == "headings[2].font":
        for index in range(1, min(len(target.headings), len(source.headings))):
            target.headings[index].font = source.headings[index].font.model_copy(deep=True)
    elif field == "headings.numbering":
        for index in range(min(len(target.headings), len(source.headings))):
            target.headings[index].numbering = source.headings[index].numbering
    elif field == "headings.font.color":
        for index in range(min(len(target.headings), len(source.headings))):
            target.headings[index].font.color = source.headings[index].font.color
    elif field == "header_footer.header_text":
        target.header_footer.header_text = source.header_footer.header_text
    elif field == "header_footer.header_alignment":
        target.header_footer.header_alignment = source.header_footer.header_alignment
    elif field == "header_footer.footer_page_number":
        target.header_footer.footer_page_number = source.header_footer.footer_page_number
    elif field == "header_footer.footer_alignment":
        target.header_footer.footer_alignment = source.header_footer.footer_alignment
    elif field == "table.caption.position":
        target.table.caption.position = source.table.caption.position
    elif field == "figure.caption.position":
        target.figure.caption.position = source.figure.caption.position
    elif field == "equations.alignment":
        target.equations.alignment = source.equations.alignment
    elif field == "references.style":
        target.references.style = source.references.style


def _profile_with_overrides(profile: FormatProfile, overrides: dict[str, Any]) -> FormatProfile:
    data = profile.model_dump(mode="json")

    def merge(target: dict[str, Any], source: dict[str, Any]) -> None:
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                merge(target[key], value)
            else:
                target[key] = value

    merge(data, overrides)
    return FormatProfile.model_validate(data)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("：", ":").replace("，", ","))


def _extract_margins_cm(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    aliases = {
        "top": ["上", "上边距"],
        "bottom": ["下", "下边距"],
        "left": ["左", "左边距"],
        "right": ["右", "右边距"],
    }
    for key, names in aliases.items():
        for name in names:
            match = re.search(rf"{re.escape(name)}(?:边距)?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:cm|厘米)", text, re.IGNORECASE)
            if match:
                result[key] = float(match.group(1))
                break
    return result


def _extract_size_pt(text: str) -> float | None:
    for label, value in _chinese_size_items():
        if label in text:
            return value
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:pt|磅)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _extract_body_size_pt(text: str) -> float | None:
    for label, value in _chinese_size_items():
        if re.search(rf"正文[^。；;\n]{{0,30}}{label}", text) or re.search(rf"{label}[^。；;\n]{{0,12}}正文", text):
            return value
    match = re.search(r"正文[^。；;\n]{0,30}(\d+(?:\.\d+)?)\s*(?:pt|磅)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _extract_title_size_pt(text: str) -> float | None:
    return _extract_anchored_size_pt(text, "中文题名") or _extract_anchored_size_pt(text, "论文题目")


def _extract_section_heading_size_pt(text: str) -> float | None:
    return _extract_anchored_size_pt(text, "各段标题") or _extract_anchored_size_pt(text, "段标题")


def _extract_anchored_size_pt(text: str, anchor: str) -> float | None:
    for label, value in _chinese_size_items():
        if re.search(rf"{anchor}[^。；;\n]{{0,30}}{label}", text):
            return value
    match = re.search(rf"{anchor}[^。；;\n]{{0,30}}(\d+(?:\.\d+)?)\s*(?:pt|磅)", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _chinese_size_items() -> list[tuple[str, float]]:
    return sorted(
        POINT_BY_CHINESE_SIZE.items(),
        key=lambda item: (item[0].startswith("小"), len(item[0])),
        reverse=True,
    )


def _extract_line_spacing(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:倍)?行距", text)
    if not match:
        match = re.search(r"行距[^0-9]{0,8}(\d+(?:\.\d+)?)\s*倍", text)
    return float(match.group(1)) if match else None


def _extract_font_color(text: str, anchor: str) -> str | None:
    hex_match = re.search(rf"{re.escape(anchor)}[^。；;\n]{{0,24}}#?([0-9A-Fa-f]{{6}})", text)
    if hex_match:
        return hex_match.group(1).upper()
    for name, value in COLOR_BY_NAME.items():
        if re.search(rf"{re.escape(anchor)}[^。；;\n]{{0,24}}(?:为|要|统一|设置为|颜色为|色为)?\s*{re.escape(name)}", text, re.IGNORECASE):
            return value
    return None


def _extract_body_or_general_font_color(text: str) -> str | None:
    body_color = _extract_font_color(text, "正文")
    if body_color:
        return body_color
    return _extract_general_font_color(text)


def _extract_general_font_color(text: str) -> str | None:
    scope_words = ("标题", "页眉", "页脚", "页码", "表题", "图题", "参考文献")
    for anchor in ("字色", "字体颜色"):
        hex_match = re.search(rf"{anchor}[^。；;\n]{{0,24}}#?([0-9A-Fa-f]{{6}})", text)
        if hex_match and not any(word in text[max(0, hex_match.start() - 8) : hex_match.start()] for word in scope_words):
            return hex_match.group(1).upper()
        for name, value in COLOR_BY_NAME.items():
            match = re.search(rf"{anchor}[^。；;\n]{{0,24}}(?:为|要|统一|设置为|颜色为|色为)?\s*{re.escape(name)}", text, re.IGNORECASE)
            if match and not any(word in text[max(0, match.start() - 8) : match.start()] for word in scope_words):
                return value
    return None


def _apply_color_to_profile_fonts(profile: FormatProfile, color: str, include_headings: bool = True) -> None:
    profile.body.font.color = color
    profile.abstract.title_font.color = color
    profile.abstract.body_font.color = color
    profile.table.caption.font.color = color
    profile.figure.caption.font.color = color
    profile.references.font.color = color
    profile.header_footer.font.color = color
    if include_headings:
        for heading in profile.headings:
            heading.font.color = color


def _color_quote(text: str, color: str) -> str:
    for name, value in COLOR_BY_NAME.items():
        if value == color and name in text:
            return name
    return f"#{color}"


def _extract_header_text(text: str) -> str | None:
    patterns = [
        r"页眉(?:文字|内容)?\s*(?:为|写|填写|显示|：|:)\s*([^\n。；;，,]{2,40})",
        r"页眉\s*([^\n。；;，,]{2,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip(" ：:，,。.;；\"“”")
            if value and not re.search(r"(居中|居左|居右|左对齐|右对齐|对齐)", value):
                return value
    return None


def _extract_alignment(text: str, anchor: str) -> str | None:
    match = re.search(rf"{re.escape(anchor)}[^。；;\n]{{0,16}}(居中|居左|居右|左对齐|右对齐|两端对齐)", text)
    if not match:
        return None
    return {
        "居中": "center",
        "居左": "left",
        "居右": "right",
        "左对齐": "left",
        "右对齐": "right",
        "两端对齐": "justified",
    }[match.group(1)]


def _alignment_zh(alignment: str) -> str:
    return {"left": "居左", "center": "居中", "right": "居右", "justified": "两端对齐"}[alignment]


def _first_match(text: str, candidates: list[str]) -> str | None:
    lowered = text.lower()
    for candidate in candidates:
        if candidate.lower() in lowered:
            return candidate
    return None


def _office_font(font: str) -> str:
    return {"宋体": "SimSun", "黑体": "SimHei", "仿宋": "FangSong", "楷体": "KaiTi"}.get(font, font)


def _caption_position_zh(position: str) -> str:
    return "上方" if position == "above" else "下方"


def _margin_value(profile: FormatProfile) -> str:
    margins = profile.page.margins_cm
    return f"上 {margins.top:g} cm，下 {margins.bottom:g} cm，左 {margins.left:g} cm，右 {margins.right:g} cm"


def _margin_quote(margins: dict[str, float]) -> str:
    return ", ".join(f"{key}={value:g}cm" for key, value in margins.items())


def _field_covered(field: str, covered: set[str]) -> bool:
    return field in covered or any(field.startswith(f"{item}.") or item.startswith(f"{field}.") for item in covered)


def _field_covered_by_any(field: str, covered: set[str]) -> bool:
    return any(_field_covered(field, {item}) for item in covered)


def _slugify_profile_id(name: str) -> str:
    ascii_slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).strip("-")
    if ascii_slug:
        return ascii_slug[:48]
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    return f"profile-{digest}"


def _agent_summary_message(draft: RequirementDraft) -> str:
    missing = "、".join(draft.summary.missing_fields[:6]) if draft.summary.missing_fields else "无"
    return (
        f"已拆解 {len(draft.summary.items)} 条格式规则。"
        f"待确认/缺失字段：{missing}。"
        "确认名称和版本后即可保存为可复用 Profile。"
    )
