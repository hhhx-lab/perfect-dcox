# Backend

FastAPI backend for the Word Format Agent workbench. It provides file upload/download, deterministic Profile schema validation, versioned Profile storage, YAML import/export, requirement sessions, format jobs, batch delivery manifests, the first DOCX/PDF formatting engine, bounded profile rule extraction jobs, structured quality reports, and user-confirmed fix-loop execution records.

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

- Jobs with `profile_id` and `profile_version` use `DocumentFormattingService` to resolve the uploaded file and immutable profile version, convert `.doc` to `.docx` when needed, parse the input, apply profile-driven DOCX formatting, export PDF when `SOFFICE_BIN` is configured, register generated output files, and update `output_file_ids`.
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
- `formatter.py`: applies profile page size/orientation, page margins, basic header text, footer PAGE numbering, body fonts, line spacing, first-line indent, heading styles, caption/equation/reference paragraph formatting, basic three-line table borders, and Word `updateFields` for refreshable fields while preserving paragraph text.
- `ooxml.py`: inspects and safely patches DOCX package XML for field refresh, TOC fields, sections, footnotes/endnotes, images, numbering references, and OMML equation counts.
- `exporter.py`: exports formatted DOCX to PDF through LibreOffice; the worker requests PDF output when `SOFFICE_BIN` is configured.
- `service.py`: orchestrates input/profile lookup, conversion, parsing, formatting, optional PDF export, output storage, and repository registration.

Required environment:

- `.docx` formatting: `FILE_STORAGE_ROOT` and a valid profile version.
- `.doc` conversion: `SOFFICE_BIN` must point to an existing LibreOffice/soffice binary.
- PDF export: `SOFFICE_BIN` must point to an existing LibreOffice/soffice binary.

## Requirement Sessions

Requirement sessions are the production UI path for turning format requirements into reusable Profiles. They live in `app/agents/requirements.py` and share one state model for both product entrances:

- `conversation`: user describes rules in natural language; the service extracts known fields and asks for missing ones.
- `document`: user uploads a `.doc/.docx` rule document; the service extracts paragraph/table text and builds a structured summary.

Routes:

```text
POST /api/requirement-sessions
GET  /api/requirement-sessions/{session_id}
POST /api/requirement-sessions/{session_id}/messages
POST /api/requirement-sessions/{session_id}/confirm
```

The session response includes messages, `missing_fields`, `requirement_summary`, `profile_draft`, `evidence`, and `uncertain_items`. `confirm` requires a profile name and version, then saves the draft as an active user Profile. Requirement sessions require a configured live LLM provider. If `LLM_API_KEY + LLM_MODEL` are missing, the provider times out, or the response is not valid structured JSON, the API returns an error instead of creating a fake profile. The deterministic extractor is template-neutral and is used only as a post-LLM guard to enforce hard rules that are explicitly present in the source text.

The backend does not mark a session as compliant merely because a profile draft exists. Missing or uncertain rules remain visible until the user confirms a profile.

## Profile Extraction Agent Boundary

Profile extraction modules live under `app/agents/` and expose a strict boundary:

- `resolve_extraction_source(...)`: accepts either an uploaded `.doc/.docx` rules file or non-empty natural-language rules.
- `extract_rule_source_text(...)`: extracts `.docx` paragraph/table text and routes legacy `.doc` through the LibreOffice conversion adapter.
- `RuleExtractionProvider`: narrow provider interface for Agent output; tests inject fake providers instead of calling a live model.
- `ConfiguredLLMRuleExtractionProvider`: default runtime provider that reads `LLM_API_KEY` and `LLM_MODEL`; it currently returns a readable local-MVP error instead of making network calls.
- `parse_agent_extraction_output(...)`: accepts structured JSON/YAML only and validates `profile_draft`, `uncertain_items`, and `evidence`.
- `ProfileExtractionService`: creates queued extraction records, processes provider output, stores completed review payloads, and records failures without creating profiles automatically.

Profile extraction routes:

```text
POST /api/profile-extractions
GET  /api/profile-extractions/{extraction_id}
```

Extraction results are review payloads, not executable profiles. The API never saves a generated profile version by itself; users must confirm through the existing Profile APIs.

File routes:

```text
POST /api/files
GET  /api/files/{file_id}
GET  /api/files/{file_id}/download
```

## Quality Reports and Fix Plans

Quality modules live under `app/quality/`:

- `inspection.py`: performs local DOCX/PDF checks and returns `QualityIssue` records.
- `service.py`: resolves output files and profile versions, runs inspection, builds `QualityReport`, computes summary counts, and persists reports.
- `fix_planning.py`: creates deterministic Agent-style explanations and validates whitelisted `FixPlan` actions.
- `fix_execution.py`: executes confirmed whitelisted formatting actions, writes fixed DOCX/PDF outputs, creates a second-pass job, and persists an updated quality report.

DOCX quality inspection currently checks:

- page size and orientation against `profile.page`
- page margins against `profile.page.margins_cm`
- supported header/footer text and footer PAGE numbering against `profile.header_footer`
- representative body paragraph indent, line spacing, and font
- representative level-one heading style
- basic table border presence
- table/figure caption text
- raw LaTeX residue such as `$...$`
- role/style consistency for common heading, body, caption, equation, and reference paragraphs
- OOXML feature inventory, Word field update policy, TOC fields, section count, footnotes/endnotes, inline vs anchored images, visual-caption pairing, list numbering, and OMML equation count

PDF quality inspection checks a readable PDF envelope, page count, extractable text, and an obvious blank/image-only warning. It uses `pypdf` for text/page inspection with a lightweight byte-level fallback. When the checker cannot judge a feature safely, it records `fail` or `unsupported` with a readable diagnostic instead of returning `pass`.

Quality report routes:

```text
POST /api/quality-reports
GET  /api/quality-reports/{report_id}
GET  /api/quality-reports/{report_id}/download?format=json|markdown
POST /api/quality-reports/{report_id}/fix-plan
POST /api/quality-reports/{report_id}/fix-loops
POST /api/quality-reports/{report_id}/fix-loops/{fix_loop_id}/execute
```

`POST /api/quality-reports` requires a profile reference and at least one output file id:

```json
{
  "profile_id": "ecnu_thesis",
  "profile_version": "1.0.0",
  "output_file_ids": ["file_xxx"],
  "job_id": "job_optional"
}
```

Reports include `summary.counts`, `summary.remaining_issue_count`, `summary.all_compliant`, flat `issues`, and grouped `issues_by_status` for `pass/fixed/warning/fail/unsupported`. A completed formatting job is not treated as proof of compliance; warning, fail, and unsupported issues remain visible.

Fix planning is intentionally constrained. The deterministic planner only considers warning/fail/unsupported issues, explains each issue, and emits whitelisted actions:

- `reapply_profile_formatting`
- `apply_table_borders`
- `apply_body_paragraph_style`
- `apply_heading_style`
- `mark_manual_review`

The validator rejects unknown actions, semantic/content edit actions, actions without target issues, unknown target issue ids, and actions that do not require user confirmation. Page setup, margins, field refresh, TOC fields, header/footer, and page-number issues are mapped to `reapply_profile_formatting` because the formatter can safely reapply those structural rules without changing document content. `POST /api/quality-reports/{report_id}/fix-loops` creates and persists a `FixLoopRecord` with original report id, fix plan id, selected issue ids, selected actions, and `confirmed` status. `POST /api/quality-reports/{report_id}/fix-loops/{fix_loop_id}/execute` then applies whitelisted formatting actions to the original DOCX output, stores fixed DOCX/PDF outputs, creates a `quality_fix` job, generates an updated quality report, and records `new_job_id`, `new_output_file_ids`, and `updated_report_id`.

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

## Batch Formatting

Batch formatting is exposed through:

```text
POST /api/batches
GET  /api/batches/{batch_id}
GET  /api/batches/{batch_id}/manifest
```

`POST /api/batches` accepts one Profile reference and multiple uploaded Word file ids. Each input receives its own `JobRecord`, DOCX/PDF outputs when possible, and a quality report. With the default `auto_fix=true`, the batch route automatically executes one safe fix-loop for whitelisted quality issues, then points the manifest to the repaired outputs and updated report when the second pass is compliant. The returned `BatchFormatRun.items` list is the delivery manifest used by the frontend download table.

If the final generated quality report still has remaining warning/fail/unsupported issues, that job is marked `quality_failed`, the item is marked `manual_review_required`, and the batch status becomes `quality_failed`. This is intentional fail-closed behavior: completed file generation is separate from final compliance.

## Tests

```bash
uv run pytest
```

Focused document checks:

```bash
uv run pytest tests/test_document_engine.py tests/test_document_formatting.py tests/test_document_worker.py
```

Focused extraction checks:

```bash
uv run pytest tests/test_profile_extractions.py tests/test_profile_extractions_api.py
```

Focused quality checks:

```bash
uv run pytest tests/test_quality_reports.py tests/test_quality_reports_api.py
```
