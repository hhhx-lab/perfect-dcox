## Why

The current product can extract basic rules, save v1 profiles, format a DOCX, optionally export PDF, and run visible quality/fix flows. In real thesis/report use, this is not stable enough: the Agent result is not a complete reusable schema, templates are not first-class, the formatter is still a direct best-effort pass, and generated files can be exposed before a closed internal verification gate proves they satisfy the supported rules.

This change upgrades the system into a production export pipeline where every rule source becomes a standard Profile v2 draft, every export goes through one deterministic compiler, optional DOCX templates can supply fixed pages and slots, and only internally verified final DOCX/PDF files are downloadable.

## What Changes

- Introduce Profile v2 fields for rule evidence, missing fields, unsupported rules, template binding, numbering/section rules, and delivery gate configuration while preserving compatibility with existing v1 profiles.
- Upgrade Agent requirement intake so conversation and uploaded format documents both require a live LLM, produce Profile v2 drafts, attach evidence, and fail clearly when analysis cannot be performed.
- Add a template-aware `FormatCompiler` export path that can bind optional DOCX templates, apply supported rules deterministically, generate a candidate DOCX, and pass it to the internal delivery gate before final file registration.
- Convert internal QC from a user-facing report/fix concept in the main export flow into a fail-closed delivery gate that validates formatting, template fit, DOCX health, and PDF export readiness before publishing downloads.
- Update job, batch, manifest, and frontend contracts so users see profile creation, template binding, export state, final downloads, and concise failure reasons rather than quality report artifacts.
- Redesign the frontend workbench around the four primary steps: create or select a Profile, bind a template, upload source documents, and download internally verified DOCX/PDF results.

## Capabilities

### New Capabilities

- `profile-v2`: The system can represent complete reusable formatting requirements, rule evidence, unsupported rules, template binding, and delivery gate settings in a single Profile v2 contract.
- `production-export-pipeline`: The system can transform a selected Profile and optional template into verified final DOCX/PDF outputs through a single compiler-driven path.
- `internal-qc-delivery-gate`: The system can block final downloads until supported formatting rules, template adaptation, DOCX health, and PDF readiness pass internal checks.
- `frontend-export-workbench`: The browser workbench can guide users through profile creation/selection, template binding, document upload, export progress, and final downloads.

### Modified Capabilities

- `agent-rule-extraction`: Conversation and document-based rule intake now targets Profile v2 drafts with evidence, missing fields, and unsupported rules, and remains fail-closed when the LLM cannot run.
- `document-output`: Output ids and batch manifests now represent internally verified final deliverables rather than best-effort formatted candidates plus visible quality artifacts.

## Impact

- Affects backend profile models, seed/import/export behavior, requirement sessions, document service/compiler, job and batch API models, quality internals, frontend API types, and workbench UI.
- Adds new backend document modules for compiler and template binding.
- Reuses existing `python-docx`, LibreOffice conversion/export, and local storage architecture.
- Keeps Agent responsibilities limited to rule understanding and explanation; Agents do not directly mutate DOCX.
- Requires tests for LLM fail-closed paths, Profile v2 compatibility, compiler output, internal QC blocking, batch manifest fields, and frontend build.

## Non-Goals

- Do not migrate local JSON metadata to PostgreSQL or queue processing to Redis in this change.
- Do not expose a downloadable QC or quality report product in the target export flow.
- Do not make browser-side JavaScript DOCX generation the authoritative export path.
- Do not rewrite thesis/report semantic content, auto-generate missing body text, or silently claim unsupported rules are compliant.
