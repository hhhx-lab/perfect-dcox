## 1. Extraction Models and Storage

- [ ] 1.1 Add backend extraction result models for source metadata, evidence, uncertain items, profile drafts, status, and errors.
- [ ] 1.2 Extend the JSON metadata repository with profile extraction job creation, update, retrieval, and listing helpers.
- [ ] 1.3 Add tests for extraction job persistence, default empty collections, and failed result serialization.

## 2. Rule Source Processing

- [ ] 2.1 Implement rule source validation for uploaded `.doc/.docx` files and natural-language text.
- [ ] 2.2 Implement rule document text extraction that handles `.docx` directly and `.doc` through the configured LibreOffice conversion path.
- [ ] 2.3 Add tests for natural-language source creation, missing/unsupported file rejection, `.doc` conversion diagnostics, and `.docx` source text extraction.

## 3. Agent Extraction Service

- [ ] 3.1 Add a bounded LLM provider interface that reads `LLM_API_KEY` and `LLM_MODEL` from settings and supports deterministic fake providers in tests.
- [ ] 3.2 Implement Agent output parsing and validation for `profile_draft`, `uncertain_items`, and evidence.
- [ ] 3.3 Implement extraction orchestration that marks jobs completed, failed, or needs review with readable diagnostics.
- [ ] 3.4 Add Agent schema tests for valid output, invalid JSON/YAML, missing evidence, unknown fields, invalid enums, and missing LLM configuration.
- [ ] 3.5 Add ECNU sample extraction coverage confirming the required profile draft fields and uncertainty handling.

## 4. Extraction API

- [ ] 4.1 Add `POST /api/profile-extractions` to create document or natural-language extraction jobs.
- [ ] 4.2 Add `GET /api/profile-extractions/{job_id}` to retrieve queued/running/completed/failed extraction results.
- [ ] 4.3 Add API tests for successful job creation, completed result retrieval, failed result retrieval, validation errors, and profile draft schema failures.

## 5. Frontend Extraction Review

- [ ] 5.1 Extend frontend API types/client methods for profile extraction creation and result retrieval.
- [ ] 5.2 Add an extraction panel for rule document/natural-language submission, job refresh, result display, uncertain item review, and evidence display.
- [ ] 5.3 Connect extracted profile drafts to the existing profile editor/save flow without auto-activating unconfirmed drafts.
- [ ] 5.4 Add frontend build verification for extraction UI states, failure messages, and manual profile management coexistence.

## 6. Documentation and Verification

- [ ] 6.1 Update README, backend README, frontend README, and `.env.example` for Agent extraction configuration, safety boundaries, and verification commands.
- [ ] 6.2 Run OpenSpec validation, backend tests, frontend build, ECNU extraction smoke check, and hardcoded secret scan.
