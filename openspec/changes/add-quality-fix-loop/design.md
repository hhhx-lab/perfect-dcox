## Context

The current system can upload Word files, manage deterministic profiles, format DOCX outputs, register output metadata, and create bounded Agent extraction records. It still has no independent quality report. A completed formatting job can therefore look successful even when margins, paragraph styles, table borders, captions, formulas, PDF text extraction, or unsupported checks still need review.

No archived OpenSpec specs exist for quality reporting or fix loops, so this change introduces new behavior while reusing the document engine and Agent boundary already present in active changes.

## Goals / Non-Goals

**Goals:**

- Generate structured quality reports for formatted DOCX/PDF outputs independent of the formatting job success state.
- Classify checks as `pass`, `fixed`, `warning`, `fail`, or `unsupported`.
- Include summary counts, issue list, profile rule references, output locations, recommendations, and report lineage.
- Provide deterministic Agent-style explanations and schema-valid fix plans for warning/fail items.
- Require explicit user confirmation before any second-pass fix workflow runs.
- Show grouped quality results and remaining issue summaries in the frontend.

**Non-Goals:**

- No semantic editing of thesis content, formula meaning, or reference substance.
- No plagiarism, grammar, or factual reference validation.
- No guarantee that unsupported Word/PDF features can be judged.
- No live LLM-dependent fix plan requirement in MVP; deterministic fallback explanations are acceptable and safer.

## Decisions

### Store quality reports as repository records

Quality reports should be stored in the existing JSON metadata repository with IDs, related job/output/profile references, summary counts, issues, optional fix plan records, and timestamps. This mirrors current file/job/profile/extraction storage and keeps the local MVP migration-free.

Alternative considered: store Markdown-only report files. Structured records are required for grouped frontend display, fix planning, and regression tests.

### Keep quality checks independent from formatter success

The report service reads generated `FileRecord` outputs and the selected `FormatProfile`; it does not trust job status alone. A formatting job can be `completed` while the quality report still has warning/fail/unsupported items.

Alternative considered: mark all checks pass when formatting succeeds. That would violate the plan and hide risk.

### Implement deterministic MVP checks first

DOCX checks should use `python-docx` and narrow OpenXML helpers for currently implemented profile rules: page margins, body line spacing/indent/font, heading font, table border presence, captions, raw LaTeX residue, and page-number unsupported/presence status. PDF checks should use a lightweight local parser when available, with unsupported/fail status for unreadable or missing outputs.

Alternative considered: use a full Word/PDF rendering comparison engine. That is too heavy for the local MVP and would introduce fragile external dependencies.

### Treat Agent fix planning as schema validation plus whitelisted actions

Fix plans must be structured and limited to whitelisted actions such as `reapply_profile_formatting`, `apply_table_borders`, `apply_body_paragraph_style`, and `mark_manual_review`. Invalid actions, semantic edits, or unconfirmed execution are rejected.

Alternative considered: free-form Agent repair instructions. That would be unsafe and hard to test.

### Make second-pass fixes explicit and lineage-preserving

The user must confirm a fix plan before a fix job is created. The fix record should preserve the original report id, selected issue ids/actions, new job/output references when available, and updated report id after rerun.

Alternative considered: auto-run fixes immediately after a warning/fail report. That removes user control and can amplify mistakes.

## Risks / Trade-offs

- Some DOCX/PDF checks are heuristic -> mark uncertain checks `warning` or `unsupported` rather than `pass`.
- PDF tooling availability can vary -> report `unsupported` or `fail` with clear diagnostics instead of hiding the check.
- JSON repository concurrency remains limited -> acceptable for MVP, with isolated repository methods for future migration.
- Fix-loop scope can grow quickly -> start with whitelisted formatting actions and explicit user confirmation.

## Migration Plan

No database migration is required. Existing metadata files without quality report or fix loop collections remain valid because repository methods can default them to empty collections. Rollback removes quality routes/services/UI while preserving existing files, jobs, profiles, and extraction records.

## Open Questions

- Whether future production reports should be exported as Markdown/PDF artifacts in addition to JSON records.
- Whether quality checks should eventually run automatically from the document worker or remain a user-triggered/report API action.
