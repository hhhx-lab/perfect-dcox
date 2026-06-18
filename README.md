<div align="center">

# Perfect DOCX

**An agent-assisted Word and PDF formatting workbench for thesis, report, and institutional document standards.**

![Project](https://img.shields.io/badge/Type-Agent%20Document%20Workbench-111827)
![Stack](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React-2563eb)
![Profiles](https://img.shields.io/badge/Profile-JSON%20Driven-7c3aed)
![Quality](https://img.shields.io/badge/QC-Fail--Closed-059669)
![Export](https://img.shields.io/badge/Output-DOCX%20%2B%20PDF-c2410c)

`./scripts/start-dev.sh`

</div>

Perfect DOCX turns messy formatting requirements into reusable, versioned profiles. It is built for workflows where a user can describe rules in natural language, upload a formatting requirement document, inspect and edit the extracted profile, then export normalized DOCX and PDF files only after internal checks pass.

This is not a naive template copier. The system separates rule understanding, profile storage, deterministic DOCX formatting, internal QC, optional PDF export, and final LLM layout review into explicit stages so failures are visible instead of silently shipped.

## Current Status

Perfect DOCX is a production-oriented local workbench with the main pipeline in place, but it is not yet a guarantee that every complex thesis template will format perfectly on the first try.

What is verified now:

- OpenAI-compatible LLM calls work through explicit `stream=true` handling.
- Real formatting requirement extraction has been tested with an ECNU thesis requirement document.
- Profile JSON v2 stores evidence, missing fields, unsupported rules, locked fields, and capability coverage.
- DOCX formatting, internal QC, PDF checks, and fail-closed delivery gates are implemented.
- The frontend exposes profile intake, visual rule editing, LLM health checks, export control, and DOCX/PDF downloads.

Important boundary:

- Unsupported or unmapped rules are not treated as success.
- Complex cover pages, binding rules, title schemas, multi-section headers, advanced TOC behavior, and arbitrary thesis templates still need broader sample-matrix validation.

## Capability Matrix

| Capability | What it does | Current maturity |
|---|---|---|
| Agent requirement intake | Reads natural language, rule documents, and style sample documents into a Profile draft | Working, with defensive schema normalization |
| Profile JSON v2 | Stores page, body, heading, captions, TOC, grid, units, template, QC, evidence, and unsupported rules | Implemented |
| Visual profile editor | Lets users inspect and adjust formatting fields in the browser | Working, still needs component split |
| Rule capability coverage | Shows whether each rule is supported by Agent, formatter, QC, and final review | Implemented |
| DOCX formatter | Applies page setup, fonts, headings, captions, tables, figures, units, TOC, headers, footers, and more | Core rules implemented |
| Internal QC gate | Checks DOCX/PDF health and blocks failed, warning, or unsupported outputs | Implemented |
| Auto-fix loop | Re-runs safe formatter actions for fixable issues before final delivery | Initial implementation |
| Final LLM review | Reviews final layout health when enabled by Profile | Integrated, requires working LLM config |
| Batch export | Processes multiple input documents and creates a delivery manifest | Implemented |
| Template binding | Merges content into optional DOCX templates | Basic support, complex templates need more validation |

## Workflow

```text
Formatting requirement
  |
  |-- Natural language conversation
  |-- Rule document upload
  |-- Style sample DOCX upload
  |-- Visual editor override
  v
Requirement Session
  |
  v
Profile JSON v2
  |
  v
FormatCompiler
  |
  v
Candidate DOCX
  |
  v
Internal DOCX QC and safe auto-fix
  |
  v
Optional PDF export and PDF QC
  |
  v
Optional required LLM final layout review
  |
  v
Final DOCX/PDF downloads
```

## Quick Start

Prepare environment variables:

```bash
cp .env.example .env
```

Start backend and frontend together:

```bash
./scripts/start-dev.sh
```

Default local URLs:

| Service | URL |
|---|---|
| Frontend | `http://127.0.0.1:5173` |
| Backend | `http://127.0.0.1:8000` |
| Backend health | `http://127.0.0.1:8000/api/health` |
| LLM health | `http://127.0.0.1:8000/api/health/llm` |

Launcher commands:

```bash
./scripts/start-dev.sh --status
./scripts/start-dev.sh --restart
./scripts/start-dev.sh --stop
```

Use alternate ports when needed:

```bash
./scripts/start-dev.sh --backend-port 8010 --frontend-port 5174
```

The launcher installs frontend dependencies when needed, starts FastAPI and Vite in the background, writes logs under `storage/logs/`, stores PID metadata under `storage/pids/`, and only stops processes it started itself.

## Environment Variables

The project is driven by `.env`. Do not commit API keys, tokens, local proxy settings, or runtime outputs.

| Variable | Required | Purpose |
|---|---|---|
| `FILE_STORAGE_ROOT` | Yes | Local storage for uploads, outputs, metadata, manifests, and logs |
| `SOFFICE_BIN` | Recommended | LibreOffice executable path, required for legacy `.doc` conversion and PDF export |
| `LLM_API_KEY` | Required for Agent and final review | OpenAI-compatible API key |
| `LLM_MODEL` | Required for Agent and final review | Model name used by requirement extraction and final review |
| `LLM_BASE_URL` | Optional | OpenAI-compatible base URL |
| `LLM_TIMEOUT_SECONDS` | Optional | Timeout for extraction and final review calls |
| `LLM_HEALTH_TIMEOUT_SECONDS` | Optional | Timeout for `/api/health/llm` real generation checks |
| `DATABASE_URL` | Optional | Reserved for production PostgreSQL integration |
| `REDIS_URL` | Optional | Reserved for production queue integration |

LLM health is checked with a real generation request. A configured key is not enough:

- `reachable=true`: the gateway authenticated and returned assistant content.
- `configured_unverified`: key and model exist, but no generation check has run.
- `unreachable`: authentication, model, gateway, or response protocol failed.

Some OpenAI-compatible gateways return usable content only when `stream=true`. Perfect DOCX explicitly enables streaming and parses both JSON and SSE responses.

## Manual Development

Backend:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Run one queued worker manually:

```bash
cd backend
uv run python -c "from app.core.config import get_settings; from app.jobs.worker import process_next_queued_job; from app.storage.local import LocalFileStorage; from app.storage.repository import JsonMetadataRepository; settings=get_settings(); storage=LocalFileStorage(settings.file_storage_root); print(process_next_queued_job(JsonMetadataRepository(settings.file_storage_root / 'metadata.json'), storage=storage, soffice_bin=settings.soffice_bin))"
```

## Validation

Backend tests:

```bash
cd backend
uv run pytest -q
```

Frontend build:

```bash
cd frontend
npm run build
```

OpenSpec validation:

```bash
openspec validate update-production-export --strict --no-interactive
```

Repository whitespace check:

```bash
git diff --check
```

Document smoke checks:

```bash
codex-docx-inspect storage/outputs/<generated-file-id>.docx
codex-docx-to-pdf storage/outputs/<generated-file-id>.docx storage/outputs
codex-pdf-inspect storage/outputs/<generated-file-id>.pdf
```

Latest verified local state:

```text
backend:   186 passed, 2 warnings
frontend:  build passed
OpenSpec:  update-production-export valid
LLM:       /api/health/llm reachable=true with gpt-5.4
```

## API Overview

| API | Purpose |
|---|---|
| `GET /api/health` | Backend health and optional service status |
| `GET /api/health/llm` | Real LLM generation health check |
| `POST /api/files` | Upload `.doc` or `.docx` files |
| `GET /api/files/{file_id}` | Read uploaded file metadata |
| `GET /api/files/{file_id}/download` | Download a stored file |
| `GET /api/profiles` | List available profiles |
| `POST /api/profiles` | Create a profile |
| `POST /api/profiles/{profile_id}/versions` | Save a new profile version |
| `POST /api/requirement-sessions` | Create an Agent requirement extraction session |
| `POST /api/requirement-sessions/{session_id}/messages` | Add natural-language refinements |
| `POST /api/requirement-sessions/{session_id}/attachments` | Add rule or style sample files to the same session |
| `POST /api/requirement-sessions/{session_id}/confirm` | Confirm a session and save a profile |
| `POST /api/jobs` | Create a single-document formatting job |
| `GET /api/jobs/{job_id}` | Read job status |
| `POST /api/batches` | Create a batch formatting run |
| `GET /api/batches/{batch_id}` | Read batch status and delivery manifest |
| `POST /api/quality-reports` | Compatibility and debugging inspection endpoint |

## Repository Layout

```text
.
|-- backend/
|   |-- app/
|   |   |-- agents/        # Requirement extraction and style sample analysis
|   |   |-- api/           # FastAPI routers
|   |   |-- documents/     # Compiler, formatter, OOXML, templates, rule registry
|   |   |-- llm/           # OpenAI-compatible diagnostics and response parsing
|   |   |-- profiles/      # Profile loading and schema models
|   |   |-- quality/       # Internal delivery gate, DOCX/PDF inspection, final review
|   |   `-- storage/       # Local metadata and file storage helpers
|   `-- tests/
|-- frontend/
|   `-- src/               # React workbench, API client, styles
|-- profiles/              # Built-in and sample formatting profiles
|-- scripts/               # Local launchers and document utilities
|-- docs/                  # Change plans, module docs, production progress docs
|-- openspec/              # OpenSpec change artifacts
|-- storage/               # Local runtime files, ignored by git
`-- README.md
```

## What The Frontend Provides

The browser workbench is designed around four loops:

1. Create or select a formatting Profile.
2. Ask the Agent to extract rules from conversation, requirement documents, or style samples.
3. Inspect and edit the Profile visually, including locked fields and capability coverage.
4. Upload Word documents and download final DOCX/PDF outputs after internal checks pass.

The rule inspector shows whether fields are supported by the Agent, formatter, QC, and final LLM review. This is intentionally visible: a rule that cannot be executed should be treated as a capability gap, not as a successful export.

## Boundaries

Perfect DOCX is designed to be conservative:

- It does not silently pass unsupported formatting rules.
- It does not treat an LLM-generated profile as automatically correct without schema validation.
- It does not publish final downloads when internal QC, PDF inspection, or required final review fails.
- It does not guarantee arbitrary school, journal, or enterprise templates are fully supported without sample validation.
- It does not store secrets in code.

Current known gaps:

- Unit rules extracted as free-form fields still need stronger mapping into executable `unit_rules`.
- Some title and binding rules need either schema expansion or template-delegated handling.
- Complex cover pages, declarations, multi-section headers and footers, and advanced TOC flows need a broader sample matrix.
- The frontend is still a large workbench file and should be split into feature modules.

## Development Rules

- Use `uv` or the project environment for Python work.
- Do not use `sudo pip`.
- Do not mix system Python, Homebrew Python, and the project environment.
- Keep secrets in `.env`.
- Keep `.env`, `storage/`, `node_modules/`, `dist/`, virtualenvs, caches, and logs out of git.
- Use the SSH remote: `git@github.com:hhhx-lab/perfect-dcox.git`.

## Project Documents

Useful references:

- `docs/real-progress-status-2026-06-12.md`
- `docs/production-format-upgrade-change-document.md`
- `openspec/changes/update-production-export/`
- `docs/change-plans/CP-20260611-001.md`
