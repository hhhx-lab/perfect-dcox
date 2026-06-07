# Backend

FastAPI backend for the Word Format Agent foundation.

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

The foundation worker only processes placeholder jobs. It marks the first queued job as running and then completed, or failed if the input file is missing.

```bash
uv run python -c "from pathlib import Path; from app.storage.repository import JsonMetadataRepository; from app.jobs.worker import process_next_queued_job; print(process_next_queued_job(JsonMetadataRepository(Path('../storage/metadata.json'))))"
```

## Tests

```bash
uv run pytest
```
