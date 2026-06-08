from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.main import create_app
from app.agents.requirements import RequirementSessionService, _slugify_profile_id
from app.models import FileRecord
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_ecnu_rule_docx, create_minimal_thesis_docx


class DeterministicProvider:
    def extract_summary(self, source_text, source_meta, base_profile):
        return {
            "items": [],
            "evidence": [],
            "uncertain_items": [],
            "profile_overrides": {},
        }


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY="test-key", LLM_MODEL="test-model"),
            requirement_provider=DeterministicProvider(),
        )
    )


def test_requirement_session_requires_llm_configuration(tmp_path: Path) -> None:
    client = TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY=None, LLM_MODEL=None)))

    response = client.post(
        "/api/requirement-sessions",
        json={"source_type": "conversation", "natural_language": "A4，正文宋体小四。"},
    )

    assert response.status_code == 400
    assert "LLM requirement extraction is not configured" in response.text


def test_chinese_profile_id_slug_is_stable() -> None:
    first = _slugify_profile_id("华东师范大学毕业论文格式要求")
    second = _slugify_profile_id("华东师范大学毕业论文格式要求")

    assert first == second
    assert first.startswith("profile-")


def test_conversation_requirement_session_creates_profile_draft(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": "A4，正文宋体小四，英文 Times New Roman，1.5 倍行距，首行缩进 2 字符，参考文献 GB/T 7714。",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["session_id"].startswith("rs_")
    assert payload["source_type"] == "conversation"
    assert payload["status"] in {"needs_user_answer", "ready_for_confirmation"}
    assert payload["profile_draft"]["body"]["font"]["chinese"] == "SimSun"
    assert payload["profile_draft"]["body"]["font"]["latin"] == "Times New Roman"
    assert payload["profile_draft"]["body"]["line_spacing"] == 1.5
    assert payload["requirement_summary"]["items"]
    assert payload["messages"][-1]["role"] == "agent"


def test_conversation_requirement_session_extracts_page_header_footer_rules(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": "Letter 横向，页眉文字为课程报告模板，页眉居右，每页页码置于页面底端居中，正文宋体小四。",
        },
    )

    assert response.status_code == 201
    draft = response.json()["profile_draft"]
    assert draft["page"]["size"] == "Letter"
    assert draft["page"]["orientation"] == "landscape"
    assert draft["header_footer"]["header_text"] == "课程报告模板"
    assert draft["header_footer"]["header_alignment"] == "right"
    assert draft["header_footer"]["footer_page_number"] is True
    assert draft["header_footer"]["footer_alignment"] == "center"


def test_conversation_requirement_session_does_not_read_a4_from_arial(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": "Letter 横向，正文楷体五号，英文 Arial，1.2 倍行距。",
        },
    )

    assert response.status_code == 201
    draft = response.json()["profile_draft"]
    assert draft["page"]["size"] == "Letter"
    assert draft["page"]["orientation"] == "landscape"


def test_conversation_requirement_session_parses_common_rule_document_wording(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": (
                "纸型主要选用 A4，纵向，个别页面可以采用 A4 横向。"
                "页边距上 2.5cm，下 2.0cm，左 3.0cm，右 2.5cm。"
                "行距一律为 1.5 倍。正文一般用宋体小四号字打印。每页要插入阿拉伯数字页码，置于页面底端居中。"
            ),
        },
    )

    assert response.status_code == 201
    draft = response.json()["profile_draft"]
    assert draft["page"]["size"] == "A4"
    assert draft["page"]["orientation"] == "portrait"
    assert draft["body"]["font"]["size_pt"] == 12
    assert draft["body"]["line_spacing"] == 1.5
    assert draft["header_footer"]["footer_page_number"] is True
    assert draft["header_footer"]["footer_alignment"] == "center"


