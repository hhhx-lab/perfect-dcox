# Frontend

React + TypeScript + Vite workbench for the Word Format Agent. The current UI supports backend health, two Agent requirement entrances, separate rule-document and input-document uploads, Profile list/detail, structured Profile editing, YAML import/export, profile-backed single/batch format runs, DOCX/PDF/report downloads, grouped quality reports, and user-confirmed fix-loop execution.

## Install and Run

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

The frontend uses `VITE_API_BASE_URL` when provided. Without it, the API client points to:

```text
http://127.0.0.1:8000/api
```

## Build

```bash
npm run build
```

## Profile UI

- The Profile panel loads `GET /api/profiles` and displays name, status, current version, source, and update time.
- Selecting a Profile loads `GET /api/profiles/{profile_id}/versions/{version}` and shows core page/body metadata.
- The structured editor covers common fields: name, version, status, page size, orientation, page margins, body font, line spacing, first-line indent, body alignment, header text, header alignment, footer page-number toggle, footer alignment, and quality-relevant profile metadata.
- Saving writes a new Profile version through the backend. Duplicate version strings are rejected by the API and surfaced without clearing the draft.
- The YAML panel imports or exports full Profile definitions for advanced editing.
- The job panel sends the selected `profile_id + profile_version` when a Profile is selected; otherwise it creates an unprofiled compatibility job.

## Requirement Intake UI

- The first screen is a four-step workflow, not a landing page: `获取格式需求 -> 确认 Profile -> 上传并处理 -> 下载与质检`.
- Step 1 has two entrances:
  - `对话生成 Profile`: posts natural-language rules to `POST /api/requirement-sessions`.
  - `上传格式文档生成 Profile`: uploads a `.doc/.docx` rule document, then posts its `file_id` to `POST /api/requirement-sessions`.
- The Agent summary area displays session status, recent messages, extracted rules, missing fields, uncertain items, and evidence.
- Rules that were filled from safe profile defaults are tagged as `system_default` and visually marked as requiring confirmation, so users can distinguish evidence-backed extraction from editable defaults.
- Users can continue the conversation through `POST /api/requirement-sessions/{session_id}/messages`, then confirm name/version through `POST /api/requirement-sessions/{session_id}/confirm`.
- Confirmation saves a reusable Profile and selects it for later formatting. The user can still load the draft into the structured editor for manual adjustment.

## Job and Output UI

- The task panel keeps uploaded file context visible while a job is being created or refreshed.
- It shows the selected profile reference used for new jobs and the persisted profile reference returned by the backend for existing jobs.
- Users can upload one or more input Word files. `开始批量规范化` calls `POST /api/batches` with `auto_quality=true` and `auto_fix=true`; `仅处理第一份` keeps the single-job path for debugging.
- Batch results display one row per input document with DOCX/PDF download buttons, quality report downloads, delivery status, safe fix-loop ids when automatic repair ran, and a plain-language verdict such as `机器质检合规`, `自动修复后合规`, or `需要人工复核`. The batch manifest can be downloaded from `GET /api/batches/{batch_id}/manifest`.
- When a completed job has `output_file_ids`, the UI calls `GET /api/files/{file_id}` for each output and displays output type, filename, size, MIME type, and file id.
- Output metadata failures are non-blocking: upload, profile editing, and job refresh remain usable while the task panel shows a partial metadata error.
- Failed, `quality_failed`, `manual_review_required`, and `export_failed` jobs display `error_message` as a formatting diagnostic without hiding the input file or profile context.

## Quality Report UI

- The output section can create `POST /api/quality-reports` only when the job has both output file ids and a persisted `profile_id + profile_version`.
- The quality report panel displays report id, profile reference, output count, creation time, five status counters, and grouped issue details for `pass`, `fixed`, `warning`, `fail`, and `unsupported`.
- The remaining issue summary uses `summary.remaining_issue_count` and `summary.all_compliant`. It only shows `全部合规` when the backend summary has zero remaining warning/fail/unsupported items; otherwise it shows the remaining count and prompts review.
- Unsupported checks remain visible in their own group, so the UI does not hide toolchain limits behind a passing state.
- The capability panel summarizes what the system can automatically guarantee and highlights boundary checks such as TOC fields, notes, visual-caption pairing, field refresh, PDF text extractability, and blank-page risk.
- Report refresh calls `GET /api/quality-reports/{report_id}` and stays scoped to the current task panel.
- Report download buttons call `GET /api/quality-reports/{report_id}/download?format=json|markdown`.

## Fix-Loop UI

- The Agent fix-plan section appears inside an available quality report. `生成修复计划` calls `POST /api/quality-reports/{report_id}/fix-plan`.
- The UI displays deterministic explanations, impact text, manual review guidance, whitelisted actions, and manual-review issue ids.
- Viewing a plan does not execute repairs. The execution button stays disabled until the user selects at least one issue from the fixable action list.
- `执行所选修复` first calls `POST /api/quality-reports/{report_id}/fix-loops`, then calls `POST /api/quality-reports/{report_id}/fix-loops/{fix_loop_id}/execute`.
- After execution, the UI refreshes the new `quality_fix` job, shows the fixed output downloads, and switches the quality panel to the updated report returned by the backend.
