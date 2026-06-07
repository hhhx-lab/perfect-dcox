# Backend

FastAPI backend for the Word Format Agent workbench. It provides file upload metadata, deterministic Profile schema validation, versioned Profile storage, YAML import/export, queued format jobs, and the first DOCX formatting engine.

## Install and Run

Use the project-local uv environment:

```bash
uv sync
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## Worker

The worker has two paths:

- Jobs with `profile_id` and `profile_version` use `DocumentFormattingService` to resolve the uploaded file and immutable profile version, convert `.doc` to `.docx` when needed, parse the input, apply profile-driven DOCX formatting, register generated output files, and update `output_file_ids`.
- Jobs without a profile keep the compatibility placeholder path: the worker verifies the input file exists and marks the job completed.

Use the app settings so the worker sees the same `FILE_STORAGE_ROOT` and `SOFFICE_BIN` values as the API:

```bash
uv run python -c "from app.core.config import get_settings; from app.jobs.worker import process_next_queued_job; from app.storage.local import LocalFileStorage; from app.storage.repository import JsonMetadataRepository; settings=get_settings(); storage=LocalFileStorage(settings.file_storage_root); print(process_next_queued_job(JsonMetadataRepository(settings.file_storage_root / 'metadata.json'), storage=storage, soffice_bin=settings.soffice_bin))"
```

Failure diagnostics are stored on the job as `error_message`, for example missing input/profile records, corrupt DOCX parse failures, or missing LibreOffice for `.doc` conversion/PDF export.

## Document Formatting Engine

Document modules live under `app/documents/`:

- `converter.py`: bypasses `.docx`; converts legacy `.doc` to `.docx` through LibreOffice headless when `SOFFICE_BIN` is configured.
- `parser.py`: inspects DOCX paragraph/table/image counts, heading candidates, styles, and extracted text before formatting.
- `formatter.py`: applies profile page margins, body fonts, line spacing, first-line indent, heading styles, caption/equation/reference paragraph formatting, and basic three-line table borders while preserving paragraph text.
- `exporter.py`: exports formatted DOCX to PDF through LibreOffice; service support exists, but the default worker currently records DOCX only.
- `service.py`: orchestrates input/profile lookup, conversion, parsing, formatting, optional PDF export, output storage, and repository registration.

Required environment:

- `.docx` formatting: `FILE_STORAGE_ROOT` and a valid profile version.
- `.doc` conversion: `SOFFICE_BIN` must point to an existing LibreOffice/soffice binary.
- PDF export: `SOFFICE_BIN` must point to an existing LibreOffice/soffice binary.

## Profiles

Profile seed data lives in `../profiles/`. On app startup, `profiles/ecnu_thesis.yaml` is loaded and saved into the local JSON metadata repository if version `1.0.0` is not already present.

The repository stores:

- `profiles`: profile summaries with status, current version, source, and update time.
- `profile_versions`: immutable version records containing the validated structured profile.

Profile routes:

```text
GET  /api/profiles
GET  /api/profiles/{profile_id}/versions/{version}
POST /api/profiles
POST /api/profiles/{profile_id}/versions
POST /api/profiles/{profile_id}/archive
POST /api/profiles/import
GET  /api/profiles/{profile_id}/versions/{version}/export
```

Job creation accepts optional profile references:

```json
{
  "input_file_id": "file_xxx",
  "profile_id": "ecnu_thesis",
  "profile_version": "1.0.0"
}
```

`profile_id` and `profile_version` must be provided together and must reference an existing version.

## Tests

```bash
uv run pytest
```

Focused document checks:

```bash
uv run pytest tests/test_document_engine.py tests/test_document_formatting.py tests/test_document_worker.py
```
