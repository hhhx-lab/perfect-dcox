## Why

The Word formatting product needs a reliable foundation before profile, document formatting, agent, and quality workflows can be built. The current repository only contains planning documents and a format sample, so this change establishes the first runnable frontend/backend platform with file upload, task tracking, storage, and configuration boundaries.

## What Changes

- Add a separated web application shell that exposes a workbench, file upload entry point, profile entry point, and task list/detail views.
- Add a FastAPI backend shell with health checks, structured configuration loading, file upload, file metadata persistence, task creation, and task status APIs.
- Add a local file storage abstraction that records uploaded files with metadata including filename, MIME type, size, sha256, and storage path.
- Add a minimal job orchestration layer that supports queued, running, completed, and failed task states without blocking HTTP requests on long document processing.
- Add project-level environment and developer startup documentation, including `.env.example` for database, queue, file storage, LLM, and LibreOffice paths.
- Do not implement DOCX formatting, PDF conversion, profile editing, agent rule extraction, quality checking, authentication, or batch processing in this change.

## Capabilities

### New Capabilities

- `web-workbench`: Web users can access the frontend shell, navigate core product areas, upload files, and inspect task status from the browser.
- `file-storage`: The backend accepts `.doc` and `.docx` uploads, stores the original file, and records retrievable metadata.
- `job-orchestration`: The backend creates and tracks asynchronous placeholder format jobs with observable lifecycle states.
- `runtime-configuration`: The application loads required runtime settings from environment files and documents safe local startup.

### Modified Capabilities

- None. No existing OpenSpec specs are present in this repository.

## Impact

- Adds `backend/` for the FastAPI application, configuration, persistence, file storage, task API, worker entry point, and tests.
- Adds `frontend/` for the React/TypeScript workbench and API client.
- Adds `storage/` as a local development storage root, with generated runtime artifacts ignored by git.
- Adds `.env.example`, project README/developer documentation, and dependency manifests.
- Adds local development dependencies for FastAPI, Pydantic settings, pytest, React, TypeScript, Vite, and frontend build tooling.