def test_conversation_requirement_session_extracts_font_color_rule(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": "A4，正文宋体小四，英文 Times New Roman，字色要黑色，标题字色也要黑色。",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    draft = payload["profile_draft"]
    fields = {item["field_path"] for item in payload["requirement_summary"]["items"]}
    assert draft["body"]["font"]["color"] == "000000"
    assert all(heading["font"]["color"] == "000000" for heading in draft["headings"])
    assert "body.font.color" in fields
    assert "headings.font.color" in fields


def test_conversation_requirement_session_extracts_ecnu_detail_rules(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": (
                "正文一般用宋体小四号字打印。中文题名用黑体小三打印，外文题名用小三打印。"
                "文章中的各段标题用黑体、小四号字打印。"
                "理科中文层次为第一层 1、2、3，第二层 1.1、2.1，第三层 1.1.1。"
                "每页插入阿拉伯数字页码，置于页面底端居中。"
                "表名放在表格正上方，图名放在图件正下方，公式应独立成行居中斜体排版。"
            ),
        },
    )

    assert response.status_code == 201
    payload = response.json()
    draft = payload["profile_draft"]
    fields = {item["field_path"] for item in payload["requirement_summary"]["items"]}
    assert draft["body"]["font"]["size_pt"] == 12
    assert draft["body"]["font"]["chinese"] == "SimSun"
    assert draft["headings"][0]["font"]["size_pt"] == 15
    assert draft["headings"][0]["font"]["chinese"] == "SimHei"
    assert draft["headings"][1]["font"]["size_pt"] == 12
    assert draft["headings"][1]["font"]["chinese"] == "SimHei"
    assert draft["headings"][0]["numbering"] == "decimal-chinese-pause"
    assert draft["headings"][1]["numbering"] == "decimal-dot"
    assert draft["header_footer"]["footer_page_number"] is True
    assert draft["header_footer"]["footer_alignment"] == "center"
    assert draft["table"]["caption"]["position"] == "above"
    assert draft["figure"]["caption"]["position"] == "below"
    assert draft["equations"]["alignment"] == "center"
    assert "headings.numbering" in fields
    assert "table.caption.position" in fields
    assert "figure.caption.position" in fields


