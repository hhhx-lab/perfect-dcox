from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from tests.document_fixtures import create_minimal_thesis_docx


class CustomLetterProvider:
    def extract_summary(self, source_text, source_meta, base_profile):
        return {
            "items": [],
            "evidence": [],
            "uncertain_items": [],
            "profile_overrides": {
                "page": {
                    "size": "Letter",
                    "orientation": "landscape",
                    "margins_cm": {"top": 1.5, "bottom": 1.5, "left": 2.0, "right": 2.0, "gutter": 0},
                },
                "fonts": {
                    "default_chinese": "KaiTi",
                    "default_latin": "Arial",
                    "default_size_pt": 10.5,
                },
                "body": {
                    "font": {"chinese": "KaiTi", "latin": "Arial", "size_pt": 10.5, "weight": "normal", "color": "000000"},
                    "line_spacing": 1.2,
                    "first_line_indent_chars": 2,
                    "alignment": "justified",
                },
                "header_footer": {
                    "header_text": "自定义课程模板",
                    "header_alignment": "right",
                    "footer_page_number": True,
                    "footer_alignment": "center",
                    "font": {"chinese": "KaiTi", "latin": "Arial", "size_pt": 10.5, "weight": "normal", "color": "000000"},
                },
                "table": {
                    "caption": {
                        "position": "above",
                        "prefix": "表",
                        "font": {"chinese": "KaiTi", "latin": "Arial", "size_pt": 10.5, "weight": "normal", "color": "000000"},
                    }
                },
                "figure": {
                    "caption": {
                        "position": "below",
                        "prefix": "图",
                        "font": {"chinese": "KaiTi", "latin": "Arial", "size_pt": 10.5, "weight": "normal", "color": "000000"},
                    }
                },
                "references": {
                    "style": "GB/T 7714",
                    "font": {"chinese": "KaiTi", "latin": "Arial", "size_pt": 10.5, "weight": "normal", "color": "000000"},
                    "hanging_indent_chars": 2,
                },
            },
        }


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(FILE_STORAGE_ROOT=tmp_path, LLM_API_KEY="test-key", LLM_MODEL="test-model"),
            requirement_provider=CustomLetterProvider(),
        )
    )


def test_agent_confirmed_custom_profile_can_drive_batch_export_quality_gate(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    session = client.post(
        "/api/requirement-sessions",
        json={
            "source_type": "conversation",
            "natural_language": (
                "Letter 横向，页边距上 1.5cm，下 1.5cm，左 2.0cm，右 2.0cm，"
                "正文楷体五号，英文 Arial，1.2 倍行距，首行缩进 2 字符，"
                "页眉文字为自定义课程模板，页眉居右，页码居中，表题在表格上方，图题在图片下方，参考文献 GB/T 7714。"
            ),
        },
    )
    assert session.status_code == 201
    assert session.json()["status"] == "ready_for_confirmation"

    confirmed = client.post(
        f"/api/requirement-sessions/{session.json()['session_id']}/confirm",
        json={
            "profile_name": "Custom Letter Landscape",
            "profile_version": "1.0.0",
            "profile_description": "Custom non-ECNU profile used for production pipeline verification.",
        },
    )
    assert confirmed.status_code == 200
    profile = confirmed.json()["profile_draft"]
    assert profile["id"] == "custom-letter-landscape"
    assert profile["page"]["size"] == "Letter"
    assert profile["page"]["orientation"] == "landscape"
    assert profile["header_footer"]["header_text"] == "自定义课程模板"

    source = create_minimal_thesis_docx(tmp_path / "input.docx")
    uploaded = client.post(
        "/api/files",
        files={
            "file": (
                "input.docx",
                source.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert uploaded.status_code == 201

    batch = client.post(
        "/api/batches",
        json={
            "profile_id": profile["id"],
            "profile_version": profile["version"],
            "input_file_ids": [uploaded.json()["file_id"]],
            "output_formats": ["docx"],
            "auto_quality": True,
        },
    )
    assert batch.status_code == 201
    payload = batch.json()
    assert payload["status"] == "completed"
    item = payload["items"][0]
    assert item["delivery_status"] == "completed"
    assert item["final_docx_file_id"]
    assert item["quality_report_id"] is None
    assert item["fix_loop_ids"] == []
    assert item["delivery_gate_summary"]["docx"]["passed"] is True

    output_meta = client.get(f"/api/files/{item['final_docx_file_id']}").json()
    output_doc = Document(output_meta["storage_path"])
    section = output_doc.sections[0]
    assert section.orientation == WD_ORIENT.LANDSCAPE
    assert round(section.page_width.cm, 1) == 27.9
    assert round(section.top_margin.cm, 1) == 1.5
    assert "自定义课程模板" in "\n".join(paragraph.text for paragraph in section.header.paragraphs)

    assert item["delivery_gate_summary"]["docx"]["remaining_issue_count"] == 0
