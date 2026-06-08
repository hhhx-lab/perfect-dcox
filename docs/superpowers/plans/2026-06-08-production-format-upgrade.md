# Production Format Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the system from a single-template, regex-like DOCX formatter into a multi-template document-formatting pipeline with profile-driven rules, quality checks, and a production-grade workflow UI.

**Architecture:** Agent extraction produces structured profile data; deterministic DOCX/PDF code applies and validates that profile. The first execution slice builds a template-neutral document role classifier, uses it in the formatter and quality checks, and reshapes the frontend into a four-step workflow that exposes the two Agent entry points clearly.

**Tech Stack:** FastAPI, Pydantic, python-docx, React, TypeScript, Vite, local JSON repository, LibreOffice PDF export.

---

### Task 1: Template-Neutral DOCX Structure Recognition

**Files:**
- Create: `backend/app/documents/structure.py`
- Modify: `backend/app/documents/formatter.py`
- Test: `backend/tests/test_document_formatting.py`

- [x] Add a paragraph role classifier that identifies TOC entries, abstract sections, keywords, numeric headings, reference sections, captions, equations, body text, and acknowledgement sections without checking a school/template name.
- [x] Replace formatter-wide state like `in_references=True` with classifier output so a TOC entry named `参考文献` cannot turn the rest of the document into reference style.
- [x] Restrict equation detection to OMML/raw math-like standalone paragraphs, not arbitrary hyphenated terms like `RISC-V` or URLs.
- [x] Add regression tests using a mixed document with a TOC, duplicated `摘要`, `RISC-V`, URL references, `表 1 给出...`, a real caption, and real references.

### Task 2: Quality Checks That Catch Bulk Misclassification

**Files:**
- Modify: `backend/app/quality/inspection.py`
- Test: `backend/tests/test_quality_reports.py`

- [x] Use the same classifier to select representative body, heading, caption, and reference paragraphs.
- [x] Add checks that detect body paragraphs accidentally styled as references, headings accidentally styled as body text, and non-caption prose accidentally centered as captions/equations.
- [x] Keep unsupported items visible; do not hide page-number or complex-TOC gaps.

### Task 3: Production Workflow Frontend

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [x] Replace loose module-first layout with a four-step workflow: `获取格式需求`, `确认 Profile`, `上传并处理`, `下载与质检`.
- [x] Put the two Agent entrances in a segmented/two-pane intake section: conversation rules and uploaded rules document.
- [x] Add clearer profile naming, selected profile, document upload, output downloads, quality gate, and fix-loop status areas.
- [x] Keep the UI dense and work-focused, with no marketing hero and no nested decorative cards.

### Task 4: Verification

**Files:**
- Modify tests only as needed.

- [x] Run `cd backend && uv run pytest -q`.
- [x] Run `cd frontend && npm run build`.
- [x] Run a DOCX smoke using the RISC-V sample and inspect the output for body/reference/heading regressions.
- [x] Use Playwright desktop/mobile screenshots to verify no major overlap or unusable controls.

### Task 5: Executable Fix Loop

**Files:**
- Create: `backend/app/quality/fix_execution.py`
- Modify: `backend/app/api/quality_reports.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Test: `backend/tests/test_quality_reports.py`

- [x] Add an endpoint that executes a confirmed fix-loop instead of only recording lineage.
- [x] Restrict execution to existing whitelisted formatting actions and reject non-executable loops.
- [x] Generate a second-pass `quality_fix` job, fixed DOCX/PDF outputs, and an updated quality report.
- [x] Update the frontend so selected fix actions execute and refresh the job/output/report state.
- [x] Verify through unit/API tests and an HTTP smoke where an original margin failure becomes a pass after execution.

### Task 6: Requirement Sessions and Reusable Profile Confirmation

**Files:**
- Create: `backend/app/agents/requirements.py`
- Create: `backend/app/api/requirement_sessions.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/storage/repository.py`
- Modify: `backend/app/main.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Test: `backend/tests/test_requirement_sessions_api.py`

- [x] Add a shared requirement session model for conversation and uploaded-format-document entrances.
- [x] Generate a structured requirement summary with extracted rules, missing fields, evidence, uncertain items, and a schema-valid Profile draft.
- [x] Support follow-up user messages so Agent questions and corrections can refine the profile draft before confirmation.
- [x] Confirm a session into a named, versioned, reusable Profile rather than silently saving an unreviewed draft.
- [x] Wire the frontend intake section to `requirement-sessions` and show rules, missing fields, evidence, follow-up input, and confirm/save controls.
- [x] Verify conversation and document session APIs through backend tests.

### Task 7: Batch Delivery Manifest and Report Downloads

**Files:**
- Modify: `backend/app/api/batches.py`
- Modify: `backend/app/api/quality_reports.py`
- Modify: `backend/app/storage/local.py`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`

- [x] Persist batch delivery manifests under `storage/manifests` and expose `GET /api/batches/{batch_id}/manifest`.
- [x] Mark jobs and batches as `quality_failed` when generated outputs still have warning/fail/unsupported quality issues.
- [x] Add quality report downloads for JSON and Markdown through `GET /api/quality-reports/{report_id}/download`.
- [x] Show manifest, DOCX, PDF, and report download buttons in the delivery section.
- [x] Keep fail-closed status visible in frontend badges.
