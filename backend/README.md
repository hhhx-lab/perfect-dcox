# Backend

FastAPI backend for the Word Format Agent workbench. It provides file upload metadata, deterministic Profile schema validation, versioned Profile storage, YAML import/export, and placeholder format jobs.

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

The current worker only processes placeholder jobs. It marks the first queued job as running and then completed, or failed if the input file is missing. Jobs may store `profile_id` and `profile_version`, but the worker does not format DOCX files yet.

```bash
uv run python -c "from pathlib import Path; from app.storage.repository import JsonMetadataRepository; from app.jobs.worker import process_next_queued_job; print(process_next_queued_job(JsonMetadataRepository(Path('../storage/metadata.json'))))"
```

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