def test_requirement_session_accepts_follow_up_and_confirms_profile(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    created = client.post(
        "/api/requirement-sessions",
        json={"source_type": "conversation", "natural_language": "A4，正文宋体小四。"},
    ).json()

    updated = client.post(
        f"/api/requirement-sessions/{created['session_id']}/messages",
        json={"content": "英文 Times New Roman，1.5 倍行距，首行缩进 2 字符，输出 Word 和 PDF。"},
    )

    assert updated.status_code == 200
    assert updated.json()["profile_draft"]["body"]["font"]["latin"] == "Times New Roman"

    confirmed = client.post(
        f"/api/requirement-sessions/{created['session_id']}/confirm",
        json={
            "profile_name": "课程报告格式",
            "profile_version": "1.0.0",
            "profile_description": "测试保存的用户自定义格式。",
        },
    )

    assert confirmed.status_code == 200
    payload = confirmed.json()
    assert payload["status"] == "confirmed"
    assert payload["profile_draft"]["name"] == "课程报告格式"
    saved_profile = client.get(f"/api/profiles/{payload['profile_draft']['id']}/versions/1.0.0")
    assert saved_profile.status_code == 200
    assert saved_profile.json()["name"] == "课程报告格式"


def test_document_requirement_session_extracts_rule_docx_text(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    source = create_minimal_thesis_docx(tmp_path / "rules.docx")
    uploaded = client.post(
        "/api/files",
        files={
            "file": (
                "rules.docx",
                source.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201

    response = client.post(
        "/api/requirement-sessions",
        json={"source_type": "document", "file_id": uploaded.json()["file_id"]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source_type"] == "document"
    assert payload["file_id"] == uploaded.json()["file_id"]
    assert payload["profile_draft"] is not None
    assert payload["requirement_summary"]["items"]


def test_document_requirement_session_extracts_ecnu_rule_document_details(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    source = create_ecnu_rule_docx(tmp_path / "华东师范大学毕业论文格式要求.docx")
    uploaded = client.post(
        "/api/files",
        files={
            "file": (
                "华东师范大学毕业论文格式要求.docx",
                source.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201

    response = client.post(
        "/api/requirement-sessions",
        json={"source_type": "document", "file_id": uploaded.json()["file_id"]},
    )

    assert response.status_code == 201
    payload = response.json()
    draft = payload["profile_draft"]
    fields = {item["field_path"] for item in payload["requirement_summary"]["items"]}
    assert draft["page"]["size"] == "A4"
    assert draft["page"]["orientation"] == "portrait"
    assert draft["page"]["margins_cm"] == {
        "top": 2.5,
        "bottom": 2.0,
        "left": 3.0,
        "right": 2.5,
        "gutter": 0.0,
    }
    assert draft["body"]["font"]["chinese"] == "SimSun"
    assert draft["body"]["font"]["latin"] == "Times New Roman"
    assert draft["body"]["font"]["size_pt"] == 12
    assert draft["body"]["line_spacing"] == 1.5
    assert draft["body"]["first_line_indent_chars"] == 2
    assert draft["headings"][0]["font"]["chinese"] == "SimHei"
    assert draft["headings"][0]["font"]["size_pt"] == 15
    assert draft["headings"][1]["font"]["chinese"] == "SimHei"
    assert draft["headings"][1]["font"]["size_pt"] == 12
    assert draft["headings"][0]["numbering"] == "decimal-chinese-pause"
    assert draft["headings"][1]["numbering"] == "decimal-dot"
    assert draft["header_footer"]["footer_page_number"] is True
    assert draft["header_footer"]["footer_alignment"] == "center"
    assert draft["table"]["caption"]["position"] == "above"
    assert draft["figure"]["caption"]["position"] == "below"
    assert draft["equations"]["alignment"] == "center"
    assert "page.margins_cm" in fields
    assert "headings.numbering" in fields
    assert "table.caption.position" in fields
    assert "figure.caption.position" in fields


def test_requirement_session_fails_when_provider_returns_schema_extra(tmp_path: Path) -> None:
    class BadProvider:
        def extract_summary(self, source_text, source_meta, base_profile):
            return {"items": [], "evidence": [], "uncertain_items": [], "profile_overrides": {"output": {"formats": ["Word"]}}}

    service = RequirementSessionService(
        JsonMetadataRepository(tmp_path / "metadata.json"),
        tmp_path,
        soffice_bin=None,
        provider=BadProvider(),
    )

    with pytest.raises(Exception, match="unsupported top-level field"):
        service.create_session("conversation", natural_language="A4，正文宋体小四。")


def test_requirement_session_keeps_known_unsupported_sections_as_uncertain(tmp_path: Path) -> None:
    class SectionProvider:
        def extract_summary(self, source_text, source_meta, base_profile):
            return {
                "items": [
                    {
                        "field_path": "page.size",
                        "label": "纸张",
                        "value": "A4",
                        "source": "document",
                        "confidence": 0.9,
                        "evidence": ["A4"],
                    }
                ],
                "evidence": [{"field_path": "page.size", "quote": "A4", "confidence": 0.9}],
                "uncertain_items": [],
                "profile_overrides": {
                    "page": {
                        "size": "A4",
                        "orientation": "portrait",
                        "margins_cm": {"top": 2.5, "bottom": 2.0, "left": 3.0, "right": 2.5, "gutter": 0},
                    },
                    "appendix": {"title_font": {"chinese": "SimHei", "size_hao": "小四"}},
                    "cover": {"required": True},
                    "toc": {"levels": 3},
                    "notes": {"font": {"chinese": "SimSun", "size_hao": "小五"}},
                },
            }

    service = RequirementSessionService(
        JsonMetadataRepository(tmp_path / "metadata.json"),
        tmp_path,
        soffice_bin=None,
        provider=SectionProvider(),
    )

    session = service.create_session("conversation", natural_language="A4，正文宋体小四。")

    assert session.profile_draft is not None
    assert session.profile_draft.page.size == "A4"
    assert {item.field_path for item in session.uncertain_items} >= {"appendix", "cover", "toc", "notes"}


def test_requirement_session_fails_when_provider_call_fails(tmp_path: Path) -> None:
    class FailingProvider:
        def extract_summary(self, source_text, source_meta, base_profile):
            from app.agents.extraction import ExtractionSourceError

            raise ExtractionSourceError("mock llm unavailable")

    client = TestClient(
        create_app(
            Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY="test-key", LLM_MODEL="test-model"),
            requirement_provider=FailingProvider(),
        )
    )

    response = client.post(
        "/api/requirement-sessions",
        json={"source_type": "conversation", "natural_language": "A4，正文宋体小四。"},
    )

    assert response.status_code == 400
    assert "mock llm unavailable" in response.text


def test_requirement_session_normalizes_common_llm_payload_aliases(tmp_path: Path) -> None:
    class AliasProvider:
        def extract_summary(self, source_text, source_meta, base_profile):
            return {
                "items": [
                    {"field": "page.size", "value": "A4", "scope": "document"},
                    {"field": "body.font.size_pt", "value": "小四", "scope": "document"},
                ],
                "evidence": [
                    {"field": "page.size", "quote": "一律用A4纸张电脑打印", "confidence": 0.9},
                    {"field": "body.font.size_pt", "quote": "正文一般用宋体小四号字打印", "confidence": 0.9},
                ],
                "uncertain_items": [
                    {"id": "default_font_color", "question": "原文未明确字色是否必须为黑色。"}
                ],
                "profile_overrides": {
                    "page": {
                        "size": "A4",
                        "orientation": "portrait",
                        "gutter_position": "left",
                        "margins_cm": {"top": 2.5, "bottom": 2.0, "left": 3.0, "right": 2.5},
                    },
                    "body": {
                        "font": {"chinese": "SimSun", "latin": "Times New Roman", "size_hao": "小四", "color": "000000"},
                        "line_spacing": 1.5,
                        "first_line_indent_chars": 2,
                        "alignment": "justified",
                    },
                    "headings": [
                        {"level": 1, "font": {"chinese": "SimHei", "size_hao": "小三", "color": "000000"}, "alignment": "center"},
                        {"level": 2, "font": {"chinese": "SimHei", "size_hao": "小四", "color": "000000"}},
                    ],
                    "title": {"font": {"chinese": "SimHei", "size_hao": "小三", "color": "000000"}, "alignment": "center"},
                    "abstract": {
                        "body_font": {"chinese": "SimSun", "latin": "Times New Roman", "size_hao": "五号", "color": "000000"}
                    },
                    "table": {"style": "three_line_table", "caption": {"position": "above"}},
                    "figure": {"caption": {"position": "below"}},
                    "equations": {"alignment": "center", "italic": True},
                    "references": {"style": "GB/T 7714", "order": "citation_order"},
                    "header_footer": {"footer_page_number": True, "footer_alignment": "center", "page_number_format": "arabic"},
                    "notes": {"font": {"chinese": "SimSun", "size_hao": "小五"}},
                },
            }

    rule_docx = create_ecnu_rule_docx(tmp_path / "ecnu-rules.docx")
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    repository.add_file(
        FileRecord(
            file_id="file_ecnu_rules",
            filename="华东师范大学毕业论文格式要求.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size=rule_docx.stat().st_size,
            sha256="a" * 64,
            storage_path=str(rule_docx),
        )
    )
    service = RequirementSessionService(repository, tmp_path, soffice_bin=None, provider=AliasProvider())

    session = service.create_session("document", file_id="file_ecnu_rules")

    assert session.profile_draft is not None
    assert session.profile_draft.body.font.size_pt == 12
    assert session.profile_draft.headings[0].font.size_pt == 15
    assert session.profile_draft.headings[1].font.size_pt == 12
    assert session.profile_draft.table.caption.position == "above"
    assert session.profile_draft.figure.caption.position == "below"
    assert session.profile_draft.equations.alignment == "center"
    assert session.requirement_summary is not None
    assert {item.field_path for item in session.requirement_summary.items} >= {"page.size", "body.font.size_pt"}
    assert any(item.field_path == "default_font_color" for item in session.uncertain_items)


def test_requirement_session_merges_document_rules_over_schema_valid_provider_drift(tmp_path: Path) -> None:
    class DriftingProvider:
        def extract_summary(self, source_text, source_meta, base_profile):
            return {
                "items": [
                    {
                        "field_path": "page.size",
                        "label": "纸张",
                        "value": "Letter",
                        "source": "document",
                        "confidence": 0.99,
                        "evidence": ["bad provider drift"],
                    },
                    {
                        "field_path": "page.orientation",
                        "label": "方向",
                        "value": "landscape",
                        "source": "document",
                        "confidence": 0.99,
                        "evidence": ["bad provider drift"],
                    },
                    {
                        "field_path": "body.font.chinese",
                        "label": "正文中文字体",
                        "value": "KaiTi",
                        "source": "document",
                        "confidence": 0.99,
                        "evidence": ["bad provider drift"],
                    },
                ],
                "evidence": [
                    {"field_path": "page.size", "quote": "bad provider drift", "confidence": 0.99},
                    {"field_path": "page.orientation", "quote": "bad provider drift", "confidence": 0.99},
                    {"field_path": "body.font.chinese", "quote": "bad provider drift", "confidence": 0.99},
                ],
                "uncertain_items": [],
                "profile_overrides": {
                    "page": {
                        "size": "Letter",
                        "orientation": "landscape",
                        "margins_cm": {"top": 1, "bottom": 1, "left": 1, "right": 1, "gutter": 0},
                    },
                    "body": {
                        "font": {
                            "chinese": "KaiTi",
                            "latin": "Arial",
                            "size_pt": 10.5,
                            "weight": "normal",
                            "color": "333333",
                        },
                        "line_spacing": 1.0,
                        "first_line_indent_chars": 0,
                        "alignment": "left",
                    },
                },
            }

    rule_docx = create_ecnu_rule_docx(tmp_path / "ecnu-rules.docx")
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    repository.add_file(
        FileRecord(
            file_id="file_ecnu_rules",
            filename="华东师范大学毕业论文格式要求.docx",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            size=rule_docx.stat().st_size,
            sha256="f" * 64,
            storage_path=str(rule_docx),
        )
    )
    service = RequirementSessionService(
        repository,
        tmp_path,
        soffice_bin=None,
        provider=DriftingProvider(),
    )

    session = service.create_session("document", file_id="file_ecnu_rules")

    assert session.profile_draft is not None
    assert session.profile_draft.page.size == "A4"
    assert session.profile_draft.page.orientation == "portrait"
    assert session.profile_draft.page.margins_cm.top == 2.5
    assert session.profile_draft.page.margins_cm.left == 3.0
    assert session.profile_draft.body.font.chinese == "SimSun"
    assert session.profile_draft.body.font.latin == "Times New Roman"
    assert session.profile_draft.body.font.size_pt == 12
    assert session.profile_draft.body.line_spacing == 1.5
    assert session.profile_draft.headings[0].font.chinese == "SimHei"
    assert session.profile_draft.table.caption.position == "above"
    assert session.profile_draft.figure.caption.position == "below"
    assert session.profile_draft.equations.alignment == "center"
    fields = {item.field_path for item in session.requirement_summary.items}  # type: ignore[union-attr]
    assert "page.size" in fields
    assert "page.orientation" in fields
    assert "body.font.chinese" in fields
