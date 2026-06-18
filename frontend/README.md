# Frontend

React + TypeScript + Vite workbench for Perfect DOCX. The UI is a direct four-step tool surface:

1. Create or select a Profile.
2. Bind an optional DOCX template.
3. Upload one or more source Word documents.
4. Export internally verified DOCX/PDF files.

The frontend does not generate DOCX/PDF locally and does not expose a quality report workflow in the primary product path. It sends configuration and files to the FastAPI backend, then renders export status, final downloads, or concise failure reasons.

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

## Main UI

- `frontend/src/App.tsx` owns the current workbench flow.
- `frontend/src/api/client.ts` defines the backend contracts, including Profile v2 fields, template ids, output formats, job delivery gate summaries, and batch delivery items.
- `frontend/src/styles.css` defines the responsive workbench layout.

## Product Flow

- Conversation entry calls `POST /api/requirement-sessions` with natural language requirements.
- Format document entry uploads `.doc/.docx`, then calls `POST /api/requirement-sessions` with the uploaded file id.
- Visual entry edits the same Profile v2 contract used by Agent-created drafts.
- Profile confirmation saves a named, versioned Profile through the backend.
- Template upload stores a DOCX file and passes its file id as `template_file_id` on export.
- Single export calls `POST /api/jobs`; batch export calls `POST /api/batches`.
- Final download links are shown only for `output_file_ids` or batch item final file ids returned by the backend.

## Validation

```bash
npm run build
```

Manual smoke should cover conversation intake, format-document intake, visual edits, template upload, source upload, single export, batch export, and final DOCX/PDF download.
