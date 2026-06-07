# Frontend

React + TypeScript + Vite workbench for the Word Format Agent. The current UI supports backend health, Word upload, Profile list/detail, structured Profile editing, YAML import/export, and placeholder job creation with an optional selected Profile version.

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
- The job panel sends the selected `profile_id + profile_version` when a Profile is selected; otherwise it creates an unprofiled placeholder job.
