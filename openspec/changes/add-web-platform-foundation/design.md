## Context

The repository currently contains the product plan, OpenSpec plans, and an ECNU Word format sample, but no runnable application code. This change establishes the base application architecture required by later profile, document formatting, agent extraction, and quality-loop changes.

The product plan requires a separated frontend/backend application, local file upload, task orchestration, safe environment configuration, and explicit development startup instructions. The platform must stay conservative: this change proves the operational shell and does not claim Word formatting correctness.

## Goals / Non-Goals

**Goals:**

- Provide a local web workbench with navigation to upload, profile, task, quality, and output areas.
- Provide a FastAPI backend with health, file upload, file metadata, placeholder format job creation, and task status endpoints.
- Persist enough metadata for uploaded files and jobs to survive process restarts in local development.
- Store uploaded originals under a configurable storage root and compute sha256 for traceability.
- Provide `.env.example` and developer documentation for local frontend, backend, and worker startup.

**Non-Goals:**

- No DOCX formatting, PDF conversion, quality inspection, profile editor, or LLM agent behavior.
- No authentication, authorization, organization management, or batch processing.
- No production deployment, external object storage, or full PostgreSQL/Redis operations requirement for MVP local startup.

## Decisions

### Use FastAPI for the backend API

FastAPI matches the product plan and gives typed request/response models, generated OpenAPI docs, and good local test ergonomics. A lightweight local persistence layer can be used for this foundation, while the API contract remains compatible with later PostgreSQL-backed implementations.

Alternative considered: Node/Express. It would align with the frontend ecosystem, but the later document processing stack is Python-heavy, so FastAPI keeps the document workers and backend in the same language.

### Use React + TypeScript + Vite for the frontend shell

Vite provides a small, quick frontend setup suitable for a new repository. React + TypeScript provides typed API integration and a broad component ecosystem for later profile editor and report views.

Alternative considered: Next.js. It is useful for server-rendered or routed production apps, but the current MVP mainly needs a local app shell consuming backend APIs.

### Use local JSON metadata plus local filesystem storage for the first foundation

The plan names PostgreSQL and Redis as preferred production components, but this first change can meet the platform acceptance criteria with a repository-local metadata store and a queue abstraction. This avoids requiring database and queue services before the first local workbench can run.

Alternative considered: require PostgreSQL and Redis immediately. That better resembles production but slows MVP validation and adds operational friction before any document processing exists.

### Model jobs as asynchronous resources even when the first worker is a placeholder

The API SHALL return a `job_id` and expose lifecycle states instead of synchronously doing document work in the upload or create-job request. A placeholder worker can mark jobs completed or failed while preserving the contract required by later document processing and quality changes.

Alternative considered: synchronous format endpoint. It would be simpler for the first task, but it conflicts with the product requirement that document processing not block HTTP requests.

### Keep secrets in `.env` and commit only `.env.example`

The platform needs LLM and document-tool configuration later. The foundation SHALL document required and optional environment variables without committing secrets.

Alternative considered: hard-code local defaults in source. That is convenient but unsafe and conflicts with the repository instructions.

## Risks / Trade-offs

- Local JSON persistence may not match later PostgreSQL behavior exactly → Keep persistence behind a repository interface and limit this change to metadata needed by acceptance criteria.
- Placeholder jobs may be mistaken for real formatting → Label job type/status and UI copy as foundation/placeholder until the DOCX formatting change lands.
- File uploads can create large local artifacts → Store generated files under ignored storage paths and keep metadata concise.
- Frontend and backend can drift in API shape → Define shared response schemas in backend tests and use a small typed frontend API client.
- OpenSpec was initialized during this pipeline and no baseline specs existed → Treat all four capabilities as ADDED, not MODIFIED.
