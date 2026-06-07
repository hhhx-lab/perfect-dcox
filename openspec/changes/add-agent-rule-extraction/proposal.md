## Why

Users can already hand-edit deterministic formatting profiles, but converting school formatting documents or natural-language requirements into a profile is still manual and error-prone. This change adds an Agent-assisted extraction flow that produces confirmable profile drafts with evidence and uncertainty instead of letting an LLM directly mutate DOCX output.

## What Changes

- Add profile extraction jobs that accept either a formatting rules `.doc/.docx` file or natural-language rule text.
- Add source text extraction for rules documents, reusing the local document toolchain and backend document modules where appropriate.
- Add a Rule Extraction Agent boundary that returns structured `profile_draft`, `uncertain_items`, and evidence, then validates the draft against the existing profile schema.
- Add backend storage/API support for extraction job lifecycle, result retrieval, and readable failures for invalid LLM output or missing configuration.
- Add frontend UI for creating extraction jobs, reviewing extracted fields/evidence/uncertainty, editing the draft, and saving it through the existing profile APIs.
- Do not let the Agent write final DOCX files, bypass the profile schema, silently use low-confidence defaults, or perform deep structure tagging of thesis content.

## Capabilities

### New Capabilities

- `rule-source-input`: The system can create profile extraction jobs from uploaded `.doc/.docx` rule documents or natural-language requirements.
- `agent-rule-extraction`: The system can run a bounded Agent that converts rule source text into schema-valid profile drafts with uncertainty and evidence.
- `profile-draft-confirmation`: The system can show extracted profile drafts, uncertain items, evidence, and allow user-confirmed saving.

### Modified Capabilities

- None. No archived OpenSpec specs exist for Agent rule extraction yet.

## Impact

- Adds backend extraction models, repository records, API routes, and worker/service logic for profile extraction jobs.
- Adds an LLM client boundary that reads `LLM_API_KEY` and `LLM_MODEL` from environment settings and can be replaced or faked in tests.
- Reuses uploaded `FileRecord` metadata and document conversion/text extraction for rules documents.
- Extends frontend API types and workbench UI with a profile extraction panel connected to existing profile save/import flows.
- Adds tests for source validation, schema validation, invalid Agent output, ECNU sample extraction, missing LLM config diagnostics, and frontend build coverage.
- Updates docs and `.env.example` to describe Agent extraction configuration and safe fallback behavior.
