# Frontend

React + TypeScript + Vite workbench for the Word Format Agent. The current UI supports backend health, Word upload, Profile list/detail, structured Profile editing, YAML import/export, format job creation with an optional selected Profile version, and output metadata display for completed document jobs.

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
- The structured editor covers common fields: name, version, status, page margins, body font, line spacing, level-one heading font, table/figure caption positions, and quality flags.
- Saving writes a new Profile version through the backend. Duplicate version strings are rejected by the API and surfaced without clearing the draft.
- The YAML panel imports or exports full Profile definitions for advanced editing.
- The job panel sends the selected `profile_id + profile_version` when a Profile is selected; otherwise it creates an unprofiled compatibility job.

## Job and Output UI

- The task panel keeps uploaded file context visible while a job is being created or refreshed.
- It shows the selected profile reference used for new jobs and the persisted profile reference returned by the backend for existing jobs.
- When a completed job has `output_file_ids`, the UI calls `GET /api/files/{file_id}` for each output and displays output type, filename, size, MIME type, and file id.
- Output metadata failures are non-blocking: upload, profile editing, and job refresh remain usable while the task panel shows a partial metadata error.
- Failed jobs display `error_message` as a formatting diagnostic without hiding the input file or profile context.
