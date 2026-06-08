from pathlib import Path

from docx import Document
from docx.shared import Cm
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.documents.formatter import format_docx_with_profile
from app.main import create_app
from app.profiles.seed import load_builtin_profiles
from app.storage.local import LocalFileStorage
from app.storage.repository import JsonMetadataRepository
from tests.document_fixtures import create_minimal_thesis_docx


def build_client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings(FILE_STORAGE_ROOT=tmp_path)))


def add_formatted_docx_output(tmp_path: Path) -> str:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    profile = load_builtin_profiles()["ecnu_thesis"]
    source = create_minimal_thesis_docx(tmp_path / "source.docx")
    formatted = format_docx_with_profile(source, tmp_path / "formatted.docx", profile)
    record = storage.store_generated_file(
        formatted,
        filename="formatted.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(record)
    return record.file_id


def add_broken_docx_output(tmp_path: Path) -> str:
    repository = JsonMetadataRepository(tmp_path / "metadata.json")
    storage = LocalFileStorage(tmp_path)
    profile = load_builtin_profiles()["ecnu_thesis"]
    source = create_minimal_thesis_docx(tmp_path / "broken-source.docx")
    formatted = format_docx_with_profile(source, tmp_path / "broken-formatted.docx", profile)
    document = Document(formatted)
    document.sections[0].top_margin = Cm(1.0)
    broken = tmp_path / "broken-output.docx"
    document.save(broken)
    record = storage.store_generated_file(
        broken,
        filename="broken-output.docx",
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    repository.add_file(record)
    return record.file_id


def test_create_and_get_quality_report_for_formatted_output(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    file_id = add_formatted_docx_output(tmp_path)

    created = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": [file_id],
            "job_id": "job_quality",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["report_id"].startswith("qr_")
    assert payload["job_id"] == "job_quality"
    assert payload["summary"]["counts"]["pass"] >= 6
    assert payload["summary"]["counts"]["unsupported"] == 0
    assert payload["summary"]["all_compliant"] is True
    assert payload["issues_by_status"]["pass"]

    loaded = client.get(f"/api/quality-reports/{payload['report_id']}")
    assert loaded.status_code == 200
    assert loaded.json()["report_id"] == payload["report_id"]


def test_create_quality_report_rejects_missing_output_or_profile(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    missing_output = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": ["file_missing"],
        },
    )
    missing_profile = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "missing",
            "profile_version": "1.0.0",
            "output_file_ids": ["file_missing"],
        },
    )

    assert missing_output.status_code == 400
    assert missing_profile.status_code == 400


def test_create_fix_plan_and_confirm_fix_loop_requires_user_confirmation(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    file_id = add_broken_docx_output(tmp_path)
    report = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": [file_id],
            "job_id": "job_quality",
        },
    ).json()

    plan_response = client.post(f"/api/quality-reports/{report['report_id']}/fix-plan")

    assert plan_response.status_code == 201
    plan = plan_response.json()
    assert plan["fix_plan_id"].startswith("fp_")
    assert plan["report_id"] == report["report_id"]
    assert plan["explanations"]
    assert plan["actions"]

    confirm_response = client.post(
        f"/api/quality-reports/{report['report_id']}/fix-loops",
        json={
            "fix_plan_id": plan["fix_plan_id"],
            "selected_issue_ids": plan["actions"][0]["target_issue_ids"],
        },
    )

    assert confirm_response.status_code == 201
    loop = confirm_response.json()
    assert loop["fix_loop_id"].startswith("fl_")
    assert loop["original_report_id"] == report["report_id"]
    assert loop["fix_plan_id"] == plan["fix_plan_id"]
    assert loop["status"] == "confirmed"
    assert loop["new_job_id"] is None
    assert loop["new_output_file_ids"] == []
    assert loop["updated_report_id"] is None

    persisted = JsonMetadataRepository(tmp_path / "metadata.json").get_quality_fix_loop(loop["fix_loop_id"])
    assert persisted is not None
    assert persisted.original_report_id == report["report_id"]
    assert persisted.selected_issue_ids == plan["actions"][0]["target_issue_ids"]


def test_confirm_fix_loop_rejects_missing_report_or_unknown_issue(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    file_id = add_formatted_docx_output(tmp_path)
    report = client.post(
        "/api/quality-reports",
        json={
            "profile_id": "ecnu_thesis",
            "profile_version": "1.0.0",
            "output_file_ids": [file_id],
        },
    ).json()
    plan = client.post(f"/api/quality-reports/{report['report_id']}/fix-plan").json()

    missing_report = client.post("/api/quality-reports/qr_missing/fix-plan")
    unknown_issue = client.post(
        f"/api/quality-reports/{report['report_id']}/fix-loops",
        json={"fix_plan_id": plan["fix_plan_id"], "selected_issue_ids": ["missing_issue"]},
    )

    assert missing_report.status_code == 404
    assert unknown_issue.status_code == 400
