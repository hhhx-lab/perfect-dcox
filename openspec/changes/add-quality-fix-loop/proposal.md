## Why

Generating a formatted DOCX is not the same as proving it meets the requested thesis profile. Users explicitly worry that one-click formatting may be wrong, so the system needs an independent quality report and a user-confirmed Agent fix loop that explains failures instead of claiming everything is compliant.

## What Changes

- Add quality report records for formatted outputs with summary counts, issue severity, profile rule references, locations, recommendations, and report artifacts.
- Add DOCX quality checks for page margins, body paragraph style, heading style, basic three-line table rules, figure/table captions, raw LaTeX residue, and page-number presence or unsupported status.
- Add PDF quality checks for openability, page count, text extractability, and obvious blank-page warnings when a PDF output is available.
- Add Agent explanation and fix-plan models that convert warning/fail issues into user-readable explanations and structured, whitelisted fix actions.
- Add user-confirmed fix loop records that create a second-pass formatting/fix job and retain links to the original report and fix plan.
- Add backend API and frontend report views so users can inspect pass/fixed/warning/fail/unsupported groups, confirm fixable items, and avoid “all compliant” messaging when issues remain.
- Do not implement thesis semantic correction, reference truth verification, plagiarism/grammar checks, or automatic changes to formulas/reference substance.

## Capabilities

### New Capabilities

- `quality-reporting`: The system can independently inspect formatted DOCX/PDF outputs and generate structured quality reports.
- `agent-fix-planning`: The system can explain warning/fail quality issues and produce schema-valid whitelisted fix plans.
- `quality-fix-loop`: The system can run a user-confirmed second-pass fix workflow and preserve original/new report lineage.

### Modified Capabilities

- None. No archived OpenSpec specs exist for quality reporting or fix loops yet.

## Impact

- Adds backend quality models, repository records, inspection services, report generation, and API routes.
- Adds Agent fix-plan validation and deterministic fallback explanations when live LLM configuration is unavailable.
- Reuses existing `FileRecord`, `JobRecord`, `FormatProfile`, document parser/formatter, and output metadata.
- Extends frontend API types and UI with grouped quality report display, fix-plan review, and explicit remaining-issue summaries.
- Adds tests for DOCX/PDF report generation, severity grouping, unsupported handling, fix-plan validation, user confirmation gating, and frontend build.
- Updates documentation with quality report limits, Agent safety boundaries, and verification commands.
