## Why

The workbench can upload Word files and manage deterministic formatting profiles, but jobs still stop at a placeholder lifecycle. To make the product useful, the backend needs a deterministic document engine that converts legacy `.doc`, parses `.docx`, applies a selected profile, and registers DOCX/PDF outputs without letting an Agent directly rewrite content.

## What Changes

- Add document input handling for `.doc` to `.docx` conversion, `.docx` parsing, and structural summaries for paragraphs, tables, images/drawings, heading candidates, and basic styles.
- Add a profile-driven DOCX formatting engine that applies page settings, body paragraph settings, heading styles, table border rules, caption position conventions, equation paragraph alignment, and reference paragraph defaults.
- Add output generation and registration for formatted DOCX and optional PDF export through LibreOffice headless.
- Replace placeholder format job behavior for formatting jobs with a deterministic processing path that updates status, progress, output file ids, and diagnostic error messages.
- Update frontend task status display to expose DOCX/PDF outputs and formatting failures.
- Do not implement Agent-driven structure inference, full reference content correction, formula OCR, cover-page automation, or quality report/fix-loop behavior in this change.

## Capabilities

### New Capabilities

- `document-input`: The system can convert legacy `.doc` files to `.docx` when required and parse `.docx` files into a structured summary.
- `docx-formatting`: The system can apply selected profile rules to a DOCX while preserving document text content.
- `document-output`: The system can register formatted DOCX/PDF outputs and surface formatting job status, outputs, and errors through backend and frontend workflows.

### Modified Capabilities

- None. No archived OpenSpec specs exist for document formatting yet.

## Impact

- Adds backend document modules for conversion, parsing, formatting, and output export.
- Adds `python-docx` and PDF inspection/export dependencies only through the project-local `uv` environment.
- Extends local file storage/repository behavior to register generated output files.
- Extends worker/job processing so `placeholder_format` jobs with profile references can produce formatted outputs.
- Adds backend tests for conversion failure handling, DOCX parsing, profile application, output registration, and worker lifecycle.
- Updates frontend API/types and task UI to display `output_file_ids`, profile references, output metadata, and errors.
- Updates documentation with document engine runtime requirements and verification commands.
