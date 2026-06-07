## Context

The backend already has FastAPI routes, local file storage, JSON metadata, placeholder jobs, and versioned deterministic profiles. Formatting jobs can reference `profile_id + profile_version`, but the worker still only marks jobs completed without reading or writing Word documents.

The document engine must fit the current local-first architecture, use the project-local `uv` environment, preserve editable DOCX as the primary output, and treat PDF as an optional delivery artifact produced by LibreOffice. It must avoid Agent-driven document mutation; Agents can be introduced later to help with uncertain rules or quality fixes.

## Goals / Non-Goals

**Goals:**

- Convert legacy `.doc` input to `.docx` before processing.
- Parse `.docx` files into a compact structure summary useful for diagnostics and tests.
- Apply selected profile settings to page layout, normal paragraphs, heading candidates, table borders, captions, equations, and references in a deterministic way.
- Register formatted DOCX and PDF output files as `FileRecord` entries and attach their ids to the job.
- Update worker status/progress/errors so formatting failures are diagnosable.
- Surface output file ids and file metadata in the frontend task panel.

**Non-Goals:**

- No Agent-driven title hierarchy inference.
- No full reference content correction, formula OCR, cover-page automation, TOC rebuild, or cross-reference rebuild.
- No independent quality report or Agent fix-loop in this change.
- No guarantee of perfect reflow for arbitrary malformed Word files; uncertain structure is conservatively preserved.

## Decisions

### Use python-docx plus selective OpenXML helpers

`python-docx` covers page margins, paragraph/run font defaults, line spacing, first-line indent, style creation, and common table edits. When a feature is not exposed directly, such as table border precision, add small OpenXML helper functions scoped to that feature.

Alternative considered: direct OpenXML for all edits. That gives maximal control but would slow MVP delivery and increase corruption risk.

### Keep conversion and PDF export behind a local LibreOffice adapter

`.doc` conversion and PDF export both depend on headless LibreOffice. A thin adapter should resolve `SOFFICE_BIN`, run conversion with explicit output directories, capture stderr/stdout, and return clear exceptions when missing or failing.

Alternative considered: rely on global wrapper commands only. The repository needs testable Python behavior and clear API error propagation, so the backend should own the adapter while still honoring local toolchain conventions.

### Register outputs as regular FileRecord entries

Generated DOCX and PDF files should be stored under the existing local storage root and registered through repository methods so frontend code can use the same file metadata shape. Output ids go into `JobRecord.output_file_ids`.

Alternative considered: add a separate output artifact table. That is more expressive but unnecessary for the current JSON repository and would complicate the API surface before quality reports exist.

### Make formatting worker deterministic and profile-required for real formatting

The worker should keep unprofiled jobs compatible as placeholder jobs, but jobs with a valid profile reference should run the formatting path. If a supplied profile reference is missing, job creation already rejects it; if files/tools fail during processing, the worker marks the job failed with a diagnostic error.

Alternative considered: silently format with the built-in profile when no profile is selected. That would obscure traceability and violate the plan requirement that jobs bind to a concrete profile version.

### Preserve content and apply conservative style heuristics

The formatter should not delete text or infer semantic changes. It can use existing paragraph styles and simple numbering/text patterns as heading candidates, apply body defaults to normal paragraphs, and style known caption/equation/reference paragraphs conservatively.

Alternative considered: aggressive restructuring. That belongs to later Agent/quality-loop changes because it requires confidence scoring and user confirmation.

## Risks / Trade-offs

- LibreOffice may be missing or fail on some `.doc` files -> fail the job with a clear `SOFFICE_BIN` or conversion diagnostic and keep the original upload.
- `python-docx` cannot express every Word feature -> use small OpenXML helpers only where required and keep unsupported features preserved rather than rewritten.
- Heuristic heading/caption detection can misclassify paragraphs -> prefer existing styles and conservative patterns; quality/Agent changes can flag unresolved cases later.
- JSON repository has limited concurrency -> acceptable for local MVP; output registration remains behind repository/storage methods for future database migration.
- PDF export is environment-sensitive -> tests should cover adapter failure and, when LibreOffice exists, integration smoke tests can run locally.

## Migration Plan

No database migration is required. Existing metadata without output file ids remains valid because `JobRecord.output_file_ids` already defaults to an empty list. Rollback is limited to removing the new document modules and reverting worker/API/frontend changes; uploaded inputs and generated output files can remain in local storage.

## Open Questions

- Whether later changes should add dedicated output artifact metadata beyond `FileRecord`.
- Whether table style requirements should grow from basic three-line borders into school-specific complex table templates.
